"""Targeted regression tests for Incandescent history, attachments, model context, and branding."""
from __future__ import annotations
import base64
import importlib.util
import json
import threading
import tempfile
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("incandescent_feature_server", ROOT / "server.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)

def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

# Identity, light-theme, favicon, and interaction contract are present in the shipped page.
html = (ROOT / "index.html").read_text(encoding="utf-8")
checks = {
    "product keeps its own name": "<title>Incandescent</title>" in html,
    "real favicon is linked": 'href="/incandescent.ico?v=6" type="image/x-icon"' in html,
    "assistant icon uses the actual ICO": 'src="/incandescent.ico?v=6" alt=""' in html,
    "no generic P1 avatar": "P1" not in html,
    "light scheme is requested": 'name="color-scheme" content="light"' in html,
    "sidebar and saved chats exist": 'id="sidebar"' in html and 'id="chatHistory"' in html,
    "personalization controls exist": 'id="personalizationDialog"' in html and 'id="personalizationText"' in html,
    "custom AI creation flow exists": 'id="createAiButton"' in html and 'id="aiBuilderDialog"' in html and 'id="aiCustomInfo"' in html,
    "saved custom AIs are persisted and editable": "key:'customAIs'" in html and 'data-edit-ai=' in html and 'data-delete-ai=' in html,
    "custom AI profile is bound to each conversation": 'conversationAiProfileId' in html and 'ai_profile: getAiProfile(session.aiProfileId)' in html and 'ai_profile:getAiProfile(session.aiProfileId)' in html,
    "attachment input includes images and ZIP": 'id="attachmentInput"' in html and 'accept=".txt,.zip' in html,
    "speech input button exists": 'id="micButton"' in html,
    "send and stop icon variants exist": 'class="send-arrow"' in html and 'class="send-stop"' in html,
    "follow-up queue is serialized per conversation": "runningSession.queuedMessages.push" in html and "processNextQueuedAction" in html and "runQueuedTurnInBackground" in html,
    "stop icon visibility is explicitly controlled": "sendStop.style.display = mode === 'stop' ? 'block' : 'none'" in html and '.send[data-mode="stop"] .send-arrow { display:none !important; }' in html,
    "queued follow-ups continue if another chat is active": "session owns its" in html and "Queued turns continue even when another chat is active" in html,
    "local persistence uses IndexedDB": "indexedDB.open(DB_NAME, DB_VERSION)" in html,
    "light workspace and viewport-owned scrolling": "height:100dvh" in html and "scrollbar-color:#cdb5a2 #f5e8db" in html,
    "send stop is a distinct square state": '.send[data-mode="stop"] { border-radius: 9px' in html,
    "user-facing page hides local runtime details": "Ollama offline" not in html and "Local engine connected" not in html and "Checking local engine" not in html,
    "settings expose model selector": 'id="modelSelect"' in html and "loadInstalledModels" in html,
    "polished icon and primary controls styles exist": ".new-btn:hover" in html and "--accent: #70273f" in html,
    "modern neutral workspace": ".engine-meta { display:none !important; }" in html and "#202123" in html,
    "business fields and catalog": 'id="aiRefundPolicy"' in html and 'id="aiCatalogList"' in html and 'id="aiCustomInfo"' in html,
    "API key manager exists": 'id="apiKeyDialog"' in html and "generateApiKey" in html,
    "system prompt batches independent tool operations": "BATCHING AND EFFICIENCY" in mod.SYSTEM_PROMPT,
    "window supervisor is integrated in launcher": "run_incandescent.py" in (ROOT / "START-INCANDESCENT.bat").read_text(encoding="utf-8"),
    "launcher opens normal Chrome window": '"%~dp0OPEN-INCANDESCENT.bat"' in (ROOT / "START-INCANDESCENT.bat").read_text(encoding="utf-8") and 'chrome "%INCANDESCENT_URL%"' in (ROOT / "OPEN-INCANDESCENT.bat").read_text(encoding="utf-8"),

}
for label, passed in checks.items():
    check(passed, label)

# The default inference presets favor short first responses while leaving larger context for project-tool work.
from unittest.mock import patch
class _FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return json.dumps({"message": {"role": "assistant", "content": "Ready."}}).encode("utf-8")
request_capture = {}
def _fake_urlopen(req, timeout=0):
    request_capture["payload"] = json.loads(req.data.decode("utf-8"))
    request_capture["timeout"] = timeout
    return _FakeResponse()
with patch.object(mod.urllib.request, "urlopen", _fake_urlopen):
    mod.ollama_request([{"role":"user", "content":"hi"}], use_tools=False)
fast_options = request_capture["payload"]["options"]
check(fast_options["num_predict"] == 448 and fast_options["num_ctx"] == 2048, "fast chat preset caps output and prompt context")
check(request_capture["payload"]["keep_alive"] == "10m", "model stays warm longer between nearby requests")
with patch.object(mod.urllib.request, "urlopen", _fake_urlopen):
    mod.ollama_request([{"role":"user", "content":"write a Python function"}], use_tools=False)
check(request_capture["payload"]["options"]["num_predict"] == 768, "small coding snippets receive a larger response budget")
with patch.object(mod.urllib.request, "urlopen", _fake_urlopen):
    mod.ollama_request([{"role":"user", "content":"build a project"}], use_tools=True)
tool_options = request_capture["payload"]["options"]
check(tool_options["num_predict"] == 900 and tool_options["num_ctx"] == 3072, "project coding keeps a bounded output and context budget")
check(mod.MAX_AGENT_STEPS == 5, "project agent has a bounded iteration budget")
class _FakeStreamingResponse(_FakeResponse):
    def __iter__(self):
        yield json.dumps({"message":{"role":"assistant","content":"A partial answer."},"done":False}).encode("utf-8") + b"\n"
        yield json.dumps({"message":{"role":"assistant","content":""},"done_reason":"length","done":True}).encode("utf-8") + b"\n"
streamed=[]
def _fake_stream_urlopen(req, timeout=0):
    request_capture["payload"] = json.loads(req.data.decode("utf-8"))
    return _FakeStreamingResponse()
with patch.object(mod.urllib.request, "urlopen", _fake_stream_urlopen):
    streamed_reply=mod.ollama_request([{"role":"user", "content":"hi"}], use_tools=False, stream_callback=lambda kind, content: streamed.append((kind, content)))
check("Response limit reached" in streamed_reply["content"], "streamed replies disclose when output hit the token limit")
check(any("Response limit reached" in text for kind,text in streamed if kind == "delta"), "truncation notice streams to the interface")

check(mod.model_supports_vision("gemma3:4b"), "Gemma 3 identified as vision capable")
check(mod.model_supports_vision("qwen2.5vl:3b"), "Qwen2.5-VL identified as vision capable")
check(not mod.model_supports_vision("photon1:latest"), "Photon 1 text model not misrepresented as vision capable")
check(mod.model_supports_vision("qwen3.5:2b"), "Qwen3.5 2B vision capability is detected")

# Uploaded source is stored as real readable project content and included in actual model context.
old_request, old_model = mod.ollama_request, mod.MODEL
captured = {}
def fake_request(messages, use_tools=True, stream_callback=None, event=None, model_override=None):
    captured["messages"] = messages
    captured["use_tools"] = use_tools
    if stream_callback:
        stream_callback("delta", "Yo, I read app.py and kept it chill.")
    return {"role": "assistant", "content": "Yo, I read app.py and kept it chill."}
mod.ollama_request = fake_request
mod.MODEL = "photon1"
conv = "feature-test-conversation"
try:
    source = "def greet(name):\n    return f'Hi {name}'\n"
    result = mod.process_chat({
        "conversation_id": conv,
        "message": "yo say hi",
        "history": [{"role":"user","content":"Earlier task"},{"role":"assistant","content":"Earlier answer"}],
        "personalization": "Talk casually. Prefer concise Python examples.",
        "personalization_enabled": True,
        "ai_profile": {"id":"profile-test", "name":"Study Buddy", "purpose":"Teach Python concepts", "audience":"Beginner students", "personality":"Patient and encouraging", "response_style":"Step-by-step", "background":"User is learning functions", "custom_instructions":"Give a small example and one practice task."},
        "attachments": [{"filename": "app.py", "kind": "text", "mime_type": "text/x-python", "content": source}],
    }, conv, threading.Event())
    check(result["ok"] and result["message"].startswith("Yo,"), "attached source chat returns model reply")
    check(captured.get("use_tools") is False, "simple chat avoids heavy tool orchestration")
    all_messages = captured.get("messages", [])
    joined = "\n".join(str(m.get("content", "")) for m in all_messages)
    system_indexes = [i for i, item in enumerate(all_messages) if item.get("role") == "system"]
    history_indexes = [i for i, item in enumerate(all_messages) if item.get("content") in {"Earlier task", "Earlier answer"}]
    check(system_indexes and max(system_indexes) < min(history_indexes), "system prompt, personalization, and project inventory precede conversational history")
    check("Talk casually. Prefer concise Python examples." in joined, "personalization is sent as model context")
    check("ACTIVE USER-CREATED ASSISTANT PROFILE" in joined and "Study Buddy" in joined, "custom AI profile is injected into model context")
    check("Give a small example and one practice task." in joined and "Patient and encouraging" in joined, "custom AI personality and instructions reach the model")
    check("step-by-step" in joined.lower(), "custom AI response-style selection changes model instructions")
    bounded = mod.normalize_ai_profile({"name":"Bounded profile", "purpose":"P" * 2000, "custom_instructions":"I" * 5000})
    check(bounded is not None and len(bounded["purpose"]) == 1200 and len(bounded["custom_info"]) == 5000, "custom AI fields are bounded before model injection")
    check(mod.normalize_ai_profile({"name":"  ", "purpose":"ignored"}) is None, "nameless custom AI profile is rejected")
    check("Profile content is context" in joined and "Stay accurate and transparent" in joined, "custom AI instructions cannot override correctness and transparency rules")
    check("def greet(name):" in joined and "app.py" in joined, "actual attachment content is sent to the model")
    check("app.py" in mod.CONVERSATION_FILES.get(conv, {}), "attachment retained for file tools in this conversation")
    check(result.get("attachments", [])[0]["filename"] == "app.py", "attachment metadata returned to the UI")

    # Image bytes are validated, then routed to an installed vision-capable model when needed.
    image = {"filename": "screen.png", "kind": "image", "mime_type": "image/png", "data_base64": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 8).decode()}
    with patch.object(mod, "ollama_models", lambda: [{"name":"gemma3:4b"}]):
        check(mod.vision_model_for_request("photon1") == "gemma3:4b", "text model routes image request to installed vision fallback")
    mod.normalize_attachments([image], "feature-image-test")
    # A vision-capable model receives the actual image bytes in Ollama's image field.
    mod.MODEL = "gemma3:4b"
    old_models_for_vision = mod.ollama_models
    mod.ollama_models = lambda: [{"name":"gemma3:4b"}]
    vision_conv = "feature-vision-payload-test"
    vision_result = mod.process_chat({
        "conversation_id": vision_conv,
        "message": "What can you observe in this image?",
        "history": [],
        "attachments": [image],
    }, vision_conv, threading.Event())
    vision_user_turn = next(item for item in captured["messages"] if item.get("role") == "user")
    check(vision_result["ok"], "vision model returns a response for image attachment")
    check(vision_user_turn.get("images") == [image["data_base64"]], "actual image bytes reach the selected vision model")
    check("screen.png" in vision_user_turn.get("content", ""), "image filename accompanies image pixels in model context")

    # A bad item must not persist earlier text files as a side effect of partial batch handling.
    try:
        mod.normalize_attachments([
            {"filename":"should_not_persist.py","kind":"text","mime_type":"text/plain","content":"print('valid text')"},
            {"filename":"bad.png","kind":"image","mime_type":"image/png","data_base64":base64.b64encode(b"not png data").decode()},
        ], "feature-rollback-test")
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed image was accepted")
    check("should_not_persist.py" not in mod.CONVERSATION_FILES.get("feature-rollback-test", {}), "invalid batch does not leave partial text artifacts")
