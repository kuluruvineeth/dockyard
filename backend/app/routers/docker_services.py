import logging
import secrets

import docker.errors
from faker import Faker
from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import docker_helpers
from app.dependencies import CurrentUser, DBSession
from app.docker_helpers import check_if_docker_image_exists
from app.errors import NotFound, ResourceConflict, ValidationException
from app.models import (
    ChangeField,
    ChangeType,
    Deployment,
    DeploymentChange,
    DeploymentStatus,
    Environment,
    Project,
    Service,
    ServiceMetrics,
    ServiceType,
    SharedRegistryCredentials,
)
from app.models.base import generate_id
from app.schemas.services import (
    DeploymentListResponse,
    DeploymentLogsResponse,
    DeploymentSchema,
    DockerServiceCreateRequest,
    ServiceCardSchema,
    ServiceChangeRequest,
    ServiceMetricsSchema,
    ServiceSchema,
    ServiceUpdateRequest,
    ToggleServiceRequest,
)
from app.services import metrics, proxy
from app.services.deploy import _healthcheck_snapshot, build_service_snapshot
from app.temporal.client import schedule_deploy_docker_service

RESERVED_PORTS = {80, 443}
CHANGE_TYPES = {"ADD", "UPDATE", "DELETE"}
ITEM_FIELDS = {
    "urls",
    "ports",
    "volumes",
    "env_variables",
    "configs",
    "shared_volumes",
}

router = APIRouter()
fake = Faker()
_logger = logging.getLogger("dockyard.docker_services")


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

    credentials = None
    if body.container_registry_credentials_id:
        result = await db.execute(
            select(SharedRegistryCredentials).where(
                SharedRegistryCredentials.id == body.container_registry_credentials_id,
                SharedRegistryCredentials.owner_id == user.id,
            )
        )
        registry = result.scalar_one_or_none()
        if registry is None:
            raise ValidationException(
                "container_registry_credentials_id",
                "invalid",
                "These registry credentials do not exist.",
            )
        credentials = {
            "username": registry.username,
            "password": registry.password,
        }

    if not check_if_docker_image_exists(body.image, credentials):
        raise ValidationException(
            "image",
            "invalid",
            f"The image `{body.image}` does not exist or could not be reached.",
        )

    slug = (body.slug or fake.slug() or "service").lower()
    # image lives in the staged SOURCE change, applied to the service at deploy time
    service = Service(
        id=generate_id("srv_dkr_"),
        slug=slug,
        project_id=project.id,
        environment_id=environment.id,
        type=ServiceType.DOCKER_REGISTRY.value,
        deploy_token=secrets.token_hex(16),
        container_registry_credentials_id=body.container_registry_credentials_id,
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
    "/api/projects/{project_slug}/{env_slug}/service-list/",
    response_model=list[ServiceCardSchema],
)
async def service_list(
    project_slug: str,
    env_slug: str,
    user: CurrentUser,
    db: DBSession,
    query: str | None = None,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)

    statement = select(Service).where(
        Service.project_id == project.id,
        Service.environment_id == environment.id,
    )
    if query:
        statement = statement.where(Service.slug.icontains(query))
    statement = statement.order_by(Service.updated_at.desc())

    services = (await db.execute(statement)).scalars().all()
    return [ServiceCardSchema.from_service(service) for service in services]


