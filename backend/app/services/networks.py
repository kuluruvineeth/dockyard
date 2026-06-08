from app import docker_helpers
from app.docker_helpers import (
    get_env_network_resource_name,
    get_resource_labels,
)


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
