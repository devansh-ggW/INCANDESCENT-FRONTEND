INCANDESCENT
============

A chat-first local AI desktop app for thoughtful answers, code, custom assistant profiles, and image analysis.

WINDOWS INSTALLER
-----------------
1. Run INCANDESCENT-Setup.exe.
2. Install and start Ollama separately. INCANDESCENT does not install or replace Ollama.
3. The setup window checks whether qwen3.5:2b is installed. If it is missing and Ollama is running, the download starts automatically with visible progress.
4. The model download is approximately 2.7–3.1 GB and requires an internet connection. Ollama stores it in its configured model directory.
5. If you skip model setup, open Prepare INCANDESCENT Model from the Start Menu later.
6. The first Windows release targets 64-bit Windows 10 and later. Older Windows builds may run the app if an existing Ollama responds, but current Ollama documentation lists Windows 10 22H2 or newer as its supported baseline. Windows ARM64 initially runs the x64 app via emulation. 32-bit Windows and Windows 7/8/8.1 are not supported by this installer.

START THE APP MANUALLY
----------------------
For developers running from source:
1. Extract the complete application folder.
2. Double-click START-INCANDESCENT.bat.
3. Keep the service window open while using the browser interface.
4. Do not open index.html directly; the app window connects to the local service.

CREATE A PERSONAL ASSISTANT
---------------------------
1. Select Create your AI in the sidebar.
2. Give the assistant a name and describe its purpose, audience, style, background, and business details.
3. Save the profile or select Save & test to begin a conversation with it.
4. Select a saved profile to start a separate conversation. You can edit or delete saved profiles.

Profiles are stored in local browser storage. They do not sync across devices, and creating a profile does not train new model weights.

FEATURES
--------
- Streamed local-model responses.
- Code and text output directly in chat.
- Attach supported source text and code for analysis.
- PNG, JPEG, and WebP image analysis using the original image plus edge and simplified-color views.
- Local chat history, saved assistant profiles, and personalization.
- Speech-to-text in supported browser environments.

DATA AND UNINSTALL
------------------
Chat/profile data is stored under %LOCALAPPDATA%\INCANDESCENT and remains after uninstall. Uninstalling INCANDESCENT does not remove Ollama or its model downloads.

TROUBLESHOOTING
---------------
- The desktop app tries to start an existing local Ollama service if it is not listening. If connection still fails, open Ollama and check %LOCALAPPDATA%\INCANDESCENT\desktop.log.
- The Start Menu's Prepare INCANDESCENT Model shortcut can install or verify qwen3.5:2b again.
- If the app cannot start, check %LOCALAPPDATA%\INCANDESCENT\desktop.log.
- If image analysis is unavailable, select an installed vision-capable model in Settings.

LIMITATIONS
-----------
This Windows installer does not bundle Ollama or model weights. The model is downloaded through the user's own Ollama installation. This build is not code-signed. Model quality and speed depend on the installed model and computer hardware. Real-device testing is required before claiming support for any Windows release/architecture.


LATEST WINDOWS INSTALLER (v1.1.1)
Download the real installer from GitHub Releases:
https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/download/v1.1.1/INCANDESCENT-Setup.exe

Standalone app:
https://github.com/devansh-ggW/INCANDESCENT-FRONTEND/releases/download/v1.1.1/INCANDESCENT.exe

After saving a custom AI, add it to Ollama under a name derived from the AI's name, or export an editable ZIP with the Modelfile, profile metadata and instructions. The ZIP does not include the multi-gigabyte model weights. Another computer needs Ollama and qwen3.5:2b.
