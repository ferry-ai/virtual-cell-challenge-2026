@echo off
REM The project venv's Python, with src/ already on PYTHONPATH.
setlocal
if "%VCC2026_DATA_ROOT%"=="" set "VCC2026_DATA_ROOT=C:\Users\ferra\vcc2026-data"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0..\src;%PYTHONPATH%"
"%VCC2026_DATA_ROOT%\.venv\Scripts\python.exe" %*
