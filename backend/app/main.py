from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import ping


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dockyard API",
        version="canary",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
    )
    register_error_handlers(app)
    app.include_router(ping.router)
    return app


app = create_app()
