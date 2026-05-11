# Graph RAG 벤치마크 평가 실행 스크립트
# 사용법: .\scripts\run_benchmark.ps1 [--category 기준값_단순] [--difficulty easy]

param(
    [string]$Category = "",
    [string]$Difficulty = "",
    [string]$Output = "evaluation\eval_result.json"
)

$args_list = @()
if ($Category) { $args_list += "--category", $Category }
if ($Difficulty) { $args_list += "--difficulty", $Difficulty }
if ($Output) { $args_list += "--output", $Output }

Write-Host "Graph RAG 벤치마크 평가 시작..." -ForegroundColor Cyan
python -m evaluation.evaluator @args_list
