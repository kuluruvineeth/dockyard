from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, DBSession
from app.errors import (
    BadRequest,
    NotFound,
    PermissionDenied,
    ResourceConflict,
    ValidationException,
)
from app.models import WorkspaceInvitation, WorkspaceMembership, WorkspaceRole
from app.schemas.workspaces import (
    CreateInvitationRequest,
    WorkspaceInvitationSchema,
    WorkspaceMembershipSchema,
)
from app.services.workspaces import get_membership

router = APIRouter()

INVITATION_TTL = timedelta(days=7)


async def _require_admin(db, user, workspace_id) -> WorkspaceMembership:
    membership = await get_membership(db, user, workspace_id)
    if membership is None or membership.role < WorkspaceRole.ADMIN.value:
        raise PermissionDenied("You must be an admin or owner of this workspace.")
    return membership


@router.post(
    "/api/workspaces/{workspace_id}/invitations/",
    status_code=201,
    response_model=WorkspaceInvitationSchema,
)
async def create_invitation(
    workspace_id: str,
    body: CreateInvitationRequest,
    user: CurrentUser,
    db: DBSession,
):
    membership = await _require_admin(db, user, workspace_id)
    if body.role > membership.role:
        raise ValidationException(
            "role", "invalid", "You cannot grant a role higher than your own."
        )

    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        username=body.username,
        role=body.role,
        expires_at=datetime.now(timezone.utc) + INVITATION_TTL,
    )
    db.add(invitation)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ResourceConflict(
            f"`{body.username}` has already been invited to this workspace."
        )
    await db.refresh(invitation)
    return WorkspaceInvitationSchema.from_invitation(invitation)


@router.get(
    "/api/workspaces/{workspace_id}/invitations/",
    response_model=list[WorkspaceInvitationSchema],
)
async def list_invitations(workspace_id: str, user: CurrentUser, db: DBSession):
    await _require_admin(db, user, workspace_id)
    result = await db.execute(
        select(WorkspaceInvitation)
        .where(WorkspaceInvitation.workspace_id == workspace_id)
        .order_by(WorkspaceInvitation.created_at.desc())
    )
    return [WorkspaceInvitationSchema.from_invitation(inv) for inv in result.scalars()]


@router.post(
    "/api/invitations/{token}/accept/",
    status_code=201,
    response_model=WorkspaceMembershipSchema,
)
async def accept_invitation(token: str, user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(WorkspaceInvitation).where(WorkspaceInvitation.token == token)
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise NotFound("This invitation does not exist.")

    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise BadRequest("This invitation has expired.")

    if invitation.username != user.username:
        raise PermissionDenied("This invitation is not addressed to you.")

    existing = await get_membership(db, user, invitation.workspace_id)
    if existing is not None:
        await db.delete(invitation)
        await db.commit()
        return WorkspaceMembershipSchema.from_membership(existing)

    membership = WorkspaceMembership(
        user_id=user.id,
        workspace_id=invitation.workspace_id,
        role=invitation.role,
    )
    db.add(membership)
    await db.delete(invitation)
    await db.commit()
    await db.refresh(membership)
    return WorkspaceMembershipSchema.from_membership(membership)
