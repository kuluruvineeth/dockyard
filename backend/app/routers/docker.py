from fastapi import APIRouter

from app.dependencies import CurrentUser
from app.docker_helpers import search_images_docker_hub
from app.errors import BadRequest
from app.schemas.docker import DockerImageSearchResponse

router = APIRouter()


@router.get("/api/docker/image-search/", response_model=DockerImageSearchResponse)
async def image_search(user: CurrentUser, q: str | None = None):
    if not q:
        raise BadRequest("a search query `q` is required")
    images = search_images_docker_hub(q)
    return DockerImageSearchResponse(images=images)
