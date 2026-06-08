import enum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampedModel, generate_id


class ChangeType(str, enum.Enum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class ChangeField(str, enum.Enum):
    SOURCE = "source"
    GIT_SOURCE = "git_source"
    BUILDER = "builder"
    COMMAND = "command"
    HEALTHCHECK = "healthcheck"
    VOLUMES = "volumes"
    SHARED_VOLUMES = "shared_volumes"
    ENV_VARIABLES = "env_variables"
    URLS = "urls"
    PORTS = "ports"
    RESOURCE_LIMITS = "resource_limits"
    CONFIGS = "configs"


class DeploymentChange(Base, TimestampedModel):
    __tablename__ = "deployment_change"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("chg_dkr_")
    )
    type: Mapped[str] = mapped_column(String(10))
    field: Mapped[str] = mapped_column(String(20), index=True)
    item_id: Mapped[str | None] = mapped_column(String, nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    service_id: Mapped[str] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), index=True
    )
    deployment_id: Mapped[str | None] = mapped_column(String, nullable=True)

    service = relationship("Service", back_populates="changes")
