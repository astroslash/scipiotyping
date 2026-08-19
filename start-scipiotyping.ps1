$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirementsPath = Join-Path $projectRoot "requirements.txt"

Set-Location $projectRoot

if (-not (Test-Path $pythonPath)) {
    Write-Host "Preparing ScipioTyping for first use..."
    py -m venv .venv
}

& $pythonPath -c "import flask, waitress, psycopg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing ScipioTyping's local components..."
    & $pythonPath -m pip install -r $requirementsPath
}

$expectedVersion = (& $pythonPath -c "import scipiotyping; print(scipiotyping.__version__)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $expectedVersion) {
    throw "ScipioTyping's installed version could not be checked."
}

$health = $null
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health" -TimeoutSec 2
} catch {
    # No local server is running yet.
}

if ($health -and $health.status -eq "ok" -and $health.application -eq "ScipioTyping") {
    if ($health.version -eq $expectedVersion) {
        Start-Process "http://127.0.0.1:5000"
        Write-Host "ScipioTyping $expectedVersion was already running, so its browser page was opened."
        exit 0
    }

    Write-Host "Restarting an older ScipioTyping server so version $expectedVersion can load..."
    $listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "::1") } |
        Select-Object -First 1
    if (-not $listener) {
        throw "The older ScipioTyping server could not be identified. Close its PowerShell window and try again."
    }
    $serverProcessId = $listener.OwningProcess
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serverProcessId"
    if (-not $serverProcess -or $serverProcess.CommandLine -notmatch '(?i)(^|\s)-m\s+scipiotyping(\s|$)') {
        throw "Port 5000 is owned by another program. Close that program before starting ScipioTyping."
    }
    Stop-Process -Id $serverProcessId -Force
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $stillListening = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalAddress -in @("127.0.0.1", "::1") }
        if (-not $stillListening) { break }
        Start-Sleep -Milliseconds 100
    }
    if ($stillListening) {
        throw "The older ScipioTyping server did not stop. Close its PowerShell window and try again."
    }
}

& $pythonPath -m scipiotyping
