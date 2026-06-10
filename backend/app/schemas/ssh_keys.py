from datetime import datetime

from pydantic import BaseModel, Field


class SSHKeySchema(BaseModel):
    id: str
    slug: str
    user: str
    public_key: str
    fingerprint: str | None
    created_at: datetime

    @classmethod
    def from_ssh_key(cls, key) -> "SSHKeySchema":
        return cls(
            id=key.id,
            slug=key.slug,
            user=key.user,
            public_key=key.public_key,
            fingerprint=key.fingerprint,
            created_at=key.created_at,
        )


class SSHKeyCreateRequest(BaseModel):
    slug: str = Field(
        min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$"
    )
    user: str = Field(min_length=1, max_length=255)
