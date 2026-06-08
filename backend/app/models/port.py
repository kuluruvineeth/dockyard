from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class PortConfiguration(Base, TimestampedModel):
    __tablename__ = "port_configuration"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("prt_")
    )
    host: Mapped[int] = mapped_column(Integer, default=0, index=True)
    forwarded: Mapped[int] = mapped_column(Integer)
