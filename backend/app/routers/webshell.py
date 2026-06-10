import asyncio
import os
import pty

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app import docker_helpers
from app.db import async_session
from app.models import Deployment, Service, User
from app.security import AUTH_USER_ID_KEY
from app.session import get_store

router = APIRouter()


async def _resolve_user(websocket: WebSocket) -> User | None:
    key = websocket.cookies.get("sessionid")
    if not key:
        return None
    loaded = get_store().load(key)
    if not loaded:
        return None
    user_id = loaded.get("data", {}).get(AUTH_USER_ID_KEY)
    if not user_id:
        return None
    async with async_session() as db:
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user


async def _resolve_container_id(deployment_hash: str, slug: str) -> str | None:
    async with async_session() as db:
        result = await db.execute(select(Service).where(Service.slug == slug))
        service = result.scalar_one_or_none()
        if service is None:
            return None
        result = await db.execute(
            select(Deployment).where(Deployment.service_id == service.id)
        )
        deployment = next(
            (d for d in result.scalars() if d.unprefixed_hash == deployment_hash),
            None,
        )
        if deployment is None:
            return None
        swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
            deployment.unprefixed_hash, service.project_id, service.id
        )

    client = docker_helpers.get_docker_client()
    containers = client.containers.list(
        filters={"label": f"com.docker.swarm.service.name={swarm_name}"}
    )
    if not containers:
        return None
    return containers[0].id


@router.websocket(
    "/api/projects/{project_slug}/{env_slug}/service-details/{slug}/deployments/{deployment_hash}/terminal/"
)
async def deployment_terminal(
    websocket: WebSocket,
    project_slug: str,
    env_slug: str,
    slug: str,
    deployment_hash: str,
):
    await websocket.accept()

    user = await _resolve_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return

    container_id = await _resolve_container_id(deployment_hash, slug)
    if container_id is None:
        await websocket.send_text(
            "\r\n\x1b[31mNo running container for this deployment.\x1b[0m\r\n"
        )
        await websocket.close()
        return

    # Open a PTY and spawn `docker exec -i -t <container> /bin/sh` attached to it,
    master_fd, slave_fd = pty.openpty()
    process = await asyncio.create_subprocess_exec(
        "docker",
        "exec",
        "-i",
        "-t",
        container_id,
        "/bin/sh",
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)
    loop = asyncio.get_running_loop()

    def _on_pty_output():
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            data = b""
        if data:
            asyncio.create_task(websocket.send_bytes(data))

    loop.add_reader(master_fd, _on_pty_output)
    try:
        while True:
            data = await websocket.receive_text()
            os.write(master_fd, data.encode("utf-8"))
    except WebSocketDisconnect:
        pass
    finally:
        loop.remove_reader(master_fd)
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        os.close(master_fd)
