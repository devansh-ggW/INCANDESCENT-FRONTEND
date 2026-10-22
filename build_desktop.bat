@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  INCANDESCENT Desktop Build
echo  Bundled renderer - no WebView2 install
echo ============================================
echo.
py -3.11 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 x64 was not found.
  echo Install Python 3.11 x64 to build the EXE.
  echo Users who receive the final EXE do not need Python.
  pause
  exit /b 1
)

py -3.11 -m pip install --upgrade pip
if errorlevel 1 goto failed
py -3.11 -m pip install -r requirements-desktop.txt
if errorlevel 1 goto failed

py -3.11 -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name INCANDESCENT ^
  --icon incandescent.ico ^
  --add-data "index.html;." ^
  --add-data "incandescent.ico;." ^
  --hidden-import server ^
  --hidden-import run_incandescent ^
  --collect-all PyQt5 ^
  --collect-all PyQt5.QtWebEngineWidgets ^
  desktop_app.py
if errorlevel 1 goto failed

echo.
echo Build complete: dist\INCANDESCENT.exe
echo This EXE bundles its own Qt WebEngine renderer.
echo.
pause
exit /b 0

:failed
echo.
echo Build failed. Read the error above before trying again.
pause
exit /b 1
