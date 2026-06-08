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
from app.models.config import Config
from app.models.env_variable import EnvVariable
from app.models.healthcheck import HealthCheck
from app.models.port import PortConfiguration
from app.models.url import URL
from app.models.volume import Volume


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

    _SINGLE_VALUE_FIELDS = {
        "source",
        "git_source",
        "builder",
        "command",
        "healthcheck",
        "resource_limits",
    }

    def add_change(self, change) -> None:
        if change.field in self._SINGLE_VALUE_FIELDS:
            for existing in list(self.changes):
                if existing.field == change.field and not existing.applied:
                    self.changes.remove(existing)
        self.changes.append(change)

    def apply_pending_changes(self, deployment=None) -> None:
        builders = {
            "DOCKERFILE": "dockerfile_builder_options",
            "STATIC_DIR": "static_dir_builder_options",
            "NIXPACKS": "nixpacks_builder_options",
            "RAILPACK": "railpack_builder_options",
        }

        def find(collection, item_id):
            return next((i for i in collection if i.id == item_id), None)

        for change in self.unapplied_changes:
            field = change.field
            ctype = change.type
            value = change.new_value or {}

            if field == "source":
                self.image = value.get("image", self.image)
                if "credentials" in value:
                    self.credentials = value["credentials"]
                if "container_registry_credentials_id" in value:
                    self.container_registry_credentials_id = value[
                        "container_registry_credentials_id"
                    ]
            elif field == "command":
                self.command = change.new_value
            elif field == "resource_limits":
                self.resource_limits = change.new_value
            elif field == "builder":
                self.builder = value.get("builder")
                attr = builders.get(self.builder)
                if attr is not None:
                    setattr(self, attr, value.get("options", value))
            elif field == "git_source":
                self.repository_url = value.get("repository_url", self.repository_url)
                self.branch_name = value.get("branch_name", self.branch_name)
                self.commit_sha = value.get("commit_sha", self.commit_sha)
            elif field == "healthcheck":
                if change.new_value is None:
                    self.healthcheck = None
                else:
                    if self.healthcheck is None:
                        self.healthcheck = HealthCheck(id=generate_id("htc_"))
                    self.healthcheck.type = value.get("type", "PATH")
                    self.healthcheck.value = value.get("value", "/")
                    self.healthcheck.interval_seconds = value.get(
                        "interval_seconds", HealthCheck.DEFAULT_INTERVAL_SECONDS
                    )
                    self.healthcheck.timeout_seconds = value.get(
                        "timeout_seconds", HealthCheck.DEFAULT_TIMEOUT_SECONDS
                    )
                    self.healthcheck.associated_port = value.get("associated_port")
            elif field == "env_variables":
                if ctype == "ADD":
                    item = EnvVariable(
                        id=generate_id("env_dkr_"),
                        key=value["key"],
                        value=value["value"],
                    )
                    self.env_variables.append(item)
                    change.item_id = item.id
                elif ctype == "UPDATE":
                    item = find(self.env_variables, change.item_id)
                    if item is not None:
                        item.key = value.get("key", item.key)
                        item.value = value.get("value", item.value)
                elif ctype == "DELETE":
                    item = find(self.env_variables, change.item_id)
                    if item is not None:
                        self.env_variables.remove(item)
            elif field == "urls":
                if ctype == "ADD":
                    item = URL(
                        id=generate_id("url_"),
                        domain=value["domain"],
                        base_path=value.get("base_path", "/"),
                        strip_prefix=value.get("strip_prefix", True),
                        redirect_to=value.get("redirect_to"),
                        associated_port=value.get("associated_port"),
                    )
                    self.urls.append(item)
                    change.item_id = item.id
                elif ctype == "UPDATE":
                    item = find(self.urls, change.item_id)
                    if item is not None:
                        item.domain = value.get("domain", item.domain)
                        item.base_path = value.get("base_path", item.base_path)
                        item.strip_prefix = value.get("strip_prefix", item.strip_prefix)
                        item.redirect_to = value.get("redirect_to", item.redirect_to)
                        item.associated_port = value.get(
                            "associated_port", item.associated_port
                        )
                elif ctype == "DELETE":
                    item = find(self.urls, change.item_id)
                    if item is not None:
                        self.urls.remove(item)
            elif field == "ports":
                if ctype == "ADD":
                    item = PortConfiguration(
                        id=generate_id("prt_"),
                        host=value.get("host", 0),
                        forwarded=value["forwarded"],
                    )
                    self.ports.append(item)
                    change.item_id = item.id
                elif ctype == "UPDATE":
                    item = find(self.ports, change.item_id)
                    if item is not None:
                        item.host = value.get("host", item.host)
                        item.forwarded = value.get("forwarded", item.forwarded)
                elif ctype == "DELETE":
                    item = find(self.ports, change.item_id)
                    if item is not None:
                        self.ports.remove(item)
            elif field == "volumes":
                if ctype == "ADD":
                    item = Volume(
                        id=generate_id("vol_"),
                        name=value.get("name") or f"vol-{generate_id('')}",
                        mode=value.get("mode", "READ_WRITE"),
                        container_path=value["container_path"],
                        host_path=value.get("host_path"),
                        service_id=self.id,
                    )
                    self.volumes.append(item)
                    change.item_id = item.id
                elif ctype == "UPDATE":
                    item = find(self.volumes, change.item_id)
                    if item is not None:
                        item.name = value.get("name", item.name)
                        item.mode = value.get("mode", item.mode)
                        item.container_path = value.get(
                            "container_path", item.container_path
                        )
                        item.host_path = value.get("host_path", item.host_path)
                elif ctype == "DELETE":
                    item = find(self.volumes, change.item_id)
                    if item is not None:
                        self.volumes.remove(item)
            elif field == "configs":
                if ctype == "ADD":
                    item = Config(
                        id=generate_id("cf_"),
                        name=value["name"],
                        mount_path=value["mount_path"],
                        contents=value.get("contents", ""),
                        language=value.get("language", "plaintext"),
                        version=1,
                    )
                    self.configs.append(item)
                    change.item_id = item.id
                elif ctype == "UPDATE":
                    item = find(self.configs, change.item_id)
                    if item is not None:
                        if "contents" in value and value["contents"] != item.contents:
                            item.version += 1
                        item.name = value.get("name", item.name)
                        item.mount_path = value.get("mount_path", item.mount_path)
                        item.contents = value.get("contents", item.contents)
                        item.language = value.get("language", item.language)
                elif ctype == "DELETE":
                    item = find(self.configs, change.item_id)
                    if item is not None:
                        self.configs.remove(item)
            elif field == "shared_volumes":
                pass

            change.applied = True
            if deployment is not None:
                change.deployment_id = deployment.id
