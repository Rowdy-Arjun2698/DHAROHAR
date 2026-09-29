[CmdletBinding()]
param([string]$Python = 'python', [switch]$SkipModels, [switch]$SkipEngine)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Push-Location $ProjectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Pass its executable using -Python.' }
    }
    $ProjectPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    & $ProjectPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    & $ProjectPython -c "from app.db import init_db; init_db()"
    if (-not $SkipModels) {
        & $ProjectPython scripts/setup_models.py
        if ($LASTEXITCODE -ne 0) { throw 'Model verification/download failed.' }
        & $ProjectPython scripts/setup_neural_voices.py
        if ($LASTEXITCODE -ne 0) { throw 'Neural voice verification/download failed.' }
    }
    $modules = Join-Path $ProjectRoot 'frontend\node_modules'
    if ((Test-Path -LiteralPath $modules) -and ((Get-Item -LiteralPath $modules).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'The development node_modules is a junction. Use Start-DHAROHAR.ps1 here, or run setup from a fresh source copy.'
    }
    Push-Location frontend
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
    if (-not $SkipEngine) {
        & docker build -f Dockerfile.engine -t dharohar-ai:engine .
        if ($LASTEXITCODE -ne 0) { throw 'Engine build failed. Start Docker Desktop with Linux containers.' }
    }
    Write-Host 'Setup complete. Run scripts\Start-DHAROHAR.ps1; see docs\SETUP.md to import your archive.'
} finally { Pop-Location }
