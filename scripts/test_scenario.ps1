# Graph RAG 엔드-투-엔드 테스트 시나리오
# 실행: PowerShell에서 .\scripts\test_scenario.ps1

$BASE = "http://localhost:8888"

Write-Host "`n=== Step 1: 헬스체크 ===" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$BASE/api/v1/health" -Method Get
    Write-Host "상태: $($health.status)" -ForegroundColor Green
    Write-Host "Neo4j: $($health.neo4j.status)"
} catch {
    Write-Host "FastAPI 서버가 실행 중이지 않습니다. uvicorn을 먼저 실행하세요." -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Step 2: 단순 질의 (탁도 기준) ===" -ForegroundColor Cyan
$body = @{ question = "수돗물 탁도 기준은 얼마인가?" } | ConvertTo-Json -Compress
try {
    $resp = Invoke-RestMethod -Uri "$BASE/api/v1/query" -Method Post `
        -ContentType "application/json" -Body $body
    Write-Host "답변: $($resp.answer)" -ForegroundColor Green
    Write-Host "Cypher: $($resp.cypher_query)"
    Write-Host "출처: $($resp.sources -join ', ')"
} catch {
    Write-Host "질의 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== Step 3: 복합 질의 (응집과 침전 비교) ===" -ForegroundColor Cyan
$body2 = @{ question = "응집 공정과 침전 공정의 차이는 무엇이며 어떤 약품을 사용하나요?" } | ConvertTo-Json -Compress
try {
    $resp2 = Invoke-RestMethod -Uri "$BASE/api/v1/query" -Method Post `
        -ContentType "application/json" -Body $body2
    Write-Host "답변: $($resp2.answer)" -ForegroundColor Green
} catch {
    Write-Host "복합 질의 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== Step 4: 그래프 노드 조회 ===" -ForegroundColor Cyan
try {
    $graph = Invoke-RestMethod -Uri "$BASE/api/v1/graph/nodes?limit=20" -Method Get
    Write-Host "노드 수: $($graph.nodes.Count)" -ForegroundColor Green
    Write-Host "관계 수: $($graph.edges.Count)"
    $graph.nodes | Select-Object -First 5 | ForEach-Object {
        Write-Host "  - [$($_.type)] $($_.label)"
    }
} catch {
    Write-Host "그래프 조회 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== Step 5: 이웃 탐색 (K-water) ===" -ForegroundColor Cyan
try {
    $neighbors = Invoke-RestMethod -Uri "$BASE/api/v1/graph/neighbors?name=K-water" -Method Get
    Write-Host "K-water 관련 노드: $($neighbors.nodes.Count)개" -ForegroundColor Green
    $neighbors.nodes | ForEach-Object {
        Write-Host "  - [$($_.type)] $($_.label)"
    }
} catch {
    Write-Host "이웃 탐색 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== Step 6: 사고 관련 질의 ===" -ForegroundColor Cyan
$body3 = @{ question = "인천 붉은 수돗물 사고의 원인과 위반된 수질기준은?" } | ConvertTo-Json -Compress
try {
    $resp3 = Invoke-RestMethod -Uri "$BASE/api/v1/query" -Method Post `
        -ContentType "application/json" -Body $body3
    Write-Host "답변: $($resp3.answer)" -ForegroundColor Green
} catch {
    Write-Host "사고 질의 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== 테스트 완료 ===" -ForegroundColor Cyan
