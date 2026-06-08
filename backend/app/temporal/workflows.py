from datetime import timedelta

from temporalio import workflow


@workflow.defn(name="create-project-resources-workflow")
class CreateProjectResourcesWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> str:
        return await workflow.execute_activity(
            "create_project_network_activity",
            payload,
            start_to_close_timeout=timedelta(seconds=30),
        )
