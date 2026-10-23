@echo off
setlocal
cd /d "%~dp0"
title INCANDESCENT

if not defined INCANDESCENT_PORT set "INCANDESCENT_PORT=8765"

if not exist "index.html" (
  echo ERROR: index.html was not found in this folder. Re-extract the complete INCANDESCENT AI ZIP.
  pause
  exit /b 1
)
if not exist "run_incandescent.py" (
  echo ERROR: The Incandescent launcher component is missing. Re-extract the complete ZIP.
  pause
  exit /b 1
)
if not exist "server.py" (
  echo ERROR: server.py was not found in this folder. Re-extract the complete INCANDESCENT AI ZIP.
  pause
  exit /b 1
)

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3 was not found. Install Python 3 and enable it in PATH, then retry.
    pause
    exit /b 1
  )
  set "PY=python"
)

call %PY% -c "import sys; assert sys.version_info >= (3,8), 'Python 3.8 or newer is required'" >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.8 or newer is required.
  pause
  exit /b 1
)

rem Avoid opening a stale/other site when the configured port is already occupied.
call %PY% -c "import socket,sys; s=socket.socket(); s.bind(('127.0.0.1',int(sys.argv[1]))); s.close()" %INCANDESCENT_PORT% >nul 2>nul
if errorlevel 1 (
  echo ERROR: Port %INCANDESCENT_PORT% is already in use.
  echo Close the previous INCANDESCENT server window first.
  echo To use another port, run in CMD:
  echo   set INCANDESCENT_PORT=8766
  echo Then launch this BAT from that same CMD window.
  pause
  exit /b 1
)

where ollama >nul 2>nul
if errorlevel 1 (
  echo The configured AI component is unavailable. Check the application setup and relaunch Incandescent.
  pause
  exit /b 1
)

call %PY% -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=1).read(1)" >nul 2>nul
if errorlevel 1 (
  echo Preparing the AI service...
  start "Incandescent AI Service" /min cmd /c "ollama serve >nul 2>&1"
  for /L %%I in (1,1,15) do (
    timeout /t 1 /nobreak >nul
    call %PY% -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=1).read(1)" >nul 2>nul
    if not errorlevel 1 goto RuntimeReady
  )
  echo The AI service is not responding yet. Incandescent will open and show a friendly status.
)

:RuntimeReady
set "INCANDESCENT_MODEL=photon1"
echo Initializing the assistant...
set "BUILD_PHOTON=0"
call ollama show photon1 >nul 2>nul
if errorlevel 1 set "BUILD_PHOTON=1"
if not "%BUILD_PHOTON%"=="1" (
  call ollama show --modelfile photon1 2>nul | findstr /i /c:"FROM qwen3:1.7b-q4_K_M" >nul
  if errorlevel 1 set "BUILD_PHOTON=1"
)
if "%BUILD_PHOTON%"=="1" (
  echo Preparing the configured model. This can take a little while...
  call ollama create photon1 -f "%~dp0Modelfile"
  if errorlevel 1 (
    echo WARNING: The configured model could not be prepared. Switching to a compatible model.
    set "INCANDESCENT_MODEL=qwen3:1.7b-q4_K_M"
  ) else (
    echo Assistant configuration verified.
  )
)
rem Keep the service console visible so startup errors and request logs can be inspected.
echo Starting Incandescent service. Keep the service console open while using the app.
start "Incandescent Service" cmd /k "%PY% run_incandescent.py"
set "INCANDESCENT_READY=0"
for /L %%I in (1,1,20) do (
  call %PY% -c "import sys,urllib.request; urllib.request.urlopen('http://127.0.0.1:%INCANDESCENT_PORT%/api/status', timeout=0.5).read(1)" >nul 2>nul
  if not errorlevel 1 (set "INCANDESCENT_READY=1" & goto ServiceReady)
  timeout /t 1 /nobreak >nul
)
:ServiceReady
if "%INCANDESCENT_READY%"=="1" (
  start "Incandescent Window Launcher" /min "%~dp0OPEN-INCANDESCENT.bat" %INCANDESCENT_PORT%
  endlocal
  exit /b 0
)
echo Incandescent could not start. Check the service window for details, then retry.
pause
endlocal
