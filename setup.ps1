param([switch]$Dev)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PSScriptRoot '.tools\python'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv from https://docs.astral.sh/uv/getting-started/installation/ and reopen PowerShell, then run setup.ps1 again.'
}
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    uv python install 3.13
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
    uv venv --python 3.13 .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$requirementsFile = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
uv pip install --python .venv\Scripts\python.exe -r $requirementsFile --constraint constraints.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path -LiteralPath 'upstream\WorldBuilder\main.py')) {
    git clone https://github.com/AdamRolander/WorldBuilder.git upstream/WorldBuilder
    if ($LASTEXITCODE -ne 0) { throw 'WorldBuilder clone failed.' }
    git -C upstream/WorldBuilder checkout 2852e3b6a833465455d625608c9341cc5747374c
    if ($LASTEXITCODE -ne 0) { throw 'Could not pin the inspected upstream version.' }
}
if (-not (Test-Path -LiteralPath 'stageai\static\vendor\three.module.js')) {
    & .venv\Scripts\python.exe scripts/fetch_assets.py
    if ($LASTEXITCODE -ne 0) { throw 'Viewer asset download failed.' }
}
Write-Host 'Setup complete. Start the local studio with .\launch.ps1' -ForegroundColor Green

