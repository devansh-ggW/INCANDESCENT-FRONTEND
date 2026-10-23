"""Offline regression tests for INCANDESCENT chat and image analysis."""
from __future__ import annotations

import base64
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("incandescent_test_server", ROOT / "server.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def valid_png() -> bytes:
    # Attachment handling validates the PNG signature; model output itself is mocked.
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 24


def main() -> None:
    # Local endpoint normalization should be deterministic on old Windows resolver stacks.
    check(mod.normalize_ollama_base("localhost:11434") == "http://127.0.0.1:11434",
          "localhost resolves to explicit IPv4")
    check(mod.normalize_ollama_base("0.0.0.0:11434") == "http://127.0.0.1:11434",
          "unspecified bind address routes to loopback")

    # Verify that a failed Ollama connection reports the endpoint and OS reason.
    old_urlopen = mod.urllib.request.urlopen
    def refuse_connection(*args, **kwargs):
        raise urllib.error.URLError("Connection refused")
    mod.urllib.request.urlopen = refuse_connection
    try:
        try:
            mod.ollama_request([{"role": "user", "content": "Hi"}], use_tools=False)
        except RuntimeError as exc:
            check("http://127.0.0.1:11434" in str(exc) and "Connection refused" in str(exc),
                  "connection error includes endpoint and network details")
        else:
            raise AssertionError("unreachable Ollama endpoint should fail")
    finally:
        mod.urllib.request.urlopen = old_urlopen

    # Safe attachment filenames and bounded prior history.
    check(mod.safe_filename("screen.png") == "screen.png", "ordinary image filename is accepted")
    check(mod.safe_filename("src/app.py") == "src/app.py", "relative source paths remain readable")
    for unsafe in ("../secret.txt", "/etc/passwd", "C:\\secret.txt", ""):
        try:
            mod.safe_filename(unsafe)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe attachment name accepted: " + repr(unsafe))

    history = mod.normalize_history([
        {"role": "system", "content": "not allowed"},
        {"role": "user", "content": "  question  "},
        {"role": "assistant", "content": "answer"},
        {"role": "tool", "content": "not allowed"},
    ])
    check(history == [{"role": "user", "content": "question"}, {"role": "assistant", "content": "answer"}],
          "history only keeps clean user and assistant messages")

    png64 = base64.b64encode(valid_png()).decode("ascii")
    image_attachments = [
        {"filename": "screen.png", "kind": "image", "mime_type": "image/png", "data_base64": png64},
        {"filename": "screen-edges.png", "kind": "image", "mime_type": "image/png", "data_base64": png64},
        {"filename": "screen-colors.png", "kind": "image", "mime_type": "image/png", "data_base64": png64},
    ]
    text_context, images, metadata = mod.normalize_attachments([
        {"filename": "snippet.py", "kind": "text", "mime_type": "text/plain", "content": "print('hello')"}
    ], "test-source")
    check("print('hello')" in text_context and not images, "source text is included directly in model context")
    check(metadata[0]["filename"] == "snippet.py" and "artifact_id" not in metadata[0],
          "source attachment context does not create an artifact")

    try:
        mod.normalize_attachments([
            {"filename": "bad.png", "kind": "image", "mime_type": "image/png",
             "data_base64": base64.b64encode(b"not a png").decode("ascii")}
        ], "test-invalid-image")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid image signature was accepted")

    # All model calls are mocked: tests do not download or launch a model.
    old_request, old_models, old_model = mod.ollama_request, mod.ollama_models, mod.MODEL
    captured = {}

    def fake_request(messages, use_tools=True, stream_callback=None, event=None, model_override=None):
        captured["messages"] = messages
        captured["use_tools"] = use_tools
        captured["model_override"] = model_override
        if stream_callback:
            stream_callback("delta", "Image and text ")
            stream_callback("delta", "analysis works.")
        return {"role": "assistant", "content": "Image and text analysis works."}

    try:
        mod.ollama_request = fake_request
        mod.MODEL = "photon1"
        mod.ollama_models = lambda: [{"name": "qwen3.5:2b", "size": 100}]
        check(mod.model_supports_vision("qwen3.5:2b"), "Qwen 3.5 is recognized as vision-capable")
        check(mod.vision_model_for_request("photon1") == "qwen3.5:2b",
              "image requests find an installed vision-capable fallback")

        result = mod.process_chat(
            {"message": "What is shown?", "attachments": image_attachments},
            "test-image-chat", threading.Event()
        )
        check(result["ok"] and result["message"] == "Image and text analysis works.",
              "image request produces a normal text answer")
        check("files" not in result, "assistant response has no generated-file field")
        check(captured["use_tools"] is False, "model tool calls are disabled")
        check(captured["model_override"] == "qwen3.5:2b", "vision model is selected for image analysis")
        user_turn = captured["messages"][-1]
        check(user_turn.get("images") == [item["data_base64"] for item in image_attachments],
              "original, edge and color images all reach the vision model")
        check("edges map" in user_turn["content"] and "color-region map" in user_turn["content"],
              "model prompt explains how derived image views should be interpreted")
        check("screen-edges.png" in user_turn["content"] and "screen-colors.png" in user_turn["content"],
              "layer filenames are available to model context")

        text_result = mod.process_chat(
            {"message": "Give me a Python example in chat.", "history": []},
            "test-text-chat", threading.Event()
        )
        check(text_result["ok"] and "files" not in text_result,
              "ordinary chat stays text-only and has no file-output field")
        check(captured["use_tools"] is False, "text response does not enable tools")

        cancelled = threading.Event()
        cancelled.set()
        cancelled_result = mod.process_chat({"message": "cancel this"}, "test-cancel", cancelled)
        check(cancelled_result.get("cancelled") is True, "cancelled requests do not call the model")

    finally:
        mod.ollama_request, mod.ollama_models, mod.MODEL = old_request, old_models, old_model

    # Exercise real HTTP routing with mocked model calls only.
    old_request, old_models, old_model = mod.ollama_request, mod.ollama_models, mod.MODEL
    streamed = {}

    def http_fake_request(messages, use_tools=True, stream_callback=None, event=None, model_override=None):
        streamed["tools"] = use_tools
        if stream_callback:
            stream_callback("delta", "Hello ")
            stream_callback("delta", "from Incandescent.")
        return {"role": "assistant", "content": "Hello from Incandescent."}

    mod.ollama_request = http_fake_request
    mod.ollama_models = lambda: [{"name": "photon1:latest", "size": 100}]
    mod.MODEL = "photon1"
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%s" % httpd.server_address[1]
    try:
        with urllib.request.urlopen(base + "/", timeout=5) as response:
            page = response.read().decode("utf-8")
            check(response.status == 200 and "INCANDESCENT" in page, "homepage responds with the shipped app")
            check('id="stopButton"' in page and 'data-copy-message=' in page, "current chat controls are served")
        with urllib.request.urlopen(base + "/api/status", timeout=5) as response:
            status = json.loads(response.read().decode("utf-8"))
            check(status["ok"] and status["ollama_connected"], "neutral availability status endpoint works")

        body = json.dumps({"conversation_id": "test-stream", "message": "say hello", "history": []}).encode("utf-8")
        request = urllib.request.Request(
            base + "/api/chat/stream", data=body,
            headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            frames = response.read().decode("utf-8")
        events = [json.loads(line) for line in frames.splitlines() if line.strip()]
        deltas = "".join(item.get("content", "") for item in events if item.get("type") == "delta")
        final = [item["data"] for item in events if item.get("type") == "final"][-1]
        check(deltas == "Hello from Incandescent.", "stream includes incremental response text")
        check(final["ok"] and final["message"] == deltas, "stream final matches emitted text")
        check("files" not in final and streamed["tools"] is False, "streaming remains text-only")

        for route in ("/api/keys", "/api/files/unknown", "/api/upload"):
            try:
                urllib.request.urlopen(base + route, timeout=5)
            except urllib.error.HTTPError as exc:
                check(exc.code == 404, "removed file/API route returns 404: " + route)
            else:
                raise AssertionError("removed route unexpectedly exists: " + route)

        unknown_body = json.dumps({"messages": [{"role": "user", "content": "Hi"}]}).encode("utf-8")
        old_api_req = urllib.request.Request(
            base + "/v1/chat/completions", data=unknown_body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            urllib.request.urlopen(old_api_req, timeout=5)
        except urllib.error.HTTPError as exc:
            check(exc.code == 404, "OpenAI-compatible API route is removed")
        else:
            raise AssertionError("removed OpenAI-compatible API route unexpectedly exists")

    finally:
        httpd.shutdown()
        thread.join(timeout=3)
        httpd.server_close()
        mod.ollama_request, mod.ollama_models, mod.MODEL = old_request, old_models, old_model

    check(not Path(mod.INFERENCE_MARKER_PATH).exists(), "inference marker is cleaned up")
    print("PASS: safe attachment validation and bounded chat history")
    print("PASS: image original, edge layer and color layer reach the vision model")
    print("PASS: text-only generation with disabled model tools and no file outputs")
    print("PASS: streaming HTTP chat, status endpoint, and removed API/file routes")


if __name__ == "__main__":
    main()
