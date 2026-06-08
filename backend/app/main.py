from fastapi import FastAPI

from app.errors import register_error_handlers
from app.middleware.csrf import CSRFMiddleware
from app.middleware.session import SessionMiddleware
from app.routers import auth, ping
from app.routers import settings as settings_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dockyard API",
        version="canary",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
    )
    register_error_handlers(app)
    app.add_middleware(SessionMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.include_router(ping.router)
    app.include_router(auth.router)
    app.include_router(settings_router.router)
    return app


app = create_app()
