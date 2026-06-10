from datetime import datetime

from pydantic import BaseModel, Field

from app.models import WorkspaceRole


class CreateInvitationRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    role: int = WorkspaceRole.MEMBER.value


class WorkspaceInvitationSchema(BaseModel):
    id: str
    workspace_id: str
    username: str
    token: str
    role: int
    expires_at: datetime

    @classmethod
    def from_invitation(cls, invitation) -> "WorkspaceInvitationSchema":
        return cls(
            id=invitation.id,
            workspace_id=invitation.workspace_id,
            username=invitation.username,
            token=invitation.token,
            role=invitation.role,
            expires_at=invitation.expires_at,
        )


class WorkspaceMembershipSchema(BaseModel):
    id: str
    workspace_id: str
    user_id: int
    role: int

    @classmethod
    def from_membership(cls, membership) -> "WorkspaceMembershipSchema":
        return cls(
            id=membership.id,
            workspace_id=membership.workspace_id,
            user_id=membership.user_id,
            role=membership.role,
        )
