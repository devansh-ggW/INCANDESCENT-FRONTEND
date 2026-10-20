# Incandescent release notes

Build date: 2026-10-20

## Product identity
- Application: Incandescent.
- Coding model: Photon 1, built from the configured Qwen3.5 2B base profile.
- Custom AI profiles configure behavior through context; they do not make new model weights.

## New in this build: Create your AI
- Added **+ Create your AI** in the sidebar.
- Builder fields cover a name, purpose, audience, response style, personality/tone, background knowledge, and extra custom instructions.
- Added required-field validation, field-length limits, clear save/edit/delete behavior, and a 50-profile limit.
- Saved profiles persist in IndexedDB, with localStorage fallback.
- Saved AIs are listed in the sidebar and can be edited, deleted, or used to start a separate conversation.
- **Save & test** saves the profile, starts a separate conversation, and sends an introduction request.
- Each conversation stores its selected profile ID; normal messages and queued follow-ups pass the matching profile to the backend. Switching chats does not transfer another chat's custom instructions.
- Backend profile normalization bounds text fields, applies selected response-style guidance, and treats user fields as preferences that cannot override correctness or safety requirements.
- Updated the interface to a warm milk / toasted-cookie / cinnamon palette for the AI builder and related workspace surfaces.

## Professional-software checklist
### Implemented now
- App/model names remain distinct.
- Custom AI creation, editing, deletion, persistence, profile-specific chats, and an explicit test flow.
- Bounded model-context injection and HTML-safe profile rendering.
- Local persistence fallback and existing chat history remain intact.
- API key controls intentionally remain absent in this phase.

### Still required before public multi-user launch
1. User accounts and server-side ownership for each AI profile.
2. API key creation, secure hashing, revocation, scopes, request quotas, rate limits, and usage accounting.
3. HTTPS deployment and a threat-model review for the public API.
4. Automated browser end-to-end testing across desktop and mobile browsers.
5. Measured model-quality and image-analysis evaluations against held-out tasks.
6. User-consented voice output, interruption, and speech playback controls.
7. Data export/import, retention controls, and clear privacy disclosures.
8. Dependency/security review, migration tests, structured crash handling, and a reproducible release build.
9. Concurrency, cancellation, memory, and recovery tests on the target Windows hardware.
10. Multi-device sync and profile access controls if account sync is added.

## Verification
- `python -m py_compile server.py incandescent_engine.py run_incandescent.py training/prepare_dataset.py training/train_lora.py training/check_hardware.py test_features.py` — passed.
- `python test_engine.py` — passed.
- `python test_features.py` — passed, including custom-AI prompt injection, response-style application, profile UI markers, existing attachment/model tests, and real favicon response.
- `python test_training_pipeline.py` — 8 tests passed.
- Node.js parse check of the inline frontend JavaScript — passed.
- CSS brace structure and required builder/request wiring checks — passed.

## Limitations
- Profiles persist in the current browser installation and do not sync to accounts or devices.
- API keys and a hosted multi-user API are not implemented yet.
- No model weight training occurs when users create a profile.
- A headless interactive browser run could not be completed in this environment; model-generation latency was not benchmarked because a live model endpoint was unavailable.
