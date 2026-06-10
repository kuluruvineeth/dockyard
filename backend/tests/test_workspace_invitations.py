from sqlalchemy import select

from app.models import User, Workspace, WorkspaceInvitation
from app.services.workspaces import get_current_workspace, get_membership


async def _make_user(session, username, password):
    u = User(username=username, is_active=True)
    u.set_password(password)
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


class TestWorkspaceInvitations:
    async def test_invite_and_accept_creates_membership(
        self, auth_client, session, user
    ):
        ws = await get_current_workspace(session, user)
        response = await auth_client.post(
            f"/api/workspaces/{ws.id}/invitations/",
            json={"username": "bob", "role": 30},
        )
        assert response.status_code == 201
        token = response.json()["token"]
        assert response.json()["role"] == 30

        bob = await _make_user(session, "bob", "bobpass123")
        login = await auth_client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "bobpass123"},
        )
        assert login.status_code == 201

        accept = await auth_client.post(f"/api/invitations/{token}/accept/")
        assert accept.status_code == 201

        membership = await get_membership(session, bob, ws.id)
        assert membership is not None
        assert membership.role == 30

        consumed = (
            await session.execute(
                select(WorkspaceInvitation).where(WorkspaceInvitation.token == token)
            )
        ).scalar_one_or_none()
        assert consumed is None

    async def test_accept_wrong_user_forbidden(self, auth_client, session, user):
        ws = await get_current_workspace(session, user)
        response = await auth_client.post(
            f"/api/workspaces/{ws.id}/invitations/", json={"username": "bob"}
        )
        token = response.json()["token"]

        await _make_user(session, "charlie", "charliepass1")
        await auth_client.post(
            "/api/auth/login",
            json={"username": "charlie", "password": "charliepass1"},
        )
        accept = await auth_client.post(f"/api/invitations/{token}/accept/")
        assert accept.status_code == 403

    async def test_non_member_cannot_invite(self, auth_client, session, user):
        other = Workspace(name="other", slug="other-ws")
        session.add(other)
        await session.commit()
        response = await auth_client.post(
            f"/api/workspaces/{other.id}/invitations/",
            json={"username": "bob"},
        )
        assert response.status_code == 403
