from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.models import User
from app.session import SESSION_COOKIE_AGE, now

AUTH_USER_ID_KEY = "_auth_user_id"


async def authenticate(db: AsyncSession, username: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not user.check_password(password):
        return None
    return user


def login(request: Request, user: User) -> None:
    session = request.state.session
    session.cycle_key()
    session[AUTH_USER_ID_KEY] = user.id
    session.set_expiry(now() + timedelta(seconds=SESSION_COOKIE_AGE))
    request.state.user = user


def logout(request: Request) -> None:
    request.state.session.flush()


def update_session_auth_hash(request: Request, user: User) -> None:
    request.state.session.modified = True
