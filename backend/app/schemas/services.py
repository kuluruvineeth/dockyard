from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models import (
    URL,
    Config,
    Deployment,
    DeploymentChange,
    EnvVariable,
    HealthCheck,
    PortConfiguration,
    Service,
    Volume,
)


class URLSchema(BaseModel):
    id: str
    domain: str
    base_path: str
    strip_prefix: bool
    redirect_to: dict | None
    associated_port: int | None


class PortSchema(BaseModel):
    id: str
    host: int
    forwarded: int


class VolumeSchema(BaseModel):
    id: str
    name: str
    mode: str
    container_path: str
    host_path: str | None


class EnvVariableSchema(BaseModel):
    id: str
    key: str
    value: str


class ConfigSchema(BaseModel):
    id: str
    name: str
    mount_path: str
    contents: str
    language: str
    version: int


class HealthCheckSchema(BaseModel):
    id: str
    type: str
    value: str
    interval_seconds: int
    timeout_seconds: int
    associated_port: int | None


class ChangeSchema(BaseModel):
    id: str
    type: str
    field: str
    item_id: str | None
    old_value: Any | None
    new_value: Any | None
    applied: bool

    @classmethod
    def from_change(cls, change: DeploymentChange) -> "ChangeSchema":
        return cls(
            id=change.id,
            type=change.type,
            field=change.field,
            item_id=change.item_id,
            old_value=change.old_value,
            new_value=change.new_value,
            applied=change.applied,
        )


class ServiceSchema(BaseModel):
    id: str
    slug: str
    type: str
    image: str | None
    command: str | None
    repository_url: str | None
    branch_name: str | None
    builder: str | None
    resource_limits: dict | None
    network_alias: str | None
    created_at: datetime
    updated_at: datetime
    urls: list[URLSchema]
    ports: list[PortSchema]
    volumes: list[VolumeSchema]
    env_variables: list[EnvVariableSchema]
    configs: list[ConfigSchema]
    healthcheck: HealthCheckSchema | None
    unapplied_changes: list[ChangeSchema]

    @classmethod
    def from_service(cls, service: Service) -> "ServiceSchema":
        return cls(
            id=service.id,
            slug=service.slug,
            type=service.type,
            image=service.image,
            command=service.command,
            repository_url=service.repository_url,
            branch_name=service.branch_name,
            builder=service.builder,
            resource_limits=service.resource_limits,
            network_alias=service.network_alias,
            created_at=service.created_at,
            updated_at=service.updated_at,
            urls=[_url(u) for u in service.urls],
            ports=[_port(p) for p in service.ports],
            volumes=[_volume(v) for v in service.volumes],
            env_variables=[_env(e) for e in service.env_variables],
            configs=[_config(c) for c in service.configs],
            healthcheck=(
                _healthcheck(service.healthcheck) if service.healthcheck else None
            ),
            unapplied_changes=[
                ChangeSchema.from_change(c) for c in service.unapplied_changes
            ],
        )


def _url(u: URL) -> URLSchema:
    return URLSchema(
        id=u.id,
        domain=u.domain,
        base_path=u.base_path,
        strip_prefix=u.strip_prefix,
        redirect_to=u.redirect_to,
        associated_port=u.associated_port,
    )


def _port(p: PortConfiguration) -> PortSchema:
    return PortSchema(id=p.id, host=p.host, forwarded=p.forwarded)


def _volume(v: Volume) -> VolumeSchema:
    return VolumeSchema(
        id=v.id,
        name=v.name,
        mode=v.mode,
        container_path=v.container_path,
        host_path=v.host_path,
    )


def _env(e: EnvVariable) -> EnvVariableSchema:
    return EnvVariableSchema(id=e.id, key=e.key, value=e.value)


def _config(c: Config) -> ConfigSchema:
    return ConfigSchema(
        id=c.id,
        name=c.name,
        mount_path=c.mount_path,
        contents=c.contents,
        language=c.language,
        version=c.version,
    )


