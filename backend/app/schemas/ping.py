from typing import Literal

from pydantic import BaseModel


class PingResponse(BaseModel):
    ping: Literal["pong"] = "pong"
