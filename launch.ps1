param([int]$Port = 5174, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & (Join-Path $PSScriptRoot 'setup.ps1')
}
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a port between 1024 and 65535.' }
$studioUrl = "http://127.0.0.1:$Port"
Write-Host "StageAI room studio: $studioUrl" -ForegroundColor Green
Write-Host 'Keep this terminal open. Press Ctrl+C to stop. Projects are saved in data/.'
if (-not $NoBrowser) {
    $env:STAGEAI_OPEN_URL = $studioUrl
    & .venv\Scripts\python.exe scripts/serve.py --port $Port --open
} else {
    & .venv\Scripts\python.exe scripts/serve.py --port $Port
}
if ($LASTEXITCODE -ne 0) { throw 'The server could not start. Check whether the selected port is in use.' }

