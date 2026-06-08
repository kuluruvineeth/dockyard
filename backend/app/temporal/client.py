import logging

from temporalio.client import Client

from app.config import settings
from app.services import deploy as deploy_service
from app.services import networks
from app.temporal.workflows import (
    CreateProjectResourcesWorkflow,
    DeployDockerServiceWorkflow,
)

_logger = logging.getLogger("dockyard.temporal")
_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(
            settings.temporalio_server_url,
            namespace=settings.temporalio_namespace,
        )
    return _client


async def schedule_create_project_resources(
    project_id: str, production_env_id: str
) -> None:
    payload = {"project_id": project_id, "production_env_id": production_env_id}

    if settings.testing:
        try:
            networks.create_project_network(project_id, production_env_id)
        except Exception as error:  # noqa: BLE001
            _logger.warning("inline project network creation failed: %s", error)
        return

    try:
        client = await get_temporal_client()
        await client.start_workflow(
            CreateProjectResourcesWorkflow.run,
            payload,
            id=f"create-{project_id}",
            task_queue=settings.main_task_queue,
        )
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not start CreateProjectResourcesWorkflow: %s", error)


async def schedule_deploy_docker_service(db, service, environment, deployment) -> None:
    if settings.testing:
        await deploy_service.deploy_docker_service(db, service, environment, deployment)
        return

    try:
        client = await get_temporal_client()
        await client.start_workflow(
            DeployDockerServiceWorkflow.run,
            deployment.id,
            id=f"deploy-{deployment.id}",
            task_queue=settings.main_task_queue,
        )
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not start DeployDockerServiceWorkflow: %s", error)
