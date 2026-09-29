"""Stage 106: a stage-98-format panel cache assembled from the universes, for stage 100.

For each source it reads the universe's ``index.csv``, keeps the targets of ``--targets-csv`` that
have effects there, and copies their rows from the universe's npz chunks, one chunk at a time
(only the rows it needs are kept), into ``<out>/<name>.npz`` with stage 98's keys ``targets,
shrunk, raw, se, n_cells, meta``. Rows follow the order of the panel; ``meta`` is the chunk's own
string, so it differs from the one stage 98 wrote for the same source (N2 of the dress rehearsal).
The universes already hold every target of the t22 sources genome-wide, so for those sources this
stands in for stages 97, 102 and 98 on a new panel (defect D10 of the dress rehearsal of 22 October,
reports/invii/prova_generale_2026-09-28/; its prototype there, ``assembla_cache.py``, stays as the
record of that run).

The panel is read by `vcc2026.panel.read_panel`. Both index formats are read: K562 and Orion name
the chunk file (empty when a target has no effects); CD4 gives an integer group, whose file is
``<table>_<NNN>.npz``, so ``cd4_mix``, ``cd4_Rest`` and the other CD4 tables all come from the CD4
universe under their own names. Every table must be as wide as the official axis.

The sources are ``--preset`` (t22's four: ``me1``, K562 of 26/09 with CD4 and Orion ``_me1``, the
estimator t25's rule sends into every cache built from then on; or ``u26``, all of 26/09, the ones
r5 and t22 match) or repeated ``--source NAME=UNIVERSE_DIR``; one of the two is required.

``manifest.json`` (`vcc2026.panel.write_cache_manifest`, as stage 98) records ``targets_sha256``,
the panel the cache was built for, which stage 100 checks against the panel it reads (defect D4);
per source the universe with the sha256 of its index and manifest, the chunks read, the targets
found and missing; the time, free disk and peak memory. With ``--compare-to`` every table is also
compared with the same-named table of another cache (target sets, row order, ``n_cells``, and for
raw, se and shrunk the finite masks and the largest absolute difference) under the rule of the
rehearsal: 0 differences, except ``cd4_mix`` within 2e-8 (``TOLERANCE``); ``rule_passed`` applies it.

Nothing is overwritten: an existing ``--out`` is refused, unless it is an empty folder (what a run
interrupted before its first table leaves), which is reused and recorded. The run refuses unless
the uncompressed size fits with ``--reserve-gib`` to spare. Memory: one chunk array (about 44 MB
for 600 targets) plus the rows kept.

    scripts/py.cmd scripts/106_assemble_panel_cache.py --preset me1 --targets-csv <bundle>/pert_counts.csv \
        --out <data_root>/processed/multisource_<date>_<run> [--compare-to <another cache>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.manifest import file_fingerprint  # noqa: E402
from vcc2026.panel import read_panel, write_cache_manifest  # noqa: E402
from vcc2026.resources import GiB, peak_rss_bytes, require, snapshot  # noqa: E402

DATA_ROOT = config.paths().data_root  # VCC2026_DATA_ROOT, else configs/config.yaml
KEYS = ("shrunk", "raw", "se")
TOLERANCE = {"cd4_mix": 2e-8}   # the rehearsal's registered parity rule (prediction 3); every other table: 0
# Name -> universe folder under <data_root>/processed: the four sources of the t22 recipe.
PRESETS = {
    "me1": {"k562": "universe_k562_2026-09-26", "cd4_mix": "universe_cd4_2026-09-27_me1",
            "orion_hct116": "universe_orion_hct116_2026-09-27_me1",
            "orion_hek293t": "universe_orion_hek293t_2026-09-27_me1"},
    "u26": {"k562": "universe_k562_2026-09-26", "cd4_mix": "universe_cd4_2026-09-26",
            "orion_hct116": "universe_orion_hct116_2026-09-26", "orion_hek293t": "universe_orion_hek293t_2026-09-26"},
}


def sha256_file(path: Path) -> str:
    return file_fingerprint(path, full=True)["sha256"]


def read_index(universe: Path) -> pd.DataFrame:
    """A universe's ``index.csv``, only the targets with effects (a non-empty ``chunk``). Read as text
    with no NA parsing, as `read_panel` reads a panel, so a target is never turned into NaN."""
    ix = pd.read_csv(universe / "index.csv", dtype=str, keep_default_na=False)
    if "chunk" not in ix.columns:
        raise SystemExit(f"{universe}/index.csv has no chunk column")
    ix = ix[ix["chunk"].notna() & (ix["chunk"].astype(str).str.strip() != "")].copy()
    ix["target"] = ix["target"].astype(str)
    return ix


def chunk_path(universe: Path, table: str, chunk) -> Path:
    """The npz holding a target of ``table``: a file name as given, or ``<table>_<NNN>.npz`` for a group."""
    s = str(chunk).strip()
    if s.endswith(".npz"):
        return universe / s
    return universe / f"{table}_{int(float(s)):03d}.npz"


def assemble(name: str, universe: Path, targets: list[str], n_genes: int) -> tuple[dict, dict]:
    """(arrays in stage-98 layout, provenance) of ``targets`` from one universe table."""
    ix = read_index(universe)
    where = dict(zip(ix["target"], ix["chunk"]))
    present = [t for t in targets if t in where]
    missing = [t for t in targets if t not in where]
    by_file: dict[Path, list[str]] = defaultdict(list)
    for t in present:
        by_file[chunk_path(universe, name, where[t])].append(t)
    rows: dict[str, dict] = {}
    metas, absent, read = [], [], []
    for path in sorted(by_file):
        want = by_file[path]
        with np.load(path, allow_pickle=False) as z:
            names = z["targets"].astype(str)
            pos = {t: i for i, t in enumerate(names)}
            take = [t for t in want if t in pos]
            absent += [t for t in want if t not in pos]
            sel = np.array([pos[t] for t in take], dtype=np.int64)
            got = {t: {} for t in take}
            for key in KEYS:
                arr = z[key]
                if arr.ndim != 2 or arr.shape[1] != n_genes:
                    raise SystemExit(f"{path}: {key} has shape {arr.shape}, not (targets, {n_genes}) on the official axis")
                part = arr[sel].copy()
                del arr
                for k, t in enumerate(take):
                    got[t][key] = part[k]
                del part
            nc = z["n_cells"]
            for k, t in enumerate(take):
                got[t]["n_cells"] = nc[sel[k]]
            meta = str(z["meta"])
        rows.update(got)
        if meta not in metas:
            metas.append(meta)
        read.append({"file": path.name, "targets_taken": len(take)})
    order = [t for t in present if t in rows]
    if not order:
        raise SystemExit(f"{name}: none of the {len(targets)} targets has effects in {universe}")
    arrays = {"targets": np.array(order)}
    for key in KEYS:
        arrays[key] = np.stack([rows[t][key] for t in order])
    arrays["n_cells"] = np.array([rows[t]["n_cells"] for t in order])
    arrays["meta"] = metas[0]
    info = {"universe": str(universe), "index_sha256": sha256_file(universe / "index.csv"),
            "universe_manifest_sha256": (sha256_file(universe / "manifest.json")
                                         if (universe / "manifest.json").exists() else None),
            "targets": len(order), "missing": missing, "listed_in_index_but_absent_from_chunk": absent,
            "chunks_read": read, "meta_variants": len(metas)}
    return arrays, info


def compare(mine: Path, ref: Path, tolerance: float = 0.0) -> dict:
    """Parity of two stage-98 tables on their shared targets, one array at a time."""
    with np.load(mine, allow_pickle=False) as a, np.load(ref, allow_pickle=False) as b:
        ta, tb = a["targets"].astype(str).tolist(), b["targets"].astype(str).tolist()
        pa, pb = {t: i for i, t in enumerate(ta)}, {t: i for i, t in enumerate(tb)}
        shared = [t for t in tb if t in pa]
        ia = np.array([pa[t] for t in shared], dtype=np.int64)
        ib = np.array([pb[t] for t in shared], dtype=np.int64)
        out = {"reference": str(ref), "targets_mine": len(ta), "targets_ref": len(tb), "shared": len(shared),
               "only_mine": sorted(set(ta) - set(tb)), "only_ref": sorted(set(tb) - set(ta)),
               "same_order": ta == tb, "meta_equal": str(a["meta"]) == str(b["meta"])}   # meta: information only
        na, nb = np.asarray(a["n_cells"], dtype=np.float64)[ia], np.asarray(b["n_cells"], dtype=np.float64)[ib]
        out["n_cells_differing"] = int((na != nb).sum())
        ok = not out["only_mine"] and not out["only_ref"] and out["n_cells_differing"] == 0
        for key in KEYS:
            x = a[key][ia].astype(np.float64)
            y = b[key][ib].astype(np.float64)
            fx, fy = np.isfinite(x), np.isfinite(y)
            both = fx & fy
            d = np.abs(x[both] - y[both])
            del x, y
            out[key] = {"finite_mask_mismatches": int((fx != fy).sum()),
                        "max_abs_diff": float(d.max()) if d.size else 0.0,
                        "entries_differing": int((d > 0).sum()),
                        "entries_above_tolerance": int((d > tolerance).sum())}
            ok = ok and out[key]["finite_mask_mismatches"] == 0 and out[key]["entries_above_tolerance"] == 0
            del d, fx, fy, both
    out["tolerance"] = tolerance
    out["rule_passed"] = bool(ok)
    return out


def parse_sources(specs: list[str] | None, preset: str | None) -> dict[str, Path]:
    if specs:
        out = {}
        for spec in specs:
            name, _, path = spec.partition("=")
            if not name or not path:
                raise SystemExit(f"--source wants NAME=UNIVERSE_DIR, got {spec!r}")
            if name in out:
                raise SystemExit(f"--source names {name!r} twice")
            out[name] = Path(path)
        return out
    return {n: DATA_ROOT / "processed" / d for n, d in PRESETS[preset].items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets-csv", type=Path, required=True, help="the panel: the bundle's pert_counts.csv")
    ap.add_argument("--out", type=Path, required=True)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--preset", choices=sorted(PRESETS), help="t22's four sources (see the docstring)")
    which.add_argument("--source", action="append", metavar="NAME=UNIVERSE_DIR",
                       help="one table; repeat for each (e.g. cd4_Rest=<cd4 universe>)")
    ap.add_argument("--compare-to", type=Path, default=None, help="a stage-98 cache to check parity against")
    ap.add_argument("--report-json", type=Path, default=None, help="also write the manifest here (a new file)")
    ap.add_argument("--reserve-gib", type=float, default=1.5, help="free disk that must remain after the output")
    args = ap.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.time()
    reused_empty = args.out.is_dir() and not any(args.out.iterdir())
    if args.out.exists() and not reused_empty:
        raise SystemExit(f"{args.out} exists; a new cache goes to a new folder")
    if args.report_json is not None and args.report_json.exists():
        raise SystemExit(f"{args.report_json} exists")
    sources = parse_sources(args.source, args.preset)
    targets = read_panel(args.targets_csv)
    n_genes = len(official_axis().symbols)
    need = len(targets) * n_genes * 4 * len(KEYS) * len(sources)   # uncompressed upper bound
    before = require(disk_bytes=need, path=args.out, reserve_bytes=int(args.reserve_gib * GiB))
    args.out.mkdir(parents=True, exist_ok=reused_empty)
    infos = {}
    for name, universe in sources.items():
        arrays, info = assemble(name, universe, targets, n_genes)
        path = args.out / f"{name}.npz"
        with open(path, "xb") as fh:
            np.savez_compressed(fh, **arrays)
        del arrays
        infos[name] = info
        log(f"{name}: {info['targets']} targets, {len(info['missing'])} missing, "
            f"{len(info['chunks_read'])} chunks read, {time.time() - t0:.0f}s")
        if args.compare_to is not None:
            ref = args.compare_to / f"{name}.npz"
            if ref.exists():
                info["parity"] = compare(path, ref, TOLERANCE.get(name, 0.0))
                p = info["parity"]
                log(f"  parity with {ref.name}: rule passed {p['rule_passed']}; shared {p['shared']}, "
                    f"only mine {len(p['only_mine'])}, only ref {len(p['only_ref'])}; max |d| raw "
                    f"{p['raw']['max_abs_diff']:.3g} se {p['se']['max_abs_diff']:.3g} shrunk "
                    f"{p['shrunk']['max_abs_diff']:.3g}; n_cells differing {p['n_cells_differing']}")
            else:
                info["parity"] = {"reference": str(ref), "missing": True}
    fields = {"started_utc": started, "out_existed_empty": reused_empty,
              "preset": args.preset, "seconds": round(time.time() - t0, 1), "peak_rss_bytes": peak_rss_bytes(),
              "free_bytes_before": before.disk_free_bytes, "free_bytes_after": snapshot(args.out).disk_free_bytes}
    if args.compare_to is not None:
        fields["compare_to"] = str(args.compare_to)
        fields["parity_rule_passed"] = all(s.get("parity", {}).get("rule_passed", False) for s in infos.values())
    manifest = write_cache_manifest(args.out, "106_assemble_panel_cache", args.targets_csv, targets, infos, **fields)
    if args.report_json is not None:
        with open(args.report_json, "x", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, default=str)
    log(f"-> {args.out}: targets_sha256 {manifest['targets_sha256'][:12]}, {manifest['seconds']}s, "
        f"peak RSS {(manifest['peak_rss_bytes'] or 0) / 2**20:.0f} MiB")


if __name__ == "__main__":
    main()
