from app.config import settings
from app.utils import strip_slash_if_exists

THIRTY_SECONDS_IN_NANOSECONDS = 30_000_000_000


def get_caddy_id_for_url(url) -> str:
    normalized_path = strip_slash_if_exists(
        url.base_path, strip_end=True, strip_start=True
    ).replace("/", "-")
    if len(normalized_path) == 0:
        normalized_path = "*"
    return f"{url.domain}-{normalized_path}"


def get_active_slot(service) -> str:
    deployment = service.latest_production_deployment
    return (deployment.slot if deployment is not None else "BLUE").lower()


def get_caddy_request_for_url(url, service, http_port) -> dict:
    proxy_handlers = []

    if url.strip_prefix:
        proxy_handlers.append(
            {
                "handler": "rewrite",
                "strip_path_prefix": strip_slash_if_exists(
                    url.base_path, strip_end=True, strip_start=False
                ),
            }
        )

    proxy_handlers.append(
        {
            "flush_interval": -1,
            "handler": "reverse_proxy",
            "health_checks": {
                "passive": {"fail_duration": THIRTY_SECONDS_IN_NANOSECONDS}
            },
            "load_balancing": {
                "retries": 3,
                "selection_policy": {"policy": "first"},
            },
            # One upstream, pointing at whichever slot currently holds
            # production. Listing both slots and letting Caddy pick "first"
            # sends traffic to whichever is earlier in the list rather than
            # whichever is current — so a deploy onto the green slot kept
            # being served by the blue container it was meant to replace.
            "upstreams": [
                {
                    "dial": f"{service.network_alias}.{get_active_slot(service)}."
                    f"{settings.internal_domain}:{http_port.forwarded}"
                },
            ],
        }
    )
    return {
        "@id": get_caddy_id_for_url(url),
        "handle": [
            {
                "handler": "subroute",
                "routes": [{"handle": proxy_handlers}],
            }
        ],
        "match": [
            {
                "path": [
                    f"{strip_slash_if_exists(url.base_path, strip_end=True, strip_start=False)}/*"
                ],
            }
        ],
    }


def get_caddy_request_for_domain(domain: str) -> dict:
    return {
        "@id": domain,
        "match": [{"host": [domain]}],
        "handle": [
            {
                "handler": "subroute",
                "routes": [],
            }
        ],
        "terminal": True,
    }


def sort_proxy_routes(routes: list[dict]) -> list[dict]:
    def path_specificity(route: dict):
        path = route["match"][0]["path"][0]
        normalized_path = path.rstrip("*")
        path_length = len(normalized_path)
        return -path_length, path.endswith("*"), -len(path)

    return sorted(routes, key=path_specificity)
