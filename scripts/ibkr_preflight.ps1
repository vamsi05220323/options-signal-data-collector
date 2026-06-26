$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run.ps1") preflight --provider ibkr
exit $LASTEXITCODE
