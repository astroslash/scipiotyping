$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

Set-Location $projectRoot

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -TimeoutSec 2
    if ($health.status -eq "ok") {
        Start-Process "http://127.0.0.1:5000"
        Write-Host "ScipioTyping was already running, so its browser page was opened."
        exit 0
    }
} catch {
    # No local server is running yet.
}

if (-not (Test-Path $pythonPath)) {
    Write-Host "Preparing ScipioTyping for first use..."
    py -m venv .venv
}

& $pythonPath -c "import flask, waitress" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing ScipioTyping's local components..."
    & $pythonPath -m pip install -r $requirementsPath
}

& $pythonPath -m scipiotyping
