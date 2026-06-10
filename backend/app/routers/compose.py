import secrets

import docker.errors
from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import docker_helpers
from app.dependencies import CurrentUser, DBSession
from app.errors import NotFound, ResourceConflict, ValidationException
from app.models import (
    ChangeField,
    ChangeType,
    ComposeStack,
    Deployment,
    DeploymentChange,
    Service,
    ServiceType,
    WorkspaceRole,
)
from app.models.base import generate_id
from app.routers.docker_services import (
    get_environment_or_404,
    get_project_or_404,
)
from app.schemas.compose import ComposeStackSchema, CreateComposeStackRequest
from app.services import compose_processor, proxy
from app.services.deploy import build_service_snapshot
from app.temporal.client import schedule_deploy_docker_service

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
    project = await get_project_or_404(
        db, user, project_slug, min_role=WorkspaceRole.MEMBER
    )
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


async def _get_stack_or_404(db, project, environment, slug):
    result = await db.execute(
        select(ComposeStack).where(
            ComposeStack.project_id == project.id,
            ComposeStack.environment_id == environment.id,
            ComposeStack.slug == slug.lower(),
        )
    )
    stack = result.scalar_one_or_none()
    if stack is None:
        raise NotFound(f"A compose stack with the slug `{slug}` does not exist.")
    return stack


@router.get(
    "/api/projects/{project_slug}/{env_slug}/compose-stacks/",
    response_model=list[ComposeStackSchema],
)
async def list_compose_stacks(
    project_slug: str, env_slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    result = await db.execute(
        select(ComposeStack)
        .where(
            ComposeStack.project_id == project.id,
            ComposeStack.environment_id == environment.id,
        )
        .order_by(ComposeStack.created_at.desc())
    )
    return [ComposeStackSchema.from_stack(s) for s in result.scalars()]


@router.put(
    "/api/projects/{project_slug}/{env_slug}/deploy-compose-stack/{slug}/",
    response_model=ComposeStackSchema,
)
async def deploy_compose_stack(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(
        db, user, project_slug, min_role=WorkspaceRole.MEMBER
    )
    environment = await get_environment_or_404(db, project, env_slug)
    stack = await _get_stack_or_404(db, project, environment, slug)

    pairs = []
    for service in stack.services:
        deployment = Deployment(
            id=generate_id("dpl_dkr_"),
            service_id=service.id,
            slot=Deployment.get_next_deployment_slot(
                service.latest_production_deployment
            ),
            commit_message="deploy compose stack",
        )
        service.deployments.append(deployment)
        service.apply_pending_changes(deployment)
        deployment.service_snapshot = build_service_snapshot(service)
        pairs.append((service, deployment))

    await db.commit()

    for service, deployment in pairs:
        await schedule_deploy_docker_service(db, service, environment, deployment)

    return ComposeStackSchema.from_stack(stack)


@router.delete(
    "/api/projects/{project_slug}/{env_slug}/compose-stack/{slug}/",
    status_code=204,
)
async def archive_compose_stack(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(
        db, user, project_slug, min_role=WorkspaceRole.MEMBER
    )
    environment = await get_environment_or_404(db, project, env_slug)
    stack = await _get_stack_or_404(db, project, environment, slug)

    client = docker_helpers.get_docker_client()
    for service in stack.services:
        for deployment in service.deployments:
            swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
                deployment.unprefixed_hash, project.id, service.id
            )
            try:
                client.services.get(swarm_name).remove()
            except docker.errors.NotFound:
                pass
            except Exception:  # noqa: BLE001
                pass
        try:
            proxy.unexpose_service_from_http(service)
        except Exception:  # noqa: BLE001
            pass

    await db.delete(stack)
    await db.commit()
    return Response(status_code=204)
