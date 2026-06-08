import enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class HealthCheckType(str, enum.Enum):
    COMMAND = "COMMAND"
    PATH = "PATH"


class HealthCheck(Base, TimestampedModel):
    __tablename__ = "healthcheck"

    DEFAULT_TIMEOUT_SECONDS = 60
    DEFAULT_INTERVAL_SECONDS = 15

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("htc_")
    )
    type: Mapped[str] = mapped_column(String(10), default=HealthCheckType.PATH.value)
    value: Mapped[str] = mapped_column(String, default="/")
    interval_seconds: Mapped[int] = mapped_column(Integer, default=15)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    associated_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
