# Activate the project environment for the current PowerShell session.
#
#   . .\scripts\env.ps1
#
# REQUIRES an ExecutionPolicy that allows local scripts. Under the Windows
# default (Restricted) this fails with UnauthorizedAccess — use the
# scripts\vcc.cmd and scripts\py.cmd wrappers instead, which have no such limit.
$VenvRoot = if ($env:VCC2026_DATA_ROOT) { $env:VCC2026_DATA_ROOT } else { "C:\Users\ferra\vcc2026-data" }
& "$VenvRoot\.venv\Scripts\Activate.ps1"
$env:PYTHONIOENCODING = "utf-8"          # the vcc CLI emits non-cp1252 characters
$env:PYTHONPATH = "$PSScriptRoot\..\src"
Write-Host "VCC 2026 environment active - $(python --version 2>&1), data in $VenvRoot" -ForegroundColor Green
