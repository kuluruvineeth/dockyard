from app.models import User, Workspace, WorkspaceMembership, WorkspaceRole
from app.services.workspaces import get_current_workspace


async def _user_with_role(session, username, workspace_id, role):
    u = User(username=username, is_active=True)
    u.set_password(f"{username}pass1")
    session.add(u)
    await session.flush()
    session.add(
        WorkspaceMembership(user_id=u.id, workspace_id=workspace_id, role=role.value)
    )
    await session.commit()
    return u


class TestRoleEnforcement:
    async def test_guest_cannot_create_project(self, auth_client, session):
        guest = User(username="guest", is_active=True)
        guest.set_password("guestpass1")
        session.add(guest)
        await session.flush()
        ws = Workspace(name="gw", slug="gw")
        session.add(ws)
        await session.flush()
        session.add(
            WorkspaceMembership(
                user_id=guest.id,
                workspace_id=ws.id,
                role=WorkspaceRole.GUEST.value,
            )
        )
        await session.commit()

        await auth_client.post(
            "/api/auth/login",
            json={"username": "guest", "password": "guestpass1"},
        )
        response = await auth_client.post("/api/projects/", json={"slug": "p"})
        assert response.status_code == 403

    async def test_member_can_create_project(self, auth_client, session):
        member = User(username="member", is_active=True)
        member.set_password("memberpass1")
        session.add(member)
        await session.flush()
        ws = Workspace(name="mw", slug="mw")
        session.add(ws)
        await session.flush()
        session.add(
            WorkspaceMembership(
                user_id=member.id,
                workspace_id=ws.id,
                role=WorkspaceRole.MEMBER.value,
            )
        )
        await session.commit()

        await auth_client.post(
            "/api/auth/login",
            json={"username": "member", "password": "memberpass1"},
        )
        response = await auth_client.post("/api/projects/", json={"slug": "memberproj"})
        assert response.status_code == 201

    async def test_list_workspaces_includes_role(self, auth_client, session, user):
        response = await auth_client.get("/api/workspaces/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["role"] == WorkspaceRole.OWNER.value

    async def test_owner_can_delete_workspace(self, auth_client, session, user):
        ws = await get_current_workspace(session, user)
        response = await auth_client.delete(f"/api/workspaces/{ws.id}/")
        assert response.status_code == 204
        listing = await auth_client.get("/api/workspaces/")
        assert listing.json() == []

    async def test_admin_cannot_delete_workspace(self, auth_client, session, user):
        ws = await get_current_workspace(session, user)
        await _user_with_role(session, "adm", ws.id, WorkspaceRole.ADMIN)
        await auth_client.post(
            "/api/auth/login", json={"username": "adm", "password": "admpass1"}
        )
        response = await auth_client.delete(f"/api/workspaces/{ws.id}/")
        assert response.status_code == 403


class TestResourceRBAC:
    async def _add_member(self, session, ws_id, username, role):
        u = User(username=username, is_active=True)
        u.set_password(f"{username}pass1")
        session.add(u)
        await session.flush()
        session.add(
            WorkspaceMembership(user_id=u.id, workspace_id=ws_id, role=role.value)
        )
        await session.commit()

    async def test_guest_reads_but_cannot_mutate(self, auth_client, session, user):
        await auth_client.post("/api/projects/", json={"slug": "shared"})
        ws = await get_current_workspace(session, user)
        await self._add_member(session, ws.id, "rguest", WorkspaceRole.GUEST)

        await auth_client.post(
            "/api/auth/login",
            json={"username": "rguest", "password": "rguestpass1"},
        )
        assert (await auth_client.get("/api/projects/shared/")).status_code == 200

        create = await auth_client.post(
            "/api/projects/shared/production/create-service/docker/",
            json={"slug": "s", "image": "nginx:latest"},
        )
        assert create.status_code == 403
        env = await auth_client.post(
            "/api/projects/shared/environments/", json={"name": "staging"}
        )
        assert env.status_code == 403

    async def test_non_owner_member_can_access_and_mutate(
        self, auth_client, session, user
    ):
        await auth_client.post("/api/projects/", json={"slug": "shared2"})
        ws = await get_current_workspace(session, user)
        await self._add_member(session, ws.id, "rmember", WorkspaceRole.MEMBER)

        await auth_client.post(
            "/api/auth/login",
            json={"username": "rmember", "password": "rmemberpass1"},
        )
        create = await auth_client.post(
            "/api/projects/shared2/production/create-service/docker/",
            json={"slug": "svc", "image": "nginx:latest"},
        )
        assert create.status_code == 201
