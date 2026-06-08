from datetime import datetime

import shortuuid
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def generate_id(prefix: str, length: int = 11) -> str:
    return f"{prefix}{shortuuid.ShortUUID().random(length=length)}"


class Base(DeclarativeBase):
    pass


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
