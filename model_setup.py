#!/usr/bin/env python3
"""First-run Ollama/model setup wizard used by the Windows installer."""
from __future__ import annotations

import ctypes
import json
import os
import platform
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

APP_TITLE = "INCANDESCENT"
MODEL_NAME = "qwen3.5:2b"
OLLAMA_DOWNLOAD_URL = "https://ollama.com/download/windows"
DEFAULT_OLLAMA_HOST = "127.0.0.1:11434"


def ollama_base_url() -> str:
    value = (os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST).strip().rstrip("/")
    if not value:
        value = DEFAULT_OLLAMA_HOST
    if "://" not in value:
        value = "http://" + value
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("OLLAMA_HOST must be a host and port, such as 127.0.0.1:11434.")
    if parsed.hostname in ("0.0.0.0", "::"):
        port = f":{parsed.port}" if parsed.port else ""
        parsed = parsed._replace(netloc="127.0.0.1" + port)
    return urllib.parse.urlunsplit(parsed).rstrip("/")


def platform_architecture() -> str:
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64", "x64"):
        return "x64"
    if machine in ("arm64", "aarch64"):
        return "ARM64"
    if machine in ("x86", "i386", "i686"):
        return "x86"
    return machine or "unknown"


def get_windows_native_architecture() -> str:
    """Detect native OS architecture, including ARM64 under x64 emulation."""
    if os.name != "nt":
        return platform_architecture()
    try:
        class ProcessorArch(ctypes.Structure):
            _fields_ = [("wProcessorArchitecture", ctypes.c_ushort), ("wReserved", ctypes.c_ushort)]
        class InfoUnion(ctypes.Union):
            _fields_ = [("dwOemId", ctypes.c_uint32), ("processor", ProcessorArch)]
        class SystemInfo(ctypes.Structure):
            _anonymous_ = ("u",)
            _fields_ = [
                ("u", InfoUnion), ("dwPageSize", ctypes.c_uint32),
                ("lpMinimumApplicationAddress", ctypes.c_void_p),
                ("lpMaximumApplicationAddress", ctypes.c_void_p),
                ("dwActiveProcessorMask", ctypes.c_size_t),
                ("dwNumberOfProcessors", ctypes.c_uint32),
                ("dwProcessorType", ctypes.c_uint32),
                ("dwAllocationGranularity", ctypes.c_uint32),
                ("wProcessorLevel", ctypes.c_ushort),
                ("wProcessorRevision", ctypes.c_ushort),
            ]
        info = SystemInfo()
        ctypes.windll.kernel32.GetNativeSystemInfo(ctypes.byref(info))
        code = int(info.processor.wProcessorArchitecture)
        return {0: "x86", 5: "ARM32", 9: "x64", 12: "ARM64"}.get(code, f"unknown ({code})")
    except Exception:
        return platform_architecture()


def windows_compatibility_note() -> str:
    if os.name != "nt":
        return "This setup wizard is intended for Windows."
    build = int(getattr(sys.getwindowsversion(), "build", 0))
    arch = get_windows_native_architecture()
    note = f"Detected system architecture: {arch}."
    if arch == "ARM64":
        note += " This release uses the x64 desktop app under Windows emulation."
    if build and build < 19045:
        return (
            f"Legacy Windows detected (build {build}). Current Ollama documentation lists "
            "Windows 10 22H2 (build 19045) or newer as its supported baseline. "
            "We'll check your existing Ollama connection; setup on this older build is best-effort. "
            + note
        )
    return "Windows version detected. " + note


def _request_json(url: str, payload: Optional[Dict[str, Any]] = None, timeout: float = 8.0):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data is not None else "GET"
    )
    return urllib.request.urlopen(request, timeout=timeout)


def installed_models(api_base: Optional[str] = None) -> List[str]:
    base = api_base or ollama_base_url()
    with _request_json(base + "/api/tags", timeout=4.0) as response:
        data = json.loads(response.read(1_000_000).decode("utf-8"))
    entries = data.get("models", []) if isinstance(data, dict) else []
    return sorted({
        str(item.get("name", "")).strip()
        for item in entries
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    })


def model_is_installed(model_names: List[str], model: str = MODEL_NAME) -> bool:
    return model in model_names or model + ":latest" in model_names or (
        model.endswith(":latest") and model[:-7] in model_names
    )


