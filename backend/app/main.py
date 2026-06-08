from fastapi import FastAPI

from app.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dockyard API",
        version="canary",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
    )
    register_error_handlers(app)
    return app


app = create_app()
