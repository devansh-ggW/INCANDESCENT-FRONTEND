# INCANDESCENT desktop app

The Windows desktop build wraps the existing index.html unchanged in a native application window. It does not redesign or duplicate the current interface.

## Desktop renderer

The app bundles Qt 5 WebEngine (Chromium-based) inside its EXE. It does not require Microsoft Edge WebView2 to be installed separately. The trade-off is that this uses an older embedded Chromium base for compatibility with older Windows systems; do not use this embedded window as a general-purpose browser or to open arbitrary internet sites. The app only loads its own loopback interface.

## Build

1. Install 64-bit Python 3.11 on the developer/build machine.
2. Keep desktop_app.py, server.py, run_incandescent.py, index.html, and incandescent.ico in the project folder.
3. Run build_desktop.bat.
4. The standalone executable is dist\INCANDESCENT.exe.

The EXE includes Python and the renderer runtime. End users do not need Python or WebView2 installed separately.

## GitHub Actions build

The Build INCANDESCENT desktop app workflow builds a Windows executable and publishes INCANDESCENT-desktop-windows as an artifact. Run it from the repository Actions tab, then download the artifact ZIP.

## Requirements on the user's PC

- Windows x64. Older Windows compatibility is the goal, but an actual smoke test on Windows 10 build 16299 is still needed before guaranteeing that exact build.
- Ollama installed and running separately by the user.
- The selected model installed in Ollama. The desktop defaults to qwen3.5:2b; Settings supports other installed models.

The wrapper does not install Ollama or download model weights. Startup diagnostics are written to %LOCALAPPDATA%\INCANDESCENT\desktop.log.

## Data and local service

- Chat/profile browser storage persists in %LOCALAPPDATA%\INCANDESCENT\WebEngine.
- The app's internal service binds only to 127.0.0.1 and does not listen on the LAN.
- Port 8765 is preferred. If busy, the app tries the next 19 ports.
- The service and optional resource-priority supervisor are stopped when the window closes.
- Closing INCANDESCENT does not stop Ollama or delete model weights.

## Scope

This is a desktop executable build, not the customer installer. Ollama and model weights are not bundled. The EXE is not code-signed. CI packaging success does not replace a real startup test on the target Windows machine.
