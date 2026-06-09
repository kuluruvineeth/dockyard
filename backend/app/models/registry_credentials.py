import enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class RegistryType(str, enum.Enum):
    DOCKER_HUB = "DOCKER_HUB"
    GITHUB = "GITHUB"
    GITLAB = "GITLAB"
    GOOGLE_ARTIFACT = "GOOGLE_ARTIFACT"
    AWS_ECR = "AWS_ECR"
    GENERIC = "GENERIC"


class SharedRegistryCredentials(Base, TimestampedModel):
    __tablename__ = "shared_registry_credentials"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("reg_cred_", 20)
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String)
    username: Mapped[str] = mapped_column(String(1024))
    password: Mapped[str] = mapped_column(Text)
    registry_type: Mapped[str] = mapped_column(
        String(32), default=RegistryType.GENERIC.value
    )
