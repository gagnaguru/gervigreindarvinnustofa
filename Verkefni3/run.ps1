#requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Model = "gpt-5.4-mini"

# Resolve python to an absolute path so Start-Process works even when
# $PSScriptRoot contains spaces (e.g. OneDrive paths).
$pythonRel = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { (Get-Command python).Source }
$python = (Resolve-Path $pythonRel).Path

# Absolute paths to scripts — Start-Process quoting around spaces is finicky,
# so we pass an array of args with the script as a quoted absolute path AND
# set -WorkingDirectory explicitly.
$ssePy   = Join-Path $PSScriptRoot "eval\dashboard\sse_server.py"
$runPy   = Join-Path $PSScriptRoot "eval\harness\run_harness.py"

# Kill any stale SSE server on 8765 before starting.
$existing = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  $existing.OwningProcess | Sort-Object -Unique | ForEach-Object {
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Milliseconds 200
}

# Start dashboard SSE server in the background, kill on exit.
$sseOut = Join-Path $env:TEMP "skill-workshop-sse.out.log"
$sseErr = Join-Path $env:TEMP "skill-workshop-sse.err.log"
$sse = Start-Process -FilePath $python -ArgumentList @("`"$ssePy`"") `
  -WorkingDirectory $PSScriptRoot `
  -WindowStyle Hidden -RedirectStandardOutput $sseOut -RedirectStandardError $sseErr -PassThru
Start-Sleep -Milliseconds 800

if ($sse.HasExited) {
  Write-Host "SSE server failed to start. stderr:"
  if (Test-Path $sseErr) { Get-Content $sseErr -Tail 20 }
  exit 1
}

$url = "http://127.0.0.1:8765/"
Write-Host "Dashboard: $url"
Start-Process $url | Out-Null

try {
  & $python $runPy --model $Model @args
  $code = $LASTEXITCODE
} finally {
  if ($sse -and -not $sse.HasExited) { Stop-Process -Id $sse.Id -Force -ErrorAction SilentlyContinue }
}
exit $code
