from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select

from app.config import settings
from app.dependencies import CurrentUser, DBSession
from app.errors import (
    AuthenticationFailed,
    PermissionDenied,
    ResourceConflict,
    ValidationException,
)
from app.middleware.csrf import ensure_csrf_cookie
from app.models import User
from app.schemas.auth import (
    AuthedResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    CSRFResponse,
    LoginRequest,
    LoginSuccessResponse,
    UpdateProfileRequest,
    UserCreatedResponse,
    UserCreationRequest,
    UserExistenceResponse,
    UserSchema,
)
from app.security import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from app.services.workspaces import create_default_workspace
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
    await db.flush()
    await create_default_workspace(db, user)
    await db.commit()
    await db.refresh(user)
    login(request, user)

    return JSONResponse(
        {"detail": "Created the first user successfully."}, status_code=201
    )


@router.post("/api/auth/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: DBSession,
    user: CurrentUser,
):
    if not user.check_password(body.current_password):
        raise ValidationException(
            "current_password", "invalid", "Current password is incorrect."
        )
    if body.new_password != body.confirm_password:
        raise ValidationException(
            "confirm_password", "invalid", "The passwords do not match."
        )
    try:
        validate_new_password(body.new_password, user)
    except PasswordValidationError as error:
        raise ValidationException(
            "new_password", error.code or "invalid", error.message
        )

    user.set_password(body.new_password)
    await db.commit()
    update_session_auth_hash(request, user)
    return ChangePasswordResponse(success=True)


@router.patch("/api/auth/update-profile", response_model=UserSchema)
async def update_profile(body: UpdateProfileRequest, db: DBSession, user: CurrentUser):
    if body.username is not None and body.username != user.username:
        existing = await db.scalar(select(User).where(User.username == body.username))
        if existing is not None:
            raise ResourceConflict("A user with this username already exists.")
        user.username = body.username
    if body.first_name is not None:
        user.first_name = body.first_name
    if body.last_name is not None:
        user.last_name = body.last_name

    await db.commit()
    await db.refresh(user)
    return UserSchema.from_user(user)
