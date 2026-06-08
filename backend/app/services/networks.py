from app import docker_helpers
from app.config import settings
from app.docker_helpers import (
    get_env_network_resource_name,
    get_resource_labels,
)


def attach_network_to_proxy(network_id: str) -> None:
    client = docker_helpers.get_docker_client()
    found = client.services.list(filters={"name": settings.proxy_service_name})
    if not found:
        return
    proxy = found[0]
    spec = proxy.attrs["Spec"]
    task_template = spec["TaskTemplate"]
    attached = task_template.get("Networks", [])
    if any(network["Target"] == network_id for network in attached):
        return
    task_template["Networks"] = [*attached, {"Target": network_id}]
    client.api.update_service(
        proxy.id,
        version=proxy.attrs["Version"]["Index"],
        name=spec["Name"],
        labels=spec.get("Labels"),
        mode=spec.get("Mode"),
        update_config=spec.get("UpdateConfig"),
        endpoint_spec=spec.get("EndpointSpec"),
        task_template=task_template,
    )


def reconcile_proxy_networks() -> list[str]:
    """Re-attach every managed project network to the proxy.

    `docker stack deploy` rewrites the proxy service spec from the stack file,
    which names only the shared network — so every attachment made by
    attach_network_to_proxy is silently dropped. The proxy and the services it
    routes to then share no network at all, their aliases stop resolving, and
    every project URL answers 502 until the attachments are put back. Since the
    dev stack is redeployed on each startup, that is otherwise every startup.

    Called once when the API boots. Idempotent, and a no-op when nothing drifted.
    """
    client = docker_helpers.get_docker_client()
    found = client.services.list(filters={"name": settings.proxy_service_name})
    if not found:
        return []
    proxy = found[0]
    spec = proxy.attrs["Spec"]
    task_template = spec["TaskTemplate"]
    attached = task_template.get("Networks", [])
    already = {network["Target"] for network in attached}

    managed = client.networks.list(filters={"label": "dky-managed=true"})
    missing = [network for network in managed if network.id not in already]
    if not missing:
        return []

    # One update carrying every missing network. Attaching them one at a time
    # forces a task restart per network and takes minutes to converge.
    task_template["Networks"] = [
        *attached,
        *({"Target": network.id} for network in missing),
    ]
    client.api.update_service(
        proxy.id,
        version=proxy.attrs["Version"]["Index"],
        name=spec["Name"],
        labels=spec.get("Labels"),
        mode=spec.get("Mode"),
        update_config=spec.get("UpdateConfig"),
        endpoint_spec=spec.get("EndpointSpec"),
        task_template=task_template,
    )
    return [network.id for network in missing]


def create_project_network(project_id: str, production_env_id: str) -> str:
    client = docker_helpers.get_docker_client()
    name = get_env_network_resource_name(production_env_id, project_id)

    existing = client.networks.list(filters={"name": name})
    if existing:
        return existing[0].id

    network = client.networks.create(
        name=name,
        scope="swarm",
        driver="overlay",
        labels=get_resource_labels(project_id, is_production="True"),
        attachable=True,
    )
    attach_network_to_proxy(network.id)
    return network.id


def create_environment_network(env_id: str, project_id: str) -> str:
    client = docker_helpers.get_docker_client()
    name = get_env_network_resource_name(env_id, project_id)

    existing = client.networks.list(filters={"name": name})
    if existing:
        return existing[0].id

    network = client.networks.create(
        name=name,
        scope="swarm",
        driver="overlay",
        labels=get_resource_labels(project_id),
        attachable=True,
    )
    attach_network_to_proxy(network.id)
    return network.id


def delete_environment_network(env_id: str, project_id: str) -> None:
    client = docker_helpers.get_docker_client()
    name = get_env_network_resource_name(env_id, project_id)
    for network in client.networks.list(filters={"name": name}):
        network.remove()


def remove_project_networks(project_id: str) -> list[str]:
    client = docker_helpers.get_docker_client()
    networks = client.networks.list(filters={"label": f"dky-project={project_id}"})
    removed = []
    for network in networks:
        network.remove()
        removed.append(network.name)
    return removed


def cleanup_networks() -> None:
    client = docker_helpers.get_docker_client()
    client.networks.prune(filters={"label!": ["dky-managed"]})
