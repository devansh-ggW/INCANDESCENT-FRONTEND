@echo off
setlocal
set "INCANDESCENT_PORT=%~1"
if not defined INCANDESCENT_PORT set "INCANDESCENT_PORT=8765"
set "INCANDESCENT_URL=http://127.0.0.1:%INCANDESCENT_PORT%"

rem Give the service a moment to start before opening the product window.
timeout /t 2 /nobreak >nul

rem Prefer a standalone browser app window so users do not see the address bar.
where msedge >nul 2>nul
if not errorlevel 1 (
  start "INCANDESCENT" msedge --app="%INCANDESCENT_URL%"
  exit /b 0
)
where chrome >nul 2>nul
if not errorlevel 1 (
  start "INCANDESCENT" chrome --app="%INCANDESCENT_URL%"
  exit /b 0
)

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
  start "INCANDESCENT" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
  start "INCANDESCENT" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%LocalAppData%\Microsoft\Edge\Application\msedge.exe" (
  start "INCANDESCENT" "%LocalAppData%\Microsoft\Edge\Application\msedge.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  start "INCANDESCENT" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
  start "INCANDESCENT" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
  start "INCANDESCENT" "%LocalAppData%\Google\Chrome\Application\chrome.exe" --app="%INCANDESCENT_URL%"
  exit /b 0
)

rem Last-resort fallback uses the user's default browser.
start "" "%INCANDESCENT_URL%"
endlocal
