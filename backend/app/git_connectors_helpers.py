import httpx

from app.errors import BadRequest


def fetch_github_app_manifest(code: str) -> dict:
    """Exchange a GitHub App manifest `code` for the app's credentials."""
    response = httpx.post(
        f"https://api.github.com/app-manifests/{code}/conversions",
        headers={
            "Accept": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if response.status_code >= 300:
        raise BadRequest("invalid Github app installation code")
    return response.json()


def exchange_gitlab_oauth_code(
    gitlab_url: str,
    app_id: str,
    secret: str,
    redirect_uri: str,
    code: str,
) -> dict:
    """Exchange a GitLab OAuth `code` for access + refresh tokens."""
    response = httpx.post(
        f"{gitlab_url}/oauth/token",
        data={
            "client_id": app_id,
            "client_secret": secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
    )
    if response.status_code >= 300:
        raise BadRequest("invalid Gitlab OAuth authorization code")
    return response.json()
