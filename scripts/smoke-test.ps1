$ErrorActionPreference = "Stop"
if ($env:SKIP_COMPOSE -ne '1') {
    python (Join-Path $PSScriptRoot 'local_setup.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$serverUrl = if ($env:REMEMBR_URL) { $env:REMEMBR_URL } else { 'http://localhost:8000' }
python (Join-Path $PSScriptRoot 'smoke_test.py') --url $serverUrl
exit $LASTEXITCODE
