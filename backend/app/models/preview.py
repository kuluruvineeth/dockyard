import enum

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel, generate_id


class PreviewSourceTrigger(str, enum.Enum):
    API = "API"
    PULL_REQUEST = "PULL_REQUEST"


class PreviewDeployState(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"


class PreviewEnvTemplate(Base, TimestampedModel):
    __tablename__ = "preview_env_template"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("pet_")
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    base_environment_id: Mapped[str] = mapped_column(
        ForeignKey("environment.id", ondelete="CASCADE")
    )
    auto_teardown: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    base_environment = relationship(
        "Environment", foreign_keys=[base_environment_id], lazy="selectin"
    )


class PreviewEnvMetadata(Base, TimestampedModel):
    __tablename__ = "preview_env_metadata"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("pem_")
    )
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environment.id", ondelete="CASCADE"), unique=True
    )
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("preview_env_template.id", ondelete="SET NULL"),
        nullable=True,
    )
    git_app_id: Mapped[str | None] = mapped_column(
        ForeignKey("git_app.id", ondelete="SET NULL"), nullable=True
    )
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_name: Mapped[str] = mapped_column(String(255))
    head_repository_url: Mapped[str] = mapped_column(String)
    source_trigger: Mapped[str] = mapped_column(String(30))
    deploy_state: Mapped[str] = mapped_column(
        String(30), default=PreviewDeployState.PENDING.value
    )
    auto_teardown: Mapped[bool] = mapped_column(Boolean, default=True)

    environment = relationship(
        "Environment",
        foreign_keys=[environment_id],
        back_populates="preview_metadata",
    )
