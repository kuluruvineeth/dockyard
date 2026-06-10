from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app import git_connectors_helpers
from app.config import PRODUCTION_ENV, settings
from app.dependencies import CurrentUser, DBSession
from app.errors import BadRequest, NotFound
from app.models import (
    Deployment,
    Environment,
    GitApp,
    GitHubApp,
    GitlabApp,
    GitRepository,
    Service,
)
from app.models.base import generate_id
from app.schemas.git_connectors import (
    GitAppSchema,
    SetupGithubAppRequest,
    SetupGitlabAppRequest,
)
from app.services.deploy import build_service_snapshot
from app.temporal.client import schedule_deploy_docker_service

router = APIRouter()


async def _auto_deploy_service(db, service: Service, head_commit: dict | None):
    environment = (
        await db.execute(
            select(Environment).where(Environment.id == service.environment_id)
        )
    ).scalar_one()
    commit = head_commit or {}
    deployment = Deployment(
        id=generate_id("dpl_git_"),
        service_id=service.id,
        slot=Deployment.get_next_deployment_slot(service.latest_production_deployment),
        commit_message=commit.get("message", "auto deploy"),
        commit_sha=commit.get("id"),
        commit_author_name=(commit.get("author") or {}).get("name"),
        trigger_method="AUTO",
    )
    service.deployments.append(deployment)
    service.apply_pending_changes(deployment)
    deployment.service_snapshot = build_service_snapshot(service)
    await db.commit()
    await schedule_deploy_docker_service(db, service, environment, deployment)


