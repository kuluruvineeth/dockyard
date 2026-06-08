import secrets

from faker import Faker
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DBSession
from app.docker_helpers import check_if_docker_image_exists
from app.errors import NotFound, ResourceConflict, ValidationException
from app.models import (
    ChangeField,
    ChangeType,
    DeploymentChange,
    Environment,
    Project,
    Service,
    ServiceType,
)
from app.models.base import generate_id
from app.schemas.services import (
    DockerServiceCreateRequest,
    ServiceSchema,
    ServiceUpdateRequest,
)

router = APIRouter()
fake = Faker()


async def get_project_or_404(db, user, slug: str) -> Project:
    result = await db.execute(
        select(Project).where(Project.slug == slug, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFound(f"A project with the slug `{slug}` does not exist.")
    return project


async def get_environment_or_404(db, project: Project, env_slug: str) -> Environment:
    result = await db.execute(
        select(Environment).where(
            Environment.project_id == project.id,
            Environment.name == env_slug.lower(),
        )
    )
    environment = result.scalar_one_or_none()
    if environment is None:
        raise NotFound(
            f"An environment with the name `{env_slug}` does not exist in this project."
        )
    return environment


@router.post(
    "/api/projects/{project_slug}/{env_slug}/create-service/docker/",
    status_code=201,
    response_model=ServiceSchema,
)
async def create_docker_service(
    project_slug: str,
    env_slug: str,
    body: DockerServiceCreateRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)

    if not check_if_docker_image_exists(body.image):
        raise ValidationException(
            "image",
            "invalid",
            f"The image `{body.image}` does not exist or could not be reached.",
        )

    slug = (body.slug or fake.slug() or "service").lower()
    service = Service(
        id=generate_id("srv_dkr_"),
        slug=slug,
        project_id=project.id,
        environment_id=environment.id,
        image=body.image,
        type=ServiceType.DOCKER_REGISTRY.value,
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
            field=ChangeField.SOURCE.value,
            new_value={"image": body.image},
        )
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


async def get_service_or_404(
    db, project: Project, environment: Environment, slug: str
) -> Service:
    result = await db.execute(
        select(Service).where(
            Service.project_id == project.id,
            Service.environment_id == environment.id,
            Service.slug == slug,
        )
    )
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFound(
            f"A service with the slug `{slug}` does not exist in this environment."
        )
    return service


@router.get(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/",
    response_model=ServiceSchema,
)
async def get_service(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)
    return ServiceSchema.from_service(service)


@router.patch(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/",
    response_model=ServiceSchema,
)
async def update_service(
    project_slug: str,
    env_slug: str,
    slug: str,
    body: ServiceUpdateRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    service.slug = body.slug.lower()
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"The slug `{body.slug}` is already used by another service."
        )

    await db.refresh(service, ["updated_at"])
    return ServiceSchema.from_service(service)
