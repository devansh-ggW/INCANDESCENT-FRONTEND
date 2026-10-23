# Incandescent release notes

## Current working branch: text-first chat and image analysis

### Interface
- Reduced the Create AI button and simplified the sidebar controls.
- Removed the duplicate New Chat control from the top bar.
- Added complete sidebar collapse/reopen behavior.
- Added a distinct stop-response button; the send arrow remains unchanged while the model works.
- Added one-click response copying alongside code-block copying.

### Image analysis
- Image attachments keep their original pixels and gain a Sobel edge view plus a simplified color-region view.
- The original and derived images are sent together to an installed vision-capable model.
- Edge and color views provide additional signals, not standalone semantic recognition.

### Response and backend scope
- The assistant now replies with text in chat; code is displayed inline for copying.
- Disabled model tool calls for writing or modifying generated files.
- Removed the API-key UI and storage, external chat-completions route, file download/preview endpoints, project ZIP import, and artifact-writing helpers.
- Updated regression tests to cover the current chat-only contract.

### Verification status
Automated verification and real-model/manual Windows testing must pass before calling this release production-ready. Do not infer runtime model quality from static checks alone.

### Not included
Installer packaging, user accounts, multi-device sync, hosted API access, voice output, and model fine-tuning.
