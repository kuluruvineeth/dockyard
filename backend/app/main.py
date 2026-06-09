import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.errors import register_error_handlers
from app.middleware.csrf import CSRFMiddleware
from app.middleware.session import SessionMiddleware
from app.routers import (
    auth,
    compose,
    docker,
    docker_services,
    git_services,
    ping,
    projects,
    registry,
)
from app.routers import settings as settings_router
from app.services import networks

_logger = logging.getLogger("dockyard.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The stack file names only the shared network, so redeploying the stack
    # drops every project network from the proxy and all routing 502s until
    # they are restored. Put them back before serving anything.
    try:
        restored = networks.reconcile_proxy_networks()
        if restored:
            _logger.info(
                "re-attached %d project network(s) to the proxy", len(restored)
            )
    except Exception as error:  # noqa: BLE001
        _logger.warning("could not reconcile proxy networks: %s", error)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dockyard API",
        version="canary",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.add_middleware(SessionMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.include_router(ping.router)
    app.include_router(auth.router)
    app.include_router(settings_router.router)
    app.include_router(projects.router)
    app.include_router(docker.router)
    app.include_router(docker_services.router)
    app.include_router(git_services.router)
    app.include_router(registry.router)
    app.include_router(compose.router)
    return app


app = create_app()
