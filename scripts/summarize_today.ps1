$ErrorActionPreference = "Stop"
$today = Get-Date -Format "yyyy-MM-dd"
& (Join-Path $PSScriptRoot "run.ps1") summarize --run-folder "data/runs/$today"
