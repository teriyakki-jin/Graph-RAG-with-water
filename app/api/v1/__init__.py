from fastapi import APIRouter
from app.api.v1 import health, query, graph

router = APIRouter(prefix="/v1")
router.include_router(health.router)
router.include_router(query.router)
router.include_router(graph.router)
