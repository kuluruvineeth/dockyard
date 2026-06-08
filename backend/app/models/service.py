import enum

from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampedModel, generate_id


class ServiceType(str, enum.Enum):
    DOCKER_REGISTRY = "DOCKER_REGISTRY"
    GIT_REPOSITORY = "GIT_REPOSITORY"


class Builder(str, enum.Enum):
    DOCKERFILE = "DOCKERFILE"
    STATIC_DIR = "STATIC_DIR"
    NIXPACKS = "NIXPACKS"
    RAILPACK = "RAILPACK"


service_urls = Table(
    "service_urls",
    Base.metadata,
    Column(
        "service_id",
        String,
        ForeignKey("service.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "url_id", String, ForeignKey("url.id", ondelete="CASCADE"), primary_key=True
    ),
)

service_ports = Table(
    "service_ports",
    Base.metadata,
    Column(
        "service_id",
        String,
        ForeignKey("service.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "port_id",
        String,
        ForeignKey("port_configuration.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

service_configs = Table(
    "service_configs",
    Base.metadata,
    Column(
        "service_id",
        String,
        ForeignKey("service.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "config_id",
        String,
        ForeignKey("config.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Service(Base, TimestampedModel):
    __tablename__ = "service"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("srv_dkr_")
    )
    slug: Mapped[str] = mapped_column(String(255))
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), index=True
    )
    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environment.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(
        String(20), default=ServiceType.DOCKER_REGISTRY.value
    )

    image: Mapped[str | None] = mapped_column(String, nullable=True)
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    network_alias: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deploy_token: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    healthcheck_id: Mapped[str | None] = mapped_column(
        ForeignKey("healthcheck.id", ondelete="SET NULL"), nullable=True
    )

    # FK columns whose targets land in later acts (kept nullable now).
    container_registry_credentials_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    git_app_id: Mapped[str | None] = mapped_column(String, nullable=True)

    repository_url: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    branch_name: Mapped[str | None] = mapped_column(String, nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String, nullable=True)
    builder: Mapped[str | None] = mapped_column(String, nullable=True)
    dockerfile_builder_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    static_dir_builder_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    nixpacks_builder_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    railpack_builder_options: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    urls = relationship("URL", secondary=service_urls, lazy="selectin")
    ports = relationship("PortConfiguration", secondary=service_ports, lazy="selectin")
    configs = relationship("Config", secondary=service_configs, lazy="selectin")
    healthcheck = relationship("HealthCheck", lazy="selectin")
    volumes = relationship(
        "Volume",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Volume.service_id",
    )
    env_variables = relationship(
        "EnvVariable", lazy="selectin", cascade="all, delete-orphan"
    )
    changes = relationship(
        "DeploymentChange",
        lazy="selectin",
        cascade="all, delete-orphan",
        back_populates="service",
    )
    project = relationship("Project")
    environment = relationship("Environment")

    __table_args__ = (
        UniqueConstraint(
            "slug", "project_id", "environment_id", name="uq_service_slug_project_env"
        ),
        UniqueConstraint(
            "network_alias",
            "project_id",
            "environment_id",
            name="uq_service_network_alias_project_env",
        ),
    )

    @property
    def unprefixed_id(self) -> str:
        return self.id.rsplit("_", 1)[-1]

    @staticmethod
    def generate_network_alias(service: "Service") -> str:
        return f"dky-{service.slug}-{service.unprefixed_id}"

    @property
    def system_env_variables(self) -> list[dict]:
        return []

    @property
    def unapplied_changes(self) -> list:
        return [change for change in self.changes if not change.applied]

    @property
    def applied_changes(self) -> list:
        return [change for change in self.changes if change.applied]
