from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class SharedVolume(Base, TimestampedModel):
    __tablename__ = "shared_volume"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("shared_vol_")
    )
    volume_id: Mapped[str] = mapped_column(ForeignKey("volume.id", ondelete="CASCADE"))
    reader_id: Mapped[str] = mapped_column(ForeignKey("service.id", ondelete="CASCADE"))
    container_path: Mapped[str] = mapped_column(String, index=True)

    __table_args__ = (
        UniqueConstraint("volume_id", "reader_id", name="uq_shared_volume_reader"),
    )
