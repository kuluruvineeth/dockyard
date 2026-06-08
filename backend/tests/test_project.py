from app.models import Environment, Project


async def _make_project(session, owner, slug):
    project = Project(owner_id=owner.id, slug=slug)
    project.environments = [Environment(name="production")]
    session.add(project)
    await session.commit()
    return project


class TestProjectListView:
    async def test_default(self, auth_client, user, session):
        await _make_project(session, user, "thullo")
        response = await auth_client.get("/api/projects/")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_list_filter_slug(self, auth_client, user, session):
        for slug in ["gh-clone", "gh-next", "dkyops"]:
            await _make_project(session, user, slug)
        response = await auth_client.get("/api/projects/", params={"slug": "gh"})
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_unauthed(self, client):
        response = await client.get("/api/projects/")
        assert response.status_code == 401


class TestProjectCreateView:
    async def test_successfully_create_project(self, auth_client):
        response = await auth_client.post("/api/projects/", json={"slug": "dky-ops"})
        assert response.status_code == 201

    async def test_create_project_with_description(self, auth_client):
        response = await auth_client.post(
            "/api/projects/",
            json={
                "slug": "dky-ops",
                "description": "self-hosted PaaS built on docker swarm",
            },
        )
        assert response.status_code == 201
        assert (
            response.json()["description"] == "self-hosted PaaS built on docker swarm"
        )

    async def test_generate_slug_if_not_specified(self, auth_client):
        response = await auth_client.post("/api/projects/", json={})
        assert response.status_code == 201
        assert response.json()["slug"] is not None

    async def test_unique_slug(self, auth_client, user, session):
        await _make_project(session, user, "dky-ops")
        response = await auth_client.post("/api/projects/", json={"slug": "dky-ops"})
        assert response.status_code == 409

    async def test_invalid_slug(self, auth_client):
        response = await auth_client.post("/api/projects/", json={"slug": "dky Ops"})
        assert response.status_code == 400

    async def test_slug_is_always_lowercase(self, auth_client):
        response = await auth_client.post("/api/projects/", json={"slug": "dky-Ops"})
        assert response.status_code == 201
        assert response.json()["slug"] == "dky-ops"

    async def test_creates_production_environment(self, auth_client):
        response = await auth_client.post("/api/projects/", json={"slug": "dky-ops"})
        assert response.status_code == 201
        envs = response.json()["environments"]
        assert len(envs) == 1
        assert envs[0]["name"] == "production"


class TestProjectUpdateView:
    async def test_successfully_update_slug(self, auth_client, user, session):
        await _make_project(session, user, "gh-next")
        response = await auth_client.put(
            "/api/projects/gh-next/", json={"slug": "kisshub"}
        )
        assert response.status_code == 200
        assert response.json()["slug"] == "kisshub"

    async def test_successfully_update_description(self, auth_client, user, session):
        await _make_project(session, user, "gh-next")
        response = await auth_client.put(
            "/api/projects/gh-next/",
            json={"description": "Clone of Github built-on nextjs app router"},
        )
        assert response.status_code == 200
        assert (
            response.json()["description"]
            == "Clone of Github built-on nextjs app router"
        )

    async def test_prevent_empty_update(self, auth_client, user, session):
        await _make_project(session, user, "gh-next")
        response = await auth_client.put("/api/projects/gh-next/", json={})
        assert response.status_code == 400

    async def test_bad_request(self, auth_client, user, session):
        await _make_project(session, user, "dky-ops")
        response = await auth_client.put(
            "/api/projects/dky-ops/", json={"slug": "Dky Ops"}
        )
        assert response.status_code == 400

    async def test_non_existent(self, auth_client):
        response = await auth_client.put(
            "/api/projects/dky-ops/", json={"slug": "zenops"}
        )
        assert response.status_code == 404

    async def test_already_existing_slug(self, auth_client, user, session):
        await _make_project(session, user, "gh-clone")
        await _make_project(session, user, "dky-ops")
        response = await auth_client.put(
            "/api/projects/dky-ops/", json={"slug": "gh-clone"}
        )
        assert response.status_code == 409

    async def test_can_rename_to_self(self, auth_client, user, session):
        await _make_project(session, user, "dky-ops")
        response = await auth_client.put(
            "/api/projects/dky-ops/", json={"slug": "dky-ops"}
        )
        assert response.status_code == 200


class TestProjectGetView:
    async def test_successfully_get_project(self, auth_client, user, session):
        await _make_project(session, user, "gh-clone")
        response = await auth_client.get("/api/projects/gh-clone/")
        assert response.status_code == 200

    async def test_non_existent(self, auth_client):
        response = await auth_client.get("/api/projects/dky-ops/")
        assert response.status_code == 404
