"""Step 5 of the dress rehearsal: a stage-98-format panel cache assembled from the universes.

Prototype of the stage proposed as D10 (not a stage: it lives in this report). For each source it
reads the universe's ``index.csv``, keeps the targets of ``--targets-csv`` that have effects there,
and copies their rows from the universe chunks, one chunk at a time (only the rows it needs are
kept), into ``<out>/<name>.npz`` with stage 98's keys ``targets, shrunk, raw, se, n_cells, meta``.
Rows follow the order of the targets file; the ``meta`` string is the chunk's own.

Both index formats are read (see ``comune.read_index``): K562 and Orion name the chunk file, CD4
gives an integer group whose file is ``<name>_<NNN>.npz`` -- so ``cd4_mix``, ``cd4_Rest`` and the
other CD4 tables all come from the CD4 universe folder under their own names.

``manifest.json`` records the targets file and its sha256 (the check D4 asks stage 100 to make), the
universes and their index hashes, the chunks read, and per source the targets found and missing.
With ``--compare-to`` it also compares every table with the same-named table of another cache
(e.g. r5 or r9): target sets, row order, ``n_cells``, and for raw, se and shrunk the finite masks
and the largest absolute difference. The registered rule (prediction 3) is 0 differences for K562
and Orion and at most 2e-8 for ``cd4_mix``; ``rule_passed`` applies it.

Nothing is overwritten. The run refuses unless the uncompressed size of the output fits with
1.5 GiB to spare. Memory: one chunk array (about 44 MB for 600 targets) plus the kept rows.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/assembla_cache.py --preset u26 ^
        --targets-csv <data_root>/raw/controls/pert_counts.csv ^
        --out <data_root>/processed/multisource_prova_2026-09-28_parita_u26 ^
        --compare-to <data_root>/processed/multisource_2026-09-23_r5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from comune import (  # noqa: E402
    SOURCES_ME1, SOURCES_U26, chunk_path, data_root, free_bytes, read_index, read_targets, require_free,
    sha256_file, write_new_json,
)
from vcc2026.resources import peak_rss_bytes  # noqa: E402

KEYS = ("shrunk", "raw", "se")
TOLERANCE = {"cd4_mix": 2e-8}   # registered prediction 3; every other source: 0


def assemble(name: str, universe: Path, targets: list[str]) -> tuple[dict, dict]:
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


def parse_sources(specs: list[str], preset: str) -> dict[str, Path]:
    if specs:
        out = {}
        for spec in specs:
            name, _, path = spec.partition("=")
            if not name or not path:
                raise SystemExit(f"--source wants NAME=UNIVERSE_DIR, got {spec!r}")
            out[name] = Path(path)
        return out
    table = SOURCES_ME1 if preset == "me1" else SOURCES_U26
    return {n: data_root() / "processed" / d for n, d in table.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targets-csv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--preset", choices=["me1", "u26"], default="me1",
                    help="the t22 sources: K562 of 26/09 with CD4/Orion _me1 (default) or all of 26/09")
    ap.add_argument("--source", action="append", default=[], metavar="NAME=UNIVERSE_DIR",
                    help="replaces the preset; repeat for each table (e.g. cd4_Rest=<cd4 universe>)")
    ap.add_argument("--compare-to", type=Path, default=None, help="a stage-98 cache to check parity against")
    ap.add_argument("--report-json", type=Path, default=None, help="also write the manifest here (new file)")
    args = ap.parse_args()
    t0 = time.time()
    # An empty folder is what an interrupted run leaves before its first table (28/09, 20:14): it is
    # reused and recorded; anything else in it is refused.
    reused_empty = args.out.is_dir() and not any(args.out.iterdir())
    if args.out.exists() and not reused_empty:
        raise SystemExit(f"{args.out} exists; a new cache goes to a new folder")
    if args.report_json is not None and args.report_json.exists():
        raise SystemExit(f"{args.report_json} exists")
    sources = parse_sources(args.source, args.preset)
    targets = read_targets(args.targets_csv)
    n_genes = 18533
    need = len(targets) * n_genes * 4 * len(KEYS) * len(sources)   # uncompressed upper bound
    free_before = require_free(args.out.parent if args.out.parent.exists() else data_root(), need)
    args.out.mkdir(parents=True, exist_ok=reused_empty)
    manifest = {"script": "reports/invii/prova_generale_2026-09-28/assembla_cache.py",
                "written_utc": None, "out_existed_empty": reused_empty, "targets_csv": str(args.targets_csv),
                "targets_csv_sha256": sha256_file(args.targets_csv), "targets_requested": len(targets),
                "preset": None if args.source else args.preset, "sources": {}, "free_bytes_before": free_before}
    for name, universe in sources.items():
        arrays, info = assemble(name, universe, targets)
        path = args.out / f"{name}.npz"
        with open(path, "xb") as fh:
            np.savez_compressed(fh, **arrays)
        del arrays
        info.update({"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        manifest["sources"][name] = info
        print(f"{name}: {info['targets']} targets, {len(info['missing'])} missing, "
              f"{len(info['chunks_read'])} chunks read, {time.time() - t0:.0f}s", flush=True)
        if args.compare_to is not None:
            ref = args.compare_to / f"{name}.npz"
            if ref.exists():
                info["parity"] = compare(path, ref, TOLERANCE.get(name, 0.0))
                p = info["parity"]
                print(f"  parity with {ref.name}: rule passed {p['rule_passed']}; shared {p['shared']}, "
                      f"only mine {len(p['only_mine'])}, only ref {len(p['only_ref'])}; max |d| raw "
                      f"{p['raw']['max_abs_diff']:.3g} se {p['se']['max_abs_diff']:.3g} shrunk "
                      f"{p['shrunk']['max_abs_diff']:.3g}; n_cells differing {p['n_cells_differing']}", flush=True)
            else:
                info["parity"] = {"reference": str(ref), "missing": True}
    manifest.update({"written_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1),
                     "peak_rss_bytes": peak_rss_bytes(), "free_bytes_after": free_bytes(args.out)})
    if args.compare_to is not None:
        manifest["parity_rule_passed"] = all(s.get("parity", {}).get("rule_passed", False)
                                             for s in manifest["sources"].values())
    write_new_json(args.out / "manifest.json", manifest)
    if args.report_json is not None:
        write_new_json(args.report_json, manifest)
    print(f"-> {args.out} ({manifest['seconds']}s, peak RSS {(manifest['peak_rss_bytes'] or 0) / 2**20:.0f} MiB)")


if __name__ == "__main__":
    main()
