from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

VALIDATION_ERROR = "validation_error"
CLIENT_ERROR = "client_error"
SERVER_ERROR = "server_error"


class APIException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "error"
    default_detail = "An error occurred."

    def __init__(self, detail: str | None = None, code: str | None = None):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code


class ResourceConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "resource_conflict"
    default_detail = "This resource already exists."


class BadRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"


class AuthenticationFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_failed"
    default_detail = "Incorrect authentication credentials."


class NotAuthenticated(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "not_authenticated"
    default_detail = "Authentication credentials were not provided."


class PermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_denied"
    default_detail = "You do not have permission to perform this action."


class NotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "Not found."


class ThrottledExceptionWithWaitTime(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "throttled"

    def __init__(self, wait: int | None = None):
        self.wait = wait
        detail = "Request was throttled."
        if wait is not None:
            detail = f"Request was throttled. Expected available in {wait} seconds."
        super().__init__(detail=detail)


class ValidationException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, attr: str | None, code: str, detail: str):
        self.attr = attr
        self.code = code
        self.detail = detail


def _envelope(type_: str, errors: list[dict], status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"type": type_, "errors": errors}
    )


def _error_type_for_status(status_code: int) -> str:
    return SERVER_ERROR if status_code >= 500 else CLIENT_ERROR


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    return _envelope(
        _error_type_for_status(exc.status_code),
        [{"code": exc.code, "detail": exc.detail, "attr": None}],
        exc.status_code,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "type" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return _envelope(
        _error_type_for_status(exc.status_code),
        [{"code": "error", "detail": str(exc.detail), "attr": None}],
        exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors: list[dict] = []
    for err in exc.errors():
        loc = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
        attr = loc[-1] if loc else None
        errors.append(
            {"code": err.get("type", "invalid"), "detail": err["msg"], "attr": attr}
        )
    return _envelope(VALIDATION_ERROR, errors, status.HTTP_400_BAD_REQUEST)


async def validation_field_exception_handler(
    request: Request, exc: ValidationException
) -> JSONResponse:
    return _envelope(
        VALIDATION_ERROR,
        [{"code": exc.code, "detail": exc.detail, "attr": exc.attr}],
        exc.status_code,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(ValidationException, validation_field_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
