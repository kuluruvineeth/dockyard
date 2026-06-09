def convert_value_to_bytes(value: float, unit: str = "BYTES") -> int:
    multipliers = {
        "BYTES": 1,
        "KILOBYTES": 1024,
        "MEGABYTES": 1024**2,
        "GIGABYTES": 1024**3,
    }
    return int(value * multipliers.get(unit, 1))


def strip_slash_if_exists(
    url: str,
    strip_end: bool = False,
    strip_start: bool = True,
) -> str:
    final_url = url
    if strip_start and url.startswith("/"):
        final_url = final_url[1:]
    if strip_end and url.endswith("/"):
        final_url = final_url[:-1]
    return final_url
