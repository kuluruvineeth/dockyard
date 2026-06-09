async def _make_project(auth_client, slug="dky-ops"):
    response = await auth_client.post("/api/projects/", json={"slug": slug})
    assert response.status_code == 201
    return slug


def _create_url(project_slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/create-service/git/"


REPO = "https://github.com/kuluruvineeth/docs"


class TestCreateGitService:
    async def test_create_git_service(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(p),
            json={"slug": "docs", "repository_url": REPO, "branch_name": "main"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "docs"
        assert data["type"] == "GIT_REPOSITORY"
        assert data["network_alias"].startswith("dky-docs-")

        changes = data["unapplied_changes"]
        git_source = [c for c in changes if c["field"] == "git_source"][0]
        assert git_source["new_value"]["repository_url"] == REPO
        assert git_source["new_value"]["branch_name"] == "main"
        assert any(c["field"] == "builder" for c in changes)

    async def test_create_git_service_bad_request(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(_create_url(p), json={"slug": "docs"})
        assert response.status_code == 400

    async def test_create_git_service_nonexistent_repository(
        self, auth_client, fake_git
    ):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(p),
            json={
                "slug": "docs",
                "repository_url": fake_git.NON_EXISTENT_REPOSITORY,
                "branch_name": "main",
            },
        )
        assert response.status_code == 400

    async def test_create_git_service_nonexistent_branch(self, auth_client):
        p = await _make_project(auth_client)
        response = await auth_client.post(
            _create_url(p),
            json={
                "slug": "docs",
                "repository_url": REPO,
                "branch_name": "nonexistent",
            },
        )
        assert response.status_code == 400

    async def test_create_git_service_conflict(self, auth_client):
        p = await _make_project(auth_client)
        body = {"slug": "docs", "repository_url": REPO, "branch_name": "main"}
        await auth_client.post(_create_url(p), json=body)
        response = await auth_client.post(_create_url(p), json=body)
        assert response.status_code == 409

    async def test_create_git_service_nonexistent_project(self, auth_client):
        response = await auth_client.post(
            _create_url("nope"),
            json={"slug": "docs", "repository_url": REPO, "branch_name": "main"},
        )
        assert response.status_code == 404


def _deploy_url(project_slug, slug, env_slug="production"):
    return f"/api/projects/{project_slug}/{env_slug}/deploy-service/git/{slug}/"


class TestDeployGitService:
    async def test_deploy_git_service_builds_and_deploys(
        self, auth_client, fake_docker
    ):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p),
            json={"slug": "docs", "repository_url": REPO, "branch_name": "main"},
        )
        response = await auth_client.put(_deploy_url(p, "docs"))
        assert response.status_code == 200
        assert response.json()["status"] == "HEALTHY"

        services = fake_docker.services.list()
        assert len(services) == 1
        assert services[0].image.startswith("dky-build-")

    async def test_deploy_git_service_applies_git_source(self, auth_client):
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p),
            json={"slug": "docs", "repository_url": REPO, "branch_name": "main"},
        )
        await auth_client.put(_deploy_url(p, "docs"))
        details = await auth_client.get(
            f"/api/projects/{p}/production/service-details/docs/"
        )
        assert details.json()["repository_url"] == REPO
        assert details.json()["branch_name"] == "main"
        assert len(details.json()["unapplied_changes"]) == 0

    async def test_build_failure_marks_deployment_failed(
        self, auth_client, fake_git_build
    ):
        def boom(url, branch, dest):
            raise RuntimeError("clone failed")

        fake_git_build.clone_git_repository = boom
        p = await _make_project(auth_client)
        await auth_client.post(
            _create_url(p),
            json={"slug": "docs", "repository_url": REPO, "branch_name": "main"},
        )
        response = await auth_client.put(_deploy_url(p, "docs"))
        assert response.status_code == 200
        assert response.json()["status"] == "FAILED"