def run_model_setup(data_dir: Path) -> int:
    """Open a native dialog and download Qwen through Ollama with progress."""
    try:
        from PyQt5.QtCore import QThread, QUrl, pyqtSignal
        from PyQt5.QtGui import QDesktopServices, QFont, QIcon
        from PyQt5.QtWidgets import (
            QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox,
            QProgressBar, QPushButton, QVBoxLayout
        )
    except Exception as exc:
        # ctypes MessageBox works without requiring WebView2 or PowerShell.
        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                "The model setup window could not be loaded.\n\n"
                + str(exc) + "\n\nSee %LOCALAPPDATA%\\INCANDESCENT\\desktop.log.",
                APP_TITLE,
                0x10,
            )
        except Exception:
            pass
        return 1

    class PullWorker(QThread):
        progress_update = pyqtSignal(int, str)
        result_ready = pyqtSignal(str, str)

        def __init__(self, do_pull: bool = False):
            super().__init__()
            self.do_pull = do_pull

        def run(self):
            try:
                base = ollama_base_url()
                with _request_json(base + "/api/tags", timeout=5.0) as response:
                    data = json.loads(response.read(1_000_000).decode("utf-8"))
                entries = data.get("models", []) if isinstance(data, dict) else []
                names = sorted({
                    str(item.get("name", "")).strip()
                    for item in entries
                    if isinstance(item, dict) and str(item.get("name", "")).strip()
                })
            except Exception as exc:
                self.result_ready.emit(
                    "offline",
                    "Ollama is not responding. Open Ollama, wait until it is running, then retry. "
                    + str(exc),
                )
                return

            if model_is_installed(names):
                self.result_ready.emit("ready", MODEL_NAME + " is already installed and ready.")
                return
            if not self.do_pull:
                self.result_ready.emit(
                    "missing",
                    "Ollama is running, but " + MODEL_NAME + " is missing. "
                    "The model download is approximately 2.7–3.1 GB.",
                )
                return

            self.progress_update.emit(0, "Connecting to Ollama model registry…")
            try:
                body = json.dumps({"name": MODEL_NAME, "stream": True}).encode("utf-8")
                request = urllib.request.Request(
                    base + "/api/pull",
                    data=body,
                    headers={"Content-Type": "application/json", "Accept": "application/x-ndjson"},
                    method="POST",
                )
                saw_success = False
                with urllib.request.urlopen(request, timeout=900) as response:
                    for raw_line in response:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            item = json.loads(line.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        if not isinstance(item, dict):
                            continue
                        if item.get("error"):
                            raise RuntimeError(str(item["error"]))
                        status = str(item.get("status") or "Downloading model…")
                        total = int(item.get("total") or 0)
                        completed = int(item.get("completed") or 0)
                        percent = max(0, min(100, int(completed * 100 / total))) if total else 0
                        self.progress_update.emit(percent, f"{status} — {percent}%" if total else status)
                        if status.casefold() == "success":
                            saw_success = True
                            self.progress_update.emit(100, "Download complete. Verifying the model…")
                if not saw_success:
                    raise RuntimeError("Ollama ended the pull stream before reporting success.")
                with _request_json(base + "/api/tags", timeout=8.0) as response:
                    fresh = json.loads(response.read(1_000_000).decode("utf-8"))
                entries = fresh.get("models", []) if isinstance(fresh, dict) else []
                names = [str(item.get("name", "")).strip() for item in entries if isinstance(item, dict)]
                if not model_is_installed(names):
                    raise RuntimeError("Ollama completed the download, but the model isn't listed yet.")
                self.result_ready.emit("ready", MODEL_NAME + " was installed successfully.")
            except urllib.error.HTTPError as exc:
                try:
                    detail = exc.read(2000).decode("utf-8", "replace")
                except Exception:
                    detail = str(exc)
                self.result_ready.emit("failed", "Ollama could not download the model. " + detail)
            except Exception as exc:
                self.result_ready.emit("failed", "Model setup did not complete: " + str(exc))

    class SetupDialog(QDialog):
        pulling = False

        def closeEvent(self, event):
            if self.pulling:
                event.ignore()
                QMessageBox.information(
                    self, APP_TITLE,
                    "The model is still downloading. Let the download finish before closing this window."
                )
            else:
                event.accept()

    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_TITLE + " Model Setup")
    dialog = SetupDialog()
    dialog.setWindowTitle("Prepare INCANDESCENT")
    dialog.setMinimumSize(590, 370)
    dialog.resize(640, 405)
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        icon = Path(bundle) / "incandescent.ico"
        if icon.is_file():
            dialog.setWindowIcon(QIcon(str(icon)))

    dialog.setStyleSheet("""
        QDialog { background: #f7f8fa; color: #20242b; }
        QLabel { color: #20242b; }
        QPushButton { min-height: 34px; padding: 0 14px; border: 1px solid #c7cbd1; border-radius: 4px; background: #fff; color: #20242b; }
        QPushButton:hover { background: #edf0f4; }
        QPushButton:disabled { color: #858b95; background: #eceff3; }
        QPushButton#primary { background: #312e81; border-color: #312e81; color: #fff; font-weight: 600; }
        QPushButton#primary:hover { background: #252266; }
        QProgressBar { border: 1px solid #c7cbd1; border-radius: 3px; background: #fff; text-align: center; min-height: 20px; }
        QProgressBar::chunk { background: #5147c8; }
    """)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(28, 24, 28, 22)
    layout.setSpacing(12)
    heading = QLabel("Prepare your local AI")
    heading.setFont(QFont("Segoe UI", 19, QFont.DemiBold))
    layout.addWidget(heading)
    intro = QLabel(
        "INCANDESCENT prepares Qwen through your existing Ollama installation. "
        "This setup does not install or replace Ollama."
    )
    intro.setWordWrap(True)
    layout.addWidget(intro)
    compatibility = QLabel(windows_compatibility_note())
    compatibility.setWordWrap(True)
    compatibility.setStyleSheet("color: #76501c; background: #fff6df; border: 1px solid #ead7ad; padding: 9px;")
    layout.addWidget(compatibility)
    status = QLabel("Checking Ollama…")
    status.setWordWrap(True)
    status.setMinimumHeight(48)
    layout.addWidget(status)
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(0)
    progress.setVisible(False)
    layout.addWidget(progress)
    detail = QLabel("Ollama must be installed and running before the model can be downloaded.")
    detail.setWordWrap(True)
    detail.setStyleSheet("color: #5b6470;")
    layout.addWidget(detail)
    layout.addStretch(1)
    buttons = QHBoxLayout()
    buttons.setSpacing(8)
    buttons.addStretch(1)
    get_ollama = QPushButton("Get Ollama")
    primary = QPushButton("Checking…")
    primary.setObjectName("primary")
    skip = QPushButton("Skip for now")
    buttons.addWidget(get_ollama)
    buttons.addWidget(skip)
    buttons.addWidget(primary)
    layout.addLayout(buttons)
    state = {"value": "checking", "worker": None}

    def set_state(value: str, message: str) -> None:
        state["value"] = value
        dialog.pulling = value == "pulling"
        status.setText(message)
        primary.setEnabled(value not in ("checking", "pulling"))
        skip.setEnabled(value != "pulling")
        get_ollama.setEnabled(value not in ("checking", "pulling"))
        if value == "offline":
            primary.setText("Retry connection")
            detail.setText("Start Ollama, then retry. Get Ollama opens the official download page.")
            get_ollama.setVisible(True)
        elif value == "missing":
            primary.setText("Download Qwen 3.5 2B")
            detail.setText("Ollama stores the model in its configured model folder. Keep the PC online during download.")
            get_ollama.setVisible(False)
        elif value == "ready":
            primary.setText("Finish")
            detail.setText("You're ready to use INCANDESCENT. Local chat history and profiles are preserved.")
            get_ollama.setVisible(False)
            progress.setVisible(True)
            progress.setValue(100)
        elif value == "failed":
            primary.setText("Retry download")
            detail.setText("Check the internet connection and Ollama status, then retry. You can skip and return using the Start Menu shortcut.")
            get_ollama.setVisible(False)
        elif value == "pulling":
            primary.setText("Downloading…")
            detail.setText("Downloading through Ollama. Progress may pause while layers are verified.")
            progress.setVisible(True)
            get_ollama.setVisible(False)
        elif value == "checking":
            primary.setText("Checking…")
            detail.setText("Checking whether Ollama is running and already has the required model.")
            progress.setVisible(False)
            get_ollama.setVisible(False)

    def progress_update(percent: int, message: str) -> None:
        progress.setVisible(True)
        progress.setValue(percent)
        status.setText(message)

    def result_ready(code: str, message: str) -> None:
        if code in ("offline", "missing", "ready", "failed"):
            set_state(code, message)

    def start_worker(do_pull: bool = False) -> None:
        set_state("pulling" if do_pull else "checking",
                  "Connecting to Ollama…" if not do_pull else "Preparing Qwen 3.5 2B download…")
        worker = PullWorker(do_pull)
        state["worker"] = worker
        worker.progress_update.connect(progress_update)
        worker.result_ready.connect(result_ready)
        worker.start()

    def primary_clicked() -> None:
        value = state["value"]
        if value == "offline":
            start_worker(False)
        elif value in ("missing", "failed"):
            start_worker(True)
        elif value == "ready":
            dialog.accept()

    def open_ollama() -> None:
        QDesktopServices.openUrl(QUrl(OLLAMA_DOWNLOAD_URL))

    def skip_setup() -> None:
        if state["value"] == "pulling":
            QMessageBox.information(dialog, APP_TITLE, "Let the model download finish before skipping setup.")
        else:
            dialog.reject()

    primary.clicked.connect(primary_clicked)
    get_ollama.clicked.connect(open_ollama)
    skip.clicked.connect(skip_setup)
    start_worker(False)
    dialog.exec_()
    return 0


__all__ = [
    "MODEL_NAME", "installed_models", "model_is_installed",
    "ollama_base_url", "run_model_setup", "windows_compatibility_note",
]
