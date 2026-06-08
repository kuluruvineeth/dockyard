import asyncio

from temporalio.worker import Worker

from app.config import settings
from app.temporal.activities import create_project_network_activity
from app.temporal.client import get_temporal_client
from app.temporal.workflows import CreateProjectResourcesWorkflow


async def main() -> None:
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.temporalio_task_queue,
        workflows=[CreateProjectResourcesWorkflow],
        activities=[create_project_network_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
