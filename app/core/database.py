from contextlib import asynccontextmanager
from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
            max_connection_pool_size=50,
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


async def check_neo4j_health() -> dict:
    try:
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            if record and record["ok"] == 1:
                return {"status": "ok", "uri": settings.neo4j_uri}
    except ServiceUnavailable as e:
        logger.error("Neo4j health check failed", error=str(e))
        return {"status": "error", "detail": str(e)}
    return {"status": "error", "detail": "unexpected response"}


@asynccontextmanager
async def get_session() -> AsyncGenerator:
    driver = await get_driver()
    async with driver.session() as session:
        yield session
