async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


def _create_url(project_slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/create-service/docker/"


def _details_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/service-details/{slug}/"


async def _make_service(auth_client, project_slug, slug, image="redis:alpine"):
    response = await auth_client.post(
        _create_url(project_slug), json={"slug": slug, "image": image}
    )
    assert response.status_code == 201
    return slug


def _changes_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/request-service-changes/{slug}/"


def _cancel_url(project_slug, slug, change_id, env_slug="production"):
    return (
        f"/api/projects/{project_slug}/{env_slug}/"
        f"cancel-service-changes/{slug}/{change_id}/"
    )


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


class TestDockerServiceGet:
    async def test_get_service_successful(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        response = await auth_client.get(_details_url(p, "cache-db"))
        assert response.status_code == 200
        assert response.json()["slug"] == "cache-db"

    async def test_get_service_non_existing(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.get(_details_url(p, "cache-db"))
        assert response.status_code == 404

    async def test_get_service_wrong_project(self, auth_client):
        p1 = await _make_project(auth_client, "kiss-cam")
        p2 = await _make_project(auth_client, "camly")
        await _make_service(auth_client, p1, "cache-db")
        response = await auth_client.get(_details_url(p2, "cache-db"))
        assert response.status_code == 404


class TestDockerServiceUpdate:
    async def test_update_slug(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        response = await auth_client.patch(
            _details_url(p, "cache-db"), json={"slug": "redis-cache"}
        )
        assert response.status_code == 200
        assert response.json()["slug"] == "redis-cache"

    async def test_bad_request(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        response = await auth_client.patch(
            _details_url(p, "cache-db"), json={"slug": "Cache DB"}
        )
        assert response.status_code == 400

    async def test_non_existent(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.patch(
            _details_url(p, "cache-db"), json={"slug": "x"}
        )
        assert response.status_code == 404

    async def test_already_existing_slug(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        await _make_service(auth_client, p, "other-svc")
        response = await auth_client.patch(
            _details_url(p, "cache-db"), json={"slug": "other-svc"}
        )
        assert response.status_code == 409

    async def test_rename_to_self(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        response = await auth_client.patch(
            _details_url(p, "cache-db"), json={"slug": "cache-db"}
        )
        assert response.status_code == 200


class TestRequestServiceChanges:
    async def test_request_source_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "source",
                "type": "UPDATE",
                "new_value": {"image": "nginx:latest"},
            },
        )
        assert response.status_code == 200
        sources = [
            c for c in response.json()["unapplied_changes"] if c["field"] == "source"
        ]
        assert len(sources) == 1
        assert sources[0]["new_value"]["image"] == "nginx:latest"

    async def test_request_command_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={"field": "command", "type": "UPDATE", "new_value": "npm run start"},
        )
        assert response.status_code == 200
        commands = [
            c for c in response.json()["unapplied_changes"] if c["field"] == "command"
        ]
        assert len(commands) == 1
        assert commands[0]["new_value"] == "npm run start"

    async def test_request_healthcheck_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "healthcheck",
                "type": "UPDATE",
                "new_value": {
                    "type": "PATH",
                    "value": "/health",
                    "associated_port": 8080,
                },
            },
        )
        assert response.status_code == 200
        checks = [
            c
            for c in response.json()["unapplied_changes"]
            if c["field"] == "healthcheck"
        ]
        assert len(checks) == 1
        assert checks[0]["new_value"]["value"] == "/health"

    async def test_request_add_url(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "urls",
                "type": "ADD",
                "new_value": {"domain": "app.dky.local", "base_path": "/"},
            },
        )
        assert response.status_code == 200
        assert any(c["field"] == "urls" for c in response.json()["unapplied_changes"])

    async def test_request_add_port(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "ports",
                "type": "ADD",
                "new_value": {"host": 8080, "forwarded": 80},
            },
        )
        assert response.status_code == 200

    async def test_request_reserved_port_rejected(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "ports",
                "type": "ADD",
                "new_value": {"host": 80, "forwarded": 8080},
            },
        )
        assert response.status_code == 400

    async def test_request_add_env(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "env_variables",
                "type": "ADD",
                "new_value": {"key": "FOO", "value": "bar"},
            },
        )
        assert response.status_code == 200

    async def test_request_invalid_field(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={"field": "bogus", "type": "ADD", "new_value": {}},
        )
        assert response.status_code == 400

    async def test_request_update_without_item_id(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "urls",
                "type": "UPDATE",
                "new_value": {"domain": "x.local"},
            },
        )
        assert response.status_code == 400


