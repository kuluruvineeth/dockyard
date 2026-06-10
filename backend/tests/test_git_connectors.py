import hashlib
import hmac
import json as _json
import secrets as _secrets

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select as _select

from app.models import Deployment as _Deployment
from app.models import Environment as _Environment
from app.models import GitHubApp
from app.models import GitlabApp as _GitlabApp
from app.models import Project as _Project
from app.models import Service as _Service
from app.models import ServiceType as _ServiceType
from app.models.base import generate_id as _generate_id


def _rsa_keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _app(**overrides) -> GitHubApp:
    defaults = dict(
        name="test app",
        app_url="https://github.com/apps/test",
        client_id="Iv1.abc123",
        app_id=12345,
        client_secret="secret",
        webhook_secret="whsecret",
        private_key="key",
        installation_id=999,
    )
    defaults.update(overrides)
    return GitHubApp(**defaults)


class TestVerifySignature:
    def test_valid_signature(self):
        app = _app(webhook_secret="e340154128314309424b7c8e90325147d99fdafa")
        body = b'{"action":"push"}'
        digest = hmac.new(
            app.webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert app.verify_signature(body, f"sha256={digest}") is True

    def test_invalid_signature(self):
        app = _app(webhook_secret="whsecret")
        assert app.verify_signature(b"body", "sha256=deadbeef") is False

    def test_signature_is_constant_time_and_format_sensitive(self):
        app = _app(webhook_secret="whsecret")
        body = b"payload"
        digest = hmac.new(b"whsecret", body, hashlib.sha256).hexdigest()
        # missing the "sha256=" prefix must fail
        assert app.verify_signature(body, digest) is False


class TestIsInstalled:
    def test_fully_configured(self):
        assert _app().is_installed is True

    def test_missing_installation_id(self):
        assert _app(installation_id=None).is_installed is False

    def test_missing_webhook_secret(self):
        assert bool(_app(webhook_secret="").is_installed) is False


class TestGenerateJwt:
    def test_jwt_is_valid_and_signed_with_client_id_issuer(self):
        private_pem, public_pem = _rsa_keypair()
        app = _app(private_key=private_pem, client_id="Iv1.xyz")
        token = app._generate_jwt()
        decoded = jwt.decode(token, public_pem, algorithms=["RS256"])
        assert decoded["iss"] == "Iv1.xyz"
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["exp"] > decoded["iat"]


class TestAuthenticatedRepositoryUrl:
    def test_injects_access_token(self, monkeypatch):
        app = _app()
        monkeypatch.setattr(app, "get_access_token", lambda: "ghs_token123")
        url = app.get_authenticated_repository_url(
            "https://github.com/octocat/Hello-World.git"
        )
        assert (
            url
            == "https://x-access-token:ghs_token123@github.com/octocat/Hello-World.git"
        )


FAKE_MANIFEST = {
    "id": 12345,
    "client_id": "Iv1.abc",
    "client_secret": "client-secret",
    "webhook_secret": "webhook-secret",
    "html_url": "https://github.com/apps/my-app",
    "pem": "-----BEGIN RSA PRIVATE KEY-----\nMIIPLACEHOLDER\n-----END RSA PRIVATE KEY-----\n",
    "name": "my-app",
}

SETUP = "/api/connectors/github/setup/"
LIST = "/api/connectors/git-apps/"


def _patch_manifest(monkeypatch):
    monkeypatch.setattr(
        "app.git_connectors_helpers.fetch_github_app_manifest",
        lambda code: FAKE_MANIFEST,
    )


class TestSetupGithubApp:
    async def test_conversion_creates_github_and_git_app(
        self, auth_client, monkeypatch
    ):
        _patch_manifest(monkeypatch)
        response = await auth_client.post(SETUP, json={"code": "abc123"})
        assert response.status_code == 303
        assert "/settings/git-apps" in response.headers["location"]

        listing = await auth_client.get(LIST)
        assert len(listing.json()) == 1
        gh = listing.json()[0]["github"]
        assert gh["app_id"] == 12345
        assert gh["name"] == "my-app"
        assert gh["is_installed"] is False

    async def test_conversion_is_idempotent_per_app_id(self, auth_client, monkeypatch):
        _patch_manifest(monkeypatch)
        await auth_client.post(SETUP, json={"code": "abc"})
        await auth_client.post(SETUP, json={"code": "def"})
        listing = await auth_client.get(LIST)
        assert len(listing.json()) == 1

    async def test_install_sets_installation_id(self, auth_client, monkeypatch):
        _patch_manifest(monkeypatch)
        await auth_client.post(SETUP, json={"code": "abc123"})
        response = await auth_client.post(
            SETUP, json={"state": "install:12345", "installation_id": 999}
        )
        assert response.status_code == 303
        gh = (await auth_client.get(LIST)).json()[0]["github"]
        assert gh["installation_id"] == 999
        assert gh["is_installed"] is True

    async def test_install_nonexistent_app_404(self, auth_client):
        response = await auth_client.post(
            SETUP, json={"state": "install:99999", "installation_id": 1}
        )
        assert response.status_code == 404

    async def test_git_app_details_not_found(self, auth_client):
        response = await auth_client.get(f"{LIST}git_con_nope/")
        assert response.status_code == 404


WEBHOOK = "/api/connectors/github/webhook/"


def _signed(payload: dict, secret: str = "webhook-secret"):
    body = _json.dumps(payload).encode("utf-8")
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, sig


def _webhook_headers(event: str, sig: str) -> dict:
    return {
        "x-github-event": event,
        "x-hub-signature-256": sig,
        "content-type": "application/json",
    }


async def _create_app(auth_client, monkeypatch):
    _patch_manifest(monkeypatch)
    await auth_client.post(SETUP, json={"code": "abc"})


class TestGithubWebhook:
    async def test_installation_adds_repositories(self, auth_client, monkeypatch):
        await _create_app(auth_client, monkeypatch)
        payload = {
            "installation": {"app_id": 12345},
            "repositories": [
                {"full_name": "octocat/Hello-World", "private": False},
                {"full_name": "octocat/Secret", "private": True},
            ],
        }
        body, sig = _signed(payload)
        response = await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("installation", sig)
        )
        assert response.status_code == 200
        repos = (await auth_client.get(LIST)).json()[0]["github"]["repositories"]
        urls = {r["url"] for r in repos}
        assert urls == {
            "https://github.com/octocat/Hello-World",
            "https://github.com/octocat/Secret",
        }

    async def test_installation_repositories_add_and_remove(
        self, auth_client, monkeypatch
    ):
        await _create_app(auth_client, monkeypatch)
        body, sig = _signed(
            {
                "installation": {"app_id": 12345},
                "repositories": [{"full_name": "octocat/a", "private": False}],
            }
        )
        await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("installation", sig)
        )
        body, sig = _signed(
            {
                "installation": {"app_id": 12345},
                "repositories_added": [{"full_name": "octocat/b", "private": True}],
                "repositories_removed": [{"full_name": "octocat/a", "private": False}],
            }
        )
        response = await auth_client.post(
            WEBHOOK,
            content=body,
            headers=_webhook_headers("installation_repositories", sig),
        )
        assert response.status_code == 200
        repos = (await auth_client.get(LIST)).json()[0]["github"]["repositories"]
        urls = {r["url"] for r in repos}
        assert urls == {"https://github.com/octocat/b"}

    async def test_ping_verifies_signature(self, auth_client, monkeypatch):
        await _create_app(auth_client, monkeypatch)
        body, sig = _signed({"hook": {"app_id": 12345}})
        response = await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("ping", sig)
        )
        assert response.status_code == 200

    async def test_invalid_signature_rejected(self, auth_client, monkeypatch):
        await _create_app(auth_client, monkeypatch)
        body, _ = _signed({"hook": {"app_id": 12345}})
        response = await auth_client.post(
            WEBHOOK,
            content=body,
            headers=_webhook_headers("ping", "sha256=deadbeef"),
        )
        assert response.status_code == 400

    async def test_unregistered_app_404(self, auth_client):
        body, sig = _signed({"hook": {"app_id": 99999}})
        response = await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("ping", sig)
        )
        assert response.status_code == 404


