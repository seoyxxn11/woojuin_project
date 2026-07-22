param([string]$SampleId)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment Python was not found: $Python" }

$arguments = @(
    (Join-Path $Root "run_benchmark.py"),
    "--config", (Join-Path $Root "config.gms.gemini.yaml")
)
if ($SampleId) { $arguments += @("--sample-id", $SampleId) }

& $Python @arguments
exit $LASTEXITCODE
