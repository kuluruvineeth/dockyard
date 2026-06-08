import os

import yaml

from app.main import app

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "openapi", "schema.yml"
)


def build_schema() -> dict:
    schema = app.openapi()
    schema["info"]["title"] = "Dockyard API"
    schema["info"]["version"] = "1.0.0 (v1)"
    return schema


def write_schema(path: str = SCHEMA_PATH) -> None:
    with open(path, "w") as handle:
        yaml.safe_dump(build_schema(), handle, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    write_schema()
    print("wrote openapi schema to openapi/schema.yml")
