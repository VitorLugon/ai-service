$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Criando ambiente virtual com Python 3.12..."
    py -3.12 -m venv .venv

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
else {
    Write-Host "Ambiente virtual existente encontrado."
}

Write-Host "Atualizando o pip..."
& $pythonPath -m pip install --upgrade pip

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Instalando as dependencias..."
& $pythonPath -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"

    Write-Host ""
    Write-Host "Arquivo .env criado a partir do .env.example."
    Write-Host "Substitua INTERNAL_API_KEY antes de executar a aplicacao."
}
else {
    Write-Host "Arquivo .env existente preservado."
}

Write-Host ""
Write-Host "Configuracao concluida."