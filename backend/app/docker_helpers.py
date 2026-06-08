import docker

SERVER_RESOURCE_LIMIT_COMMAND = (
    "sh -c 'nproc && grep MemTotal /proc/meminfo | awk \"{print \\$2 * 1024}\"'"
)


def get_network_resource_name(project_id: str) -> str:
    return f"net-{project_id}"


def get_env_network_resource_name(env_id: str, project_id: str) -> str:
    return f"net-{project_id}-{env_id}"


def get_resource_labels(project_id: str, **kwargs: str) -> dict[str, str]:
    return {"dky-managed": "true", "dky-project": project_id, **kwargs}


def get_volume_resource_name(volume_id: str) -> str:
    return f"vol-{volume_id}"


def get_config_resource_name(config_id: str, version: int) -> str:
    return f"cf-{config_id}-{version}"


def get_swarm_service_name_for_deployment(
    deployment_hash: str, project_id: str, service_id: str
) -> str:
    return f"srv-{project_id}-{service_id}-{deployment_hash}"


_client = None


def get_docker_client():
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def get_server_resource_limits() -> tuple[int, int]:
    client = get_docker_client()
    result: bytes = client.containers.run(
        image="busybox",
        command=SERVER_RESOURCE_LIMIT_COMMAND,
        remove=True,
    )
    no_of_cpus, max_memory_in_bytes = (
        result.decode(encoding="utf-8").strip().split("\n")
    )
    return int(no_of_cpus), int(max_memory_in_bytes)