@router.get(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/",
    response_model=DeploymentListResponse,
)
async def deployment_list(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    result = await db.execute(
        select(Deployment)
        .where(Deployment.service_id == service.id)
        .order_by(Deployment.queued_at.desc())
    )
    deployments = result.scalars().all()
    return DeploymentListResponse(
        results=[DeploymentSchema.from_deployment(d) for d in deployments],
        count=len(deployments),
    )


@router.get(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/{deployment_hash}/",
    response_model=DeploymentSchema,
)
async def deployment_single(
    project_slug: str,
    env_slug: str,
    slug: str,
    deployment_hash: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    result = await db.execute(
        select(Deployment).where(Deployment.service_id == service.id)
    )
    deployment = next(
        (
            d
            for d in result.scalars()
            if d.unprefixed_hash == deployment_hash or d.id == deployment_hash
        ),
        None,
    )
    if deployment is None:
        raise NotFound(
            f"A deployment with the hash `{deployment_hash}` does not exist."
        )
    return DeploymentSchema.from_deployment(deployment)


@router.get(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/{deployment_hash}/metrics/",
    response_model=list[ServiceMetricsSchema],
)
async def deployment_metrics(
    project_slug: str,
    env_slug: str,
    slug: str,
    deployment_hash: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    result = await db.execute(
        select(Deployment).where(Deployment.service_id == service.id)
    )
    deployment = next(
        (
            d
            for d in result.scalars()
            if d.unprefixed_hash == deployment_hash or d.id == deployment_hash
        ),
        None,
    )
    if deployment is None:
        raise NotFound(
            f"A deployment with the hash `{deployment_hash}` does not exist."
        )

    try:
        sample = metrics.collect_deployment_metrics(service, deployment)
        if sample is not None:
            db.add(sample)
            await db.commit()
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not collect deployment metrics: %s", error)

    result = await db.execute(
        select(ServiceMetrics)
        .where(ServiceMetrics.deployment_id == deployment.id)
        .order_by(ServiceMetrics.created_at.desc())
        .limit(60)
    )
    rows = list(result.scalars().all())
    return [ServiceMetricsSchema.from_metrics(m) for m in reversed(rows)]


@router.get(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/{deployment_hash}/logs/",
    response_model=DeploymentLogsResponse,
)
async def deployment_logs(
    project_slug: str,
    env_slug: str,
    slug: str,
    deployment_hash: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    result = await db.execute(
        select(Deployment).where(Deployment.service_id == service.id)
    )
    deployment = next(
        (
            d
            for d in result.scalars()
            if d.unprefixed_hash == deployment_hash or d.id == deployment_hash
        ),
        None,
    )
    if deployment is None:
        raise NotFound(
            f"A deployment with the hash `{deployment_hash}` does not exist."
        )

    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )
    lines: list[str] = []
    try:
        swarm = client.services.get(swarm_name)
        for chunk in swarm.logs(stdout=True, stderr=True, tail=200):
            text = (
                chunk.decode("utf-8", errors="replace")
                if isinstance(chunk, bytes)
                else str(chunk)
            )
            lines.extend(line for line in text.splitlines() if line)
    except docker.errors.NotFound:
        pass
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not read deployment logs: %s", error)

    return DeploymentLogsResponse(logs=lines[-500:])


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


@router.put(
    "/api/projects/{project_slug}/{env_slug}/deploy-service/docker/{slug}/",
    response_model=DeploymentSchema,
)
async def deploy_docker_service_view(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    slot = Deployment.get_next_deployment_slot(service.latest_production_deployment)
    deployment = Deployment(
        id=generate_id("dpl_dkr_"),
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
    "/api/projects/{project_slug}/{env_slug}/redeploy-service/docker/{slug}/{deployment_hash}/",
    response_model=DeploymentSchema,
)
async def redeploy_docker_service(
    project_slug: str,
    env_slug: str,
    slug: str,
    deployment_hash: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    result = await db.execute(
        select(Deployment).where(Deployment.service_id == service.id)
    )
    target = next(
        (
            d
            for d in result.scalars()
            if d.unprefixed_hash == deployment_hash or d.id == deployment_hash
        ),
        None,
    )
    if target is None:
        raise NotFound(
            f"A deployment with the hash `{deployment_hash}` does not exist."
        )

    snapshot = target.service_snapshot or {}

    snapshot_image = snapshot.get("image")
    if snapshot_image is not None and snapshot_image != service.image:
        service.add_change(
            DeploymentChange(
                type=ChangeType.UPDATE.value,
                field=ChangeField.SOURCE.value,
                new_value={"image": snapshot_image},
                old_value={"image": service.image},
            )
        )
    snapshot_command = snapshot.get("command")
    if snapshot_command != service.command:
        service.add_change(
            DeploymentChange(
                type=ChangeType.UPDATE.value,
                field=ChangeField.COMMAND.value,
                new_value=snapshot_command,
                old_value=service.command,
            )
        )

    snapshot_resource_limits = snapshot.get("resource_limits")
    if snapshot_resource_limits != service.resource_limits:
        service.add_change(
            DeploymentChange(
                type=ChangeType.UPDATE.value,
                field=ChangeField.RESOURCE_LIMITS.value,
                new_value=snapshot_resource_limits,
                old_value=service.resource_limits,
            )
        )

    snapshot_healthcheck = snapshot.get("healthcheck")
    current_healthcheck = _healthcheck_snapshot(service.healthcheck)
    if snapshot_healthcheck != current_healthcheck:
        service.add_change(
            DeploymentChange(
                type=ChangeType.UPDATE.value,
                field=ChangeField.HEALTHCHECK.value,
                new_value=snapshot_healthcheck,
                old_value=current_healthcheck,
            )
        )

    slot = Deployment.get_next_deployment_slot(service.latest_production_deployment)
    deployment = Deployment(
        id=generate_id("dpl_dkr_"),
        service_id=service.id,
        slot=slot,
        commit_message="redeploy",
        is_redeploy_of_id=target.id,
    )
    service.deployments.append(deployment)
    service.apply_pending_changes(deployment)
    deployment.service_snapshot = build_service_snapshot(service)
    await db.commit()

    await schedule_deploy_docker_service(db, service, environment, deployment)

    await db.refresh(deployment, ["queued_at"])
    return DeploymentSchema.from_deployment(deployment)


@router.delete(
    "/api/projects/{project_slug}/{env_slug}/archive-service/docker/{slug}/",
    status_code=204,
)
async def archive_docker_service(
    project_slug: str, env_slug: str, slug: str, user: CurrentUser, db: DBSession
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    client = docker_helpers.get_docker_client()
    for deployment in service.deployments:
        swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
            deployment.unprefixed_hash, service.project_id, service.id
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

    await db.delete(service)
    await db.commit()
    return Response(status_code=204)


@router.put(
    "/api/projects/{project_slug}/{env_slug}/toggle-service/docker/{slug}/",
    response_model=DeploymentSchema,
)
async def toggle_service(
    project_slug: str,
    env_slug: str,
    slug: str,
    body: ToggleServiceRequest,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    deployment = service.latest_production_deployment
    if deployment is None:
        raise ResourceConflict(
            "This service has no current production deployment to toggle."
        )

    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )
    try:
        swarm = client.services.get(swarm_name)
    except docker.errors.NotFound:
        raise NotFound("The deployment's swarm service does not exist.")

    if body.desired_state == "stop":
        swarm.scale(0)
        deployment.status = DeploymentStatus.SLEEPING.value
    else:
        swarm.scale(1)
        deployment.status = DeploymentStatus.HEALTHY.value

    await db.commit()
    await db.refresh(deployment, ["queued_at"])
    return DeploymentSchema.from_deployment(deployment)


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


def _find(collection, item_id):
    if item_id is None:
        return None
    return next((i for i in collection if i.id == item_id), None)


def _validate_change_and_old_value(service, field, ctype, item_id, new_value):
    nv = new_value if isinstance(new_value, dict) else {}

    if field == ChangeField.COMMAND.value:
        return service.command
    if field == ChangeField.RESOURCE_LIMITS.value:
        return service.resource_limits
    if field == ChangeField.SOURCE.value:
        if not nv.get("image"):
            raise ValidationException("new_value", "required", "An image is required.")
        return {"image": service.image, "credentials": service.credentials}
    if field == ChangeField.HEALTHCHECK.value:
        h = service.healthcheck
        if h is None:
            return None
        return {
            "type": h.type,
            "value": h.value,
            "interval_seconds": h.interval_seconds,
            "timeout_seconds": h.timeout_seconds,
            "associated_port": h.associated_port,
        }
    if field == ChangeField.PORTS.value:
        if ctype in ("ADD", "UPDATE"):
            host = nv.get("host", 80)
            if host in RESERVED_PORTS:
                raise ValidationException(
                    "new_value", "invalid", "Ports 80 and 443 are reserved."
                )
            if not nv.get("forwarded"):
                raise ValidationException(
                    "new_value", "required", "A forwarded port is required."
                )
            for port in service.ports:
                if port.host == host and port.id != item_id:
                    raise ValidationException(
                        "new_value", "invalid", f"Host port {host} is already used."
                    )
        item = _find(service.ports, item_id)
        return {"host": item.host, "forwarded": item.forwarded} if item else None
    if field == ChangeField.URLS.value:
        if ctype in ("ADD", "UPDATE"):
            domain = nv.get("domain")
            base_path = nv.get("base_path", "/")
            if not domain:
                raise ValidationException(
                    "new_value", "required", "A domain is required."
                )
            for url in service.urls:
                if (
                    url.domain == domain
                    and url.base_path == base_path
                    and url.id != item_id
                ):
                    raise ValidationException(
                        "new_value", "invalid", "This URL is already in use."
                    )
        item = _find(service.urls, item_id)
        return {"domain": item.domain, "base_path": item.base_path} if item else None
    if field == ChangeField.ENV_VARIABLES.value:
        if ctype in ("ADD", "UPDATE"):
            key = nv.get("key")
            if not key:
                raise ValidationException("new_value", "required", "A key is required.")
            for env in service.env_variables:
                if env.key == key and env.id != item_id:
                    raise ValidationException(
                        "new_value", "invalid", f"The variable `{key}` already exists."
                    )
        item = _find(service.env_variables, item_id)
        return {"key": item.key, "value": item.value} if item else None
    if field == ChangeField.VOLUMES.value:
        if ctype in ("ADD", "UPDATE"):
            container_path = nv.get("container_path")
            if not container_path:
                raise ValidationException(
                    "new_value", "required", "A container path is required."
                )
            for volume in service.volumes:
                if volume.container_path == container_path and volume.id != item_id:
                    raise ValidationException(
                        "new_value",
                        "invalid",
                        f"The mount point `{container_path}` is already used.",
                    )
        item = _find(service.volumes, item_id)
        return (
            {
                "name": item.name,
                "mode": item.mode,
                "container_path": item.container_path,
                "host_path": item.host_path,
            }
            if item
            else None
        )
    if field == ChangeField.CONFIGS.value:
        if ctype in ("ADD", "UPDATE"):
            mount_path = nv.get("mount_path")
            if not mount_path:
                raise ValidationException(
                    "new_value", "required", "A mount path is required."
                )
            for config in service.configs:
                if config.mount_path == mount_path and config.id != item_id:
                    raise ValidationException(
                        "new_value",
                        "invalid",
                        f"The mount path `{mount_path}` is already used.",
                    )
        item = _find(service.configs, item_id)
        return (
            {
                "name": item.name,
                "mount_path": item.mount_path,
                "contents": item.contents,
            }
            if item
            else None
        )
    return None


@router.put(
    "/api/projects/{project_slug}/{env_slug}/request-service-changes/{slug}/",
    response_model=ServiceSchema,
)
async def request_service_changes(
    project_slug: str,
    env_slug: str,
    slug: str,
    body: ServiceChangeRequest,
    user: CurrentUser,
    db: DBSession,
):
    if body.field not in {f.value for f in ChangeField}:
        raise ValidationException(
            "field", "invalid", f"`{body.field}` is not a valid field."
        )
    if body.type not in CHANGE_TYPES:
        raise ValidationException(
            "type", "invalid", f"`{body.type}` is not a valid change type."
        )
    if (
        body.field in ITEM_FIELDS
        and body.type in ("UPDATE", "DELETE")
        and not body.item_id
    ):
        raise ValidationException(
            "item_id", "required", "An item_id is required for UPDATE and DELETE."
        )

    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    new_value = body.new_value
    if (
        body.field == ChangeField.RESOURCE_LIMITS.value
        and isinstance(new_value, dict)
        and not new_value
    ):
        new_value = None

    old_value = _validate_change_and_old_value(
        service, body.field, body.type, body.item_id, new_value
    )

    if new_value != old_value or body.type == "DELETE":
        service.add_change(
            DeploymentChange(
                type=body.type,
                field=body.field,
                item_id=body.item_id,
                new_value=new_value,
                old_value=old_value,
            )
        )
        await db.commit()
        await db.refresh(service, ["updated_at"])

    return ServiceSchema.from_service(service)


@router.delete(
    "/api/projects/{project_slug}/{env_slug}/cancel-service-changes/{slug}/{change_id}/",
    status_code=204,
)
async def cancel_service_changes(
    project_slug: str,
    env_slug: str,
    slug: str,
    change_id: str,
    user: CurrentUser,
    db: DBSession,
):
    project = await get_project_or_404(db, user, project_slug)
    environment = await get_environment_or_404(db, project, env_slug)
    service = await get_service_or_404(db, project, environment, slug)

    change = _find(service.unapplied_changes, change_id)
    if change is None:
        raise NotFound(f"A pending change with the id `{change_id}` does not exist.")

    if change.field == ChangeField.SOURCE.value and service.image is None:
        raise ResourceConflict(
            "Cannot cancel this change: the service would be left without an image."
        )

    service.changes.remove(change)
    await db.commit()
    return Response(status_code=204)
