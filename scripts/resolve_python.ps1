param()

$ErrorActionPreference = "Stop"

function Test-RealPython {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    if ($Path -like "*\WindowsApps\python*.exe") {
        return $false
    }
    try {
        & $Path --version *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-RealPython $venvPython) {
    Write-Output $venvPython
    exit 0
}

$candidates = @()

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    $candidates += $pythonCmd.Source
}

$pyCmd = Get-Command py -ErrorAction SilentlyContinue
if ($pyCmd) {
    try {
        $pyPath = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $candidates += $pyPath
        }
    }
    catch {
    }
}

$bundledPython = "C:\Users\cmedu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$candidates += $bundledPython

foreach ($candidate in $candidates) {
    if (Test-RealPython $candidate) {
        Write-Output $candidate
        exit 0
    }
}

Write-Error "No usable Python found. Install Python 3.11+ from https://www.python.org/downloads/windows/ and make sure 'Add python.exe to PATH' is selected."
exit 1
