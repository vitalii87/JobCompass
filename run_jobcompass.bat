@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m app
) else (
    python -m app
)

if errorlevel 1 (
    echo.
    echo JobCompass could not start. Install Python 3.11 or newer.
    pause
)
