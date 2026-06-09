import logging
import tempfile
import time
from time import monotonic

import docker.errors
from docker.types import (
    ConfigReference,
    EndpointSpec,
    Healthcheck,
    NetworkAttachmentConfig,
    RestartPolicy,
)

from app import docker_helpers
from app.config import settings
from app.models import DeploymentStatus
from app.models.healthcheck import HealthCheck, HealthCheckType
from app.services import git_build, proxy
from app.session import now

_logger = logging.getLogger("dockyard.deploy")

MAX_SERVICE_RESTART_COUNT = 3
HEALTHCHECK_INTERVAL_SECONDS = 2
RETAINED_SUPERSEDED_DEPLOYMENTS = 1
RESTART_DELAY_SECONDS = 5
RESTART_WINDOW_SECONDS = 600
NANOSECONDS_PER_SECOND = 1_000_000_000

ACCESS_MODE_MAP = {"READ_WRITE": "rw", "READ_ONLY": "ro"}


def _healthcheck_snapshot(healthcheck) -> dict | None:
    if healthcheck is None:
        return None
    return {
        "type": healthcheck.type,
        "value": healthcheck.value,
        "interval_seconds": healthcheck.interval_seconds,
        "timeout_seconds": healthcheck.timeout_seconds,
        "associated_port": healthcheck.associated_port,
    }


def build_service_snapshot(service) -> dict:
    return {
        "image": service.image,
        "command": service.command,
        "healthcheck": _healthcheck_snapshot(service.healthcheck),
        "resource_limits": service.resource_limits,
        "urls": [
            {
                "domain": u.domain,
                "base_path": u.base_path,
                "strip_prefix": u.strip_prefix,
                "redirect_to": u.redirect_to,
                "associated_port": u.associated_port,
            }
            for u in service.urls
        ],
        "ports": [{"host": p.host, "forwarded": p.forwarded} for p in service.ports],
        "env_variables": [
            {"key": e.key, "value": e.value} for e in service.env_variables
        ],
        "volumes": [
            {
                "name": v.name,
                "mode": v.mode,
                "container_path": v.container_path,
                "host_path": v.host_path,
            }
            for v in service.volumes
        ],
        "configs": [
            {
                "name": c.name,
                "mount_path": c.mount_path,
                "contents": c.contents,
                "language": c.language,
            }
            for c in service.configs
        ],
    }


def build_git_image(service, deployment) -> str:
    image_tag = (
        f"dky-build-{service.id.rsplit('_', 1)[-1]}:{deployment.unprefixed_hash}"
    )
    options = service.dockerfile_builder_options or {}
    dockerfile_path = options.get("dockerfile_path", "./Dockerfile")
    with tempfile.TemporaryDirectory() as build_dir:
        head_sha = git_build.clone_git_repository(
            service.repository_url, service.branch_name, build_dir
        )
        # A manual deploy has no commit attached to it — the clone is the only
        # place that knows which one is actually being built.
        if head_sha and not deployment.commit_sha:
            deployment.commit_sha = head_sha
        git_build.build_docker_image(
            build_dir,
            dockerfile_path,
            image_tag,
            build_args={
                "COMMIT_SHA": deployment.commit_sha or "",
                "BUILT_AT": now().isoformat(timespec="seconds"),
            },
        )
    return image_tag


def create_docker_volumes_for_deployment(service) -> None:
    client = docker_helpers.get_docker_client()
    for volume in service.volumes:
        if volume.host_path:
            continue
        name = docker_helpers.get_volume_resource_name(volume.id)
        try:
            client.volumes.get(name)
        except docker.errors.NotFound:
            client.volumes.create(
                name=name,
                driver="local",
                labels=docker_helpers.get_resource_labels(
                    service.project_id, parent=service.id
                ),
            )


