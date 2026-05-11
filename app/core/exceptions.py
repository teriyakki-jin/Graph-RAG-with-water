from fastapi import Request
from fastapi.responses import JSONResponse
from neo4j.exceptions import ServiceUnavailable, CypherSyntaxError, AuthError


async def neo4j_unavailable_handler(request: Request, exc: ServiceUnavailable) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "graph_db_unavailable", "detail": "Neo4j에 연결할 수 없습니다."},
    )


async def cypher_error_handler(request: Request, exc: CypherSyntaxError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "cypher_syntax_error", "detail": str(exc)},
    )


async def neo4j_auth_handler(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "graph_db_auth_error", "detail": "Neo4j 인증에 실패했습니다."},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(ServiceUnavailable, neo4j_unavailable_handler)
    app.add_exception_handler(CypherSyntaxError, cypher_error_handler)
    app.add_exception_handler(AuthError, neo4j_auth_handler)