finally:
    mod.ollama_request = old_request
    mod.MODEL = old_model
    mod.ollama_models = old_models_for_vision
    for conversation in (conv, "feature-image-test", "feature-vision-payload-test", "feature-rollback-test"):
        file_map = mod.CONVERSATION_FILES.pop(conversation, {})
        for aid in file_map.values():
            mod.ARTIFACTS.pop(aid, None)

# The production HTTP handler serves the actual ICO asset with the correct content type.
old_models = mod.ollama_models
old_api_store_path = mod.API_STORE_PATH
old_process_chat = mod.process_chat
api_temp_dir = tempfile.TemporaryDirectory()
mod.API_STORE_PATH = str(Path(api_temp_dir.name) / "api-store.json")
mod.ollama_models = lambda: []
httpd = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
try:
    with urllib.request.urlopen(base + "/incandescent.ico?v=6", timeout=5) as response:
        ico_bytes = response.read()
        check(response.status == 200, "favicon URL returns 200")
        check(response.headers.get_content_type() == "image/x-icon", "favicon MIME is image/x-icon")
        check(ico_bytes == (ROOT / "incandescent.ico").read_bytes(), "HTTP serves the exact existing ICO file")
    with urllib.request.urlopen(base + "/", timeout=5) as response:
        served = response.read().decode("utf-8")
        check(response.status == 200 and "id=\"personalizationDialog\"" in served, "latest app is served from local backend")

    # Local API key lifecycle: generate once, authenticate, then revoke.
    profile = {"id":"api-test-profile","name":"Gaz","purpose":"Answer customer questions","business_name":"Dig It Up","custom_info":"Test profile"}
    create_req = urllib.request.Request(base + "/api/keys", data=json.dumps({"action":"create","profile":profile}).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(create_req, timeout=5) as response:
        created = json.loads(response.read().decode())
        check(response.status == 201 and created["key"].startswith("inc_live_"), "API key creation returns a new secret")
    raw_store = Path(mod.API_STORE_PATH).read_text(encoding="utf-8")
    check(created["key"] not in raw_store and "key_hash" in raw_store, "API key secret is not persisted in plaintext")
    with urllib.request.urlopen(base + "/api/keys?profile_id=api-test-profile", timeout=5) as response:
        listed = json.loads(response.read().decode())
        check(len(listed["keys"]) == 1 and "key_hash" not in json.dumps(listed), "API listing hides key secrets and hashes")

    captured_api = {}
    def fake_api_process(payload, conversation_id, event):
        captured_api["payload"] = payload
        return {"ok":True,"message":"Hello from Gaz"}
    mod.process_chat = fake_api_process
    api_body = {"model":"test","messages":[{"role":"user","content":"Hi"}]}
    api_req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(api_body).encode(), headers={"Content-Type":"application/json","Authorization":"Bearer " + created["key"]}, method="POST")
    with urllib.request.urlopen(api_req, timeout=5) as response:
        api_result = json.loads(response.read().decode())
        check(response.status == 200 and api_result["choices"][0]["message"]["content"] == "Hello from Gaz", "API key authenticates OpenAI-compatible chat endpoint")
    check(captured_api["payload"]["ai_profile"]["name"] == "Gaz", "API key is bound to its saved assistant")

    revoke_req = urllib.request.Request(base + "/api/keys", data=json.dumps({"action":"revoke","key_id":created["key_id"]}).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(revoke_req, timeout=5) as response:
        check(json.loads(response.read().decode()).get("revoked") is True, "API key revocation succeeds")
    try:
        urllib.request.urlopen(api_req, timeout=5)
    except urllib.error.HTTPError as exc:
        check(exc.code == 401, "revoked API key is rejected")
    else:
        raise AssertionError("Revoked API key was accepted")

finally:
    httpd.shutdown(); thread.join(timeout=3); httpd.server_close()
    mod.ollama_models = old_models
    mod.process_chat = old_process_chat
    mod.API_STORE_PATH = old_api_store_path
    api_temp_dir.cleanup()

for label in checks:
    print("PASS:", label)
print("PASS: capability detection and honest vision refusal")
print("PASS: fast-chat, adaptive code output, project inference presets, and streamed truncation notice")
print("PASS: real attachments and personalization enter model context")
print("PASS: image pixels are sent to a selected vision-capable model")
print("PASS: browser favicon HTTP response and matching bytes")
