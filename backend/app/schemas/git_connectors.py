from datetime import datetime

from pydantic import BaseModel


class GitHubAppSchema(BaseModel):
    id: str
    name: str
    app_url: str
    app_id: int
    installation_id: int | None
    is_installed: bool

    @classmethod
    def from_github_app(cls, gh) -> "GitHubAppSchema":
        return cls(
            id=gh.id,
            name=gh.name,
            app_url=gh.app_url,
            app_id=gh.app_id,
            installation_id=gh.installation_id,
            is_installed=gh.is_installed,
        )


class GitAppSchema(BaseModel):
    id: str
    github: GitHubAppSchema | None
    created_at: datetime

    @classmethod
    def from_git_app(cls, git_app) -> "GitAppSchema":
        return cls(
            id=git_app.id,
            github=(
                GitHubAppSchema.from_github_app(git_app.github)
                if git_app.github
                else None
            ),
            created_at=git_app.created_at,
        )


class SetupGithubAppRequest(BaseModel):
    code: str | None = None
    state: str | None = None
    installation_id: int | None = None
