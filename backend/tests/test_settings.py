class TestSettings:
    async def test_get_api_settings(self, auth_client):
        response = await auth_client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "root_domain" in data
        assert "app_domain" in data
        assert "image_version" in data
        assert "commit_sha" in data

    async def test_get_api_settings_requires_auth(self, client):
        response = await client.get("/api/settings")
        assert response.status_code == 401

    async def test_server_resource_limits(self, auth_client):
        response = await auth_client.get("/api/server/resource-limits")
        assert response.status_code == 200
        data = response.json()
        assert data["no_of_cpus"] == 4
        assert data["max_memory_in_bytes"] == 8 * 1024**3

    async def test_server_resource_limits_requires_auth(self, client):
        response = await client.get("/api/server/resource-limits")
        assert response.status_code == 401
