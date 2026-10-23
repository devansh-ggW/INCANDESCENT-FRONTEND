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
