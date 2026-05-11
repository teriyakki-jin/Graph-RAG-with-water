from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.database import get_driver, close_driver
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting GraphRAG API", env=settings.app_env)
    await get_driver()   # 앱 시작 시 드라이버 초기화 & 연결 확인
    yield
    await close_driver()
    logger.info("GraphRAG API shutdown complete")


app = FastAPI(
    title="Graph RAG API",
    description="수처리 도메인 지식 그래프 기반 RAG 시스템",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api")
register_exception_handlers(app)
