async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


def _create_url(project_slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/create-service/docker/"


class TestDockerServiceCreate:
    async def test_create_simple_service(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug), json={"slug": "cache-db", "image": "redis:alpine"}
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "cache-db"

    async def test_slug_generated_if_not_specified(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug), json={"image": "redis:alpine"}
        )
        assert response.status_code == 201
        assert response.json()["slug"]

    async def test_slug_lowercased(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug),
            json={"slug": "Dky-Ops-fronT", "image": "ghcr.io/dky-ops-front:latest"},
        )
        assert response.status_code == 201
        assert response.json()["slug"] == "dky-ops-front"

    async def test_slug_accepts_underscores(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug),
            json={"slug": "hello_nginx", "image": "nginxdemos/hello:latest"},
        )
        assert response.status_code == 201

    async def test_sets_network_alias(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug), json={"slug": "valkey", "image": "valkey:alpine"}
        )
        assert response.status_code == 201
        assert response.json()["network_alias"].startswith("dky-valkey-")

    async def test_stages_source_change(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug), json={"slug": "cache", "image": "redis:alpine"}
        )
        assert response.status_code == 201
        changes = response.json()["unapplied_changes"]
        assert len(changes) == 1
        assert changes[0]["field"] == "source"
        assert changes[0]["new_value"]["image"] == "redis:alpine"

    async def test_bad_request(self, auth_client):
        slug = await _make_project(auth_client)
        response = await auth_client.post(_create_url(slug), json={})
        assert response.status_code == 400

    async def test_nonexistent_project(self, auth_client):
        response = await auth_client.post(
            _create_url("gh-clone"),
            json={"slug": "cache-db", "image": "redis:alpine"},
        )
        assert response.status_code == 404

    async def test_conflict_with_slug(self, auth_client):
        slug = await _make_project(auth_client)
        await auth_client.post(
            _create_url(slug), json={"slug": "cache-db", "image": "redis:alpine"}
        )
        response = await auth_client.post(
            _create_url(slug), json={"slug": "cache-db", "image": "redis:alpine"}
        )
        assert response.status_code == 409

    async def test_nonexistent_image(self, auth_client, fake_docker):
        slug = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(slug),
            json={"slug": "main-app", "image": fake_docker.NONEXISTANT_IMAGE},
        )
        assert response.status_code == 400
