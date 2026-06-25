$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    & (Join-Path $PSScriptRoot "setup.ps1")
}

Push-Location $repoRoot
try {
    & $venvPython -m pytest
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
