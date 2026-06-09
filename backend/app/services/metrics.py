from app import docker_helpers
from app.models import ServiceMetrics
from app.models.base import generate_id


def _compute_cpu_percent(stats: dict) -> float:
    cpu = stats.get("cpu_stats", {})
    precpu = stats.get("precpu_stats", {})
    cpu_total = cpu.get("cpu_usage", {}).get("total_usage", 0)
    pre_total = precpu.get("cpu_usage", {}).get("total_usage", 0)
    system = cpu.get("system_cpu_usage", 0)
    pre_system = precpu.get("system_cpu_usage", 0)
    online = cpu.get("online_cpus") or len(
        cpu.get("cpu_usage", {}).get("percpu_usage") or [1]
    )
    cpu_delta = cpu_total - pre_total
    system_delta = system - pre_system
    if system_delta > 0 and cpu_delta > 0:
        return (cpu_delta / system_delta) * online * 100.0
    return 0.0


def _sum_network(stats: dict) -> tuple[int, int]:
    rx = tx = 0
    for interface in (stats.get("networks") or {}).values():
        rx += interface.get("rx_bytes", 0)
        tx += interface.get("tx_bytes", 0)
    return rx, tx


def _sum_blkio(stats: dict) -> tuple[int, int]:
    read = write = 0
    entries = stats.get("blkio_stats", {}).get("io_service_bytes_recursive") or []
    for entry in entries:
        op = str(entry.get("op", "")).lower()
        if op == "read":
            read += entry.get("value", 0)
        elif op == "write":
            write += entry.get("value", 0)
    return read, write


def collect_deployment_metrics(service, deployment) -> ServiceMetrics | None:
    client = docker_helpers.get_docker_client()
    swarm_name = docker_helpers.get_swarm_service_name_for_deployment(
        deployment.unprefixed_hash, service.project_id, service.id
    )
    containers = client.containers.list(
        filters={"label": f"com.docker.swarm.service.name={swarm_name}"}
    )
    if not containers:
        return None

    stats = containers[0].stats(stream=False)
    rx, tx = _sum_network(stats)
    read, write = _sum_blkio(stats)
    return ServiceMetrics(
        id=generate_id("metric_"),
        service_id=service.id,
        deployment_id=deployment.id,
        cpu_percent=_compute_cpu_percent(stats),
        memory_bytes=stats.get("memory_stats", {}).get("usage", 0),
        net_rx_bytes=rx,
        net_tx_bytes=tx,
        disk_read_bytes=read,
        disk_writes_bytes=write,
    )
