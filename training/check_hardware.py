#!/usr/bin/env python3
"""Check whether this computer is a plausible Photon 1 LoRA training host before installing ML packages."""
from __future__ import annotations
import os
import platform
import shutil
import subprocess
import sys


def system_ram_gib():
    try:
        if os.name == "nt":
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stats = MEMORYSTATUSEX(); stats.dwLength = ctypes.sizeof(stats)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stats)):
                return stats.ullTotalPhys / (1024 ** 3), stats.ullAvailPhys / (1024 ** 3)
        if os.path.exists("/proc/meminfo"):
            values = {}
            for line in open("/proc/meminfo", encoding="utf-8"):
                parts = line.split()
                if len(parts) >= 2 and parts[0].rstrip(":") in {"MemTotal", "MemAvailable"}:
                    values[parts[0].rstrip(":")] = int(parts[1]) * 1024
            if "MemTotal" in values:
                return values["MemTotal"] / (1024 ** 3), values.get("MemAvailable", 0) / (1024 ** 3)
        if hasattr(os, "sysconf"):
            total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            available = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
            return total / (1024 ** 3), available / (1024 ** 3)
    except Exception:
        pass
    return None, None


def gpu_info():
    if not shutil.which("nvidia-smi"):
        return []
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=4, check=False)
        if result.returncode != 0:
            return []
        rows = []
        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) == 3:
                try: rows.append({"name": parts[0], "total_gib": int(parts[1]) / 1024, "free_gib": int(parts[2]) / 1024})
                except ValueError: pass
        return rows
    except Exception:
        return []


def classify_training_hardware(total_ram_gib, available_ram_gib, gpus):
    if not gpus:
        return "blocked", "No NVIDIA CUDA GPU was detected. Do not install the training stack for this PC; use it for inference, agent development, and evaluation only."
    best = max(gpus, key=lambda gpu: gpu.get("free_gib", 0))
    if best.get("free_gib", 0) < 7:
        return "blocked", f"The largest detected free VRAM budget is {best.get('free_gib', 0):.1f} GiB; the guarded LoRA recipe requires at least 7 GiB free."
    if total_ram_gib is not None and total_ram_gib < 12:
        return "not_recommended", f"System RAM is only {total_ram_gib:.1f} GiB. The recipe may still run out of host memory even though the GPU has enough VRAM."
    return "candidate", f"{best['name']} has {best['free_gib']:.1f} GiB free VRAM. This is a candidate host, not a guarantee; run the guarded training script and monitor RAM/VRAM."


def main():
    total, available = system_ram_gib()
    gpus = gpu_info()
    print("PHOTON 1 TRAINING CAPABILITY CHECK")
    print("OS:", platform.platform())
    print("Python:", sys.version.split()[0])
    print("CPU threads:", os.cpu_count() or "unknown")
    print("System RAM:", (f"{total:.1f} GiB total / {available:.1f} GiB available" if total is not None and available is not None else "unavailable"))
    if gpus:
        for gpu in gpus: print("GPU:", f"{gpu['name']} — {gpu['free_gib']:.1f}/{gpu['total_gib']:.1f} GiB VRAM free/total")
    else:
        print("GPU: no NVIDIA GPU reported by nvidia-smi")
    level, note = classify_training_hardware(total, available, gpus)
    print("Assessment:", level.upper())
    print(note)
    print("No training was started and no model weights were changed by this check.")
    return 0 if level == "candidate" else 2


if __name__ == "__main__":
    raise SystemExit(main())
