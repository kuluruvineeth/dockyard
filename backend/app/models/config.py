from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class Config(Base, TimestampedModel):
    __tablename__ = "config"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("cf_")
    )
    name: Mapped[str] = mapped_column(String)
    mount_path: Mapped[str] = mapped_column(String, index=True)
    contents: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String, default="plaintext")
    version: Mapped[int] = mapped_column(Integer, default=1, index=True)
