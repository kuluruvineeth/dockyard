from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models import Environment, Project


class SimpleEnvironmentSchema(BaseModel):
    id: str
    name: str
    is_preview: bool
    created_at: datetime

    @classmethod
    def from_environment(cls, environment: Environment) -> "SimpleEnvironmentSchema":
        return cls(
            id=environment.id,
            name=environment.name,
            is_preview=environment.is_preview,
            created_at=environment.created_at,
        )


class ProjectSchema(BaseModel):
    id: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    environments: list[SimpleEnvironmentSchema]
    healthy_services: int = 0
    total_services: int = 0
    healthy_stack_services: int = 0
    total_stack_services: int = 0

    @classmethod
    def from_project(
        cls,
        project: Project,
        healthy_services: int = 0,
        total_services: int = 0,
    ) -> "ProjectSchema":
        return cls(
            id=project.id,
            slug=project.slug,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
            environments=[
                SimpleEnvironmentSchema.from_environment(env)
                for env in project.environments
            ],
            healthy_services=healthy_services,
            total_services=total_services,
        )


class ProjectCreateRequest(BaseModel):
    slug: str | None = Field(default=None, max_length=255, pattern=r"^[-a-zA-Z0-9_]+$")
    description: str | None = None


class CreateEnvironmentRequest(BaseModel):
    name: str = Field(
        min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$"
    )


class ProjectUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, max_length=255, pattern=r"^[-a-zA-Z0-9_]+$")
    description: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ProjectUpdateRequest":
        if self.slug is None and self.description is None:
            raise ValueError("one of `slug` or `description` should be provided")
        return self
