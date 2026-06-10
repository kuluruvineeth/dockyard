from sqlalchemy import select

from app.models import (
    Project,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from app.routers.projects import accessible_projects_filter
from app.services.workspaces import (
    create_default_workspace,
    get_current_workspace,
)


class TestWorkspaceCreation:
    async def test_signup_creates_owner_workspace(self, client, session):
        response = await client.post(
            "/api/auth/create-initial-user",
            json={"username": "alice", "password": "Str0ngP@ssw0rd!"},
        )
        assert response.status_code == 201

        alice = (
            await session.execute(select(User).where(User.username == "alice"))
        ).scalar_one()
        membership = (
            await session.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.user_id == alice.id
                )
            )
        ).scalar_one()
        assert membership.role == WorkspaceRole.OWNER.value

        workspace = (
            await session.execute(
                select(Workspace).where(Workspace.id == membership.workspace_id)
            )
        ).scalar_one()
        assert workspace.slug == "alice"


class TestWorkspaceScoping:
    async def test_project_scoped_to_current_workspace(
        self, auth_client, session, user
    ):
        response = await auth_client.post("/api/projects/", json={"slug": "myproj"})
        assert response.status_code == 201

        project = (
            await session.execute(select(Project).where(Project.slug == "myproj"))
        ).scalar_one()
        workspace = await get_current_workspace(session, user)
        assert project.workspace_id == workspace.id

        listing = await auth_client.get("/api/projects/")
        assert any(p["slug"] == "myproj" for p in listing.json())

    async def test_project_invisible_across_workspaces(self, auth_client, session):
        await auth_client.post("/api/projects/", json={"slug": "secret"})

        bob = User(username="bob", is_active=True)
        bob.set_password("x")
        session.add(bob)
        await session.flush()
        await create_default_workspace(session, bob)
        await session.commit()

        bob_projects = (
            (
                await session.execute(
                    select(Project).where(accessible_projects_filter(bob))
                )
            )
            .scalars()
            .all()
        )
        assert len(bob_projects) == 0
