"""Offline regression tests for INCANDESCENT AI / Photon 1. Never contacts Ollama."""
import io
import json
import threading
import shutil
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
import importlib.util

SERVER_FILE = Path(__file__).with_name("server.py")
spec = importlib.util.spec_from_file_location("incandescent_test_server", SERVER_FILE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def check(condition, message):
    if not condition:
        raise AssertionError(message)

# Relative project paths are preserved, while traversal and absolute paths fail.
check(mod.safe_filename("index.html") == "index.html", "basic filename")
check(mod.safe_filename("src/components/App.jsx") == "src/components/App.jsx", "nested path preserved")
for bad in ("../outside.py", "src/../../outside.py", "/absolute/path.py", "C:\\secret.txt", "src//empty.js"):
    try:
        mod.safe_filename(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe path accepted: " + bad)

# Distinguish chat snippets from true file/project work.
check(not mod.truthy_file_task("Show me a Python function in chat that reverses a string"), "short example should remain chat")
check(not mod.truthy_file_task("Explain what CSS specificity means"), "concept question should remain chat")
check(mod.truthy_file_task("Build a complete responsive website"), "website should create files")
check(mod.truthy_file_task("Create index.html and styles.css"), "explicit extensions should create files")
check(mod.truthy_file_task("Build a multi-file application"), "multi-file project should create files")
check(mod.truthy_file_task("Make me a VS Code extension"), "extension requests should create project files")
check(mod.truthy_file_task("Build an online store"), "online store requests should create project files")
check(mod.truthy_file_task("Build a calculator"), "common small projects should create runnable files")
app_validation = mod.validate_artifact("index.html", (SERVER_FILE.parent / "index.html").read_text(encoding="utf-8"))
check(app_validation["ok"], "Incandescent's own HTML passes its available static parser checks: " + repr(app_validation.get("issues")))
check(mod.truthy_file_task("Create a React dashboard"), "dashboard projects should create files")
check(not mod.truthy_file_task("Show me a JavaScript function in chat"), "explicit inline snippet stays in chat")
check("default to HTML + CSS + JavaScript" in mod.SYSTEM_PROMPT, "project agent infers sensible default website stack")

# The CPU supervisor watches a short-lived marker; it must always clear cleanly.
marker = Path(mod.INFERENCE_MARKER_PATH)
mod.set_inference_active(True)
check(marker.is_file(), "inference activity marker is created")
mod.set_inference_active(False)
check(not marker.exists(), "inference activity marker is removed")

# Static validation tests.
valid_html = '<!doctype html><html><head><title>Test</title></head><body><h1>Hello</h1></body></html>'
check(mod.validate_artifact("index.html", valid_html)["ok"], "valid HTML should pass structural checks")
check(not mod.validate_artifact("data.json", '{bad json}')["ok"], "bad JSON should fail")
check(not mod.validate_artifact("main.py", 'def x(:\n pass')["ok"], "bad Python should fail")
if shutil.which("node"):
    check(mod.validate_artifact("good.js", "const answer = 42;\n")["ok"], "valid JavaScript should pass Node syntax parsing")
    check(not mod.validate_artifact("bad.js", "const answer = ;\n")["ok"], "invalid JavaScript should fail Node syntax parsing")

# ZIP import preserves paths, imports text, and skips secrets/dependencies/traversal.
archive_buffer = io.BytesIO()
with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("demo/index.html", valid_html)
    archive.writestr("demo/src/app.js", "const answer = 42;\n")
    archive.writestr("demo/.env", "API_KEY=not-for-import\n")
    archive.writestr("demo/node_modules/x/index.js", "throw new Error('skip')")
    archive.writestr("../escape.py", "print('bad')")
conversation = "test-upload-conversation"
result = mod.ingest_project_zip(conversation, archive_buffer.getvalue())
check(result["ok"] is True and result["imported_count"] == 2, "ZIP imports supported project text files")
project_zip_id = mod.CONVERSATION_FILES[conversation].get("incandescent-project.zip")
check(project_zip_id in mod.ARTIFACTS, "multi-file projects receive a downloadable ZIP bundle")
with zipfile.ZipFile(io.BytesIO(mod.ARTIFACTS[project_zip_id]["bytes"])) as project_zip:
    check(set(project_zip.namelist()) == {"demo/index.html", "demo/src/app.js"}, "project ZIP preserves source paths and excludes skipped files")
check("demo/index.html" in mod.CONVERSATION_FILES[conversation], "HTML path imported")
check("demo/src/app.js" in mod.CONVERSATION_FILES[conversation], "nested source path imported")
check("demo/.env" not in mod.CONVERSATION_FILES[conversation], "secret filename skipped")
check("../escape.py" not in mod.CONVERSATION_FILES[conversation], "traversal filename skipped")
check("demo/node_modules/x/index.js" not in mod.CONVERSATION_FILES[conversation], "dependencies skipped")
search_result = mod.execute_tool("search_artifacts", {"query": "hello", "filename_filter": "index.html"}, conversation, threading.Event(), {"value": False}, {"value": False}, False)
check(search_result["ok"] and search_result["match_count"] == 1, "literal search finds source line")
check(search_result["matches"][0]["filename"] == "demo/index.html", "search returns relative path")

# Exercise HTTP status, model list failure shape, streaming general chat, and downloads.
old_request = mod.ollama_request
old_ollama_models = mod.ollama_models
old_model = mod.MODEL
captured = {}
def fake_request(messages, use_tools=True, stream_callback=None, event=None):
    captured["use_tools"] = use_tools
    if stream_callback:
        stream_callback("delta", "Yo bro, ")
        stream_callback("delta", "Photon is live.")
    return {"role": "assistant", "content": "Yo bro, Photon is live."}
mod.ollama_request = fake_request
httpd = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{httpd.server_address[1]}"
try:
    with urllib.request.urlopen(base + "/", timeout=5) as response:
        check(response.status == 200, "homepage responds")
        page = response.read().decode("utf-8")
        check("INCANDESCENT" in page and 'id="sidebar"' in page and "Copy code" in page and "modelSelect" in page and "apiKeyDialog" in page, "updated frontend serves workspace, model selector, and API key manager")
    payload = {"conversation_id": "test-stream-chat", "message": "yo bro what is 2+2", "history": []}
    request = urllib.request.Request(base + "/api/chat/stream", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"}, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        stream_body = response.read().decode("utf-8")
    events = [json.loads(line) for line in stream_body.splitlines() if line.strip()]
    deltas = "".join(item.get("content", "") for item in events if item.get("type") == "delta")
    final = [item["data"] for item in events if item.get("type") == "final"][-1]
    check(captured.get("use_tools") is False, "normal chat bypasses tool schemas")
    check(deltas == "Yo bro, Photon is live.", "stream events carry partial text")
    check(final["ok"] is True and final["message"] == deltas, "stream final agrees with emitted text")

    # Model selection resolves an untagged Photon alias and only allows installed models.
    mod.ollama_models = lambda: [{"name": "photon1:latest", "size": 100}, {"name": "qwen3.5:2b", "size": 200}]
    model_req = urllib.request.Request(base + "/api/model", data=json.dumps({"model": "photon1"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(model_req, timeout=5) as response:
        selected = json.loads(response.read().decode())
    check(selected["ok"] and selected["model"] == "photon1:latest" and selected["model_display"] == "Photon 1", "model selector resolves Photon alias")
    model_bad_req = urllib.request.Request(base + "/api/model", data=json.dumps({"model": "not-installed"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(model_bad_req, timeout=5)
    except urllib.error.HTTPError as exc:
        check(exc.code == 404, "uninstalled model is rejected")
    else:
        raise AssertionError("uninstalled model unexpectedly accepted")

    # Create a known artifact and verify real preview/download routes.
    aid = mod.execute_tool("create_artifact", {"filename": "src/app.js", "content": "const answer = 42;\n"}, "http-download-test", threading.Event(), {"value": False}, {"value": False}, True)["id"]
    with urllib.request.urlopen(base + "/api/files/" + aid + "/preview", timeout=5) as response:
        check(response.read().decode() == "const answer = 42;\n", "artifact preview endpoint")
    with urllib.request.urlopen(base + "/api/files/" + aid, timeout=5) as response:
        check(response.headers.get("Content-Disposition", "").startswith("attachment;"), "download disposition")
        check(response.read() == b"const answer = 42;\n", "artifact download bytes")

    # ZIP project upload route (raw body) returns imported source files.
    upload_zip = io.BytesIO()
    with zipfile.ZipFile(upload_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("site/index.html", valid_html)
    upload_req = urllib.request.Request(base + "/api/upload?conversation_id=http-upload-test", data=upload_zip.getvalue(), headers={"Content-Type": "application/zip"}, method="POST")
    with urllib.request.urlopen(upload_req, timeout=5) as response:
        upload_data = json.loads(response.read().decode())
    check(upload_data["ok"] and upload_data["imported_count"] == 1, "HTTP project ZIP import endpoint")
finally:
    httpd.shutdown()
    thread.join(timeout=3)
    httpd.server_close()
    mod.ollama_request = old_request
    mod.ollama_models = old_ollama_models
    mod.MODEL = old_model
    mod.CONVERSATION_FILES.pop(conversation, None)
    mod.CONVERSATION_FILES.pop("http-upload-test", None)
    mod.CONVERSATION_FILES.pop("http-download-test", None)
    for aid, artifact in list(mod.ARTIFACTS.items()):
        if artifact.get("conversation_id") in {conversation, "http-upload-test", "http-download-test"}:
            mod.ARTIFACTS.pop(aid, None)

print("PASS: relative-path security and traversal rejection")
print("PASS: chat-versus-file intent selection")
print("PASS: HTML, JSON, and Python static validation")
print("PASS: safe project ZIP import, filtering, and multi-file bundle export")
print("PASS: HTTP homepage and token-streaming chat")
print("PASS: artifact preview and download routes")
print("PASS: installed-model selection and Photon alias handling")
print("PASS: raw ZIP upload route")
