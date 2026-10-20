# Incandescent — Professional software checklist

## Implemented in this build
- Product identity: Incandescent is the app; Photon 1 is the coding model.
- Create/edit/delete custom AI profiles with purpose, audience, style, personality, background, and custom instructions.
- Persist profiles in IndexedDB with localStorage fallback.
- Start a separate conversation bound to a selected profile; save the profile reference with conversation history.
- Send the selected profile to the backend on normal and queued turns, where it is converted to bounded system context.
- Warm milk / toasted-cookie / cinnamon visual surfaces for the builder and sidebar.
- Validation and length caps on custom instructions; API keys are intentionally not exposed or generated yet.

## Professional hardening still required before public launch
1. Add a real authenticated backend, user accounts, and server-side profile ownership. Browser storage alone is per-browser and is not a cloud sync system.
2. Implement API key creation, hashing at rest, revocation, scope/usage limits, rate limiting, and audit logs before exposing an API.
3. Add automated end-to-end browser tests on supported desktop/mobile browsers.
4. Add model quality evaluation against held-out realistic tasks and verify image analysis with a compatible vision model.
5. Add voice output and optional streaming speech playback with explicit user controls.
6. Add data export/import and retention controls; document storage and privacy behavior.
7. Run a dependency/security review and validate every release on a clean Windows install.
8. Benchmark concurrency, cancellation, memory usage, request timeouts, and model failure recovery on target hardware.
9. Add account-bound profile permissions, secure secret handling, and deployment-specific HTTPS configuration before multi-user hosting.
10. Establish release versioning, migration tests, crash reporting that avoids collecting private prompts, and a reproducible build checklist.

## Not included by design in this build
- No API keys or public hosted API yet.
- Creating a custom AI stores configuration and injects its behavior into model context; it does not change model weights or constitute fine-tuning.
- Profiles are stored on the current browser installation; cross-device sharing requires a user/account backend.
