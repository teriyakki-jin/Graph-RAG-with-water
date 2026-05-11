from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import check_neo4j_health

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    neo4j: dict


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    neo4j_status = await check_neo4j_health()
    overall = "ok" if neo4j_status["status"] == "ok" else "degraded"
    return HealthResponse(status=overall, neo4j=neo4j_status)
