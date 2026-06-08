import hmac
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import NotAuthenticated
from app.models import User
from app.security import AUTH_HASH_KEY, AUTH_USER_ID_KEY, session_auth_hash

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DBSession) -> User:
    user_id = request.state.session.get(AUTH_USER_ID_KEY)
    if user_id is None:
        raise NotAuthenticated()
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise NotAuthenticated()

    session_hash = request.state.session.get(AUTH_HASH_KEY)
    if session_hash is not None and not hmac.compare_digest(
        session_hash, session_auth_hash(user)
    ):
        raise NotAuthenticated()

    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
