"""Step 2 of the dress rehearsal: the fake bundle, copies of A/B/C relabelled D/E/F.

For each new context N (D, E, F) with its source O from the draw's permutation
(``estrazione.json``), ``context_O.h5ad`` is copied with ``shutil.copyfile`` (a real copy, never a
link: the copy is then opened for writing) to ``context_N.h5ad`` in ``--out``, and in the copy only
the one-element dataset ``obs/context/categories`` is rewritten, in place, from O to N; its dtype
and attributes stay. Then:

- every dataset of the copy is compared with the source block by block (``X/data``, ``X/indices``,
  ``X/indptr``, ``var/_index``, ``obs/target_gene``, ``obs/ntc_id`` and all the rest), and every
  attribute of every object; the only allowed difference is the rewritten label;
- the originals get a full sha256 before and after, which must match;
- their head+tail fingerprints must match the ones in t22's stage-45 manifest.

``gene_names.csv`` is copied from the controls; ``pert_counts.csv`` is the draw's fake panel (the
bundle of 22/10 brings its own). ``manifest.json`` is modelled on the official one, with
``partition: "prova"``, contexts D/E/F, the mapping, and a note that these are renamed copies, not
new data. A copy of it goes to ``--report``. Nothing is overwritten; the run refuses unless the
copies fit with 1.5 GiB to spare.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/bundle_finto.py
    (defaults: --controls-dir <data_root>/raw/controls --out <data_root>/raw/controls_prova_2026-09-28)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import h5py  # noqa: E402
import numpy as np  # noqa: E402

from comune import HERE, REPO, data_root, require_free, sha256_file, write_new_json  # noqa: E402
from vcc2026.manifest import file_fingerprint  # noqa: E402

LABEL = "obs/context/categories"
NAMED = ["X/data", "X/indices", "X/indptr", "var/_index", "obs/target_gene", "obs/ntc_id"]
T22_MANIFEST = REPO / "reports/invii/trial_2026-09-26/t22_manifest_45_generate_prediction.json"
BLOCK = 1 << 23   # values per block when comparing


def _objects(f: h5py.File) -> dict[str, object]:
    out = {"/": f}
    f.visititems(lambda name, obj: out.__setitem__(name, obj))
    return out


def _attrs_equal(a, b) -> bool:
    if set(a.attrs) != set(b.attrs):
        return False
    for k in a.attrs:
        x, y = a.attrs[k], b.attrs[k]
        if isinstance(x, np.ndarray) or isinstance(y, np.ndarray):
            if not np.array_equal(np.asarray(x), np.asarray(y)):
                return False
        elif x != y:
            return False
    return True


def _dataset_equal(a: h5py.Dataset, b: h5py.Dataset, block: int = BLOCK) -> bool:
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    if a.shape == ():
        return bool(np.array_equal(np.asarray(a[()]), np.asarray(b[()])))
    n = a.shape[0]
    step = max(1, block // max(1, int(np.prod(a.shape[1:], dtype=np.int64))))
    for lo in range(0, n, step):
        x, y = a[lo:lo + step], b[lo:lo + step]
        if x.dtype.kind == "f":
            if not np.array_equal(x, y, equal_nan=True):
                return False
        elif not np.array_equal(x, y):
            return False
    return True


def compare_files(src: Path, dst: Path, allowed: str = LABEL, block: int = BLOCK) -> dict:
    """Every object of ``dst`` against ``src``: same tree, same attributes, same values, except the
    values of dataset ``allowed``. Returns {"equal": bool, "differences": [...], "named": {...}}."""
    diffs, named = [], {}
    with h5py.File(src, "r") as fa, h5py.File(dst, "r") as fb:
        oa, ob = _objects(fa), _objects(fb)
        if set(oa) != set(ob):
            diffs.append({"tree": {"only_src": sorted(set(oa) - set(ob)), "only_dst": sorted(set(ob) - set(oa))}})
        for name in sorted(set(oa) & set(ob)):
            a, b = oa[name], ob[name]
            if type(a) is not type(b):
                diffs.append({name: "kind"})
                continue
            if not _attrs_equal(a, b):
                diffs.append({name: "attributes"})
            if isinstance(a, h5py.Dataset):
                same = _dataset_equal(a, b, block)
                for prefix in NAMED:
                    if name == prefix or name.startswith(prefix + "/"):
                        named[name] = same
                if not same and name != allowed:
                    diffs.append({name: "values"})
    return {"equal": not diffs, "differences": diffs, "named": named}


def relabel(path: Path, old: str, new: str) -> dict:
    """Rewrite the one context label of a control file in place; returns before/after."""
    with h5py.File(path, "r+") as f:
        ds = f[LABEL]
        before = [str(v) for v in ds.asstr()[:]]
        if before != [old]:
            raise SystemExit(f"{path}: {LABEL} is {before}, expected [{old!r}]")
        attrs = {k: ds.attrs[k] for k in ds.attrs}
        dtype = ds.dtype
        ds[0] = new
        after = [str(v) for v in ds.asstr()[:]]
        if after != [new] or ds.dtype != dtype or {k: ds.attrs[k] for k in ds.attrs} != attrs:
            raise SystemExit(f"{path}: the label rewrite changed more than the label")
    return {"before": before, "after": after}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = data_root()
    ap.add_argument("--controls-dir", type=Path, default=root / "raw" / "controls")
    ap.add_argument("--out", type=Path, default=root / "raw" / "controls_prova_2026-09-28")
    ap.add_argument("--estrazione", type=Path, default=HERE / "estrazione.json",
                    help="the draw's summary: its mapping_new_to_old says which copy becomes which context")
    ap.add_argument("--panel", type=Path, default=HERE / "pert_counts.csv", help="the fake panel for the bundle")
    ap.add_argument("--t22-manifest", type=Path, default=T22_MANIFEST,
                    help="stage-45 manifest whose head+tail fingerprints of the originals must still match")
    ap.add_argument("--report", type=Path, default=HERE, help="where the copy of manifest.json goes")
    args = ap.parse_args()
    t0 = time.time()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; a new bundle goes to a new folder")
    report_copy = args.report / "bundle_manifest.json"
    if report_copy.exists():
        raise SystemExit(f"{report_copy} exists")
    mapping = json.loads(args.estrazione.read_text(encoding="utf-8"))["mapping_new_to_old"]
    if sorted(mapping) != ["D", "E", "F"] or sorted(mapping.values()) != ["A", "B", "C"]:
        raise SystemExit(f"mapping {mapping} is not a permutation of A/B/C onto D/E/F")
    official = json.loads((args.controls_dir / "manifest.json").read_text(encoding="utf-8"))
    t22 = json.loads(args.t22_manifest.read_text(encoding="utf-8"))["inputs"]

    sources = {new: args.controls_dir / f"context_{old}.h5ad" for new, old in mapping.items()}
    need = sum(p.stat().st_size for p in sources.values()) + (1 << 20)
    free_before = require_free(args.out.parent, need)

    originals = {}
    for new, old in mapping.items():
        src = sources[new]
        fp = file_fingerprint(src)
        rec = t22.get(f"controls:{old}", {})
        originals[old] = {"path": str(src), "bytes": src.stat().st_size, "sha256_before": sha256_file(src),
                          "fingerprint": fp["sha256"], "fingerprint_mode": fp["sha256_mode"],
                          "fingerprint_t22": rec.get("sha256"),
                          "fingerprint_matches_t22": fp["sha256"] == rec.get("sha256")}
        print(f"original {old}: sha256 {originals[old]['sha256_before'][:12]}..., fingerprint as in t22: "
              f"{originals[old]['fingerprint_matches_t22']}")

    args.out.mkdir(parents=True)
    copies = {}
    for new, old in sorted(mapping.items()):
        src, dst = sources[new], args.out / f"context_{new}.h5ad"
        shutil.copyfile(src, dst)
        if os.path.samefile(src, dst) or os.stat(dst).st_nlink != 1:
            raise SystemExit(f"{dst} is not an independent copy")
        label = relabel(dst, old, new)
        cmp = compare_files(src, dst)
        copies[new] = {"from": old, "path": str(dst), "bytes": dst.stat().st_size, "label": label,
                       "comparison": cmp, "sha256": sha256_file(dst)}
        print(f"context_{new}.h5ad <- context_{old}.h5ad: only the label differs: {cmp['equal']}")
    shutil.copyfile(args.controls_dir / "gene_names.csv", args.out / "gene_names.csv")
    shutil.copyfile(args.panel, args.out / "pert_counts.csv")

    for new, old in mapping.items():
        o = originals[old]
        o["sha256_after"] = sha256_file(sources[new])
        o["unchanged"] = o["sha256_after"] == o["sha256_before"]

    checks = {
        "originals_unchanged": all(o["unchanged"] for o in originals.values()),
        "fingerprints_match_t22": all(o["fingerprint_matches_t22"] for o in originals.values()),
        "copies_differ_only_in_label": all(c["comparison"]["equal"] for c in copies.values()),
        "named_datasets_identical": all(bool(c["comparison"]["named"]) and all(c["comparison"]["named"].values())
                                        for c in copies.values()),
        "labels_rewritten": all(c["label"]["after"] == [n] for n, c in copies.items()),
    }
    manifest = {
        "season": official.get("season"),
        "partition": "prova",
        "panel_id": "prova-2026-09-28",
        "contexts": ["D", "E", "F"],
        "pert_col": official.get("pert_col"),
        "context_col": official.get("context_col"),
        "control_label": official.get("control_label"),
        "n_genes": official.get("n_genes"),
        "n_constructs": official.get("n_constructs"),
        "per_context": {new: {**{k: v for k, v in official.get("per_context", {}).get(old, {}).items()
                                 if k != "ground_truth_cells"}, "ground_truth_cells": None, "copy_of": old}
                        for new, old in sorted(mapping.items())},
        "cells_per_pert": official.get("cells_per_pert"),
        "prova": {
            "nota": "copia rinominata, non dati nuovi: context_D/E/F sono copie di context_A/B/C con la sola "
                    "etichetta obs/context riscritta; pert_counts.csv e' il pannello finto della prova",
            "mapping_new_to_old": mapping,
            "script": "reports/invii/prova_generale_2026-09-28/bundle_finto.py",
            "written_utc": datetime.now(timezone.utc).isoformat(),
            "originals": originals,
            "copies": copies,
            "panel_sha256": sha256_file(args.out / "pert_counts.csv"),
            "gene_names_sha256": sha256_file(args.out / "gene_names.csv"),
            "checks": checks,
            "free_bytes_before": free_before,
            "seconds": round(time.time() - t0, 1),
        },
    }
    write_new_json(args.out / "manifest.json", manifest)
    write_new_json(report_copy, manifest)
    print(json.dumps(checks, indent=1))
    if not all(checks.values()):
        raise SystemExit("a check failed; see manifest.json")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
