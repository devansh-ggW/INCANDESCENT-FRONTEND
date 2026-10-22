# INCANDESCENT desktop app

The desktop edition opens the existing index.html unchanged in a normal Windows application window. It does not redesign or duplicate the UI. The local Python HTTP service runs invisibly inside the same process, so users no longer need to launch or keep a server console open.

## Build

For a local Windows build:

1. Install 64-bit Python 3.11.
2. Keep desktop_app.py, server.py, run_incandescent.py, index.html, and incandescent.ico in the same project folder.
3. Run build_desktop.bat.
4. The standalone executable is created at dist\INCANDESCENT.exe.

The one-file build includes its Python runtime and UI assets; the target PC does not need Python installed.

## GitHub Actions build

The Build INCANDESCENT desktop app workflow builds the Windows executable on a Windows runner and publishes it as a workflow artifact. Run it manually from the repository's Actions tab or use a push/PR that touches desktop-build files. Download the INCANDESCENT-desktop-windows artifact and extract the ZIP to get INCANDESCENT.exe.

## Requirements on the user's PC

- Windows x64, with Microsoft Edge WebView2 Runtime available.
- Ollama installed and running separately by the user.
- The desired model installed in Ollama. The desktop app defaults to qwen3.5:2b; Settings still allows choosing another installed model.

The wrapper does not install Ollama or download model weights. If WebView2 is missing or fails to initialize, the app shows a startup error and writes diagnostics to %LOCALAPPDATA%\INCANDESCENT\desktop.log.

## Data and local service

- Browser chat/profile storage persists in %LOCALAPPDATA%\INCANDESCENT\WebViewData.
- The service binds only to 127.0.0.1. It is used internally by the desktop window and does not listen on the LAN.
- Port 8765 is preferred to preserve the existing browser origin. If busy, the app tries the next 19 ports.
- The service and resource-priority supervisor are stopped when the window closes.
- Closing INCANDESCENT does not stop Ollama or delete model weights.

## Scope and testing

This step creates the desktop wrapper and automated Windows build, not the later customer installer. It does not bundle Ollama or a language model and is not a code-signed public release. The final executable still needs a real launch test on the target Windows computer; successful packaging alone does not prove WebView2 support on every Windows version.