def create_docker_configs_for_deployment(service) -> None:
    client = docker_helpers.get_docker_client()
    for config in service.configs:
        name = docker_helpers.get_config_resource_name(config.id, config.version)
        try:
            client.configs.get(name)
        except docker.errors.NotFound:
            client.configs.create(
                name=name,
                labels=docker_helpers.get_resource_labels(
                    service.project_id, parent=service.id
                ),
                data=config.contents.encode("utf-8"),
            )


class TerminalDeployError(Exception):
    """A failure this deployment can never recover from by being retried.

    Everything else — an unreachable docker daemon, a dropped database
    connection — propagates untouched so Temporal retries the step.
    """


def _healthcheck_probe_port(service, healthcheck) -> int:
    if healthcheck.associated_port:
        return healthcheck.associated_port
    for port in service.ports:
        if port.forwarded:
            return port.forwarded
    return 80


def build_container_healthcheck(service) -> Healthcheck | None:
    """Hand the probe to Swarm so it runs continuously, not just once.

    Swarm restarts a container that stops answering, which is what makes the
    gate below meaningful — it reads a verdict rather than guessing from
    whether a process happens to be alive.
    """
    healthcheck = service.healthcheck
    if healthcheck is None:
        return None

    if healthcheck.type == HealthCheckType.COMMAND.value:
        test = ["CMD-SHELL", healthcheck.value]
    else:
        port = _healthcheck_probe_port(service, healthcheck)
        path = healthcheck.value
        # Loopback first, then the container's own hostname. An app that binds
        # only to its container IP is unreachable on loopback — Next.js in
        # standalone mode does exactly that, because Docker sets HOSTNAME to
        # the container id and its server binds that single interface.
        # curl and wget are both tried because alpine images ship one or the
        # other, rarely both. $HOSTNAME expands in the container at probe time.
        attempts = [
            f"curl -fsS http://127.0.0.1:{port}{path}",
            f"wget -q -O /dev/null http://127.0.0.1:{port}{path}",
            f"curl -fsS http://$HOSTNAME:{port}{path}",
            f"wget -q -O /dev/null http://$HOSTNAME:{port}{path}",
        ]
        test = ["CMD-SHELL", " || ".join(attempts)]

    second = 1_000_000_000
    return Healthcheck(
        test=test,
        interval=healthcheck.interval_seconds * second,
        timeout=healthcheck.timeout_seconds * second,
        retries=MAX_SERVICE_RESTART_COUNT,
        start_period=HEALTHCHECK_INTERVAL_SECONDS * second,
    )


