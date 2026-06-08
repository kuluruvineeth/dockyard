from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampedModel, generate_id


class URL(Base, TimestampedModel):
    __tablename__ = "url"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("url_")
    )
    domain: Mapped[str] = mapped_column(String)
    base_path: Mapped[str] = mapped_column(String, default="/")
    strip_prefix: Mapped[bool] = mapped_column(Boolean, default=True)
    redirect_to: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    associated_port: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("domain", "base_path", name="uq_url_domain_base_path"),
    )

    def __repr__(self) -> str:
        base = (
            self.base_path if self.base_path.startswith("/") else f"/{self.base_path}"
        )
        return f"URL({self.domain}{base})"
