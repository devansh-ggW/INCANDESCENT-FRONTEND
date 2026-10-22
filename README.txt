INCANDESCENT
============
A chat-first AI workspace for thoughtful answers, code, custom assistant profiles, and image analysis.

START THE APP
-------------
1. Extract the complete application folder.
2. Double-click START-INCANDESCENT.bat.
3. Use the Incandescent window that opens. Keep the service window open while using it.
4. Do not open index.html directly; the app window connects to the running service.

CREATE A PERSONAL ASSISTANT
---------------------------
1. Select Create your AI in the sidebar.
2. Give the assistant a name and describe its purpose, audience, style, background, and business details.
3. Save the profile or select Save & test to begin a conversation with it.
4. Select a saved profile to start a separate conversation. You can edit or delete saved profiles.

Profiles are stored in the current browser's IndexedDB, with a localStorage fallback. They do not sync across browsers or devices, and creating a profile does not train new model weights.

WHAT YOU CAN DO
---------------
- Ask questions and receive streamed text responses.
- Get code directly in chat, with one-click copying for code blocks and full responses.
- Attach supported source text or code for analysis.
- Drop a PNG, JPEG, or WebP image for visual analysis. The app sends the original image with edge and simplified-color analysis views to a vision-capable model.
- Save chat history and personalize responses.
- Use speech-to-text in browsers that support it.

TEXT-ONLY OUTPUT
----------------
Generated code and explanations stay in the conversation. This build does not create downloadable output files, import project ZIPs, expose API keys, or provide a hosted API. Copy the exact code or response from the chat when needed.

TROUBLESHOOTING
---------------
- If a reply cannot start, close the application and relaunch START-INCANDESCENT.bat.
- If no model choices appear in Settings, check the configured model service and reopen Settings.
- If image analysis is unavailable, select an installed vision-capable model.
- If the application port is already in use, close the previous Incandescent service before relaunching.

QUALITY AND LIMITATIONS
-----------------------
The quality of responses depends on the selected model and its available context. Edge and color views are supporting visual signals; object and text interpretation is performed by the selected vision model and can be uncertain. Static tests do not replace real-model testing on the target Windows computer.

No installer, user accounts, cloud profile sync, hosted API, or model fine-tuning is included in this build.
