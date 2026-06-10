import secrets

from faker import Faker
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import git_helpers
from app.dependencies import CurrentUser, DBSession
from app.errors import ResourceConflict, ValidationException
from app.models import (
    ChangeField,
    ChangeType,
    Deployment,
    DeploymentChange,
    GitApp,
    Service,
    ServiceType,
    WorkspaceRole,
)
from app.models.base import generate_id
from app.routers.docker_services import (
    get_environment_or_404,
    get_project_or_404,
    get_service_or_404,
)
from app.schemas.services import (
    DeploymentSchema,
    GitServiceCreateRequest,
    ServiceSchema,
)
from app.services.deploy import build_service_snapshot
from app.services.workspaces import require_project_role
from app.temporal.client import schedule_deploy_docker_service

router = APIRouter()
fake = Faker()


class AutoDeployRequest(BaseModel):
    enabled: bool


BUILDER_OPTION_FIELDS = {
    "DOCKERFILE": "dockerfile_builder_options",
    "STATIC_DIR": "static_dir_builder_options",
    "NIXPACKS": "nixpacks_builder_options",
    "RAILPACK": "railpack_builder_options",
}


@router.post(
    "/api/projects/{project_slug}/{env_slug}/create-service/git/",
    status_code=201,
    response_model=ServiceSchema,
)
async def create_git_service(
    project_slug: str,
    env_slug: str,
    body: GitServiceCreateRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    await require_project_role(db, user, project, WorkspaceRole.MEMBER)
    environment = await get_environment_or_404(db, project, env_slug)

    if body.builder not in BUILDER_OPTION_FIELDS:
        raise ValidationException(
            "builder", "invalid", f"`{body.builder}` is not a valid builder."
        )

    if not git_helpers.check_if_git_repository_exists(
        body.repository_url, body.branch_name
    ):
        raise ValidationException(
            "repository_url",
            "invalid",
            f"The repository `{body.repository_url}` (branch `{body.branch_name}`)"
            " does not exist or could not be reached.",
        )

    if body.git_app_id is not None:
        result = await db.execute(select(GitApp).where(GitApp.id == body.git_app_id))
        if result.scalar_one_or_none() is None:
            raise ValidationException(
                "git_app_id",
                "invalid",
                "This git app connection does not exist.",
            )

    git_source = {
        "repository_url": body.repository_url,
        "branch_name": body.branch_name,
    }
    if body.git_app_id is not None:
        git_source["git_app_id"] = body.git_app_id

    slug = (body.slug or fake.slug() or "service").lower()
    # git source + builder live in staged changes, applied at deploy time
    service = Service(
        id=generate_id("srv_git_"),
        slug=slug,
        project_id=project.id,
        environment_id=environment.id,
        type=ServiceType.GIT_REPOSITORY.value,
        deploy_token=secrets.token_hex(16),
    )
    service.network_alias = Service.generate_network_alias(service)
    service.urls = []
    service.ports = []
    service.configs = []
    service.volumes = []
    service.env_variables = []
    service.changes = [
        DeploymentChange(
            type=ChangeType.UPDATE.value,
            field=ChangeField.GIT_SOURCE.value,
            new_value=git_source,
        ),
        DeploymentChange(
            type=ChangeType.UPDATE.value,
            field=ChangeField.BUILDER.value,
            new_value={
                "builder": body.builder,
                "options": {"dockerfile_path": body.dockerfile_path},
            },
        ),
    ]
    db.add(service)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"A service with the slug `{slug}` already exists in this environment."
        )

    await db.refresh(service, ["created_at", "updated_at"])
    return ServiceSchema.from_service(service)


@router.put(
    "/api/projects/{project_slug}/{env_slug}/deploy-service/git/{slug}/",
    response_model=DeploymentSchema,
)
async def deploy_git_service_view(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    await require_project_role(db, user, project, WorkspaceRole.MEMBER)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    slot = Deployment.get_next_deployment_slot(service.latest_production_deployment)
    deployment = Deployment(
        id=generate_id("dpl_git_"),
        service_id=service.id,
        slot=slot,
        commit_message="update service",
    )
    service.deployments.append(deployment)
    service.apply_pending_changes(deployment)
    deployment.service_snapshot = build_service_snapshot(service)
    await db.commit()

    await schedule_deploy_docker_service(db, service, environment, deployment)

    await db.refresh(deployment, ["queued_at"])
    return DeploymentSchema.from_deployment(deployment)


@router.put(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/toggle-auto-deploy/",
    response_model=ServiceSchema,
)
async def toggle_auto_deploy(
    project_slug: str,
    env_slug: str,
    slug: str,
    body: AutoDeployRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    await require_project_role(db, user, project, WorkspaceRole.MEMBER)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    service.auto_deploy_enabled = body.enabled
    response = ServiceSchema.from_service(service)
    await db.commit()
    return response
