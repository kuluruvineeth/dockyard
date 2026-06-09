import httpx

from app.config import settings


class CaddyClient:
    def __init__(self, admin_host: str):
        self.admin_host = admin_host

    def get(self, path: str):
        return httpx.get(f"{self.admin_host}{path}", timeout=5)

    def post(self, path: str, json):
        return httpx.post(f"{self.admin_host}{path}", json=json, timeout=5)

    def put(self, path: str, json):
        return httpx.put(f"{self.admin_host}{path}", json=json, timeout=5)

    def patch(self, path: str, json):
        return httpx.patch(f"{self.admin_host}{path}", json=json, timeout=5)

    def delete(self, path: str):
        return httpx.delete(f"{self.admin_host}{path}", timeout=5)


_client: CaddyClient | None = None


def get_caddy_client() -> CaddyClient:
    global _client
    if _client is None:
        _client = CaddyClient(settings.caddy_proxy_admin_host)
    return _client
