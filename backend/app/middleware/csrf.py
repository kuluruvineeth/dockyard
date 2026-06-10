import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
# webhook endpoints are authenticated by provider signatures, not CSRF tokens
CSRF_EXEMPT_PREFIXES = (
    "/api/connectors/github/webhook",
    "/api/connectors/gitlab/webhook",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.testing:
            return await call_next(request)

        exempt = any(request.url.path.startswith(p) for p in CSRF_EXEMPT_PREFIXES)
        if request.method not in SAFE_METHODS and not exempt:
            cookie_token = request.cookies.get("csrftoken")
            header_token = request.headers.get("X-CSRFToken")
            if not cookie_token or cookie_token != header_token:
                return JSONResponse(
                    status_code=403,
                    content={
                        "type": "client_error",
                        "errors": [
                            {
                                "code": "permission_denied",
                                "detail": "CSRF Failed: CSRF token missing or incorrect.",
                                "attr": None,
                            }
                        ],
                    },
                )

        return await call_next(request)


def ensure_csrf_cookie(request: Request, response) -> None:
    if not request.cookies.get("csrftoken"):
        response.set_cookie(
            "csrftoken",
            secrets.token_hex(32),
            samesite="lax",
            secure=not settings.debug,
        )
