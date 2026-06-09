from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class SharedEnvVariable(Base, TimestampedModel):
    __tablename__ = "shared_env_variable"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("env_prj_")
    )
    key: Mapped[str] = mapped_column(String(255))
    value: Mapped[str] = mapped_column(Text, default="")
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environment.id", ondelete="CASCADE"), index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "key", "environment_id", name="uq_shared_env_variable_key_environment"
        ),
        Index("ix_shared_env_variable_key", "key"),
    )
