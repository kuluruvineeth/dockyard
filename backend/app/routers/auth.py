from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import AuthenticationFailed, PermissionDenied, ValidationException
from app.middleware.csrf import ensure_csrf_cookie
from app.models import User
from app.schemas.auth import (
    AuthedResponse,
    CSRFResponse,
    LoginRequest,
    LoginSuccessResponse,
    UserCreatedResponse,
    UserCreationRequest,
    UserExistenceResponse,
    UserSchema,
)
from app.security import authenticate, login, logout
from app.session import now
from app.throttling import ScopedRateThrottle
from app.validators import ValidationError as PasswordValidationError
from app.validators import validate_new_password

router = APIRouter()

login_throttle = ScopedRateThrottle("login", settings.anon_throttle_rate)
initial_registration_throttle = ScopedRateThrottle(
    "initial_registration", "30/minute", skip_authed=True
)


async def _user_count(db) -> int:
    return await db.scalar(select(func.count()).select_from(User))


@router.post(
    "/api/auth/login",
    status_code=201,
    response_model=LoginSuccessResponse,
    dependencies=[Depends(login_throttle)],
)
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


@router.get(
    "/api/auth/check-user-existence",
    response_model=UserExistenceResponse,
    dependencies=[Depends(initial_registration_throttle)],
)
async def check_user_existence(db: DBSession):
    count = await _user_count(db)
    return UserExistenceResponse(exists=count > 0)


@router.post(
    "/api/auth/create-initial-user",
    status_code=201,
    response_model=UserCreatedResponse,
    dependencies=[Depends(initial_registration_throttle)],
)
async def create_initial_user(
    request: Request, body: UserCreationRequest, db: DBSession
):
    if await _user_count(db) > 0:
        raise PermissionDenied("A user already exists.")

    try:
        validate_new_password(body.password)
    except PasswordValidationError as error:
        raise ValidationException("password", error.code or "invalid", error.message)

    user = User(username=body.username, is_superuser=True, is_active=True)
    user.set_password(body.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    login(request, user)

    return JSONResponse(
        {"detail": "Created the first user successfully."}, status_code=201
    )
