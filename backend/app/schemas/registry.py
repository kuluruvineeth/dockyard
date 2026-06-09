from datetime import datetime

from pydantic import BaseModel, Field


class RegistryCredentialsSchema(BaseModel):
    id: str
    name: str
    url: str
    username: str
    registry_type: str
    created_at: datetime

    @classmethod
    def from_credentials(cls, credentials) -> "RegistryCredentialsSchema":
        return cls(
            id=credentials.id,
            name=credentials.name,
            url=credentials.url,
            username=credentials.username,
            registry_type=credentials.registry_type,
            created_at=credentials.created_at,
        )


class RegistryCredentialsRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    username: str = Field(min_length=1, max_length=1024)
    password: str = Field(min_length=1)
    registry_type: str = "GENERIC"
