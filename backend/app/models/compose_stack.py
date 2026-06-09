from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel, generate_id


class ComposeStack(Base, TimestampedModel):
    __tablename__ = "compose_stack"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("compose_stk_", 15)
    )
    slug: Mapped[str] = mapped_column(String(40), index=True)
    network_alias_prefix: Mapped[str] = mapped_column(String(40))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environment.id", ondelete="CASCADE"), index=True
    )
    deploy_token: Mapped[str | None] = mapped_column(String(35), nullable=True)
    user_content: Mapped[str] = mapped_column(Text, default="")

    services = relationship(
        "Service",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Service.compose_stack_id",
    )

    __table_args__ = (
        UniqueConstraint(
            "slug", "environment_id", name="uq_compose_stack_slug_environment"
        ),
    )
