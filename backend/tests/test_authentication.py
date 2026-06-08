from datetime import timedelta
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import User
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

    async def test_login_ratelimit(self, client):
        response = None
        for _ in range(6):
            response = await client.post("/api/auth/login", json={})
        assert response.status_code == 429


class TestUserExistenceAndCreation:
    async def test_check_user_existence_no_user(self, client):
        response = await client.get("/api/auth/check-user-existence")
        assert response.status_code == 200
        assert response.json().get("exists") is False

    async def test_check_user_existence_with_user(self, client, user):
        response = await client.get("/api/auth/check-user-existence")
        assert response.status_code == 200
        assert response.json().get("exists") is True

    async def test_create_user_success(self, client):
        response = await client.post(
            "/api/auth/create-initial-user",
            json={"username": "mohai", "password": "mohai123"},
        )
        assert response.status_code == 201
        assert response.cookies.get("sessionid") is not None

    async def test_create_user_already_exists(self, client, user):
        response = await client.post(
            "/api/auth/create-initial-user",
            json={"username": "fred", "password": "fred12345"},
        )
        assert response.status_code == 403

    async def test_create_user_bad_request(self, client):
        response = await client.post("/api/auth/create-initial-user", json={})
        assert response.status_code == 400

    async def test_create_user_weak_password(self, client):
        bad_passwords = [
            "123",
            "12345678",
            "admin123",
            "password123",
            "qwerty123",
            "ALLUPPERCASE",
            "alllowercase",
            "!@#$%^#$%^&*(-)",
        ]
        for index, password in enumerate(bad_passwords):
            response = await client.post(
                "/api/auth/create-initial-user",
                json={"username": f"fred{index}", "password": password},
            )
            assert response.status_code == 400
            error = response.json().get("errors", [])[0]
            assert error.get("attr") == "password"

    async def test_create_user_invalid_username(self, client):
        response = await client.post(
            "/api/auth/create-initial-user",
            json={"username": "invalid-user name", "password": "validpassword123"},
        )
        assert response.status_code == 400

    async def test_create_user_should_authenticate_user(self, client):
        response = await client.post(
            "/api/auth/create-initial-user",
            json={"username": "mocherif", "password": "validpassword123"},
        )
        assert response.status_code == 201
        response = await client.get("/api/auth/me")
        assert response.status_code == 200


class TestChangePasswordView:
    _payload = {
        "current_password": "password",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123",
    }

    async def test_successful_password_change(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password", json=self._payload
        )
        assert response.status_code == 200
        assert (await auth_client.get("/api/auth/me")).status_code == 200

    async def test_requires_authentication(self, client):
        response = await client.post("/api/auth/change-password", json=self._payload)
        assert response.status_code == 401

    async def test_invalid_current_password(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={**self._payload, "current_password": "wrongpassword"},
        )
        assert response.status_code == 400
        error = response.json()["errors"][0]
        assert error["attr"] == "current_password"
        assert error["code"] == "invalid"

    async def test_mismatched_confirmation(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={**self._payload, "confirm_password": "differentpassword123"},
        )
        assert response.status_code == 400
        assert response.json()["errors"][0]["attr"] == "confirm_password"

    async def test_weak_password(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "password",
                "new_password": "123",
                "confirm_password": "123",
            },
        )
        assert response.status_code == 400
        error = response.json()["errors"][0]
        assert error["attr"] == "new_password"
        assert error["code"] == "min_length"

    async def test_common_password(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "password",
                "new_password": "password123",
                "confirm_password": "password123",
            },
        )
        assert response.status_code == 400
        assert response.json()["errors"][0]["attr"] == "new_password"

    async def test_numeric_only_password(self, auth_client):
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "password",
                "new_password": "889955113366",
                "confirm_password": "889955113366",
            },
        )
        assert response.status_code == 400
        error = response.json()["errors"][0]
        assert error["attr"] == "new_password"
        assert error["code"] == "password_entirely_numeric"

    async def test_missing_fields(self, auth_client):
        response = await auth_client.post("/api/auth/change-password", json={})
        assert response.status_code == 400
        error = response.json()["errors"][0]
        assert error["code"] == "required"
        assert error["attr"] == "current_password"

    async def test_invalidates_other_sessions(self, auth_client, user):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client2:
            assert (
                await client2.post(
                    "/api/auth/login",
                    json={"username": "kuluruvineeth", "password": "password"},
                )
            ).status_code == 201

            assert (
                await auth_client.post("/api/auth/change-password", json=self._payload)
            ).status_code == 200

            assert (await auth_client.get("/api/auth/me")).status_code == 200
            assert (await client2.get("/api/auth/me")).status_code == 401


class TestUpdateProfileView:
    async def test_successful_profile_update(self, auth_client):
        response = await auth_client.patch(
            "/api/auth/update-profile",
            json={"username": "newusername", "first_name": "John", "last_name": "Doe"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "newusername"

    async def test_requires_authentication(self, client):
        response = await client.patch(
            "/api/auth/update-profile", json={"username": "newusername"}
        )
        assert response.status_code == 401

    async def test_duplicate_username(self, auth_client, session):
        other = User(username="existinguser", is_active=True)
        other.set_password("password123")
        session.add(other)
        await session.commit()

        response = await auth_client.patch(
            "/api/auth/update-profile", json={"username": "existinguser"}
        )
        assert response.status_code == 409

    async def test_invalid_username_format(self, auth_client):
        response = await auth_client.patch(
            "/api/auth/update-profile", json={"username": "fred kiss3"}
        )
        assert response.status_code == 400
        error = response.json()["errors"][0]
        assert error["code"] == "invalid"
        assert error["attr"] == "username"

    async def test_same_username_allowed(self, auth_client):
        response = await auth_client.patch(
            "/api/auth/update-profile", json={"username": "kuluruvineeth"}
        )
        assert response.status_code == 200

    async def test_partial_data(self, auth_client):
        response = await auth_client.patch(
            "/api/auth/update-profile", json={"first_name": "John"}
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "John"


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
