#!/usr/bin/env python3
"""Native Windows window for INCANDESCENT, using the existing UI unchanged."""
from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

APP_TITLE = "INCANDESCENT"
DEFAULT_MODEL = "qwen3.5:2b"
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_ATTEMPTS = 20


def application_data_dir() -> Path:
    """Stable, writable storage that survives one-file extraction cleanup."""
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(root) / APP_TITLE
    path.mkdir(parents=True, exist_ok=True)
    return path


def show_error(message: str) -> None:
    """Display startup errors even in a windowed executable with no console."""
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


def configure_logging(data_dir: Path) -> None:
    logging.basicConfig(
        filename=str(data_dir / "desktop.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def make_server(backend):
    """Bind only to loopback; prefer port 8765 to retain existing browser data."""
    start = DEFAULT_PORT
    try:
        candidate = int(os.environ.get("INCANDESCENT_PORT", str(DEFAULT_PORT)))
        if 1024 <= candidate <= 65535:
            start = candidate
    except (TypeError, ValueError):
        pass

    last_error: Optional[OSError] = None
    for offset in range(PORT_ATTEMPTS):
        port = start + offset
        if port > 65535:
            break
        try:
            httpd = backend.ThreadingHTTPServer((HOST, port), backend.Handler)
            httpd.daemon_threads = True
            return httpd
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


def main() -> int:
    data_dir = application_data_dir()
    configure_logging(data_dir)

    if os.name != "nt":
        show_error("The packaged desktop app is designed for Windows.")
        return 1

    # Users install/manage Ollama themselves. The desktop defaults to Qwen 3.5 2B.
    os.environ.setdefault("INCANDESCENT_MODEL", DEFAULT_MODEL)
    os.environ["INCANDESCENT_HOST"] = HOST

    try:
        import webview
    except Exception as exc:
        logging.exception("Could not import pywebview.")
        show_error(
            "The desktop window could not be loaded. Download the official desktop "
            "build again. If the problem continues, send desktop.log from:\n"
            f"{data_dir}\n\nDetails: {exc}"
        )
        return 1

    httpd = None
    supervisor_stop = threading.Event()
    supervisor_thread = None
    try:
        backend = importlib.import_module("server")
        backend.HOST = HOST
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

        # Resource-priority tuning is optional; the UI must still work without it.
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
            logging.exception("Resource-priority supervisor did not start.")

        if not wait_until_ready(url):
            raise RuntimeError("The local INCANDESCENT interface did not become ready.")

        logging.info("Starting desktop window at %s", url)
        webview.create_window(
            APP_TITLE,
            url,
            width=1280,
            height=850,
            min_size=(900, 600),
            resizable=True,
            background_color="#fbf7f1",
            text_select=True,
        )
        # Persist browser storage across launches; the web UI is served unchanged.
        webview.start(
            debug=False,
            private_mode=False,
            storage_path=str(data_dir / "WebViewData"),
        )
        return 0
    except Exception as exc:
        logging.exception("Desktop startup failed.")
        show_error(
            "INCANDESCENT could not open its desktop window. The app uses Microsoft "
            "Edge WebView2 to render the existing interface. Check that WebView2 "
            "Runtime is installed and Windows is up to date, then relaunch.\n\n"
            "Ollama and model weights were not changed. Diagnostic log:\n"
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
                logging.exception("Could not shut down local service cleanly.")
        if supervisor_thread and supervisor_thread.is_alive():
            supervisor_thread.join(timeout=1.0)


if __name__ == "__main__":
    raise SystemExit(main())
