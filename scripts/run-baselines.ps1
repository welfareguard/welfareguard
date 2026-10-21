# One command per model: run the P0 task, then export every log to clusters.
# Usage (from the repo folder, venv active, ANTHROPIC_API_KEY set):
#   .\scripts\run-baselines.ps1
#   .\scripts\run-baselines.ps1 -Models anthropic/claude-haiku-4-5-20251001 -Epochs 2
# All three defaults are Anthropic models, so no second SDK or key is needed.
param(
    [string[]]$Models = @("anthropic/claude-opus-5", "anthropic/claude-haiku-4-5-20251001"),
    [int]$Epochs = 4,
    [string]$Scenarios = "all",
    [string]$Arms = "all"
)
$ErrorActionPreference = "Stop"
if (-not $env:ANTHROPIC_API_KEY) { throw "Set `$env:ANTHROPIC_API_KEY first." }
foreach ($m in $Models) {
    Write-Host "=== $m ===" -ForegroundColor Cyan
    inspect eval src/welfareguard/evals/inspect_task.py@p0 --model $m --epochs $Epochs -T scenarios=$Scenarios -T arms=$Arms --log-dir logs/
    if ($LASTEXITCODE -ne 0) { throw "inspect eval failed for $m" }
}
python -m welfareguard.evals "logs/*.eval" --out clusters/
python -m welfareguard.evals.report "logs/*.eval" --out docs/results/baseline-table.md
Write-Host "done: clusters/ and docs/results/baseline-table.md updated" -ForegroundColor Green
