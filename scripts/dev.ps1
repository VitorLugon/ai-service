$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$fastApiPath = Join-Path $projectRoot ".venv\Scripts\fastapi.exe"

if (-not (Test-Path $fastApiPath)) {
    Write-Error "FastAPI nao encontrado. Execute scripts\setup.ps1."
    exit 1
}

& $fastApiPath dev app/main.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}