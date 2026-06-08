from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class EnvVariable(Base, TimestampedModel):
    __tablename__ = "env_variable"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("env_dkr_")
    )
    service_id: Mapped[str] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("key", "service_id", name="uq_env_key_service"),)
