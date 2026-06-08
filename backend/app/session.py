import json
import secrets
from datetime import datetime, timedelta
from datetime import timezone as tz

import redis

from app.config import settings

SESSION_COOKIE_AGE = 60 * 60 * 24 * 14


def now() -> datetime:
    return datetime.now(tz.utc)


class MemorySessionStore:
    _store: dict[str, dict] = {}

    def load(self, key: str) -> dict | None:
        return self._store.get(key)

    def save(self, key: str, data: dict, expiry: str) -> None:
        self._store[key] = {"data": data, "expiry": expiry}

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RedisSessionStore:
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url)

    def load(self, key: str) -> dict | None:
        raw = self._redis.get(f"session:{key}")
        return json.loads(raw) if raw else None

    def save(self, key: str, data: dict, expiry: str) -> None:
        ttl = int((datetime.fromisoformat(expiry) - now()).total_seconds())
        self._redis.set(
            f"session:{key}",
            json.dumps({"data": data, "expiry": expiry}),
            ex=max(ttl, 1),
        )

    def delete(self, key: str) -> None:
        self._redis.delete(f"session:{key}")


_store: MemorySessionStore | RedisSessionStore | None = None


def get_store() -> MemorySessionStore | RedisSessionStore:
    global _store
    if _store is None:
        _store = MemorySessionStore() if settings.testing else RedisSessionStore()
    return _store


class Session:
    def __init__(
        self,
        key: str | None = None,
        data: dict | None = None,
        expiry: datetime | None = None,
    ) -> None:
        self.session_key = key
        self.data = data or {}
        self.expiry = expiry
        self.modified = False
        self.deleted = False

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def __setitem__(self, key: str, value) -> None:
        self.data[key] = value
        self.modified = True

    def pop(self, key: str, default=None):
        self.modified = True
        return self.data.pop(key, default)

    def flush(self) -> None:
        self.data = {}
        self.deleted = True
        self.modified = True

    def cycle_key(self) -> None:
        self.session_key = secrets.token_hex(20)
        self.modified = True

    def get_expiry_date(self) -> datetime:
        return self.expiry or (now() + timedelta(seconds=SESSION_COOKIE_AGE))

    def set_expiry(self, value: datetime) -> None:
        self.expiry = value
        self.modified = True
