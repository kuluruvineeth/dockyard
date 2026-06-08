import os

import yaml

from app.main import app

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "openapi", "schema.yml"
)

_VALIDATION_ITEM = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "detail": {"type": "string"},
        "attr": {"type": "string"},
    },
    "required": ["code", "detail", "attr"],
}
_CLIENT_ITEM = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "detail": {"type": "string"},
        "attr": {"type": "string", "nullable": True},
    },
    "required": ["code", "detail", "attr"],
}


def _envelope(type_value: str, item_ref: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": [type_value]},
            "errors": {
                "type": "array",
                "items": {"$ref": f"#/components/schemas/{item_ref}"},
            },
        },
        "required": ["type", "errors"],
    }


ERROR_COMPONENTS = {
    "ValidationErrorItem": _VALIDATION_ITEM,
    "ClientServerErrorItem": _CLIENT_ITEM,
    "ValidationErrorResponse": _envelope("validation_error", "ValidationErrorItem"),
    "ClientErrorResponse": _envelope("client_error", "ClientServerErrorItem"),
    "ServerErrorResponse": _envelope("server_error", "ClientServerErrorItem"),
    "ErrorResponse": {
        "oneOf": [
            {"$ref": "#/components/schemas/ValidationErrorResponse"},
            {"$ref": "#/components/schemas/ClientErrorResponse"},
            {"$ref": "#/components/schemas/ServerErrorResponse"},
        ]
    },
}


def build_schema() -> dict:
    schema = app.openapi()
    schema["info"]["title"] = "Dockyard API"
    schema["info"]["version"] = "1.0.0 (v1)"

    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components.update(ERROR_COMPONENTS)
    components.pop("HTTPValidationError", None)
    components.pop("ValidationError", None)

    error_ref = {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            for status_code, response in responses.items():
                if str(status_code)[0] in ("4", "5"):
                    response["content"] = {"application/json": dict(error_ref)}
            responses["default"] = {
                "description": "Error",
                "content": {"application/json": dict(error_ref)},
            }

    return schema


def write_schema(path: str = SCHEMA_PATH) -> None:
    with open(path, "w") as handle:
        yaml.safe_dump(build_schema(), handle, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    write_schema()
    print("wrote openapi schema to openapi/schema.yml")
