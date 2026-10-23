"""Portable startup tests for local Ollama connection recovery."""
from __future__ import annotations

import urllib.error
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import desktop_app


class OllamaStartupTests(unittest.TestCase):
    class LocalBackend:
        OLLAMA_BASE = "http://127.0.0.1:11434"

    def test_already_running_ollama_is_not_spawned_again(self):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with patch("desktop_app.urllib.request.urlopen", return_value=response), \
             patch("desktop_app.subprocess.Popen") as popen:
            self.assertTrue(desktop_app.ensure_ollama_running(self.LocalBackend))
        popen.assert_not_called()

    def test_missing_local_service_starts_existing_binary_and_waits_for_ready(self):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        previous_child = desktop_app._OLLAMA_CHILD
        try:
            with patch("desktop_app.urllib.request.urlopen",
                       side_effect=[urllib.error.URLError("connection refused"), response]), \
                 patch("desktop_app.find_ollama_executable", return_value=Path("ollama.exe")), \
                 patch("desktop_app.subprocess.Popen") as popen:
                self.assertTrue(desktop_app.ensure_ollama_running(self.LocalBackend, timeout_seconds=1))
                popen.assert_called_once()
                self.assertEqual(popen.call_args.args[0], ["ollama.exe", "serve"])
        finally:
            desktop_app._OLLAMA_CHILD = previous_child

    def test_remote_ollama_host_is_never_started_locally(self):
        class RemoteBackend:
            OLLAMA_BASE = "http://192.0.2.10:11434"
        with patch("desktop_app.urllib.request.urlopen") as urlopen, \
             patch("desktop_app.subprocess.Popen") as popen:
            self.assertFalse(desktop_app.ensure_ollama_running(RemoteBackend))
        urlopen.assert_not_called()
        popen.assert_not_called()

    def test_native_download_handler_is_connected_and_accepts_files(self):
        source = Path(__file__).with_name("desktop_app.py").read_text(encoding="utf-8")
        self.assertIn("profile.downloadRequested.connect(handle_download_requested)", source)
        self.assertIn("QFileDialog.getSaveFileName(", source)
        self.assertIn("download.setPath(str(destination))", source)
        self.assertIn("download.accept()", source)


if __name__ == "__main__":
    unittest.main()
