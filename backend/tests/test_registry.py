CRED_URL = "/api/registry-credentials/"


async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


class TestRegistryCredentials:
    async def test_create(self, auth_client):
        response = await auth_client.post(
            CRED_URL,
            json={
                "name": "ghcr",
                "url": "https://ghcr.io",
                "username": "me",
                "password": "secret",
                "registry_type": "GITHUB",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "ghcr"
        assert data["registry_type"] == "GITHUB"
        # the password must never be returned
        assert "password" not in data

    async def test_list(self, auth_client):
        await auth_client.post(
            CRED_URL,
            json={"name": "a", "url": "https://x", "username": "u", "password": "p"},
        )
        response = await auth_client.get(CRED_URL)
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_delete(self, auth_client):
        created = await auth_client.post(
            CRED_URL,
            json={"name": "a", "url": "https://x", "username": "u", "password": "p"},
        )
        credential_id = created.json()["id"]
        response = await auth_client.delete(f"{CRED_URL}{credential_id}/")
        assert response.status_code == 204
        listing = await auth_client.get(CRED_URL)
        assert len(listing.json()) == 0

    async def test_invalid_registry_type(self, auth_client):
        response = await auth_client.post(
            CRED_URL,
            json={
                "name": "a",
                "url": "https://x",
                "username": "u",
                "password": "p",
                "registry_type": "BOGUS",
            },
        )
        assert response.status_code == 400

    async def test_create_service_with_credentials(self, auth_client):
        p = await _make_project(auth_client)
        created = await auth_client.post(
            CRED_URL,
            json={"name": "a", "url": "https://x", "username": "u", "password": "p"},
        )
        credential_id = created.json()["id"]
        response = await auth_client.post(
            f"/api/projects/{p}/production/create-service/docker/",
            json={
                "slug": "app",
                "image": "private/img:latest",
                "container_registry_credentials_id": credential_id,
            },
        )
        assert response.status_code == 201

    async def test_create_service_with_nonexistent_credentials(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            f"/api/projects/{p}/production/create-service/docker/",
            json={
                "slug": "app",
                "image": "redis:alpine",
                "container_registry_credentials_id": "reg_cred_doesnotexist",
            },
        )
        assert response.status_code == 400
