from pydantic import BaseModel


class DockerImageResult(BaseModel):
    full_image: str
    description: str


class DockerImageSearchResponse(BaseModel):
    images: list[DockerImageResult]
