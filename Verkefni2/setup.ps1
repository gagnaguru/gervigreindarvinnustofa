#requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== TDD Workshop -- setup =="

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "[RED] python not found."; exit 2 }
$pyver = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
Write-Host "  [OK]  python ($pyver)"

if (-not (Test-Path ".venv")) {
  Write-Host "  ...creating .venv"
  & python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
Write-Host "  [OK]  python deps installed"

Write-Host "  ...verifying pytest"
& .\.venv\Scripts\python.exe -m pytest --version | Out-Null
Write-Host "  [OK]  pytest ready"

Write-Host ""
Write-Host "Setup complete. Open this folder in Cursor or start a Codex session."
exit 0
