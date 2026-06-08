import time
from collections import defaultdict

from starlette.requests import Request

from app.errors import ThrottledExceptionWithWaitTime

_history: dict[str, list[float]] = defaultdict(list)

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def _parse_rate(rate: str) -> tuple[int, int]:
    num, period = rate.split("/")
    return int(num), _PERIODS[period.rstrip("s")]


class ScopedRateThrottle:
    def __init__(self, scope: str, rate: str, skip_authed: bool = False):
        self.scope = scope
        self.num_requests, self.window = _parse_rate(rate)
        self.skip_authed = skip_authed

    async def __call__(self, request: Request) -> None:
        if self.skip_authed and request.state.session.get("_auth_user_id"):
            return
        ident = request.client.host if request.client else "anon"
        key = f"{self.scope}:{ident}"
        current = time.time()
        history = _history[key]
        while history and history[0] <= current - self.window:
            history.pop(0)
        if len(history) >= self.num_requests:
            wait = int(self.window - (current - history[0]))
            raise ThrottledExceptionWithWaitTime(wait)
        history.append(current)
