import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel, generate_id

github_app_repositories = Table(
    "github_app_repositories",
    Base.metadata,
    Column(
        "github_app_id",
        ForeignKey("github_app.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "repository_id",
        ForeignKey("git_repository.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class GitRepository(Base, TimestampedModel):
    __tablename__ = "git_repository"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("repo_", 14)
    )
    owner: Mapped[str] = mapped_column(String(255), index=True)
    repo: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(String, unique=True)
    private: Mapped[bool] = mapped_column(Boolean)


class GitHubApp(Base, TimestampedModel):
    __tablename__ = "github_app"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("gh_app_", 14)
    )
    name: Mapped[str] = mapped_column(String(255))
    installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    app_url: Mapped[str] = mapped_column(String(255))
    client_id: Mapped[str] = mapped_column(String(255))
    app_id: Mapped[int] = mapped_column(Integer, unique=True)
    client_secret: Mapped[str] = mapped_column(Text)
    webhook_secret: Mapped[str] = mapped_column(Text)
    private_key: Mapped[str] = mapped_column(Text)

    repositories = relationship(
        "GitRepository",
        secondary=github_app_repositories,
        lazy="selectin",
    )

    def _generate_jwt(self) -> str:
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            # issued 60s in the past to allow for clock drift
            "iat": now - 60,
            # 10 minute maximum
            "exp": now + timedelta(minutes=10).seconds,
            "iss": self.client_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def get_access_token(self) -> str:
        assert self.is_installed

        token_jwt = self._generate_jwt()
        response = httpx.post(
            f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {token_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        return response.json()["token"]

    def get_authenticated_repository_url(self, repo_url: str) -> str:
        access_token = self.get_access_token()
        return (
            f"https://x-access-token:{access_token}@"
            f"{repo_url.replace('https://', '')}"
        )

    def verify_signature(self, payload_body: bytes, signature_header: str) -> bool:
        hash_object = hmac.new(
            self.webhook_secret.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256,
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)

    @property
    def is_installed(self) -> bool:
        return (
            bool(self.installation_id)
            and bool(self.client_id)
            and bool(self.client_secret)
            and bool(self.webhook_secret)
            and bool(self.private_key)
        )
