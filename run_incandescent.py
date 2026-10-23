#!/usr/bin/env python3
"""Launch Incandescent and yield CPU to foreground apps during model inference.

Windows-only priority management uses documented Win32 process APIs. It changes
scheduling priority temporarily, never model weights, generation settings, or
application data. Non-Windows systems simply run the server normally.
"""
from __future__ import annotations

import ctypes
import os
import runpy
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / ".incandescent-inference-active"
POLL_SECONDS = 0.6
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
TARGET_NAMES = {"ollama_llama_server.exe", "ollama.exe"}


def _processes() -> List[Tuple[int, str]]:
    """Return process ids/names using the Windows Toolhelp snapshot API."""
    if os.name != "nt":
        return []

    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return []
    result: List[Tuple[int, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            result.append((int(entry.th32ProcessID), str(entry.szExeFile)))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return result


def _priority_api():
    """Load only the Win32 calls needed to temporarily change priority."""
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetPriorityClass.argtypes = [wintypes.HANDLE]
    kernel32.GetPriorityClass.restype = wintypes.DWORD
    kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetPriorityClass.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def supervise(stop: threading.Event) -> None:
    """Lower AI process priority while a request is active; restore it afterward."""
    if os.name != "nt":
        while not stop.wait(POLL_SECONDS):
            pass
        return

    try:
        api = _priority_api()
    except Exception:
        # The app still works normally if the OS blocks priority inspection.
        while not stop.wait(POLL_SECONDS):
            pass
        return

    access = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_INFORMATION
    original: Dict[int, int] = {}

    def restore_all() -> None:
        for pid, priority in list(original.items()):
            handle = api.OpenProcess(access, False, pid)
            if handle:
                try:
                    api.SetPriorityClass(handle, priority)
                finally:
                    api.CloseHandle(handle)
            original.pop(pid, None)

    try:
        while not stop.is_set():
            active = MARKER.exists()
            current_targets = {
                pid for pid, name in _processes()
                if name.casefold() in TARGET_NAMES
            }
            for pid in current_targets:
                handle = api.OpenProcess(access, False, pid)
                if not handle:
                    continue
                try:
                    current = int(api.GetPriorityClass(handle) or 0)
                    if active:
                        if pid not in original and current:
                            original[pid] = current
                        if current and current != BELOW_NORMAL_PRIORITY_CLASS:
                            api.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
                    elif pid in original:
                        previous = original[pid]
                        if current != previous:
                            api.SetPriorityClass(handle, previous)
                        original.pop(pid, None)
                finally:
                    api.CloseHandle(handle)
            # Drop records for processes that have exited, avoiding PID reuse.
            for pid in list(original):
                if pid not in current_targets:
                    original.pop(pid, None)
            stop.wait(POLL_SECONDS)
    finally:
        restore_all()


def main() -> None:
    try:
        MARKER.unlink(missing_ok=True)
        (ROOT / (MARKER.name + ".tmp")).unlink(missing_ok=True)
    except OSError:
        pass

    stop = threading.Event()
    watcher = threading.Thread(target=supervise, args=(stop,), name="Incandescent-responsiveness", daemon=True)
    watcher.start()
    try:
        runpy.run_path(str(ROOT / "server.py"), run_name="__main__")
    finally:
        stop.set()
        watcher.join(timeout=2.5)
        try:
            MARKER.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