async def _make_linked_git_service(auth_client, session, git_app_id):
    await auth_client.post("/api/projects/", json={"slug": "proj"})
    project = (
        await session.execute(_select(_Project).where(_Project.slug == "proj"))
    ).scalar_one()
    env = (
        await session.execute(
            _select(_Environment).where(_Environment.project_id == project.id)
        )
    ).scalar_one()
    service = _Service(
        id=_generate_id("srv_git_"),
        slug="webapp",
        project_id=project.id,
        environment_id=env.id,
        type=_ServiceType.GIT_REPOSITORY.value,
        git_app_id=git_app_id,
        repository_url="https://github.com/octocat/repo.git",
        branch_name="main",
        auto_deploy_enabled=True,
        deploy_token=_secrets.token_hex(16),
    )
    service.network_alias = _Service.generate_network_alias(service)
    service.urls = []
    service.ports = []
    service.configs = []
    service.volumes = []
    service.env_variables = []
    service.changes = []
    session.add(service)
    await session.commit()
    return service


def _push_payload(ref: str) -> dict:
    return {
        "ref": ref,
        "installation": {"id": 999},
        "repository": {"full_name": "octocat/repo"},
        "head_commit": {
            "id": "abc123sha",
            "message": "new commit",
            "author": {"name": "Octo Cat"},
        },
    }


