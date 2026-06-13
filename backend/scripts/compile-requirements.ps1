# Regenerate requirements.txt lockfile from requirements.in (run after changing direct deps).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m pip install pip-tools -q
python -m piptools compile requirements.in -o requirements.txt --resolver=backtracking --strip-extras
Write-Host "Updated backend/requirements.txt"
