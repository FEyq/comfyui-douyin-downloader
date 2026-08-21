@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Music Note Cookie Helper
if /i "%~1"=="--check" (
    echo Batch syntax and command parsing OK.
    exit /b 0
)

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "PYTHON_ARGS="

if exist "%PYTHON%" (
    "%PYTHON%" -c "import sys" >nul 2>&1
    if errorlevel 1 set "PYTHON="
)

if not defined PYTHON (
    set "PYTHON="
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py"
        set "PYTHON_ARGS=-3"
    )
)

if not defined PYTHON (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON=python"
)

if not defined PYTHON (
    echo Python 3 was not found. Please install Python 3.8 or newer.
    pause
    exit /b 1
)

echo Python: %PYTHON% %PYTHON_ARGS%
"%PYTHON%" %PYTHON_ARGS% -c "import tkinter, playwright" >nul 2>&1
if errorlevel 1 (
    echo Installing the Playwright dependency...
    "%PYTHON%" %PYTHON_ARGS% -m pip install --disable-pip-version-check playwright
    if errorlevel 1 (
        echo.
        echo Playwright installation failed. Check your network connection.
        pause
        exit /b 1
    )
)

echo Starting the three-step Music Note Cookie helper...
"%PYTHON%" %PYTHON_ARGS% "%~dp0cookie_helper.py"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo The Cookie helper exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
