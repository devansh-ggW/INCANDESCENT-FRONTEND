"""Regression checks for custom assistant Ollama/portable packaging."""
from __future__ import annotations

import io
import json
import zipfile

import server


def main():
    raw_profile = {
        "name": "Store Copilot",
        "purpose": "Help customers with product and policy questions.",
        "personality": "Friendly and conversational. This includes " + chr(34) * 3 + " in user input.",
        "business_name": "Example Shop",
        "catalog": [{"name": "Classic Tee", "price": "₹799", "category": "T-shirts", "description": "Cotton tee"}],
    }
    profile = server.normalize_ai_profile(raw_profile)
    assert profile is not None
    assert server.ollama_model_name(profile["name"]) == "store-copilot:latest"
    assert server.ollama_model_name("Dawg") == "dawg:latest"
    assert server.ollama_model_name("Dig It Up!") == "dig-it-up:latest"
    try:
        server.ollama_model_name(" !! ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty normalized model names must be rejected")

    named_package = server.build_ai_export_package(profile, "Dawg")
    with zipfile.ZipFile(io.BytesIO(named_package)) as named_archive:
        named_readme = named_archive.read("README.txt").decode("utf-8")
        assert "ollama create dawg -f Modelfile" in named_readme

    modelfile = server.build_ai_modelfile(profile)
    assert modelfile.startswith("FROM qwen3.5:2b" + chr(10))
    assert 'SYSTEM """' in modelfile
    assert modelfile.count('"""') == 2, "profile text must not close the SYSTEM delimiter"
    assert "This includes " + chr(34) * 3 in profile["personality"]
    assert "Never quote, define, analyze, or explain slang unless the user asks" in modelfile

    package = server.build_ai_export_package(profile)
    assert package.startswith(b"PK"), "export must be a ZIP archive"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert set(archive.namelist()) == {"Modelfile", "profile.json", "README.txt"}
        exported_profile = json.loads(archive.read("profile.json").decode("utf-8"))
        assert exported_profile["name"] == "Store Copilot"
        exported_modelfile = archive.read("Modelfile").decode("utf-8")
        assert exported_modelfile.startswith("FROM qwen3.5:2b")
        readme = archive.read("README.txt").decode("utf-8")
        assert "ollama create store-copilot -f Modelfile" in readme
        assert "not the multi-gigabyte model weights" in readme

    try:
        server.build_ai_modelfile({"name": "No purpose"})
    except ValueError:
        pass
    else:
        raise AssertionError("profiles without a purpose must not export")


if __name__ == "__main__":
    main()
    print("PASS: custom AI Ollama Modelfile and editable ZIP export")


def test_http_endpoints(profile):
    """Exercise both real app routes with only the local Ollama call mocked."""
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from unittest.mock import patch

    base_url = None
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

    def post_json(route):
        body = json.dumps({"profile": profile, "model_name": "Dawg"}).encode("utf-8")
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

            with post_json("/api/ai/install") as response:
                result = json.loads(response.read().decode("utf-8"))
                assert response.status == 200
                assert result["ok"] is True
                assert result["model"] == "dawg:latest"

        request_body = captured.get("payload", {})
        assert request_body.get("model") == "dawg:latest"
        assert request_body.get("name") == "dawg:latest"
        assert request_body.get("stream") is False
        assert request_body.get("modelfile", "").startswith("FROM qwen3.5:2b")
    finally:
        httpd.shutdown()
        thread.join(timeout=3)
        httpd.server_close()
        server.ollama_models = original_models


# Run route tests after the pure packaging tests above.
if __name__ == "__main__":
    test_http_endpoints({
        "name": "Store Copilot",
        "purpose": "Help customers with product and policy questions.",
        "personality": "Friendly and conversational.",
    })
    print("PASS: custom AI HTTP install/export endpoints with mocked Ollama")