def create_swarm_service_for_deployment(service, environment, deployment, image):
    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )

    try:
        client.services.get(swarm_name)
        return swarm_name
    except docker.errors.NotFound:
        pass

    envs: list[str] = [
        f"DOCKYARD_DEPLOYMENT_HASH={deployment.unprefixed_hash}",
        "DOCKYARD_DEPLOYMENT_TYPE=docker",
    ]
    for env in service.env_variables:
        envs.append(f"{env.key}={env.value}")

    mounts: list[str] = []
    for volume in service.volumes:
        mode = ACCESS_MODE_MAP.get(volume.mode, "rw")
        if volume.host_path:
            mounts.append(f"{volume.host_path}:{volume.container_path}:{mode}")
        else:
            mounts.append(
                f"{docker_helpers.get_volume_resource_name(volume.id)}"
                f":{volume.container_path}:{mode}"
            )

    exposed_ports: dict[int, int] = {}
    for port in service.ports:
        if port.host:
            exposed_ports[port.host] = port.forwarded
    endpoint_spec = EndpointSpec(ports=exposed_ports) if exposed_ports else None

    config_refs: list[ConfigReference] = []
    for config in service.configs:
        name = docker_helpers.get_config_resource_name(config.id, config.version)
        try:
            docker_config = client.configs.get(name)
        except docker.errors.NotFound:
            continue
        config_refs.append(
            ConfigReference(
                config_id=docker_config.id,
                config_name=name,
                filename=config.mount_path,
            )
        )

    client.services.create(
        image=image,
        command=service.command,
        name=swarm_name,
        healthcheck=build_container_healthcheck(service),
        mounts=mounts,
        configs=config_refs or None,
        endpoint_spec=endpoint_spec,
        env=envs,
        labels=docker_helpers.get_resource_labels(
            service.project_id,
            deployment_hash=deployment.id,
            service=service.id,
        ),
        networks=[
            NetworkAttachmentConfig(
                target=docker_helpers.get_env_network_resource_name(
                    environment.id, service.project_id
                ),
                aliases=(
                    [
                        service.network_alias,
                        f"{service.network_alias}.{deployment.slot.lower()}."
                        f"{settings.internal_domain}",
                    ]
                    if service.network_alias
                    else []
                ),
            )
        ],
        restart_policy=RestartPolicy(
            # "any", not "on-failure". Swarm stops a container that fails its
            # healthcheck, and a well-behaved process exits 0 when asked to
            # stop — which "on-failure" reads as success and never replaces.
            # A service that went unhealthy would stay at 0/1 forever.
            condition="any",
            delay=RESTART_DELAY_SECONDS * NANOSECONDS_PER_SECOND,
            # Bounded, and bounded within a window. Unlimited restarts turn a
            # service that can never start into thousands of dead containers,
            # which is slow enough to make the docker daemon itself unusable.
            # The window resets the count, so a service that fails once a day
            # still recovers forever; only a genuine crash loop gives up.
            max_attempts=MAX_SERVICE_RESTART_COUNT,
            window=RESTART_WINDOW_SECONDS * NANOSECONDS_PER_SECOND,
        ),
    )
    return swarm_name


def _container_health(client, task) -> str | None:
    container_id = (task.get("Status", {}).get("ContainerStatus") or {}).get(
        "ContainerID"
    )
    if not isinstance(container_id, str) or not container_id:
        return None
    try:
        state = client.api.inspect_container(container_id).get("State", {})
        health = (state.get("Health") or {}).get("Status")
    except Exception:  # noqa: BLE001
        # The task is scheduled on another node, so its container cannot be
        # inspected from here. Swarm is still running the probe; fall back to
        # trusting the task state it publishes.
        return None
    return health if isinstance(health, str) else None


def run_deployment_healthcheck(service, deployment) -> tuple[str, str]:
    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )

    healthcheck = service.healthcheck
    timeout = (
        healthcheck.timeout_seconds
        if healthcheck is not None
        else HealthCheck.DEFAULT_TIMEOUT_SECONDS
    )

    start_time = monotonic()
    status, reason = (
        DeploymentStatus.UNHEALTHY.value,
        "The service failed to meet the healthcheck requirements when starting.",
    )
    while (monotonic() - start_time) < timeout:
        try:
            swarm_service = client.services.get(swarm_name)
            task_list = swarm_service.tasks(filters={"desired-state": "running"})
        except Exception as error:  # noqa: BLE001
            return DeploymentStatus.UNHEALTHY.value, str(error)

        running = [
            task
            for task in task_list
            if task.get("Status", {}).get("State") == "running"
        ]
        for task in running:
            health = _container_health(client, task)
            if health == "unhealthy":
                status, reason = (
                    DeploymentStatus.UNHEALTHY.value,
                    "The service started but did not answer its healthcheck.",
                )
                continue
            if health in (None, "healthy"):
                # None means either no healthcheck is configured or the task
                # runs on another node; in both cases a running task is the
                # strongest signal available.
                status, reason = (
                    DeploymentStatus.HEALTHY.value,
                    "The service is healthy.",
                )
                break
        if status == DeploymentStatus.HEALTHY.value:
            break

        time.sleep(HEALTHCHECK_INTERVAL_SECONDS)

    return status, reason


def remove_swarm_service_for_deployment(service, deployment) -> bool:
    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )
    try:
        client.services.get(swarm_name).remove()
        return True
    except docker.errors.NotFound:
        return False


