$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Error "Ambiente virtual nao encontrado. Execute scripts\setup.ps1."
    exit 1
}

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "=== $Name ==="

    & $Command

    if ($LASTEXITCODE -ne 0) {
        Write-Error "$Name falhou."
        exit $LASTEXITCODE
    }
}

Invoke-Check "Ruff lint" {
    & $pythonPath -m ruff check .
}

Invoke-Check "Ruff format" {
    & $pythonPath -m ruff format --check .
}

Invoke-Check "mypy" {
    & $pythonPath -m mypy app
}

Invoke-Check "Testes e cobertura" {
    & $pythonPath -m pytest
}

Write-Host ""
Write-Host "Todas as verificacoes foram concluidas com sucesso."