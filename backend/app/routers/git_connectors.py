from fastapi import APIRouter, Response
from sqlalchemy import select

from app import git_connectors_helpers
from app.config import PRODUCTION_ENV, settings
from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound
from app.models import GitApp, GitHubApp
from app.models.base import generate_id
from app.schemas.git_connectors import GitAppSchema, SetupGithubAppRequest

router = APIRouter()


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
