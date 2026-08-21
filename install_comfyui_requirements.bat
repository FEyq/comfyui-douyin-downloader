@echo off
setlocal
cd /d "%~dp0"
title Install Douyin ComfyUI Dependencies

set "PYTHON="
if exist "%~dp0..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\python\python.exe" set "PYTHON=%~dp0..\..\python\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\python\python.exe" set "PYTHON=%~dp0..\..\..\python\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\..\python\python.exe" set "PYTHON=%~dp0..\..\..\..\python\python.exe"
if not defined PYTHON set "PYTHON=python"

echo Using Python: %PYTHON%
"%PYTHON%" -m pip install -r requirements.txt
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo Dependencies installed. Run check_douyin_node.bat before restarting ComfyUI.
) else (
    echo Dependency installation failed.
)
pause
exit /b %EXIT_CODE%

