$ErrorActionPreference = "Stop"
python (Join-Path $PSScriptRoot 'local_setup.py') @args
exit $LASTEXITCODE