class TestCancelServiceChanges:
    async def test_cancel_non_source_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.put(
            _changes_url(p, "svc"),
            json={
                "field": "env_variables",
                "type": "ADD",
                "new_value": {"key": "FOO", "value": "bar"},
            },
        )
        env_change = [
            c
            for c in response.json()["unapplied_changes"]
            if c["field"] == "env_variables"
        ][0]
        response = await auth_client.delete(_cancel_url(p, "svc", env_change["id"]))
        assert response.status_code == 204

    async def test_cancel_source_strand_guard(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.get(_details_url(p, "svc"))
        source_change = [
            c for c in response.json()["unapplied_changes"] if c["field"] == "source"
        ][0]
        response = await auth_client.delete(_cancel_url(p, "svc", source_change["id"]))
        assert response.status_code == 409

    async def test_cancel_nonexistent_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc")
        response = await auth_client.delete(_cancel_url(p, "svc", "chg_dkr_nope"))
        assert response.status_code == 404


class TestServiceList:
    async def test_list_services(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc-a")
        await _make_service(auth_client, p, "svc-b")
        response = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_list_filter(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "cache-db")
        await _make_service(auth_client, p, "web-app")
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-list/", params={"query": "cache"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_card_image_from_source_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        response = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        card = response.json()[0]
        assert card["image"] == "redis"
        assert card["tag"] == "alpine"
        assert card["status"] == "NOT_DEPLOYED_YET"


def _deploy_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/deploy-service/docker/{slug}/"


class TestDeployDockerService:
    async def test_deploy_simple_service(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="caddy:2.8-alpine")
        response = await auth_client.put(_deploy_url(p, "app"))
        assert response.status_code == 200
        data = response.json()

        deployment_hash = data["id"].rsplit("_", 1)[-1]
        services = fake_docker.services.list()
        assert len(services) == 1
        assert services[0].name.startswith("srv-")
        assert services[0].name.endswith(deployment_hash)
        assert services[0].image == "caddy:2.8-alpine"

        assert data["status"] == "HEALTHY"
        assert data["is_current_production"] is True
        assert data["slot"] == "BLUE"

    async def test_deploy_service_with_env(self, auth_client, fake_docker):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="caddy:2.8-alpine")
        await auth_client.put(
            _changes_url(p, "app"),
            json={
                "field": "env_variables",
                "type": "ADD",
                "new_value": {"key": "REDIS_PASSWORD", "value": "secret"},
            },
        )
        await auth_client.put(_deploy_url(p, "app"))
        swarm_service = fake_docker.services.list()[0]
        assert "REDIS_PASSWORD=secret" in swarm_service.env
        assert "DOCKYARD_DEPLOYMENT_TYPE=docker" in swarm_service.env

    async def test_deploy_applies_source_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        await auth_client.put(_deploy_url(p, "svc"))
        response = await auth_client.get(_details_url(p, "svc"))
        assert response.json()["image"] == "redis:alpine"
        assert len(response.json()["unapplied_changes"]) == 0

    async def test_deploy_nonexistent_service(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.put(_deploy_url(p, "nope"))
        assert response.status_code == 404

    async def test_second_deploy_uses_green_slot(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        first = await auth_client.put(_deploy_url(p, "svc"))
        assert first.json()["slot"] == "BLUE"
        await auth_client.put(
            _changes_url(p, "svc"),
            json={"field": "command", "type": "UPDATE", "new_value": "echo hi"},
        )
        second = await auth_client.put(_deploy_url(p, "svc"))
        assert second.json()["slot"] == "GREEN"
        assert second.json()["is_current_production"] is True

    async def test_deploy_unhealthy_when_replica_never_runs(
        self, auth_client, monkeypatch
    ):
        monkeypatch.setattr("tests.fakes.FakeSwarmService.running", False)
        monkeypatch.setattr(
            "app.models.healthcheck.HealthCheck.DEFAULT_TIMEOUT_SECONDS", 0
        )
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        response = await auth_client.put(_deploy_url(p, "svc"))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UNHEALTHY"
        assert data["is_current_production"] is False
        assert data["status_reason"]

    async def test_deploy_with_url_exposes_caddy_route(self, auth_client, fake_caddy):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="caddy:2.8-alpine")
        await auth_client.put(
            _changes_url(p, "app"),
            json={
                "field": "urls",
                "type": "ADD",
                "new_value": {
                    "domain": "app.dky.local",
                    "base_path": "/",
                    "associated_port": 80,
                },
            },
        )
        await auth_client.put(_deploy_url(p, "app"))

        assert "app.dky.local" in fake_caddy.domains
        routes = fake_caddy.domains["app.dky.local"]["handle"][0]["routes"]
        assert any(r["@id"] == "app.dky.local-*" for r in routes)
        reverse_proxy = routes[0]["handle"][0]["routes"][0]["handle"][-1]
        dials = [u["dial"] for u in reverse_proxy["upstreams"]]
        # One upstream, aimed at the slot this deployment actually landed on.
        assert len(dials) == 1
        assert ".blue." in dials[0] and dials[0].endswith(":80")

    async def test_deploy_without_url_does_not_touch_caddy(
        self, auth_client, fake_caddy
    ):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        await auth_client.put(_deploy_url(p, "svc"))
        assert fake_caddy.domains == {}


class TestServiceCardStatus:
    async def test_card_status_reflects_deployment(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "svc", image="redis:alpine")
        before = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        assert before.json()[0]["status"] == "NOT_DEPLOYED_YET"

        await auth_client.put(_deploy_url(p, "svc"))
        after = await auth_client.get(f"/api/projects/{p}/production/service-list/")
        assert after.json()[0]["status"] == "HEALTHY"


class TestDeploymentList:
    async def test_list_deployments(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="redis:alpine")
        await auth_client.put(_deploy_url(p, "app"))
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-details/app/deployments/"
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1
        assert response.json()["count"] == 1

    async def test_list_deployments_empty(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="redis:alpine")
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-details/app/deployments/"
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) == 0

    async def test_list_deployments_service_non_existing(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-details/nope/deployments/"
        )
        assert response.status_code == 404

    async def test_single_deployment(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="redis:alpine")
        deploy = await auth_client.put(_deploy_url(p, "app"))
        deployment_hash = deploy.json()["id"].rsplit("_", 1)[-1]
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-details/app/deployments/{deployment_hash}/"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "HEALTHY"

    async def test_single_deployment_non_existing(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="redis:alpine")
        response = await auth_client.get(
            f"/api/projects/{p}/production/service-details/app/deployments/nope/"
        )
        assert response.status_code == 404


def _redeploy_url(project_slug, slug, deployment_hash, env_slug="production"):
    return (
        f"/api/projects/{project_slug}/{env_slug}/"
        f"redeploy-service/docker/{slug}/{deployment_hash}/"
    )


class TestRedeployDockerService:
    async def test_redeploy_restores_image_with_computed_change(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="valkey:7.2-alpine")
        initial = await auth_client.put(_deploy_url(p, "app"))
        initial_hash = initial.json()["id"].rsplit("_", 1)[-1]

        await auth_client.put(
            _changes_url(p, "app"),
            json={
                "field": "source",
                "type": "UPDATE",
                "new_value": {"image": "valkey:7.3-alpine"},
            },
        )
        await auth_client.put(_deploy_url(p, "app"))

        response = await auth_client.put(_redeploy_url(p, "app", initial_hash))
        assert response.status_code == 200

        deployments = await auth_client.get(
            f"/api/projects/{p}/production/service-details/app/deployments/"
        )
        assert deployments.json()["count"] == 3

        service = await auth_client.get(_details_url(p, "app"))
        assert service.json()["image"] == "valkey:7.2-alpine"

    async def test_redeploy_non_existing_deployment(self, auth_client):
        p = await _make_project(auth_client)
        await _make_service(auth_client, p, "app", image="redis:alpine")
        await auth_client.put(_deploy_url(p, "app"))
        response = await auth_client.put(_redeploy_url(p, "app", "nope"))
        assert response.status_code == 404
