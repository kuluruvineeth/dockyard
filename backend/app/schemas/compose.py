from datetime import datetime

from pydantic import BaseModel, Field


class ComposeStackServiceSchema(BaseModel):
    id: str
    slug: str


class ComposeStackSchema(BaseModel):
    id: str
    slug: str
    services: list[ComposeStackServiceSchema]
    created_at: datetime

    @classmethod
    def from_stack(cls, stack) -> "ComposeStackSchema":
        return cls(
            id=stack.id,
            slug=stack.slug,
            services=[
                ComposeStackServiceSchema(id=s.id, slug=s.slug) for s in stack.services
            ],
            created_at=stack.created_at,
        )


class CreateComposeStackRequest(BaseModel):
    slug: str = Field(
        min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$"
    )
    contents: str = Field(min_length=1)
