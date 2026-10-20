@echo off
setlocal
set "INCANDESCENT_PORT=%~1"
if not defined INCANDESCENT_PORT set "INCANDESCENT_PORT=8765"
set "INCANDESCENT_URL=http://127.0.0.1:%INCANDESCENT_PORT%"

rem Open a normal browser window with tabs and address bar enabled.
timeout /t 2 /nobreak >nul
where chrome >nul 2>nul
if not errorlevel 1 (
  start "" chrome "%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
  start "" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" "%INCANDESCENT_URL%"
  exit /b 0
)
if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" (
  start "" "%LocalAppData%\Google\Chrome\Application\chrome.exe" "%INCANDESCENT_URL%"
  exit /b 0
)
start "" "%INCANDESCENT_URL%"
endlocal
