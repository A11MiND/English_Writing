from fastapi import APIRouter, Request, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.responses import ApiException, ErrorCode, success_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def root_health(request: Request) -> dict:
    settings = get_settings()
    return success_response(
        request,
        {
            "service": "api",
            "status": "ok",
            "environment": settings.environment,
            "checks": {},
        },
    )


@router.get("/api/health")
async def api_health(request: Request) -> dict:
    settings = get_settings()
    checks = {"api": "ok"}
    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
    finally:
        await redis.aclose()

    return success_response(
        request,
        {
            "service": "api",
            "status": "ok" if checks["redis"] == "ok" else "degraded",
            "environment": settings.environment,
            "checks": checks,
        },
    )


@router.get("/api/health/db")
async def db_health(request: Request) -> dict:
    settings = get_settings()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("select 1"))
    except Exception as exc:
        raise ApiException(
            ErrorCode.HEALTH_CHECK_FAILED,
            "Database health check failed.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    return success_response(
        request,
        {
            "service": "api",
            "status": "ok",
            "environment": settings.environment,
            "checks": {"database": "ok"},
        },
    )
