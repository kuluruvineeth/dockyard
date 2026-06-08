import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampedModel, generate_id


class DeploymentStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    CANCELLED = "CANCELLED"
    CANCELLING = "CANCELLING"
    FAILED = "FAILED"
    PREPARING = "PREPARING"
    BUILDING = "BUILDING"
    STARTING = "STARTING"
    RESTARTING = "RESTARTING"
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    REMOVED = "REMOVED"
    SLEEPING = "SLEEPING"


class DeploymentSlot(str, enum.Enum):
    BLUE = "BLUE"
    GREEN = "GREEN"


class DeploymentTriggerMethod(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    API = "API"


class Deployment(Base, TimestampedModel):
    __tablename__ = "deployment"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("dpl_dkr_")
    )
    slot: Mapped[str] = mapped_column(String(10), default=DeploymentSlot.BLUE.value)
    status: Mapped[str] = mapped_column(
        String(20), default=DeploymentStatus.QUEUED.value
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current_production: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    service_id: Mapped[str] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), index=True
    )
    service_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    commit_message: Mapped[str] = mapped_column(Text, default="update service")
    trigger_method: Mapped[str] = mapped_column(
        String(15), default=DeploymentTriggerMethod.MANUAL.value
    )
    commit_sha: Mapped[str | None] = mapped_column(String(45), nullable=True)
    commit_author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    pull_request_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ignore_build_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    build_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    build_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_redeploy_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("deployment.id", ondelete="SET NULL"), nullable=True
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    service = relationship("Service", back_populates="deployments")
    changes = relationship("DeploymentChange", back_populates="deployment")

    __table_args__ = (Index("ix_deployment_status", "status"),)

    @property
    def unprefixed_hash(self) -> str:
        return self.id.rsplit("_", 1)[-1]

    @staticmethod
    def get_next_deployment_slot(latest_production_deployment) -> str:
        if (
            latest_production_deployment is not None
            and latest_production_deployment.slot == DeploymentSlot.BLUE.value
            and latest_production_deployment.status != DeploymentStatus.FAILED.value
        ):
            return DeploymentSlot.GREEN.value
        return DeploymentSlot.BLUE.value
