import secrets

from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DBSession
from app.errors import ResourceConflict, ValidationException
from app.models import (
    ChangeField,
    ChangeType,
    ComposeStack,
    DeploymentChange,
    Service,
    ServiceType,
)
from app.models.base import generate_id
from app.routers.docker_services import (
    get_environment_or_404,
    get_project_or_404,
)
from app.schemas.compose import ComposeStackSchema, CreateComposeStackRequest
from app.services import compose_processor

router = APIRouter()


@router.post(
    "/api/projects/{project_slug}/{env_slug}/create-compose-stack/",
    status_code=201,
    response_model=ComposeStackSchema,
)
async def create_compose_stack(
    project_slug: str,
    env_slug: str,
    body: CreateComposeStackRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)

    parsed = compose_processor.parse_compose(body.contents)
    deployable = {name: spec for name, spec in parsed.items() if spec.get("image")}
    if not deployable:
        raise ValidationException(
            "contents",
            "invalid",
            "No deployable services (with an `image`) found in the compose file.",
        )

    slug = body.slug.lower()
    stack = ComposeStack(
        id=generate_id("compose_stk_", 15),
        slug=slug,
        network_alias_prefix=slug,
        project_id=project.id,
        environment_id=environment.id,
        deploy_token=secrets.token_hex(16)[:35],
        user_content=body.contents,
    )
    stack.services = []

    for name, spec in deployable.items():
        service = Service(
            id=generate_id("srv_dkr_"),
            slug=f"{slug}-{name}".lower(),
            project_id=project.id,
            environment_id=environment.id,
            type=ServiceType.DOCKER_REGISTRY.value,
            deploy_token=secrets.token_hex(16),
        )
        service.network_alias = Service.generate_network_alias(service)
        service.urls = []
        service.ports = []
        service.configs = []
        service.volumes = []
        service.env_variables = []

        changes = [
            DeploymentChange(
                type=ChangeType.UPDATE.value,
                field=ChangeField.SOURCE.value,
                new_value={"image": spec["image"]},
            )
        ]
        if spec.get("command"):
            changes.append(
                DeploymentChange(
                    type=ChangeType.UPDATE.value,
                    field=ChangeField.COMMAND.value,
                    new_value=spec["command"],
                )
            )
        for port in spec.get("ports", []):
            changes.append(
                DeploymentChange(
                    type=ChangeType.ADD.value,
                    field=ChangeField.PORTS.value,
                    new_value=port,
                )
            )
        for key, value in spec.get("environment", {}).items():
            changes.append(
                DeploymentChange(
                    type=ChangeType.ADD.value,
                    field=ChangeField.ENV_VARIABLES.value,
                    new_value={"key": key, "value": value},
                )
            )
        service.changes = changes
        stack.services.append(service)

    db.add(stack)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"A compose stack with the slug `{slug}` already exists in this environment."
        )

    await db.refresh(stack, ["created_at"])
    return ComposeStackSchema.from_stack(stack)
