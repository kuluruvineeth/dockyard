from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import NotAuthenticated
from app.models import User
from app.security import AUTH_USER_ID_KEY

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DBSession) -> User:
    user_id = request.state.session.get(AUTH_USER_ID_KEY)
    if user_id is None:
        raise NotAuthenticated()
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise NotAuthenticated()
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