def reap_superseded_services(service, deployment) -> list[str]:
    """Drop every deployment older than the one kept for rollback.

    The immediately previous deployment stays running — that is what makes
    going back free. Everything behind it is dead weight holding CPU, memory
    and a network alias.
    """
    superseded = sorted(
        (other for other in service.deployments if other.id != deployment.id),
        key=lambda other: other.queued_at,
        reverse=True,
    )

    reaped: list[str] = []
    for other in superseded[RETAINED_SUPERSEDED_DEPLOYMENTS:]:
        if other.status == DeploymentStatus.REMOVED.value:
            continue
        try:
            if remove_swarm_service_for_deployment(service, other):
                reaped.append(other.id)
        except Exception as error:  # noqa: BLE001
            _logger.warning("could not reap deployment %s: %s", other.id, error)
    return reaped


def discard_failed_deployment(service, deployment) -> bool:
    """Tear down a deployment that never became healthy.

    Restarts are unbounded, so a container that can never pass its healthcheck
    would otherwise be replaced forever. Nothing is serving from it — traffic
    never moved — so the only thing it can do is burn the machine.
    """
    try:
        return remove_swarm_service_for_deployment(service, deployment)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not discard deployment %s: %s", deployment.id, error)
        return False


async def mark_deployment_failed(db, deployment, reason: str) -> None:
    deployment.status = DeploymentStatus.FAILED.value
    deployment.status_reason = reason
    deployment.finished_at = now()
    await db.commit()


async def prepare_deployment_image(db, service, deployment) -> str:
    if service.type == "GIT_REPOSITORY":
        deployment.status = DeploymentStatus.BUILDING.value
        if deployment.started_at is None:
            deployment.started_at = now()
        deployment.build_started_at = now()
        await db.commit()
        try:
            image = build_git_image(service, deployment)
        except Exception as error:  # noqa: BLE001
            raise TerminalDeployError(f"Build failed: {error}") from error
        deployment.build_finished_at = now()
        await db.commit()
        return image

    if service.image is None:
        raise TerminalDeployError("No image to deploy.")
    return service.image


async def start_deployment_service(db, service, environment, deployment, image) -> None:
    deployment.status = DeploymentStatus.STARTING.value
    if deployment.started_at is None:
        deployment.started_at = now()
    await db.commit()

    create_docker_volumes_for_deployment(service)
    create_docker_configs_for_deployment(service)
    create_swarm_service_for_deployment(service, environment, deployment, image)


async def gate_deployment_on_health(db, service, deployment) -> str:
    status, reason = run_deployment_healthcheck(service, deployment)
    deployment.status = status
    deployment.status_reason = (
        None if status == DeploymentStatus.HEALTHY.value else reason
    )
    deployment.finished_at = now()
    await db.commit()
    return status


async def switch_traffic_to_deployment(db, service, deployment) -> None:
    for other in service.deployments:
        if other.id != deployment.id and other.is_current_production:
            other.is_current_production = False
    deployment.is_current_production = True
    await db.commit()
    proxy.expose_service_to_http(service)


async def deploy_docker_service(db, service, environment, deployment) -> None:
    try:
        image = await prepare_deployment_image(db, service, deployment)
        await start_deployment_service(db, service, environment, deployment, image)
        status = await gate_deployment_on_health(db, service, deployment)
    except TerminalDeployError as error:
        await mark_deployment_failed(db, deployment, str(error))
        return
    except Exception as error:  # noqa: BLE001
        _logger.warning("deployment failed: %s", error)
        await mark_deployment_failed(db, deployment, str(error))
        return

    if status != DeploymentStatus.HEALTHY.value:
        discard_failed_deployment(service, deployment)
        return

    try:
        await switch_traffic_to_deployment(db, service, deployment)
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not expose service to http: %s", error)
    reap_superseded_services(service, deployment)
