#!/usr/bin/env python3
"""Standalone Windows desktop host for the existing INCANDESCENT web UI.

Qt WebEngine is bundled with the executable, so the target PC does not need
Microsoft Edge WebView2 installed separately. The existing index.html is not
modified; a loopback-only Python service supplies the HTML and chat API.
"""
from __future__ import annotations

import importlib
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

APP_TITLE = "INCANDESCENT"
DEFAULT_MODEL = "qwen3.5:2b"
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_ATTEMPTS = 20


def application_data_dir() -> Path:
    """Return a stable writable user-data path outside PyInstaller's temp folder."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(root) / APP_TITLE
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(name: str) -> Path:
    """Resolve bundled data files during one-file or source execution."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    root = Path(bundle_root) if bundle_root else Path(__file__).resolve().parent
    return root / name


def configure_logging(data_dir: Path) -> None:
    logging.basicConfig(
        filename=str(data_dir / "desktop.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def show_error(message: str) -> None:
    """Show a startup error without requiring a console window."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_TITLE, message, parent=root)
        root.destroy()
    except Exception:
        logging.exception("Could not show startup dialog.")
        try:
            with (application_data_dir() / "desktop.log").open("a", encoding="utf-8") as log:
                log.write("\n" + APP_TITLE + " startup error:\n" + message + "\n")
        except OSError:
            pass


def make_server(backend):
    """Bind locally, preferring port 8765 for a stable app origin."""
    start = DEFAULT_PORT
    try:
        requested = int(os.environ.get("INCANDESCENT_PORT", str(DEFAULT_PORT)))
        if 1024 <= requested <= 65535:
            start = requested
    except (TypeError, ValueError):
        pass

    last_error: Optional[OSError] = None
    for offset in range(PORT_ATTEMPTS):
        port = start + offset
        if port > 65535:
            break
        try:
            server = backend.ThreadingHTTPServer((HOST, port), backend.Handler)
            server.daemon_threads = True
            return server
        except OSError as exc:
            last_error = exc
    raise OSError(
        f"Could not find a free local port from {start} to "
        f"{min(start + PORT_ATTEMPTS - 1, 65535)}."
    ) from last_error


def wait_until_ready(url: str, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request(url, headers={"Accept": "text/html"})
            with urllib.request.urlopen(request, timeout=0.35) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.08)
    return False


_OLLAMA_CHILD: Optional[subprocess.Popen] = None


def find_ollama_executable() -> Optional[Path]:
    """Find an already-installed local Ollama binary; never downloads or installs it."""
    for command in ("ollama.exe", "ollama"):
        found = shutil.which(command)
        if found:
            return Path(found)
    roots = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Ollama" / "ollama.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Ollama" / "ollama.exe",
    ]
    return next((candidate for candidate in roots if candidate.is_file()), None)


def ensure_ollama_running(backend, timeout_seconds: float = 7.0) -> bool:
    """Wake up an existing local Ollama install when its API is not listening yet."""
    global _OLLAMA_CHILD
    try:
        parsed = urllib.parse.urlsplit(backend.OLLAMA_BASE)
        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            return False  # Respect intentionally remote OLLAMA_HOST values.
    except Exception:
        return False

    tags_url = backend.OLLAMA_BASE.rstrip("/") + "/api/tags"

    def probe() -> bool:
        try:
            request = urllib.request.Request(tags_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=0.65) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False

    if probe():
        return True

    executable = find_ollama_executable()
    if executable is None:
        logging.warning("Ollama API is not reachable at %s and no installed ollama.exe was found.", backend.OLLAMA_BASE)
        return False

    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        _OLLAMA_CHILD = subprocess.Popen(
            [str(executable), "serve"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=flags,
        )
        logging.info("Started the existing Ollama service from %s", executable)
    except (OSError, ValueError) as exc:
        # A background Ollama service may be starting at the same time. Probe anyway.
        logging.info("Could not start an Ollama child process (%s); checking whether another service is starting.", exc)

    deadline = time.monotonic() + max(0.5, timeout_seconds)
    while time.monotonic() < deadline:
        if probe():
            logging.info("Ollama API is available at %s", backend.OLLAMA_BASE)
            return True
        time.sleep(0.25)
    logging.warning("Ollama API did not become available at %s after startup attempt.", backend.OLLAMA_BASE)
    return False


def main() -> int:
    data_dir = application_data_dir()
    configure_logging(data_dir)

    if os.name != "nt":
        show_error("The packaged desktop app is designed for Windows.")
        return 1

    # The user installs/manages Ollama. The desktop app defaults to Qwen 3.5 2B.
    os.environ.setdefault("INCANDESCENT_MODEL", DEFAULT_MODEL)
    os.environ["INCANDESCENT_HOST"] = HOST

    if "--setup-model" in sys.argv[1:]:
        from model_setup import run_model_setup
        return run_model_setup(data_dir)

    try:
        from PyQt5.QtCore import Qt, QUrl
        from PyQt5.QtGui import QDesktopServices, QIcon
        from PyQt5.QtWidgets import QApplication, QMainWindow
        from PyQt5.QtWebEngineWidgets import (
            QWebEnginePage,
            QWebEngineProfile,
            QWebEngineSettings,
            QWebEngineView,
        )
    except Exception as exc:
        logging.exception("Bundled Qt WebEngine could not be imported.")
        show_error(
            "The built-in desktop renderer could not start. Re-download the complete "
            "INCANDESCENT desktop package and try again.\n\n"
            "Diagnostic log:\n"
            f"{data_dir / 'desktop.log'}\n\nDetails: {exc}"
        )
        return 1

    httpd = None
    supervisor_stop = threading.Event()
    supervisor_thread = None
    try:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        app = QApplication(sys.argv)
        app.setApplicationName(APP_TITLE)
        app.setOrganizationName(APP_TITLE)
        app.setQuitOnLastWindowClosed(True)

        # Dynamic imports are explicitly included by the PyInstaller build flags.
        backend = importlib.import_module("server")
        backend.HOST = HOST
        # Start only an Ollama installation already present on this PC if its local
        # API is asleep. The UI can still open when Ollama is unavailable; status and
        # the request error then show the exact configured endpoint/reason.
        ensure_ollama_running(backend)
        httpd = make_server(backend)
        port = int(httpd.server_address[1])
        url = f"http://{HOST}:{port}/"

        service_thread = threading.Thread(
            target=httpd.serve_forever,
            kwargs={"poll_interval": 0.25},
            name="INCANDESCENT-local-service",
            daemon=True,
        )
        service_thread.start()

        try:
            supervisor = importlib.import_module("run_incandescent")
            supervisor_thread = threading.Thread(
                target=supervisor.supervise,
                args=(supervisor_stop,),
                name="INCANDESCENT-resource-supervisor",
                daemon=True,
            )
            supervisor_thread.start()
        except Exception:
            logging.exception("Optional resource-priority supervisor did not start.")

        if not wait_until_ready(url):
            raise RuntimeError("The local INCANDESCENT interface did not become ready.")

        storage_dir = data_dir / "WebEngine"
        cache_dir = data_dir / "Cache"
        storage_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Named persistent profile keeps browser-side app data between sessions.
        profile = QWebEngineProfile(APP_TITLE, app)
        profile.setPersistentStoragePath(str(storage_dir))
        profile.setCachePath(str(cache_dir))
        profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

        class LocalOnlyPage(QWebEnginePage):
            """Keep the bundled, older renderer on the local app UI only."""

            def acceptNavigationRequest(self, target_url, navigation_type, is_main_frame):
                local = (
                    target_url.scheme().lower() in ("http", "https")
                    and target_url.host().lower() == HOST
                    and target_url.port() == port
                )
                if local:
                    return True
                # Links in model answers can open in the user's regular browser;
                # redirects and embedded frames may not navigate the old engine away.
                if (
                    navigation_type == QWebEnginePage.NavigationTypeLinkClicked
                    and target_url.scheme().lower() in ("http", "https")
                ):
                    QDesktopServices.openUrl(target_url)
                return False

        window = QMainWindow()
        window.setWindowTitle(APP_TITLE)
        window.resize(1280, 850)
        window.setMinimumSize(900, 600)
        icon = resource_path("incandescent.ico")
        if icon.is_file():
            window.setWindowIcon(QIcon(str(icon)))

        view = QWebEngineView(window)
        page = LocalOnlyPage(profile, view)
        view.setPage(page)
        settings = view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        view.load(QUrl(url))
        window.setCentralWidget(view)

        logging.info("Starting bundled Qt WebEngine at %s", url)
        window.show()
        return int(app.exec_())
    except Exception as exc:
        logging.exception("INCANDESCENT desktop startup failed.")
        show_error(
            "INCANDESCENT could not open its desktop window. This build includes "
            "its own renderer and does not require a separate WebView2 install.\n\n"
            "Check the diagnostic log:\n"
            f"{data_dir / 'desktop.log'}\n\nDetails: {exc}"
        )
        return 1
    finally:
        supervisor_stop.set()
        if httpd is not None:
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                logging.exception("Could not shut down the local service cleanly.")
        if supervisor_thread and supervisor_thread.is_alive():
            supervisor_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
