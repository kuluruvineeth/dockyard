import enum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel, generate_id


class WorkspaceRole(enum.IntEnum):
    GUEST = 10
    MEMBER = 30
    ADMIN = 40
    OWNER = 50


class Workspace(Base, TimestampedModel):
    __tablename__ = "workspace"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("ws_")
    )
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    memberships = relationship(
        "WorkspaceMembership",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class WorkspaceMembership(Base, TimestampedModel):
    __tablename__ = "workspace_membership"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("wsm_")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspace.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[int] = mapped_column(Integer, default=WorkspaceRole.MEMBER.value)

    workspace = relationship("Workspace", back_populates="memberships")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "workspace_id", name="uq_membership_user_workspace"
        ),
    )
