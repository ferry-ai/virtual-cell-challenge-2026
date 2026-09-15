@echo off
REM The orchestrator console. Mirrors py.cmd: UTF-8 and src/ on PYTHONPATH.
REM
REM It prefers <data_root>\orch-venv (playwright + pyyaml, for the web adapters) and falls
REM back to the project venv, which is enough for the engine, the Gemini CLI adapter and
REM the offline rehearsal. VCC2026_ORCH_PYTHON overrides both. The analysis environment
REM stays untouched: playwright is not installed into it.
setlocal
if "%VCC2026_DATA_ROOT%"=="" set "VCC2026_DATA_ROOT=C:\Users\ferra\vcc2026-data"
if "%VCC2026_ORCH_PYTHON%"=="" if exist "%VCC2026_DATA_ROOT%\orch-venv\Scripts\python.exe" set "VCC2026_ORCH_PYTHON=%VCC2026_DATA_ROOT%\orch-venv\Scripts\python.exe"
if "%VCC2026_ORCH_PYTHON%"=="" set "VCC2026_ORCH_PYTHON=%VCC2026_DATA_ROOT%\.venv\Scripts\python.exe"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%~dp0..\src;%PYTHONPATH%"
"%VCC2026_ORCH_PYTHON%" -m orchestrator.cli %*
