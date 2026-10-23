import os
import unittest
from unittest.mock import patch

import model_setup


class ModelSetupHelpersTest(unittest.TestCase):
    def test_default_ollama_host(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(model_setup.ollama_base_url(), "http://127.0.0.1:11434")

    def test_host_without_scheme(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "localhost:11434"}, clear=True):
            self.assertEqual(model_setup.ollama_base_url(), "http://localhost:11434")

    def test_unspecified_bind_host_routes_to_loopback(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "0.0.0.0:11434"}, clear=True):
            self.assertEqual(model_setup.ollama_base_url(), "http://127.0.0.1:11434")

    def test_invalid_ollama_host_is_rejected(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "ftp://not-valid"}, clear=True):
            with self.assertRaises(ValueError):
                model_setup.ollama_base_url()

    def test_default_model_is_qwen_35_two_billion(self):
        self.assertEqual(model_setup.MODEL_NAME, "qwen3.5:2b")

    def test_model_detects_exact_installed_tag(self):
        self.assertTrue(model_setup.model_is_installed(["qwen3.5:2b"]))

    def test_model_missing_is_false(self):
        self.assertFalse(model_setup.model_is_installed(["llama3.2:latest"]))

    def test_missing_model_transitions_same_worker_into_pull(self):
        from pathlib import Path
        source = Path(model_setup.__file__).read_text(encoding="utf-8")
        self.assertIn("__AUTO_PULL__:", source)
        callback = source.split("def result_ready(code: str, message: str)", 1)[1].split(
            "def start_worker(do_pull: bool = False)", 1
        )[0]
        self.assertNotIn('start_worker(True)', callback)

    def test_windows_note_is_safe_on_non_windows(self):
        if os.name != "nt":
            self.assertEqual(model_setup.windows_compatibility_note(), "This setup wizard is intended for Windows.")


if __name__ == "__main__":
    unittest.main()
