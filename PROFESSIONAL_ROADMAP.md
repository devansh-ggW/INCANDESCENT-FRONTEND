# INCANDESCENT — Quality and release roadmap

## Implemented in the current working branch
- Reduced Create your AI to a compact rounded rectangle.
- Removed the duplicate top-right New Chat control; the sidebar keeps one New Chat button under Create AI.
- Made the hamburger control fully hide and reopen the desktop sidebar.
- Kept the send arrow stable and added a separate stop-response button.
- Added one-click copying for complete assistant responses and code blocks.
- Added browser-side image preprocessing: original image, Sobel edge map, and simplified color-region view.
- Routed image requests to an installed vision-capable model and explained the supporting layers in the model context.
- Changed generation to text-only responses in the chat.
- Removed API-key creation, API-key storage, external chat-completions routes, generated-file downloads, ZIP import, and the old artifact writer.
- Replaced regression tests that depended on file creation and API keys with tests for chat, image analysis, and the current UI.

## Validation required before release
1. Run the GitHub Actions regression workflow and fix every failure before merging.
2. Run py_compile and the same regression suite on the target Windows version.
3. Test actual inference with the configured text model, including long code answers, errors, empty answers, and output limits.
4. Test image analysis on real images with the intended vision model. Compare original-image interpretation against the edge and color views; do not treat those views as independent object recognition.
5. Manually test the sidebar at desktop and mobile widths, including keyboard access and reopening after collapse.
6. Test stop-response during generation, while queued follow-ups exist, and while switching chats.
7. Test clipboard fallback in browsers where Clipboard API access is unavailable, including copying fenced code and a full answer.
8. Check attachment-size limits, unsupported file types, corrupt images, repeated attachments, and large images on the target hardware.
9. Review keyboard focus, accessible labels, dialog behavior, reduced-motion settings, contrast, and narrow-screen layout.
10. Measure memory use and response latency on the target PC; fix visible freezes and long unresponsive periods.
11. Complete a security/privacy review of browser storage, attachment processing, host checks, and error messages.
12. Update the release notes only with checks that have actually passed.

## Deferred for later
- Installer and distribution packaging.
- Accounts, multi-device profile sync, and cloud storage.
- Public or third-party API access.
- Model training or fine-tuning.
- Voice output.

## Release rule
Do not label the project production-ready until automated checks, real-model image and text tests, and a manual Windows UI pass have all been completed. The current changes make progress toward that bar; they do not prove every possible bug has been eliminated.
