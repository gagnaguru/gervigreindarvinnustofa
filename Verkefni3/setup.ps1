#requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== Skill Workshop -- setup =="

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

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
  Write-Host "[RED] codex CLI not found. Install: https://developers.openai.com/codex/cli/install"
  exit 2
}
Write-Host "  [OK]  codex CLI on PATH"

if (-not $env:OPENAI_API_KEY) {
  $loginCheck = & codex login status 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[RED] no OPENAI_API_KEY and codex not logged in. Run 'codex login' or set `$env:OPENAI_API_KEY."
    exit 2
  }
  Write-Host "  [OK]  codex authenticated (login)"
} else {
  Write-Host "  [OK]  OPENAI_API_KEY set"
}

& .\.venv\Scripts\python.exe .\eval\harness\setup_check.py
exit $LASTEXITCODE
