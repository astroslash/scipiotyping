$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
& ".\.venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& ".\.venv\Scripts\python.exe" -m flask --app scipiotyping validate-content
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& ".\.venv\Scripts\python.exe" -m scripts.release_check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& ".\.venv\Scripts\python.exe" -m scripts.browser_smoke
exit $LASTEXITCODE
