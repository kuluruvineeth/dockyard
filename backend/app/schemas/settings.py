from pydantic import BaseModel


class SettingsResponse(BaseModel):
    root_domain: str
    app_domain: str
    image_version: str
    commit_sha: str | None


class ResourceLimitResponse(BaseModel):
    no_of_cpus: int
    max_memory_in_bytes: int
