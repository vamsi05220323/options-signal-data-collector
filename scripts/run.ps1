param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AppArgs
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Virtual environment missing. Running setup first..."
    & (Join-Path $PSScriptRoot "setup.ps1")
}

Push-Location $repoRoot
try {
    & $venvPython -m src.main @AppArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
