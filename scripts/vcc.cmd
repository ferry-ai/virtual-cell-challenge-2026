@echo off
REM Wrapper around the project venv's vcc CLI.
REM .cmd files are not subject to PowerShell's ExecutionPolicy, unlike .ps1.
setlocal
if "%VCC2026_DATA_ROOT%"=="" set "VCC2026_DATA_ROOT=C:\Users\ferra\vcc2026-data"
set "PYTHONIOENCODING=utf-8"
"%VCC2026_DATA_ROOT%\.venv\Scripts\vcc.exe" %*
