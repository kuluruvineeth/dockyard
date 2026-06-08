from datetime import timedelta

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import AuthenticationFailed
from app.middleware.csrf import ensure_csrf_cookie
from app.schemas.auth import (
    AuthedResponse,
    CSRFResponse,
    LoginRequest,
    LoginSuccessResponse,
    UserSchema,
)
from app.security import authenticate, login, logout
from app.session import now

router = APIRouter()


@router.post("/api/auth/login", status_code=201, response_model=LoginSuccessResponse)
async def login_view(
    request: Request,
    body: LoginRequest,
    db: DBSession,
    redirect_to: str | None = None,
):
    user = await authenticate(db, body.username, body.password)
    if user is None:
        raise AuthenticationFailed("Invalid username or password")

    login(request, user)

    if redirect_to is not None:
        return RedirectResponse(redirect_to, status_code=302)
    return JSONResponse({"success": True}, status_code=201)


@router.delete("/api/auth/logout", status_code=204)
async def logout_view(request: Request, user: CurrentUser):
    logout(request)
    return Response(status_code=204)


@router.get("/api/auth/me", response_model=AuthedResponse)
async def me_view(request: Request, user: CurrentUser):
    session = request.state.session
    if session.get_expiry_date() < (
        now() + timedelta(days=settings.session_expire_threshold)
    ):
        session.set_expiry(now() + timedelta(seconds=settings.session_extend_period))
    return AuthedResponse(user=UserSchema.from_user(user), membership=None)


@router.get("/api/csrf", response_model=CSRFResponse)
async def csrf_view(request: Request):
    response = JSONResponse({"details": "CSRF cookie set"})
    ensure_csrf_cookie(request, response)
    return response
