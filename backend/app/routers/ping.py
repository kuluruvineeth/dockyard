from fastapi import APIRouter

from app.schemas.ping import PingResponse

router = APIRouter()


@router.get("/api/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    return PingResponse(ping="pong")
