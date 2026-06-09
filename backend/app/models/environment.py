from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import PRODUCTION_ENV_NAME
from app.models.base import Base, TimestampedModel, generate_id


class Environment(Base, TimestampedModel):
    __tablename__ = "environment"

    PRODUCTION_ENV_NAME = PRODUCTION_ENV_NAME

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("project_env_", 15)
    )
    name: Mapped[str] = mapped_column(String(255))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    is_preview: Mapped[bool] = mapped_column(Boolean, default=False)

    project = relationship("Project", back_populates="environments")
    variables = relationship(
        "SharedEnvVariable",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("name", "project_id", name="uq_environment_name_project"),
        Index("ix_environment_name", "name"),
    )

    @property
    def workflow_id(self) -> str:
        return f"create-env-{self.id}"

    @property
    def archive_workflow_id(self) -> str:
        return f"archive-env-{self.id}"

    def __str__(self) -> str:
        return f"Environment({self.name})"
