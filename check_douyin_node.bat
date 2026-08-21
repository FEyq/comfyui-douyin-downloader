@echo off
setlocal
cd /d "%~dp0"
title Check Douyin ComfyUI Node

set "PYTHON="
if exist "%~dp0..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\..\python_embeded\python.exe" set "PYTHON=%~dp0..\..\..\..\python_embeded\python.exe"
if not defined PYTHON if exist "%~dp0..\..\python\python.exe" set "PYTHON=%~dp0..\..\python\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\python\python.exe" set "PYTHON=%~dp0..\..\..\python\python.exe"
if not defined PYTHON if exist "%~dp0..\..\..\..\python\python.exe" set "PYTHON=%~dp0..\..\..\..\python\python.exe"
if not defined PYTHON set "PYTHON=python"

echo Python: %PYTHON%
echo Node directory: %~dp0
echo.
"%PYTHON%" -c "import sys; sys.path.insert(0, r'%~dp0..'); print('Executable:', sys.executable); import requests; print('requests: OK'); import gmssl; print('gmssl: OK'); import av; print('av: OK'); import comfyui_douyin_downloader as p; print('NODE_CLASS_MAPPINGS:', p.NODE_CLASS_MAPPINGS); print('NODE CHECK: OK')"
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo NODE CHECK: FAILED - copy the full error above.
if "%EXIT_CODE%"=="0" echo NODE CHECK: PASSED - restart ComfyUI and reload the workflow.
pause
exit /b %EXIT_CODE%

