from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dockyard API",
        version="canary",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
    )
    return app


app = create_app()
