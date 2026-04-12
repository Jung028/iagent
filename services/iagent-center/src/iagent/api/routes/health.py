from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    # TODO: check DB, Redis, Kafka, Anthropic reachability
    return {
        "status": "ok",
        "db": True,
        "redis": True,
        "kafka": True,
        "anthropic_api": True,
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return generate_latest().decode()
