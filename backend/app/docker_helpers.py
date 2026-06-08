import docker

SERVER_RESOURCE_LIMIT_COMMAND = (
    "sh -c 'nproc && grep MemTotal /proc/meminfo | awk \"{print \\$2 * 1024}\"'"
)

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
