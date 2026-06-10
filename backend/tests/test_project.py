from app.models import Environment, Project
from app.services.workspaces import get_current_workspace


async def _make_project(session, owner, slug):
    workspace = await get_current_workspace(session, owner)
    project = Project(
        owner_id=owner.id,
        workspace_id=workspace.id if workspace is not None else None,
        slug=slug,
    )
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

    async def test_service_health_counts(self, auth_client, fake_docker):
        await auth_client.post("/api/projects/", json={"slug": "demo"})
        await auth_client.post(
            "/api/projects/demo/production/create-service/docker/",
            json={"slug": "app", "image": "caddy:2.8-alpine"},
        )
        await auth_client.post(
            "/api/projects/demo/production/create-service/docker/",
            json={"slug": "cache", "image": "redis:alpine"},
        )
        await auth_client.put(
            "/api/projects/demo/production/deploy-service/docker/app/"
        )

        response = await auth_client.get("/api/projects/")
        assert response.status_code == 200
        project = next(p for p in response.json() if p["slug"] == "demo")
        assert project["total_services"] == 2
        assert project["healthy_services"] == 1
        assert project["total_stack_services"] == 0
        assert project["healthy_stack_services"] == 0

        detail = await auth_client.get("/api/projects/demo/")
        assert detail.json()["total_services"] == 2
        assert detail.json()["healthy_services"] == 1


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

    async def test_provisions_production_network(self, auth_client, fake_docker):
        response = await auth_client.post("/api/projects/", json={"slug": "dky-net"})
        assert response.status_code == 201
        networks = fake_docker.networks.list()
        assert len(networks) == 1
        assert networks[0].name.startswith("net-")
        assert networks[0].attrs["Labels"]["is_production"] == "True"


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


class TestArchiveProject:
    async def test_archive_project(self, auth_client, fake_docker):
        await auth_client.post("/api/projects/", json={"slug": "demo"})
        await auth_client.post(
            "/api/projects/demo/production/create-service/docker/",
            json={"slug": "app", "image": "redis:alpine"},
        )
        await auth_client.put(
            "/api/projects/demo/production/deploy-service/docker/app/"
        )
        assert len(fake_docker.services.list()) == 1

        response = await auth_client.delete("/api/projects/demo/")
        assert response.status_code == 204

        get = await auth_client.get("/api/projects/demo/")
        assert get.status_code == 404
        assert len(fake_docker.services.list()) == 0

    async def test_archive_removes_project_networks(self, auth_client, fake_docker):
        await auth_client.post("/api/projects/", json={"slug": "demo"})
        assert len(fake_docker.networks.list()) > 0
        response = await auth_client.delete("/api/projects/demo/")
        assert response.status_code == 204
        assert len(fake_docker.networks.list()) == 0

    async def test_archive_non_existing_project(self, auth_client):
        response = await auth_client.delete("/api/projects/nope/")
        assert response.status_code == 404
