from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

HEALTHY = "HEALTHY"


@workflow.defn(name="create-project-resources-workflow")
class CreateProjectResourcesWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> str:
        return await workflow.execute_activity(
            "create_project_network_activity",
            payload,
            start_to_close_timeout=timedelta(seconds=30),
        )


@workflow.defn(name="deploy-docker-service-workflow")
class DeployDockerServiceWorkflow:
    """One deploy, as a sequence of steps Temporal records as they complete.

    A worker that dies mid-deploy is replaced and the new one resumes at the
    first step that never finished. Every step is idempotent, so a step that
    was half-done converges instead of duplicating.
    """

    @workflow.run
    async def run(self, deployment_id: str) -> str:
        try:
            image = await workflow.execute_activity(
                "prepare_deployment_image_activity",
                deployment_id,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            await workflow.execute_activity(
                "start_deployment_service_activity",
                args=[deployment_id, image],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            status = await workflow.execute_activity(
                "gate_deployment_on_health_activity",
                deployment_id,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
        except ActivityError as error:
            await workflow.execute_activity(
                "mark_deployment_failed_activity",
                args=[deployment_id, _failure_reason(error)],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return deployment_id

        if status != HEALTHY:
            await workflow.execute_activity(
                "discard_failed_deployment_activity",
                deployment_id,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            return deployment_id

        await workflow.execute_activity(
            "switch_traffic_activity",
            deployment_id,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        await workflow.execute_activity(
            "reap_superseded_services_activity",
            deployment_id,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        return deployment_id


def _failure_reason(error: ActivityError) -> str:
    cause = error.cause
    return str(cause) if cause is not None else str(error)
