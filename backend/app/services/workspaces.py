from sqlalchemy import select

from app.models import Workspace, WorkspaceMembership, WorkspaceRole


async def create_default_workspace(db, user) -> Workspace:
    workspace = Workspace(
        name=f"{user.username}'s workspace", slug=user.username.lower()
    )
    db.add(workspace)
    await db.flush()
    membership = WorkspaceMembership(
        user_id=user.id,
        workspace_id=workspace.id,
        role=WorkspaceRole.OWNER.value,
    )
    db.add(membership)
    return workspace


async def get_membership(db, user, workspace_id) -> WorkspaceMembership | None:
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user.id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def get_current_workspace(db, user) -> Workspace | None:
    result = await db.execute(
        select(Workspace)
        .join(
            WorkspaceMembership,
            Workspace.id == WorkspaceMembership.workspace_id,
        )
        .where(WorkspaceMembership.user_id == user.id)
        .order_by(WorkspaceMembership.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()
