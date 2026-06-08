from temporalio import activity

from app.services import networks


@activity.defn(name="create_project_network_activity")
async def create_project_network_activity(payload: dict) -> str:
    return networks.create_project_network(
        payload["project_id"], payload["production_env_id"]
    )
