from app.services.compose_processor import parse_compose

COMPOSE = """
services:
  web:
    image: nginx:alpine
    ports:
      - "8080:80"
    environment:
      - APP_ENV=production
  cache:
    image: redis:alpine
    command: redis-server --save ""
"""


async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


def _create_url(project_slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/create-compose-stack/"


class TestComposeProcessor:
    def test_parses_services(self):
        parsed = parse_compose(COMPOSE)
        assert set(parsed.keys()) == {"web", "cache"}
        assert parsed["web"]["image"] == "nginx:alpine"
        assert parsed["web"]["ports"] == [{"host": 8080, "forwarded": 80}]
        assert parsed["web"]["environment"] == {"APP_ENV": "production"}
        assert parsed["cache"]["command"] == 'redis-server --save ""'

    def test_empty_compose(self):
        assert parse_compose("") == {}
        assert parse_compose("services: {}") == {}

    def test_environment_as_mapping(self):
        parsed = parse_compose(
            "services:\n  a:\n    image: x\n    environment:\n      KEY: val"
        )
        assert parsed["a"]["environment"] == {"KEY": "val"}


class TestCreateComposeStack:
    async def test_create_stack(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "myapp"
        slugs = {s["slug"] for s in data["services"]}
        assert slugs == {"myapp-web", "myapp-cache"}

    async def test_stack_services_are_real_services(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        # the created services show up in the environment service list
        listing = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        slugs = {s["slug"] for s in listing.json()}
        assert "myapp-web" in slugs
        assert "myapp-cache" in slugs

    async def test_web_service_has_staged_changes(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        details = await auth_client.get(
            f"/api/projects/{p}/production/service-details/myapp-web/"
        )
        fields = {c["field"] for c in details.json()["unapplied_changes"]}
        assert "source" in fields
        assert "ports" in fields
        assert "env_variables" in fields

    async def test_no_deployable_services(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(p),
            json={
                "slug": "myapp",
                "contents": "services:\n  build-only:\n    build: .",
            },
        )
        assert response.status_code == 400

    async def test_conflict(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        response = await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        assert response.status_code == 409


def _deploy_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/deploy-compose-stack/{slug}/"


class TestDeployComposeStack:
    async def test_deploy_stack_deploys_all_services(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        response = await auth_client.put(_deploy_url(p, "myapp"))
        assert response.status_code == 200
        assert len(fake_docker.services.list()) == 2

    async def test_deploy_stack_marks_services_healthy(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        await auth_client.put(_deploy_url(p, "myapp"))
        listing = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        statuses = {s["slug"]: s["status"] for s in listing.json()}
        assert statuses["myapp-web"] == "HEALTHY"
        assert statuses["myapp-cache"] == "HEALTHY"

    async def test_deploy_nonexistent_stack(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.put(_deploy_url(p, "nope"))
        assert response.status_code == 404

    async def test_list_stacks(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        response = await auth_client.get(
            f"/api/projects/{p}/production/compose-stacks/"
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["slug"] == "myapp"


def _archive_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/compose-stack/{slug}/"


class TestArchiveComposeStack:
    async def test_archive_stack(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p), json={"slug": "myapp", "contents": COMPOSE}
        )
        await auth_client.put(_deploy_url(p, "myapp"))
        assert len(fake_docker.services.list()) == 2

        response = await auth_client.delete(_archive_url(p, "myapp"))
        assert response.status_code == 204
        assert len(fake_docker.services.list()) == 0

        stacks = await auth_client.get(f"/api/projects/{p}/production/compose-stacks/")
        assert len(stacks.json()) == 0
        listing = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        assert len(listing.json()) == 0

    async def test_archive_nonexistent_stack(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.delete(_archive_url(p, "nope"))
        assert response.status_code == 404
