import yaml


def parse_compose(content: str) -> dict:
    data = yaml.safe_load(content) or {}
    if not isinstance(data, dict):
        return {}
    services = data.get("services", {})
    if not isinstance(services, dict):
        return {}

    result: dict[str, dict] = {}
    for name, spec in services.items():
        if not isinstance(spec, dict):
            continue
        result[name] = {
            "image": spec.get("image"),
            "command": _normalize_command(spec.get("command")),
            "ports": _normalize_ports(spec.get("ports") or []),
            "environment": _normalize_environment(spec.get("environment")),
        }
    return result


def _normalize_command(command) -> str | None:
    if command is None:
        return None
    if isinstance(command, list):
        return " ".join(str(part) for part in command)
    return str(command)


def _normalize_ports(ports) -> list[dict]:
    result: list[dict] = []
    for port in ports:
        if isinstance(port, dict):
            target = port.get("target")
            published = port.get("published", target)
            if target is not None:
                result.append({"host": int(published), "forwarded": int(target)})
            continue
        parts = str(port).split(":")
        try:
            if len(parts) >= 2:
                result.append({"host": int(parts[-2]), "forwarded": int(parts[-1])})
            elif len(parts) == 1:
                result.append({"host": int(parts[0]), "forwarded": int(parts[0])})
        except ValueError:
            continue
    return result


def _normalize_environment(environment) -> dict:
    result: dict[str, str] = {}
    if isinstance(environment, dict):
        for key, value in environment.items():
            result[key] = "" if value is None else str(value)
    elif isinstance(environment, list):
        for item in environment:
            key, sep, value = str(item).partition("=")
            if sep:
                result[key] = value
    return result
