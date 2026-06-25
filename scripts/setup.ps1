param(
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if ($Recreate -and (Test-Path -LiteralPath $venvDir)) {
    Remove-Item -LiteralPath $venvDir -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    $basePython = & (Join-Path $PSScriptRoot "resolve_python.ps1")
    Write-Host "Creating virtual environment with: $basePython"
    & $basePython -m venv $venvDir
}

Write-Host "Installing dependencies..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $repoRoot "requirements.txt")

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot ".env.local"))) {
    Copy-Item -LiteralPath (Join-Path $repoRoot ".env.example") -Destination (Join-Path $repoRoot ".env.local")
    Write-Host "Created .env.local from .env.example"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Python: $venvPython"
Write-Host "Next: .\scripts\mock_preflight.ps1"
