"""The t30 export procedure on the control cells of bench lines (PROTOCOLLO_CONFRONTI.md §7): does the high common
share of the exported correction follow the competition controls or the export procedure?

Same network (HepG2 fold), same anchors of the panel targets, same functions and seed as the export
(reports/modelli/ibrido_selettivo_2026-10-04/export_abc.py, imported, with the arguments recorded in the t30 effects
manifest); only the control cells change: the `non-targeting` rows of a bench line's real_cells.npz instead of the
official control file. No weight, no truth, no effects file is written.

Positive control (--reproduce A): the official controls of a context through this script must give back the R stored
in correction_<ctx>.npz, else nothing else is read.

Per line, on the corrected panel targets and the genes the line's file measures (R finite): the common share
||mean_i R_i||^2 / mean_i ||R_i||^2, RMS(R), RMS(s(A)) and their ratio; the same quantities of the stored A/B/C
corrections restricted to the same genes; the cosine between the line's common vector and each context's.

    .\\scripts\\py.cmd reports/modelli/diagnosi_t30_2026-10-04/export_on_line_controls.py --reproduce A \
        --line HepG2 <real_cells.npz> --line H1 <real_cells.npz> --line RPE1 <real_cells.npz> --out <new json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HYBRID = HERE.parent / "ibrido_selettivo_2026-10-04"
sys.path.insert(0, str(HYBRID))
import export_abc as EX  # noqa: E402

DATA = Path(os.environ.get("VCC2026_DATA_ROOT", "C:/Users/ferra/vcc2026-data"))
EXPORT = DATA / "processed/ibrido_selettivo_2026-10-04/export_abc_r2"
MANIFEST = REPO / "reports/invii/trial_2026-10-04/t30_effects_manifest.json"
F32 = np.float32
SHARE_LOW, SHARE_HIGH, RATIO_LOW, RATIO_HIGH = 0.35, 0.55, 0.5, 0.6


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def export_arguments() -> SimpleNamespace:
    argv = json.loads(MANIFEST.read_text(encoding="utf-8"))["argv"]
    got = {argv[i].lstrip("-").replace("-", "_"): Path(argv[i + 1]) for i in range(1, len(argv), 2)}
    return SimpleNamespace(**got)


def line_controls(path: Path, model_genes: list, input_genes: np.ndarray) -> dict:
    """export_abc.read_controls for the `non-targeting` rows of a bench real_cells.npz."""
    z = np.load(path, allow_pickle=False)
    x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
    x = x[np.flatnonzero(z["labels"].astype(str) == "non-targeting")].tocsc()
    var = [str(g) for g in z["genes"]]
    pos = {g: i for i, g in enumerate(model_genes)}
    col = np.array([pos.get(g, -1) for g in var], np.int64)
    measured = np.zeros(len(model_genes), bool)
    measured[col[col >= 0]] = True
    lib = np.asarray(x @ (col >= 0).astype(np.float64)).ravel().astype(F32)
    vpos = {g: j for j, g in enumerate(var)}
    in_var = np.array([vpos.get(model_genes[g], -1) for g in input_genes], np.int64)
    x_in = np.zeros((x.shape[0], input_genes.size), np.float32)
    have = in_var >= 0
    x_in[:, have] = x[:, in_var[have]].toarray()
    return {"x_in": np.minimum(x_in, 65504).astype(np.float16), "measured": measured, "lib": lib,
            "cells": int(x.shape[0]), "var_genes": len(var), "var_off_model": int((col < 0).sum()),
            "input_genes_absent": int((~have).sum()), "median_library": float(np.median(lib))}


def stats(R: np.ndarray, SA: np.ndarray, genes_ok: np.ndarray) -> tuple[dict, np.ndarray]:
    """Common share and amplitudes on rows = corrected targets and the columns `genes_ok` (NaN counts as 0)."""
    Rz = np.nan_to_num(R[:, genes_ok].astype(np.float64), nan=0.0)
    Az = np.nan_to_num(SA[:, genes_ok].astype(np.float64), nan=0.0)
    e = float((Rz ** 2).sum(1).mean())
    bar = Rz.mean(0)
    rr, ra = float(np.sqrt((Rz ** 2).mean())), float(np.sqrt((Az ** 2).mean()))
    per = np.sqrt((Rz ** 2).sum(1) / np.maximum((Az ** 2).sum(1), 1e-30))
    return {"genes": int(genes_ok.sum()), "common_share_R": float((bar ** 2).sum() / e) if e > 0 else 0.0,
            "rms_R": rr, "rms_s_anchor": ra, "ratio_rms_pooled": rr / ra if ra > 0 else None,
            "ratio_rms_per_target_median": float(np.median(per)),
            "rms_common_vector": float(np.sqrt((bar ** 2).mean()))}, bar


def cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-30))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--line", nargs=2, action="append", required=True, metavar=("NAME", "REAL_CELLS"))
    p.add_argument("--reproduce", default="A", help="competition context of the positive control")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    log = lambda m: print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)  # noqa: E731
    args = export_arguments()
    model, ck = EX.load_model(args.model)
    model_genes = [str(g) for g in ck["genes"]]
    input_genes = np.asarray(ck["input_genes"], np.int64)
    with np.load(args.effects / "effects_A.npz", allow_pickle=False) as z:
        targets, official = [str(t) for t in z["targets"]], [str(g) for g in z["genes"]]
    anc = EX.panel_anchors(args, model_genes, targets)
    el = anc["eligible"]
    mpos = {g: i for i, g in enumerate(model_genes)}
    off = np.array([mpos.get(g, -1) for g in official], np.int64)          # official axis -> model axis
    stored = {}
    for c in "ABC":
        with np.load(EXPORT / f"correction_{c}.npz", allow_pickle=False) as z:
            Rm = np.full((len(targets), len(model_genes)), np.nan, F32)
            Am = np.full((len(targets), len(model_genes)), np.nan, F32)
            Rm[:, off[off >= 0]] = z["R"][:, off >= 0]
            Am[:, off[off >= 0]] = z["s_anchor"][:, off >= 0]
            stored[c] = (Rm, Am)

    log(f"positive control: the official controls of {a.reproduce} through this script")
    ctrl = EX.read_controls(args.controls / f"context_{a.reproduce}.h5ad", model_genes, input_genes)
    R, SA, _ = EX.corrections(model, ck, ctrl, anc, targets, log=log)
    both = np.isfinite(R[el]) & np.isfinite(stored[a.reproduce][0][el])
    gap = float(np.abs(R[el][both] - stored[a.reproduce][0][el][both]).max())
    same_support = bool(np.array_equal(np.isfinite(R[el]), np.isfinite(stored[a.reproduce][0][el])))
    positive = {"context": a.reproduce, "max_abs_gap_to_stored_R": gap, "same_defined_pairs": same_support,
                "passed": gap == 0.0 and same_support}
    log(f"positive control: {positive}")
    if not positive["passed"]:
        a.out.write_text(json.dumps({"positive_control": positive, "stopped": "the export is not reproduced"}, indent=1),
                         encoding="utf-8")
        raise SystemExit("the stored correction is not reproduced: nothing else is read")

    lines = {}
    for name, path in a.line:
        path = Path(path)
        log(f"line {name}: {path}")
        ctrl = line_controls(path, model_genes, input_genes)
        R, SA, how = EX.corrections(model, ck, ctrl, anc, targets, log=log)
        ok = ctrl["measured"] & np.isfinite(R[el]).any(0)
        st, bar = stats(R[el], SA[el], ok)
        comp = {}
        for c in "ABC":
            sc, bc = stats(stored[c][0][el], stored[c][1][el], ok)
            comp[c] = {**sc, "cos_common_vector_with_line": cos(bar, bc)}
        lines[name] = {"real_cells": str(path), "real_cells_sha256": sha(path),
                       "controls": {k: ctrl[k] for k in ("cells", "var_genes", "var_off_model", "input_genes_absent",
                                                         "median_library")},
                       "draws": how, "line": st, "competition_on_the_same_genes": comp}
        log(f"line {name}: share {st['common_share_R']:.3f}, ratio {st['ratio_rms_pooled']:.3f}; "
            f"A/B/C same genes {[round(comp[c]['common_share_R'], 3) for c in 'ABC']}")
    shares = [v["line"]["common_share_R"] for v in lines.values()]
    ratios = [v["line"]["ratio_rms_pooled"] for v in lines.values()]
    comp_shares = [v["competition_on_the_same_genes"][c]["common_share_R"] for v in lines.values() for c in "ABC"]
    comp_ratios = [v["competition_on_the_same_genes"][c]["ratio_rms_pooled"] for v in lines.values() for c in "ABC"]

    def verdict(vals, comp, low, high):
        if all(v <= low for v in vals) and all(v >= high for v in comp):
            return "segue i controlli di gara"
        if sum(v >= high for v in vals) >= 2:
            return "segue la procedura o i bersagli del pannello"
        return "non distinto"

    out = {"written_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "protocol": "reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md §7",
           "network": {"model_sha256": sha(args.model), "held_group": anc["held"], "sources": anc["sources"]},
           "corrected_targets": int(el.sum()), "positive_control": positive, "lines": lines,
           "thresholds": {"share_low": SHARE_LOW, "share_high": SHARE_HIGH, "ratio_low": RATIO_LOW,
                          "ratio_high": RATIO_HIGH},
           "reading": {"common_share": verdict(shares, comp_shares, SHARE_LOW, SHARE_HIGH),
                       "amplitude_ratio": verdict(ratios, comp_ratios, RATIO_LOW, RATIO_HIGH)},
           "note": ("diagnostic of corrections, no truth and no score; H1 and RPE1 are training lines of this network, "
                    "HepG2 its held-out line; none is a Flex context")}
    a.out.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out["reading"]))


if __name__ == "__main__":
    main()
