async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


def _env_url(project_slug):
    return f"/api/projects/{project_slug}/environments/"


def _env_detail_url(project_slug, env_slug):
    return f"/api/projects/{project_slug}/environments/{env_slug}/"


class TestCreateEnvironment:
    async def test_create_empty_environment(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(_env_url(p), json={"name": "staging"})
        assert response.status_code == 201
        assert response.json()["name"] == "staging"
        assert response.json()["is_preview"] is False

    async def test_create_lowercases_name(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(_env_url(p), json={"name": "Staging"})
        assert response.status_code == 201
        assert response.json()["name"] == "staging"

    async def test_create_already_existing_causes_conflict(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(_env_url(p), json={"name": "staging"})
        response = await auth_client.post(_env_url(p), json={"name": "staging"})
        assert response.status_code == 409

    async def test_create_production_conflicts(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(_env_url(p), json={"name": "production"})
        assert response.status_code == 409

    async def test_create_appears_in_project(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(_env_url(p), json={"name": "staging"})
        project = await auth_client.get(f"/api/projects/{p}/")
        names = [e["name"] for e in project.json()["environments"]]
        assert "staging" in names
        assert "production" in names

    async def test_create_creates_network(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        before = len(fake_docker.networks.list())
        await auth_client.post(_env_url(p), json={"name": "staging"})
        assert len(fake_docker.networks.list()) == before + 1

    async def test_create_invalid_name(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(_env_url(p), json={"name": "bad name!"})
        assert response.status_code == 400

    async def test_create_project_non_existing(self, auth_client):
        response = await auth_client.post(_env_url("nope"), json={"name": "staging"})
        assert response.status_code == 404


class TestDeleteEnvironment:
    async def test_delete_environment(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(_env_url(p), json={"name": "staging"})
        response = await auth_client.delete(_env_detail_url(p, "staging"))
        assert response.status_code == 204
        project = await auth_client.get(f"/api/projects/{p}/")
        names = [e["name"] for e in project.json()["environments"]]
        assert "staging" not in names

    async def test_cannot_delete_production(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.delete(_env_detail_url(p, "production"))
        assert response.status_code == 409

    async def test_delete_non_existing(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.delete(_env_detail_url(p, "nope"))
        assert response.status_code == 404


def _var_url(project_slug, env="production"):
    return f"/api/projects/{project_slug}/environments/{env}/variables/"


class TestEnvironmentVariables:
    async def test_create_variable(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _var_url(p), json={"key": "SHARED", "value": "hello"}
        )
        assert response.status_code == 201
        assert response.json()["key"] == "SHARED"
        assert response.json()["value"] == "hello"

    async def test_list_variables(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(_var_url(p), json={"key": "A", "value": "1"})
        response = await auth_client.get(_var_url(p))
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_duplicate_key_conflicts(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(_var_url(p), json={"key": "A", "value": "1"})
        response = await auth_client.post(_var_url(p), json={"key": "A", "value": "2"})
        assert response.status_code == 409

    async def test_delete_variable(self, auth_client):
        p = await _make_project(auth_client)
        created = await auth_client.post(_var_url(p), json={"key": "A", "value": "1"})
        variable_id = created.json()["id"]
        response = await auth_client.delete(f"{_var_url(p)}{variable_id}/")
        assert response.status_code == 204
        listing = await auth_client.get(_var_url(p))
        assert len(listing.json()) == 0

    async def test_variable_injected_into_deploy(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        await auth_client.post(
            _var_url(p), json={"key": "SHARED_KEY", "value": "shared_val"}
        )
        await auth_client.post(
            f"/api/projects/{p}/production/create-service/docker/",
            json={"slug": "app", "image": "redis:alpine"},
        )
        await auth_client.put(
            f"/api/projects/{p}/production/deploy-service/docker/app/"
        )
        swarm = fake_docker.services.list()[0]
        assert "SHARED_KEY=shared_val" in swarm.env
