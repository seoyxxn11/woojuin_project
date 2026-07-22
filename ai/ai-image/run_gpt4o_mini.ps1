param(
    [string]$SampleId
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment Python was not found: $Python"
}

$EnvFile = Join-Path $Root ".env"
if (-not $env:GMS_API_KEY -and -not (Test-Path $EnvFile)) {
    $secureKey = Read-Host "Enter GMS API key" -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $env:GMS_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

$arguments = @(
    (Join-Path $Root "run_benchmark.py"),
    "--config", (Join-Path $Root "config.gms.yaml"),
    "--model-id", "gpt-4o-mini"
)

if ($SampleId) {
    $arguments += @("--sample-id", $SampleId)
}

& $Python @arguments
exit $LASTEXITCODE
