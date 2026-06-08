import asyncio

from temporalio.worker import Worker

from app.config import settings
from app.temporal.activities import (
    create_project_network_activity,
    discard_failed_deployment_activity,
    gate_deployment_on_health_activity,
    mark_deployment_failed_activity,
    prepare_deployment_image_activity,
    reap_superseded_services_activity,
    start_deployment_service_activity,
    switch_traffic_activity,
)
from app.temporal.client import get_temporal_client
from app.temporal.workflows import (
    CreateProjectResourcesWorkflow,
    DeployDockerServiceWorkflow,
)


async def main() -> None:
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.temporalio_task_queue,
        workflows=[CreateProjectResourcesWorkflow, DeployDockerServiceWorkflow],
        activities=[
            create_project_network_activity,
            discard_failed_deployment_activity,
            prepare_deployment_image_activity,
            start_deployment_service_activity,
            gate_deployment_on_health_activity,
            switch_traffic_activity,
            reap_superseded_services_activity,
            mark_deployment_failed_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
