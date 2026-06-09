from sqlalchemy import BigInteger, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class ServiceMetrics(Base, TimestampedModel):
    __tablename__ = "service_metrics"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("metric_")
    )
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    net_tx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    net_rx_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    disk_read_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    disk_writes_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    service_id: Mapped[str] = mapped_column(
        ForeignKey("service.id", ondelete="CASCADE"), index=True
    )
    deployment_id: Mapped[str] = mapped_column(
        ForeignKey("deployment.id", ondelete="CASCADE"), index=True
    )
