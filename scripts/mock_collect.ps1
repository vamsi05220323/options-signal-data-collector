param(
    [int]$DurationSeconds = 30
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "run.ps1") collect-file --signals-file data/sample_signals_today.csv --provider mock --duration-seconds $DurationSeconds
