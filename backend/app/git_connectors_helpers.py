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
