from datetime import timedelta
from unittest.mock import patch

from app.session import now as real_now


class TestAuthLoginView:
    async def test_successful_login(self, client, user):
        response = await client.post(
            "/api/auth/login",
            json={"username": "kuluruvineeth", "password": "password"},
        )
        assert response.status_code == 201
        assert response.cookies.get("sessionid") is not None

    async def test_login_redirect_to_if_provided(self, client, user):
        redirect_path = "https://example-service-dpl_xyz.dky.local/"
        response = await client.post(
            "/api/auth/login",
            params={"redirect_to": redirect_path},
            json={"username": "kuluruvineeth", "password": "password"},
        )
        assert response.status_code == 302
        assert response.cookies.get("sessionid") is not None
        assert response.headers.get("location") == redirect_path

    async def test_unsuccessful_login(self, client, user):
        response = await client.post(
            "/api/auth/login",
            json={"username": "user", "password": "bad_password"},
        )
        assert response.status_code == 401

    async def test_bad_request(self, client):
        response = await client.post("/api/auth/login", json={})
        assert response.status_code == 400


class TestAuthMeView:
    async def test_authed(self, auth_client):
        response = await auth_client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json().get("user") is not None
        assert response.json()["user"]["username"] == "kuluruvineeth"

    async def test_authed_renew_session(self, auth_client):
        fixed_time = real_now() + timedelta(days=13)
        with patch("app.routers.auth.now", return_value=fixed_time):
            response = await auth_client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.cookies.get("sessionid") is not None

    async def test_unauthed(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401


class TestAuthLogoutView:
    async def test_successful_logout(self, auth_client):
        response = await auth_client.delete("/api/auth/logout")
        assert response.status_code == 204

    async def test_unsuccessful_logout(self, client):
        response = await client.delete("/api/auth/logout")
        assert response.status_code == 401


class TestCSRFView:
    async def test_successful(self, client):
        response = await client.get("/api/csrf")
        assert response.status_code == 200
        assert response.cookies.get("csrftoken") is not None
