from fastapi import APIRouter

from app.config import settings as app_settings
from app.dependencies import CurrentUser
from app.docker_helpers import get_server_resource_limits
from app.schemas.settings import ResourceLimitResponse, SettingsResponse

router = APIRouter()


@router.get("/api/settings", response_model=SettingsResponse)
async def get_api_settings(user: CurrentUser):
    return SettingsResponse(
        root_domain=app_settings.root_domain,
        app_domain=app_settings.app_domain,
        image_version=app_settings.image_version,
        commit_sha=app_settings.commit_sha,
    )


@router.get("/api/server/resource-limits", response_model=ResourceLimitResponse)
async def get_server_resource_limits_view(user: CurrentUser):
    no_of_cpus, max_memory_in_bytes = get_server_resource_limits()
    return ResourceLimitResponse(
        no_of_cpus=no_of_cpus, max_memory_in_bytes=max_memory_in_bytes
    )