def _healthcheck(h: HealthCheck) -> HealthCheckSchema:
    return HealthCheckSchema(
        id=h.id,
        type=h.type,
        value=h.value,
        interval_seconds=h.interval_seconds,
        timeout_seconds=h.timeout_seconds,
        associated_port=h.associated_port,
    )


class DockerServiceCreateRequest(BaseModel):
    slug: str | None = Field(default=None, max_length=255, pattern=r"^[-a-zA-Z0-9_]+$")
    image: str = Field(min_length=1)
    container_registry_credentials_id: str | None = None


class ServiceUpdateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[-a-zA-Z0-9_]+$")


class GitServiceCreateRequest(BaseModel):
    slug: str | None = Field(default=None, max_length=255, pattern=r"^[-a-zA-Z0-9_]+$")
    repository_url: str = Field(min_length=1)
    branch_name: str = Field(min_length=1)
    builder: str = Field(default="DOCKERFILE")
    dockerfile_path: str = Field(default="./Dockerfile")


class ServiceChangeRequest(BaseModel):
    field: str
    type: str
    item_id: str | None = None
    new_value: Any = None


class ToggleServiceRequest(BaseModel):
    desired_state: Literal["start", "stop"]


class DeploymentSchema(BaseModel):
    id: str
    status: str
    status_reason: str | None
    slot: str
    is_current_production: bool
    commit_message: str
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_deployment(cls, deployment: Deployment) -> "DeploymentSchema":
        return cls(
            id=deployment.id,
            status=deployment.status,
            status_reason=deployment.status_reason,
            slot=deployment.slot,
            is_current_production=deployment.is_current_production,
            commit_message=deployment.commit_message,
            queued_at=deployment.queued_at,
            started_at=deployment.started_at,
            finished_at=deployment.finished_at,
        )


class DeploymentListResponse(BaseModel):
    results: list[DeploymentSchema]
    count: int


class DeploymentLogsResponse(BaseModel):
    logs: list[str]


class ServiceMetricsSchema(BaseModel):
    cpu_percent: float
    memory_bytes: int
    net_rx_bytes: int
    net_tx_bytes: int
    disk_read_bytes: int
    disk_writes_bytes: int
    created_at: datetime

    @classmethod
    def from_metrics(cls, metrics) -> "ServiceMetricsSchema":
        return cls(
            cpu_percent=metrics.cpu_percent,
            memory_bytes=metrics.memory_bytes,
            net_rx_bytes=metrics.net_rx_bytes,
            net_tx_bytes=metrics.net_tx_bytes,
            disk_read_bytes=metrics.disk_read_bytes,
            disk_writes_bytes=metrics.disk_writes_bytes,
            created_at=metrics.created_at,
        )


class ServiceCardSchema(BaseModel):
    id: str
    slug: str
    type: str
    status: str
    image: str | None
    tag: str | None
    url: str | None
    volume_number: int
    updated_at: datetime

    @classmethod
    def from_service(cls, service: Service) -> "ServiceCardSchema":
        image = service.image
        if image is None:
            source = next(
                (c for c in service.changes if c.field == "source" and not c.applied),
                None,
            )
            if source and isinstance(source.new_value, dict):
                image = source.new_value.get("image")

        name, tag = (None, None)
        if image:
            parts = image.split(":", 1)
            name = parts[0]
            tag = parts[1] if len(parts) > 1 else "latest"

        status = "NOT_DEPLOYED_YET"
        production = service.latest_production_deployment
        if production is not None:
            status = production.status

        return cls(
            id=service.id,
            slug=service.slug,
            type="docker" if service.type == "DOCKER_REGISTRY" else "git",
            status=status,
            image=name,
            tag=tag,
            url=service.urls[0].domain if service.urls else None,
            volume_number=len(service.volumes),
            updated_at=service.updated_at,
        )
