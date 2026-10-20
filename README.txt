INCANDESCENT AI
===============
A personal AI workspace powered by Photon 1.

GET STARTED
-----------
1. Extract the complete ZIP into a folder.
2. Double-click START-INCANDESCENT.bat.
3. Use the Incandescent application window that opens; the service window is minimized.
4. Leave the service running while using the app. Do not open index.html directly.

CREATE YOUR OWN AI
------------------
1. Select + Create your AI in the sidebar.
2. Give it a name and describe what it should help with. The other fields define its audience, tone, response style, background knowledge, and additional instructions.
3. Select Save AI to keep it in your workspace, or Save & test to open a new conversation and run an introduction test.
4. Select a saved AI under Your AIs to start another separate conversation with its profile. Use the edit button to update it or the delete button to remove it.

Custom AIs are saved in this browser's local storage (IndexedDB with a localStorage fallback). They are behavioral profiles used as context for Photon 1; they do not create separate model weights. Profiles do not sync across browsers or computers in this release. API key generation and hosted API access are not included yet.

WHAT YOU CAN DO
---------------
- Ask questions and get streaming replies.
- Build websites, scripts, APIs, and multi-file project deliverables.
- Upload source files or a supported project ZIP for analysis.
- Copy code from chat, preview files, and download individual artifacts or a ZIP.
- Save conversations and personalize how Incandescent responds.
- Use speech-to-text in browsers that support it.

TIPS FOR STRONGER RESULTS
-------------------------
- For a large project, ask for a complete first milestone, then iterate in follow-ups.
- Upload project source and manifests, not dependency folders or build output.
- Review generated code before using it in production. Static checks do not prove
  runtime correctness, and generated code is not automatically executed.
- Image understanding depends on the selected model configuration. If image
  analysis is unavailable, text and source-code attachments still work.

TROUBLESHOOTING
---------------
- If Incandescent says the assistant is unavailable, close the application and
  relaunch START-INCANDESCENT.bat. Check the setup if the message persists.
- If the application cannot connect, check the minimized service window and
  relaunch the app. The launcher prefers a standalone app window when a supported
  browser is installed.
- If a project ZIP imports no source files, exclude dependencies, build folders,
  binary blobs, and secrets. Import is limited to 12 MB compressed and up to 80
  supported source files / 12 MB of unpacked text.
- Generated artifacts are temporary session outputs. Download important files
  before closing or restarting the application.
- If the default application port is occupied, close the previous Incandescent
  instance or set INCANDESCENT_PORT=8766 in Command Prompt before restarting.

RESPONSIVENESS
---------------
While a request is being processed, the Windows supervisor temporarily yields
CPU scheduling priority for the model runtime so foreground apps can remain
responsive. It restores the previous priorities after the request. This does not
change model weights or answer-quality settings; token generation can still be
slow on older CPUs.

MODEL AND TRAINING
------------------
Photon 1 is the coding model used by Incandescent, based on the configured
Qwen3.5 2B model in this release. This release does not include new model-weight
training. Advanced training and evaluation utilities require a suitable training
environment and a reviewed, legally usable dataset.
