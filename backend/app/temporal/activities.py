from sqlalchemy import select
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.db import async_session
from app.models import Deployment, Environment, Service
from app.services import deploy as deploy_service
from app.services import networks


@activity.defn(name="create_project_network_activity")
async def create_project_network_activity(payload: dict) -> str:
    return networks.create_project_network(
        payload["project_id"], payload["production_env_id"]
    )


async def _load_deployment(db, deployment_id: str):
    deployment = (
        await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    ).scalar_one()
    service = (
        await db.execute(select(Service).where(Service.id == deployment.service_id))
    ).scalar_one()
    environment = (
        await db.execute(
            select(Environment).where(Environment.id == service.environment_id)
        )
    ).scalar_one()
    return deployment, service, environment


@activity.defn(name="prepare_deployment_image_activity")
async def prepare_deployment_image_activity(deployment_id: str) -> str:
    async with async_session() as db:
        deployment, service, _ = await _load_deployment(db, deployment_id)
        try:
            return await deploy_service.prepare_deployment_image(
                db, service, deployment
            )
        except deploy_service.TerminalDeployError as error:
            raise ApplicationError(str(error), non_retryable=True) from error


@activity.defn(name="start_deployment_service_activity")
async def start_deployment_service_activity(deployment_id: str, image: str) -> str:
    async with async_session() as db:
        deployment, service, environment = await _load_deployment(db, deployment_id)
        await deploy_service.start_deployment_service(
            db, service, environment, deployment, image
        )
    return deployment_id


@activity.defn(name="gate_deployment_on_health_activity")
async def gate_deployment_on_health_activity(deployment_id: str) -> str:
    async with async_session() as db:
        deployment, service, _ = await _load_deployment(db, deployment_id)
        return await deploy_service.gate_deployment_on_health(db, service, deployment)


@activity.defn(name="switch_traffic_activity")
async def switch_traffic_activity(deployment_id: str) -> str:
    async with async_session() as db:
        deployment, service, _ = await _load_deployment(db, deployment_id)
        await deploy_service.switch_traffic_to_deployment(db, service, deployment)
    return deployment_id


@activity.defn(name="discard_failed_deployment_activity")
async def discard_failed_deployment_activity(deployment_id: str) -> bool:
    async with async_session() as db:
        deployment, service, _ = await _load_deployment(db, deployment_id)
        return deploy_service.discard_failed_deployment(service, deployment)


@activity.defn(name="reap_superseded_services_activity")
async def reap_superseded_services_activity(deployment_id: str) -> list[str]:
    async with async_session() as db:
        deployment, service, _ = await _load_deployment(db, deployment_id)
        return deploy_service.reap_superseded_services(service, deployment)


@activity.defn(name="mark_deployment_failed_activity")
async def mark_deployment_failed_activity(deployment_id: str, reason: str) -> str:
    async with async_session() as db:
        deployment, _, _ = await _load_deployment(db, deployment_id)
        await deploy_service.mark_deployment_failed(db, deployment, reason)
    return deployment_id
