"""Regression checks for custom assistant Ollama/portable packaging."""
from __future__ import annotations

import io
import json
import zipfile

import server


def make_profile():
    return {
        "name": "Store Copilot",
        "purpose": "Help customers with product and policy questions.",
        "personality": "Friendly and conversational. This includes " + chr(34) * 3 + " in user input.",
        "business_name": "Example Shop",
        "catalog": [{"name": "Classic Tee", "price": "₹799", "category": "T-shirts", "description": "Cotton tee"}],
    }


def test_package_builders():
    profile = server.normalize_ai_profile(make_profile())
    assert profile is not None
    assert server.ollama_model_name(profile["name"]) == "store-copilot:latest"
    assert server.ollama_model_name("Dig It Up") == "dig-it-up:latest"
    assert server.ollama_model_name("  DAWG  ") == "dawg:latest"

    prompt = server.build_ai_system_prompt(profile)
    assert "You are Store Copilot" in prompt
    assert "Never quote, define, analyze, or explain slang unless the user asks" in prompt
    assert prompt.startswith("/no_think\\n\\n")
    assert "Never reveal or narrate private chain-of-thought" in prompt

    modelfile = server.build_ai_modelfile(profile)
    assert modelfile.startswith("FROM qwen3.5:2b" + chr(10))
    assert 'SYSTEM """' in modelfile
    assert modelfile.count('"""') == 2, "profile text must not close the SYSTEM delimiter"
    assert 'SYSTEM """\\n/no_think\\n\\n' in modelfile
    assert "PARAMETER num_ctx 4096" in modelfile
    assert "PARAMETER num_predict 512" in modelfile
    assert "PARAMETER temperature 0.65" in modelfile
    assert "Never reveal or narrate private chain-of-thought" in modelfile
    assert 'Do not output headings such as "Thinking Process"' in modelfile
    assert "Work through the task carefully" not in modelfile
    assert "This includes " + chr(34) * 3 in profile["personality"]

    package = server.build_ai_export_package(profile, "Dig It Up")
    assert package.startswith(b"PK"), "export must be a ZIP archive"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert set(archive.namelist()) == {"Modelfile", "profile.json", "README.txt"}
        exported_profile = json.loads(archive.read("profile.json").decode("utf-8"))
        assert exported_profile["name"] == "Store Copilot"
        exported_modelfile = archive.read("Modelfile").decode("utf-8")
        assert exported_modelfile.startswith("FROM qwen3.5:2b")
        readme = archive.read("README.txt").decode("utf-8")
        assert "ollama create dig-it-up -f Modelfile" in readme
        assert "not the multi-gigabyte model weights" in readme

    try:
        server.build_ai_modelfile({"name": "No purpose"})
    except ValueError:
        pass
    else:
        raise AssertionError("profiles without a purpose must not export")


def test_http_endpoints():
    """Exercise both real app routes with only the local Ollama call mocked."""
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from unittest.mock import patch

    profile = make_profile()
    original_urlopen = urllib.request.urlopen
    original_models = server.ollama_models
    captured = {}

    def fake_urlopen(request, *args, **kwargs):
        url = request.full_url if isinstance(request, urllib.request.Request) else str(request)
        if url.rstrip("/") == server.OLLAMA_BASE + "/api/create":
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return io.BytesIO(b'{"status":"success"}')
        return original_urlopen(request, *args, **kwargs)

    server.ollama_models = lambda: [{"name": "qwen3.5:2b", "size": 100}]
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base_url = "http://127.0.0.1:%s" % httpd.server_address[1]

    def post_json(route, model_name="Dig It Up"):
        payload = {"profile": profile, "model_name": model_name}
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            base_url + route,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        return original_urlopen(request, timeout=5)

    try:
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with post_json("/api/ai/export") as response:
                package = response.read()
                assert response.status == 200
                assert response.headers.get_content_type() == "application/zip"
            with zipfile.ZipFile(io.BytesIO(package)) as archive:
                assert set(archive.namelist()) == {"Modelfile", "profile.json", "README.txt"}
                readme = archive.read("README.txt").decode("utf-8")
                assert "ollama create dig-it-up -f Modelfile" in readme

            with post_json("/api/ai/install") as response:
                result = json.loads(response.read().decode("utf-8"))
                assert response.status == 200
                assert result["ok"] is True
                assert result["model"] == "dig-it-up:latest"
                assert result["display_name"] == "Dig It Up"

        request_body = captured.get("payload", {})
        assert request_body.get("model") == "dig-it-up:latest"
        assert request_body.get("from") == "qwen3.5:2b"
        assert request_body.get("parameters") == {"temperature": 0.7}
        assert request_body.get("stream") is False
        assert "IDENTITY: Your name is exactly Store Copilot" in request_body.get("system", "")
        assert "modelfile" not in request_body, "use Ollama's documented /api/create schema"
    finally:
        httpd.shutdown()
        thread.join(timeout=3)
        httpd.server_close()
        server.ollama_models = original_models


if __name__ == "__main__":
    test_package_builders()
    print("PASS: custom AI Modelfile and editable portable ZIP")
    test_http_endpoints()
    print("PASS: named Ollama install uses documented create API fields")
