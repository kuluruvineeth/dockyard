from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import PRODUCTION_ENV_NAME
from app.models.base import Base, TimestampedModel, generate_id


class Project(Base, TimestampedModel):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("prj_")
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner = relationship("User")
    environments = relationship(
        "Environment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def create_task_id(self) -> str:
        return f"create-{self.id}"

    @property
    def production_env(self):
        for environment in self.environments:
            if environment.name == PRODUCTION_ENV_NAME:
                return environment
        return None

    def __str__(self) -> str:
        return f"Project({self.slug})"