async def _handle_push(db, data: dict, body: bytes, signature: str) -> Response:
    installation_id = data["installation"]["id"]
    git_app = (
        await db.execute(
            select(GitApp)
            .join(GitHubApp, GitApp.github_app_id == GitHubApp.id)
            .where(GitHubApp.installation_id == installation_id)
        )
    ).scalar_one_or_none()
    if git_app is None:
        raise NotFound(
            "This github app has not been registered in this Dockyard instance"
        )
    if not git_app.github.verify_signature(body, signature):
        raise BadRequest("Invalid webhook signature")

    ref = data.get("ref", "")
    # only branch pushes trigger deploys (ignore tags etc.)
    if ref.startswith("refs/heads/"):
        branch_name = ref.split("/")[-1]
        repository_url = f"https://github.com/{data['repository']['full_name']}.git"
        services = (
            (
                await db.execute(
                    select(Service).where(
                        Service.git_app_id == git_app.id,
                        Service.repository_url == repository_url,
                        Service.branch_name == branch_name,
                        Service.auto_deploy_enabled.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        head_commit = data.get("head_commit")
        for service in services:
            await _auto_deploy_service(db, service, head_commit)

    return Response(status_code=200)


def _map_repository(repository: dict) -> dict:
    owner, repo = repository["full_name"].split("/")
    return {
        "owner": owner,
        "repo": repo,
        "url": f"https://github.com/{owner}/{repo}",
        "private": repository["private"],
    }


async def add_repositories(db, github_app: GitHubApp, repos: list[dict]) -> None:
    existing_on_app = {r.url for r in github_app.repositories}
    for spec in repos:
        if spec["url"] in existing_on_app:
            continue
        result = await db.execute(
            select(GitRepository).where(GitRepository.url == spec["url"])
        )
        repo = result.scalar_one_or_none()
        if repo is None:
            repo = GitRepository(
                id=generate_id("repo_", 14),
                owner=spec["owner"],
                repo=spec["repo"],
                url=spec["url"],
                private=spec["private"],
            )
            db.add(repo)
        github_app.repositories.append(repo)
        existing_on_app.add(spec["url"])
    await db.commit()


@router.post("/api/connectors/github/setup/", status_code=303, response_class=Response)
async def setup_github_app(
    body: SetupGithubAppRequest, user: CurrentUser, db: DBSession
):
    state = body.state or ""

    if ":" in state:
        # installation callback: state = "install:<app_id>"
        _, app_id_str = state.split(":", 1)
        app_id = int(app_id_str)
        result = await db.execute(
            select(GitApp)
            .join(GitHubApp, GitApp.github_app_id == GitHubApp.id)
            .where(GitHubApp.app_id == app_id)
        )
        git_app = result.scalar_one_or_none()
        if git_app is None:
            raise NotFound(f"Github app with id {app_id} does not exist")
        git_app.github.installation_id = body.installation_id
        await db.commit()
    else:
        # manifest conversion: exchange the code for the app credentials
        data = git_connectors_helpers.fetch_github_app_manifest(body.code or "")
        result = await db.execute(
            select(GitHubApp).where(GitHubApp.app_id == data["id"])
        )
        github_app = result.scalar_one_or_none()
        if github_app is None:
            github_app = GitHubApp(
                id=generate_id("gh_app_", 14),
                app_id=data["id"],
                client_id=data["client_id"],
                client_secret=data["client_secret"],
                webhook_secret=data["webhook_secret"],
                app_url=data["html_url"],
                private_key=data["pem"],
                name=data["name"],
            )
            db.add(github_app)
            await db.flush()

        result = await db.execute(
            select(GitApp).where(GitApp.github_app_id == github_app.id)
        )
        git_app = result.scalar_one_or_none()
        if git_app is None:
            git_app = GitApp(
                id=generate_id("git_con_", 14), github_app_id=github_app.id
            )
            db.add(git_app)
        await db.commit()

    base_url = ""
    if settings.environment != PRODUCTION_ENV:
        base_url = "http://localhost:5173"
    return Response(
        status_code=303, headers={"Location": f"{base_url}/settings/git-apps"}
    )


@router.post("/api/connectors/gitlab/setup/", status_code=303, response_class=Response)
async def setup_gitlab_app(
    body: SetupGitlabAppRequest, user: CurrentUser, db: DBSession
):
    tokens = git_connectors_helpers.exchange_gitlab_oauth_code(
        body.gitlab_url, body.app_id, body.secret, body.redirect_uri, body.code
    )
    gitlab_app = GitlabApp(
        id=generate_id("gl_app_", 14),
        name=body.name,
        gitlab_url=body.gitlab_url,
        redirect_uri=body.redirect_uri,
        app_id=body.app_id,
        secret=body.secret,
        refresh_token=tokens["refresh_token"],
    )
    db.add(gitlab_app)
    await db.flush()
    git_app = GitApp(id=generate_id("git_con_", 14), gitlab_app_id=gitlab_app.id)
    db.add(git_app)
    await db.commit()

    base_url = ""
    if settings.environment != PRODUCTION_ENV:
        base_url = "http://localhost:5173"
    return Response(
        status_code=303, headers={"Location": f"{base_url}/settings/git-apps"}
    )


@router.get("/api/connectors/git-apps/", response_model=list[GitAppSchema])
async def list_git_apps(user: CurrentUser, db: DBSession):
    result = await db.execute(select(GitApp).order_by(GitApp.created_at.desc()))
    return [GitAppSchema.from_git_app(g) for g in result.scalars()]


@router.get("/api/connectors/git-apps/{git_app_id}/", response_model=GitAppSchema)
async def git_app_details(git_app_id: str, user: CurrentUser, db: DBSession):
    result = await db.execute(select(GitApp).where(GitApp.id == git_app_id))
    git_app = result.scalar_one_or_none()
    if git_app is None:
        raise NotFound(f"A git app with id `{git_app_id}` does not exist.")
    return GitAppSchema.from_git_app(git_app)


async def _get_app_or_404(db, app_id: int) -> GitHubApp:
    result = await db.execute(select(GitHubApp).where(GitHubApp.app_id == app_id))
    gh = result.scalar_one_or_none()
    if gh is None:
        raise NotFound(
            "This github app has not been registered in this Dockyard instance"
        )
    return gh


@router.post("/api/connectors/github/webhook/", response_class=Response)
async def github_webhook(request: Request, db: DBSession):
    body = await request.body()
    data = await request.json()
    event = request.headers.get("x-github-event")
    signature = request.headers.get("x-hub-signature-256") or ""

    if event == "push":
        return await _handle_push(db, data, body, signature)

    if event == "ping":
        gh = await _get_app_or_404(db, data["hook"]["app_id"])
    elif event in ("installation", "installation_repositories"):
        gh = await _get_app_or_404(db, data["installation"]["app_id"])
    else:
        return Response(status_code=200)

    if not gh.verify_signature(body, signature):
        raise BadRequest("Invalid webhook signature")

    if event == "installation":
        repos = [_map_repository(r) for r in data.get("repositories", [])]
        await add_repositories(db, gh, repos)
    elif event == "installation_repositories":
        added = [_map_repository(r) for r in data.get("repositories_added", [])]
        if added:
            await add_repositories(db, gh, added)
        removed_urls = {
            _map_repository(r)["url"] for r in data.get("repositories_removed", [])
        }
        if removed_urls:
            gh.repositories = [r for r in gh.repositories if r.url not in removed_urls]
            await db.commit()

    return Response(status_code=200)
