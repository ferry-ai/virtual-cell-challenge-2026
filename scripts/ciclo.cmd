@echo off
REM Chain of cycles: plan, review (Codex), implementation (Claude), control (Grok).
REM Windows Task Scheduler runs "ciclo.cmd guardiano" at logon; "ciclo.cmd run" is the
REM morning fallback that waits for the plan and drains the queue.
REM Contract and commands: docs\CICLO_GIORNALIERO.md
setlocal
if "%VCC2026_DATA_ROOT%"=="" set "VCC2026_DATA_ROOT=C:\Users\ferra\vcc2026-data"
set "PYTHONIOENCODING=utf-8"
set "HERE=%~dp0"
set "CYCLE_PYTHON=%VCC2026_CYCLE_PYTHON%"
if "%CYCLE_PYTHON%"=="" set "CYCLE_PYTHON=python"
set "LOG=%VCC2026_DATA_ROOT%\ciclo\scheduler.log"
if not exist "%VCC2026_DATA_ROOT%\ciclo" mkdir "%VCC2026_DATA_ROOT%\ciclo"
echo [%DATE% %TIME%] ciclo.cmd %* >> "%LOG%"
"%CYCLE_PYTHON%" "%HERE%32_daily_cycle.py" %* >> "%LOG%" 2>&1
set "CODE=%ERRORLEVEL%"
echo [%DATE% %TIME%] exit %CODE% >> "%LOG%"
exit /b %CODE%
