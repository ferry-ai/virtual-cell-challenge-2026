"""Measured machine limits, and the peak memory a run actually used.

Every resource number this project has ever acted on came from a measurement
(`reports/candidate_verification/hardware.json`,
`reports/grok_verification/hardware.json`), and the measurements moved between
sessions: 8.4 GB RAM / 28.0 GB free disk on 11 September, 7.81 GB / 31.11 GB on
12 September. So a run that approaches either limit re-measures rather than
trusting a document, which is what `snapshot()` is for.

`peak_rss_bytes()` reports the process's peak working set -- the number that
decides whether a job fits, since an average is useless when one block
allocates 600 MB. `psutil` is not installed in this environment, so Windows is
read through `GetProcessMemoryInfo` directly and POSIX through `getrusage`.

`require()` exists because the alternative -- discovering that a 4 GB write ran
out of disk after 40 minutes -- destroys the run and leaves a truncated file
that looks like an artifact.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

__all__ = ["ResourceSnapshot", "snapshot", "peak_rss_bytes", "require", "GiB"]

GiB = 1024**3


@dataclass(frozen=True)
class ResourceSnapshot:
    """RAM and disk as measured at one instant, plus what produced them."""

    ram_total_bytes: int | None
    ram_available_bytes: int | None
    disk_path: str
    disk_total_bytes: int
    disk_free_bytes: int
    cpu_count: int | None
    platform: str
    source: str

    @property
    def disk_free_gib(self) -> float:
        return self.disk_free_bytes / GiB

    @property
    def ram_available_gib(self) -> float | None:
        if self.ram_available_bytes is None:
            return None
        return self.ram_available_bytes / GiB

    def as_dict(self) -> dict:
        d = asdict(self)
        d["ram_total_gib"] = (
            None if self.ram_total_bytes is None else self.ram_total_bytes / GiB
        )
        d["ram_available_gib"] = (
            None if self.ram_available_bytes is None else self.ram_available_bytes / GiB
        )
        d["disk_free_gib"] = self.disk_free_bytes / GiB
        return d


def _windows_memory() -> tuple[int, int]:
    import ctypes
    import ctypes.wintypes as wt

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", wt.DWORD),
            ("dwMemoryLoad", wt.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        raise OSError("GlobalMemoryStatusEx failed")
    return int(stat.ullTotalPhys), int(stat.ullAvailPhys)


def _posix_memory() -> tuple[int | None, int | None]:
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        total = None
    avail = None
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                avail = int(line.split()[1]) * 1024
                break
    return total, avail


def snapshot(path: Path | str | None = None) -> ResourceSnapshot:
    """Measure RAM and free disk now. `path` selects the filesystem to report."""
    target = Path(path) if path is not None else Path.cwd()
    # Walk up to an existing ancestor: the run directory may not exist yet.
    probe = target
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    usage = shutil.disk_usage(probe)

    if sys.platform == "win32":
        total, avail = _windows_memory()
        src = "GlobalMemoryStatusEx + shutil.disk_usage"
    else:
        total, avail = _posix_memory()
        src = "/proc/meminfo + shutil.disk_usage"

    return ResourceSnapshot(
        ram_total_bytes=total,
        ram_available_bytes=avail,
        disk_path=str(probe),
        disk_total_bytes=usage.total,
        disk_free_bytes=usage.free,
        cpu_count=os.cpu_count(),
        platform=platform.platform(),
        source=src,
    )


def peak_rss_bytes() -> int | None:
    """Peak working set of this process, or None if it cannot be read.

    An average or an instantaneous reading would not answer the question that
    matters -- whether the job ever came close to the ceiling -- because the
    peak is set by a single block, not by the steady state.
    """
    if sys.platform == "win32":
        import ctypes
        import ctypes.wintypes as wt

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", wt.DWORD),
                ("PageFaultCount", wt.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        # GetCurrentProcess returns the pseudo-handle -1. Without argtypes,
        # ctypes marshals that Python int in a way the call rejects, and the
        # failure is silent -- it returns 0 and the peak reads as "unknown".
        get_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_info.argtypes = [
            wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wt.DWORD
        ]
        get_info.restype = wt.BOOL
        ok = get_info(
            wt.HANDLE(ctypes.windll.kernel32.GetCurrentProcess()),
            ctypes.byref(counters),
            counters.cb,
        )
        return int(counters.PeakWorkingSetSize) if ok else None

    try:
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return None
    # Linux reports kilobytes, macOS bytes.
    return int(peak) if sys.platform == "darwin" else int(peak) * 1024


def require(
    *,
    disk_bytes: int = 0,
    path: Path | str | None = None,
    reserve_bytes: int = 10 * GiB,
    ram_bytes: int = 0,
) -> ResourceSnapshot:
    """Refuse to start a job that the measured machine cannot finish.

    `reserve_bytes` defaults to the 10 GiB floor written into
    `configs/candidate_ingestion.json` (`resource_policy`): the project keeps
    that much free rather than filling the disk to the last byte.

    Raises:
        RuntimeError: naming the shortfall, so the caller reports a measured
            bottleneck instead of a truncated output file.
    """
    snap = snapshot(path)
    if disk_bytes and snap.disk_free_bytes - disk_bytes < reserve_bytes:
        raise RuntimeError(
            f"needs {disk_bytes / GiB:.2f} GiB on {snap.disk_path} but only "
            f"{snap.disk_free_bytes / GiB:.2f} GiB is free and "
            f"{reserve_bytes / GiB:.2f} GiB must stay reserved"
        )
    if ram_bytes and snap.ram_available_bytes is not None:
        if snap.ram_available_bytes < ram_bytes:
            raise RuntimeError(
                f"needs {ram_bytes / GiB:.2f} GiB of RAM but only "
                f"{snap.ram_available_bytes / GiB:.2f} GiB is available"
            )
    return snap
