"""Run one stage (or rehearsal script) in-process and append its measurements to ``tempi.jsonl``.

The wrapped script runs through ``runpy.run_path`` as ``__main__``, with ``sys.argv`` set to its
own arguments, in this same process: so the peak working set read afterwards
(``vcc2026.resources.peak_rss_bytes``, Windows ``PeakWorkingSetSize``) is the stage's peak plus
this wrapper's few megabytes. One JSON line per run: the exact argv, UTC start and end read from
the clock, seconds, exit code (``SystemExit`` code, 1 on an uncaught exception, with its type and
message), peak RSS, and free disk before and after on the volume of ``--disk-path``.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/misura.py [--log <jsonl>] [--label <text>] ^
        -- scripts/100_build_context_effects.py --recipe ... --out ...

Everything after ``--`` is the script and its arguments, passed through untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))

from vcc2026.resources import peak_rss_bytes  # noqa: E402


def _free(path: Path) -> int:
    p = path
    while not p.exists() and p != p.parent:
        p = p.parent
    return shutil.disk_usage(p).free


def run(script: str, script_args: list[str], log: Path, label: str | None, disk_path: Path) -> int:
    record = {"label": label, "script": script, "argv": [script, *script_args], "cwd": os.getcwd(),
              "pid": os.getpid(), "disk_path": str(disk_path), "free_bytes_before": _free(disk_path),
              "start_utc": datetime.now(timezone.utc).isoformat()}
    t0 = time.perf_counter()
    code, error = 0, None
    old_argv = sys.argv
    sys.argv = [script, *script_args]
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        c = exc.code
        code = 0 if c is None else (c if isinstance(c, int) else 1)
        if not isinstance(c, (int, type(None))):
            error = {"type": "SystemExit", "message": str(c)}
    except BaseException as exc:  # noqa: BLE001 - recorded, then the code says it failed
        code = 1
        error = {"type": type(exc).__name__, "message": str(exc),
                 "traceback_tail": traceback.format_exc().splitlines()[-6:]}
        traceback.print_exc()
    finally:
        sys.argv = old_argv
    record.update({"end_utc": datetime.now(timezone.utc).isoformat(),
                   "seconds": round(time.perf_counter() - t0, 3), "exit_code": code, "error": error,
                   "peak_rss_bytes": peak_rss_bytes(), "free_bytes_after": _free(disk_path),
                   "peak_rss_note": "process peak working set: the stage plus this wrapper"})
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, default=str) + "\n")
    print(f"[misura] exit {code}, {record['seconds']:.1f}s, peak RSS "
          f"{(record['peak_rss_bytes'] or 0) / 2**20:.0f} MiB, free {record['free_bytes_before'] / 2**30:.2f} -> "
          f"{record['free_bytes_after'] / 2**30:.2f} GiB -> {log}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        raise SystemExit("usage: misura.py [--log PATH] [--label TEXT] [--disk-path PATH] -- SCRIPT [ARGS...]")
    cut = argv.index("--")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", type=Path, default=HERE / "tempi.jsonl")
    ap.add_argument("--label", default=None)
    ap.add_argument("--disk-path", type=Path, default=Path.home(),
                    help="a path on the volume whose free space is recorded (default: the home folder, on C:)")
    args = ap.parse_args(argv[:cut])
    rest = argv[cut + 1:]
    if not rest:
        raise SystemExit("nothing to run after --")
    return run(rest[0], rest[1:], args.log, args.label, args.disk_path)


if __name__ == "__main__":
    raise SystemExit(main())
