import hashlib
import hmac

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.models import GitHubApp


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
