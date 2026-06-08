from types import SimpleNamespace

from app.config import settings
from app.services.proxy import (
    get_caddy_id_for_url,
    get_caddy_request_for_domain,
    get_caddy_request_for_url,
    sort_proxy_routes,
)


def _url(domain="app.dky.local", base_path="/", strip_prefix=True):
    return SimpleNamespace(
        domain=domain, base_path=base_path, strip_prefix=strip_prefix
    )


class TestCaddyIdForUrl:
    def test_root_path_is_star(self):
        assert get_caddy_id_for_url(_url(base_path="/")) == "app.dky.local-*"

    def test_sub_path(self):
        assert get_caddy_id_for_url(_url(base_path="/api")) == "app.dky.local-api"

    def test_nested_path_uses_dashes(self):
        assert get_caddy_id_for_url(_url(base_path="/api/v1")) == "app.dky.local-api-v1"


class TestCaddyRequestForUrl:
    def test_reverse_proxy_to_the_active_slot_only(self):
        url = _url(base_path="/", strip_prefix=False)
        service = SimpleNamespace(
            network_alias="dky-app-x",
            latest_production_deployment=SimpleNamespace(slot="GREEN"),
        )
        port = SimpleNamespace(forwarded=8000)
        route = get_caddy_request_for_url(url, service, port)

        assert route["@id"] == "app.dky.local-*"
        handlers = route["handle"][0]["routes"][0]["handle"]
        reverse_proxy = handlers[-1]
        assert reverse_proxy["handler"] == "reverse_proxy"
        dials = [u["dial"] for u in reverse_proxy["upstreams"]]
        # Exactly one upstream, and it is the slot currently in production.
        # Listing both slots let Caddy's "first" policy keep serving the old
        # container after a deploy had already switched production over.
        assert dials == [f"dky-app-x.green.{settings.internal_domain}:8000"]
        assert route["match"][0]["path"] == ["/*"]

    def test_reverse_proxy_follows_the_slot_when_it_changes(self):
        url = _url(base_path="/", strip_prefix=False)
        service = SimpleNamespace(
            network_alias="dky-app-x",
            latest_production_deployment=SimpleNamespace(slot="BLUE"),
        )
        port = SimpleNamespace(forwarded=8000)
        route = get_caddy_request_for_url(url, service, port)
        reverse_proxy = route["handle"][0]["routes"][0]["handle"][-1]
        dials = [u["dial"] for u in reverse_proxy["upstreams"]]
        assert dials == [f"dky-app-x.blue.{settings.internal_domain}:8000"]

    def test_reverse_proxy_defaults_to_blue_before_anything_is_live(self):
        url = _url(base_path="/", strip_prefix=False)
        service = SimpleNamespace(
            network_alias="dky-app-x", latest_production_deployment=None
        )
        port = SimpleNamespace(forwarded=8000)
        route = get_caddy_request_for_url(url, service, port)
        reverse_proxy = route["handle"][0]["routes"][0]["handle"][-1]
        dials = [u["dial"] for u in reverse_proxy["upstreams"]]
        assert dials == [f"dky-app-x.blue.{settings.internal_domain}:8000"]

    def test_strip_prefix_prepends_rewrite_handler(self):
        url = _url(base_path="/api", strip_prefix=True)
        service = SimpleNamespace(
            network_alias="a",
            latest_production_deployment=SimpleNamespace(slot="BLUE"),
        )
        port = SimpleNamespace(forwarded=80)
        route = get_caddy_request_for_url(url, service, port)

        handlers = route["handle"][0]["routes"][0]["handle"]
        assert handlers[0]["handler"] == "rewrite"
        assert handlers[0]["strip_path_prefix"] == "/api"
        assert route["match"][0]["path"] == ["/api/*"]

    def test_no_rewrite_when_strip_prefix_false(self):
        url = _url(base_path="/api", strip_prefix=False)
        service = SimpleNamespace(
            network_alias="a",
            latest_production_deployment=SimpleNamespace(slot="BLUE"),
        )
        port = SimpleNamespace(forwarded=80)
        route = get_caddy_request_for_url(url, service, port)
        handlers = route["handle"][0]["routes"][0]["handle"]
        assert all(h["handler"] != "rewrite" for h in handlers)


class TestCaddyRequestForDomain:
    def test_domain_route_structure(self):
        route = get_caddy_request_for_domain("app.dky.local")
        assert route["@id"] == "app.dky.local"
        assert route["match"] == [{"host": ["app.dky.local"]}]
        assert route["terminal"] is True
        assert route["handle"][0]["routes"] == []


class TestSortProxyRoutes:
    def test_longer_paths_first(self):
        routes = [
            {"match": [{"path": ["/*"]}]},
            {"match": [{"path": ["/api/v1/*"]}]},
            {"match": [{"path": ["/api/*"]}]},
        ]
        ordered = [r["match"][0]["path"][0] for r in sort_proxy_routes(routes)]
        assert ordered == ["/api/v1/*", "/api/*", "/*"]
