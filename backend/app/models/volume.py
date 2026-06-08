import enum

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class VolumeMode(str, enum.Enum):
    READ_WRITE = "READ_WRITE"
    READ_ONLY = "READ_ONLY"


class Volume(Base, TimestampedModel):
    __tablename__ = "volume"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("vol_")
    )
    mode: Mapped[str] = mapped_column(String(10), default=VolumeMode.READ_WRITE.value)
    name: Mapped[str] = mapped_column(String)
    container_path: Mapped[str] = mapped_column(String, index=True)
    host_path: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    service_id: Mapped[str] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), index=True
    )
