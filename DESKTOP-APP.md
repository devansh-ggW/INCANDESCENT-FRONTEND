# INCANDESCENT desktop app and Windows installer

The Windows desktop build wraps the existing index.html unchanged in a native application window. It does not redesign or duplicate the current interface.

## Windows installer

The installer is a per-user Windows setup EXE. It installs the desktop app, creates Start Menu shortcuts and an optional desktop shortcut, then launches a small model-setup window. The model setup checks Ollama and, if needed, downloads qwen3.5:2b through the local Ollama API with visible progress. It never installs or replaces Ollama. If Ollama is missing or offline, it offers the official Windows download page and allows the user to retry or skip; a Start Menu shortcut lets them return to model setup later.

The model is downloaded into Ollama's configured model directory, not into the INCANDESCENT install folder. Allow around 3 GB or more of disk space and a working internet connection.

The first Windows release targets 64-bit Windows 10 and later. Windows ARM64 is initially supported through the x64 app under Windows emulation where the OS permits it; native ARM64 is a later target. A full 32-bit Windows release is not offered. The user's Windows 10 build 16299 has been tested with the desktop app, but current Ollama documentation lists Windows 10 22H2 (build 19045) or later as its supported Windows baseline. The first-run model wizard warns on older builds and proceeds only if Ollama actually responds. Windows 7/8/8.1 are not included in this release.

## Desktop renderer

The app bundles Qt WebEngine (Chromium-based) inside its EXE. It does not require Microsoft Edge WebView2 installed separately. The renderer is intended only for the local INCANDESCENT UI; HTTP(S) links clicked in the app are sent to the normal system browser instead of navigating the embedded engine.

The Qt 5 WebEngine package uses an older Chromium baseline. The host restricts navigation to its loopback app, but this should not be used as a general-purpose browser or to open untrusted web pages.

## Build on Windows

1. Install 64-bit Python 3.11 on the build machine.
2. Install Inno Setup 6.3 or later.
3. Keep desktop_app.py, model_setup.py, server.py, run_incandescent.py, index.html, incandescent.ico, and installer/INCANDESCENT.iss in the project folder.
4. Run build_desktop.bat.
5. The desktop executable is dist\INCANDESCENT.exe and the installer is dist\installer\INCANDESCENT-Setup.exe.

End users do not need Python or WebView2 installed separately. Ollama and model weights are not bundled; the model is downloaded through the user's own Ollama installation.

## Data and uninstall

- Chat/profile browser storage persists in %LOCALAPPDATA%\INCANDESCENT\WebEngine.
- The app's internal service binds only to 127.0.0.1 and does not listen on the LAN.
- Uninstall removes INCANDESCENT application files and shortcuts, not Ollama or the model store.
- Chat/profile data in %LOCALAPPDATA%\INCANDESCENT is preserved when the application is uninstalled.

## Scope and validation

This is the first Windows installer target, not a macOS/Linux installer. It is not code-signed. Packaging success is not proof of launch compatibility on every Windows revision; a real install, model-pull, restart, and uninstall test is required on each claimed OS/architecture.

Before a commercial release, review the licenses of bundled PyQt5 and Qt WebEngine components and the installer compiler's licensing terms.


## Custom assistant deployment

Saved custom assistants work as profiles inside INCANDESCENT. After saving, users can add an assistant to their local Ollama model list or download an editable ZIP containing a `Modelfile`, `profile.json`, and setup instructions.

The named Ollama model is created from `qwen3.5:2b`; that base model must be installed first. The exported ZIP contains assistant configuration, not the several-gigabyte Qwen weights. A recipient installs Ollama, pulls the same base model, then runs the `ollama create` command documented in the ZIP's `README.txt`.

The Windows installer automatically starts downloading `qwen3.5:2b` through the existing Ollama service once Ollama is responding and the model is missing. INCANDESCENT does not install Ollama itself.


## Windows v1.1.1 compatibility and connection recovery

The bundled Qt WebEngine can be older than the Chromium engine in a regular browser. The shipped UI therefore uses a child-removal fallback rather than `Element.replaceChildren()`, which is not present in some older embedded builds. Before showing the workspace, the Windows host probes the existing local Ollama API and attempts to start `ollama.exe serve` if Ollama is installed but not listening. It never installs Ollama and leaves custom remote `OLLAMA_HOST` endpoints alone. Connection errors include the configured endpoint and underlying network reason for diagnosis.
