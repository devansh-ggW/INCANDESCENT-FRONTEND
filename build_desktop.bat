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
  --hidden-import model_setup ^
  desktop_app.py
if errorlevel 1 goto failed

echo.
echo Build complete: dist\INCANDESCENT.exe
echo The EXE bundles Qt WebEngine and does not require WebView2.
echo.

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if defined ISCC (
  "%ISCC%" "installer\INCANDESCENT.iss"
  if errorlevel 1 goto failed
  echo Installer built: dist\installer\INCANDESCENT-Setup.exe
) else (
  echo Inno Setup was not found, so only the desktop EXE was built.
  echo Install Inno Setup 6.3+ and compile installer\INCANDESCENT.iss to build the installer.
)
echo.
pause
exit /b 0

:failed
echo.
echo Build failed. Read the error above before trying again.
pause
exit /b 1
