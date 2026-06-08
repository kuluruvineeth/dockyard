from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.session import Session, get_store


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        store = get_store()
        key = request.cookies.get("sessionid")
        loaded = store.load(key) if key else None

        if loaded:
            expiry = (
                datetime.fromisoformat(loaded["expiry"])
                if loaded.get("expiry")
                else None
            )
            session = Session(key=key, data=loaded["data"], expiry=expiry)
        else:
            session = Session()

        request.state.session = session
        response = await call_next(request)

        if session.deleted:
            if key:
                store.delete(key)
            response.delete_cookie("sessionid")
        elif session.modified:
            if session.session_key is None:
                session.cycle_key()
            expiry = session.get_expiry_date()
            store.save(session.session_key, session.data, expiry.isoformat())
            response.set_cookie(
                "sessionid",
                session.session_key,
                expires=expiry,
                httponly=True,
                samesite="lax",
                secure=not settings.debug,
            )

        return response