class TestPushAutoDeploy:
    async def test_push_triggers_auto_deploy(self, auth_client, session, monkeypatch):
        _patch_manifest(monkeypatch)
        await auth_client.post(SETUP, json={"code": "abc"})
        await auth_client.post(
            SETUP, json={"state": "install:12345", "installation_id": 999}
        )
        git_app_id = (await auth_client.get(LIST)).json()[0]["id"]
        service = await _make_linked_git_service(auth_client, session, git_app_id)

        body, sig = _signed(_push_payload("refs/heads/main"))
        response = await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("push", sig)
        )
        assert response.status_code == 200

        deps = (
            (
                await session.execute(
                    _select(_Deployment).where(_Deployment.service_id == service.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(deps) == 1
        assert deps[0].trigger_method == "AUTO"
        assert deps[0].commit_sha == "abc123sha"
        assert deps[0].commit_author_name == "Octo Cat"

    async def test_tag_push_is_ignored(self, auth_client, session, monkeypatch):
        _patch_manifest(monkeypatch)
        await auth_client.post(SETUP, json={"code": "abc"})
        await auth_client.post(
            SETUP, json={"state": "install:12345", "installation_id": 999}
        )
        git_app_id = (await auth_client.get(LIST)).json()[0]["id"]
        service = await _make_linked_git_service(auth_client, session, git_app_id)

        body, sig = _signed(_push_payload("refs/tags/v1.0.0"))
        response = await auth_client.post(
            WEBHOOK, content=body, headers=_webhook_headers("push", sig)
        )
        assert response.status_code == 200
        deps = (
            (
                await session.execute(
                    _select(_Deployment).where(_Deployment.service_id == service.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(deps) == 0


GITLAB_SETUP = "/api/connectors/gitlab/setup/"


def _gitlab_app(**overrides) -> _GitlabApp:
    defaults = dict(
        name="my gitlab",
        gitlab_url="https://gitlab.com",
        redirect_uri="https://dky/cb",
        app_id="appid",
        secret="sec",
        refresh_token="rt123",
    )
    defaults.update(overrides)
    return _GitlabApp(**defaults)


class TestGitlabModel:
    def test_is_installed(self):
        assert _gitlab_app().is_installed is True
        assert bool(_gitlab_app(refresh_token="").is_installed) is False

    def test_authenticated_url_uses_oauth2(self):
        app = _gitlab_app()
        url = app.get_authenticated_repository_url(
            "https://gitlab.com/me/repo.git", "tok"
        )
        assert url == "https://oauth2:tok@gitlab.com/me/repo.git"


class TestSetupGitlabApp:
    async def test_setup_creates_gitlab_and_git_app(self, auth_client, monkeypatch):
        monkeypatch.setattr(
            "app.git_connectors_helpers.exchange_gitlab_oauth_code",
            lambda *a, **k: {"access_token": "at", "refresh_token": "rt-new"},
        )
        response = await auth_client.post(
            GITLAB_SETUP,
            json={
                "name": "gl",
                "redirect_uri": "https://dky/cb",
                "app_id": "appid",
                "secret": "sec",
                "code": "code123",
            },
        )
        assert response.status_code == 303
        ga = (await auth_client.get(LIST)).json()[0]
        assert ga["github"] is None
        assert ga["gitlab"]["name"] == "gl"
        assert ga["gitlab"]["app_id"] == "appid"
        assert ga["gitlab"]["is_installed"] is True


def _git_create_url(p):
    return f"/api/projects/{p}/production/create-service/git/"


def _details_url(p):
    return f"/api/projects/{p}/production/service-details/app/"


class TestLinkServiceToApp:
    async def test_git_service_linked_and_applied_at_deploy(
        self, auth_client, monkeypatch
    ):
        _patch_manifest(monkeypatch)
        await auth_client.post(SETUP, json={"code": "abc"})
        git_app_id = (await auth_client.get(LIST)).json()[0]["id"]
        await auth_client.post("/api/projects/", json={"slug": "p"})
        response = await auth_client.post(
            _git_create_url("p"),
            json={
                "slug": "app",
                "repository_url": "https://github.com/octocat/repo.git",
                "branch_name": "main",
                "builder": "DOCKERFILE",
                "git_app_id": git_app_id,
            },
        )
        assert response.status_code == 201
        await auth_client.put("/api/projects/p/production/deploy-service/git/app/")
        details = (await auth_client.get(_details_url("p"))).json()
        assert details["git_app_id"] == git_app_id

    async def test_invalid_git_app_rejected(self, auth_client):
        await auth_client.post("/api/projects/", json={"slug": "p2"})
        response = await auth_client.post(
            _git_create_url("p2"),
            json={
                "slug": "app",
                "repository_url": "https://github.com/octocat/repo.git",
                "branch_name": "main",
                "builder": "DOCKERFILE",
                "git_app_id": "git_con_doesnotexist",
            },
        )
        assert response.status_code == 400

    async def test_toggle_auto_deploy(self, auth_client):
        await auth_client.post("/api/projects/", json={"slug": "p3"})
        await auth_client.post(
            _git_create_url("p3"),
            json={
                "slug": "app",
                "repository_url": "https://github.com/octocat/repo.git",
                "branch_name": "main",
                "builder": "DOCKERFILE",
            },
        )
        details = (await auth_client.get(_details_url("p3"))).json()
        assert details["auto_deploy_enabled"] is True

        response = await auth_client.put(
            "/api/projects/p3/production/service-details/app/toggle-auto-deploy/",
            json={"enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["auto_deploy_enabled"] is False
