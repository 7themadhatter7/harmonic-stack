@echo off
REM Harmonic Stack Launcher - Windows
REM Ghost in the Machine Labs

cd /d "%~dp0"

echo ============================================
echo   HARMONIC STACK LAUNCHER
echo   Ghost in the Machine Labs
echo ============================================
echo.

REM Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Check for Ollama
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ollama not found in PATH
    pause
    exit /b 1
)

REM Parse arguments
set START_FLAG=
set PRELOAD_FLAG=

:parse_args
if "%~1"=="" goto run
if /i "%~1"=="--start" set START_FLAG=--start
if /i "%~1"=="--preload" set PRELOAD_FLAG=--preload
if /i "%~1"=="-s" set START_FLAG=--start
if /i "%~1"=="-p" set PRELOAD_FLAG=--preload
shift
goto parse_args

:run
python harmonic_launcher.py %START_FLAG% %PRELOAD_FLAG% --save

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Launcher failed
    pause
    exit /b 1
)

echo.
echo Done.
pause
