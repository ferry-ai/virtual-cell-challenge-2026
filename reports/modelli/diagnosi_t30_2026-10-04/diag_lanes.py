"""Diagnostic lane B of the t30 reading (PROTOCOLLO_CONFRONTI.md of this folder): on one held-out line, with the frozen
network outputs and the frozen selector weights of the D-056 bench, the six local members of arms that separate the
candidate causes of the t30 loss. Nothing is trained and no weight is chosen here.

Same real cells, targets, bench seed and generator stream as hybrid_lanes.py laneB (imported from
reports/modelli/ibrido_selettivo_2026-10-04, never edited). R is the correction of the arm `ibrido`, w the selective
weights of the weights file, R_bar the mean of R over the lane's targets (gene-wise, an undefined R counts as 0).

| arm          | effects                                   | what it stands for                                         |
|--------------|-------------------------------------------|------------------------------------------------------------|
| all          | T_all                                     | the bench baseline (transfer_all_J, the network's anchor)  |
| all_w0       | T_all + 0 R                               | parity control: cells must equal `all`                     |
| all_wR       | T_all + w R                               | the bench case (must reproduce the stored ibrido_selettivo)|
| all_wRspec   | T_all + w (R - R_bar)                     | the correction without its common component                |
| all_wRcom    | T_all + w R_bar                           | the common component alone                                 |
| all_wRdose   | T_all + w ((R - R_bar) + c R_bar)         | common share raised to --dose-share (the export's level)   |
| prod         | T_prod                                    | the recipe's sources without the held-out line             |
| prod_wR      | T_prod + w R                              | the t30 analogue: R learned against another anchor         |
| prod_wRspec  | T_prod + w (R - R_bar)                    |                                                            |
| prod_wRcom   | T_prod + w R_bar                          |                                                            |
| prod_wRdose  | T_prod + w ((R - R_bar) + c R_bar)        |                                                            |
| prod_x15     | 1.5 T_prod                                | the amplitude part of the t28 emission (no gene dispersion)|
| prod_wR_x15  | 1.5 (T_prod + w R)                        |                                                            |

c >= 0 is the factor on R_bar that brings the common share  ||mean_i R_i||^2 / mean_i ||R_i||^2  of the lane's
corrections to --dose-share; it is computed from R alone, on the genes where T_all is defined, never from the truth.
Writes bench/ (scaled_local.csv, bench.json), effects_diagnostics.json (common share, RMS ratios, cosines between the
two baselines and R), parity.json, run.json. Not VCC scores.

    py diag_lanes.py --run <train> --cube <cube_r2> --protocol <PROTOCOLLO.json> --target-keys <json> \
        --held-group HepG2 --splits <splits.json> --anchors-manifest <manifest> --weights <weights.json> \
        --real <real_cells.npz> --targets <targets.json> --out <new dir> [--dose-share 0.65]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
HYBRID = HERE.parent / "ibrido_selettivo_2026-10-04"
sys.path.insert(0, str(HYBRID))
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
import hybrid_lanes as HL  # noqa: E402
from arms import AMPLITUDE_T25  # noqa: E402
from common import now_utc, sha256, write_json  # noqa: E402
from fitting import transfer_for  # noqa: E402

F32 = np.float32
ARM = "ibrido"
X15 = 1.5


def common_share(R: np.ndarray) -> float:
    """||mean_i R_i||^2 / mean_i ||R_i||^2 over rows (R already 0 where undefined)."""
    e = float((R.astype(np.float64) ** 2).sum(1).mean())
    return float((R.astype(np.float64).mean(0) ** 2).sum() / e) if e > 0 else 0.0


def split_common(R: np.ndarray, defined: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(R - R_bar, R_bar broadcast) with R_bar the mean over rows of R on `defined` pairs (0 elsewhere)."""
    Rz = np.where(defined, np.nan_to_num(R, nan=0.0), 0.0).astype(np.float64)
    bar = Rz.mean(0, keepdims=True)
    return (Rz - bar).astype(F32), np.broadcast_to(bar, Rz.shape).astype(F32)


def dose_factor(spec: np.ndarray, com: np.ndarray, share: float) -> float:
    """c >= 0 with common share of spec + c com equal to `share` (spec has zero row mean, so the share is
    c^2 B / (c^2 B + S) with B = ||R_bar||^2 and S = mean_i ||spec_i||^2)."""
    if not 0 < share < 1:
        raise SystemExit(f"--dose-share must be in (0, 1), got {share}")
    B = float((com[0].astype(np.float64) ** 2).sum())
    S = float((spec.astype(np.float64) ** 2).sum(1).mean())
    if B <= 0:
        raise SystemExit("the correction has no common component: no dose arm")
    return float(np.sqrt(share * S / ((1 - share) * B)))


def row_cos(a: np.ndarray, b: np.ndarray, ok: np.ndarray) -> np.ndarray:
    az, bz = np.where(ok, a, 0.0).astype(np.float64), np.where(ok, b, 0.0).astype(np.float64)
    na, nb = np.linalg.norm(az, axis=1), np.linalg.norm(bz, axis=1)
    return np.where((na > 0) & (nb > 0), (az * bz).sum(1) / np.maximum(na * nb, 1e-30), np.nan)


def rms(x: np.ndarray, ok: np.ndarray) -> float:
    n = int(ok.sum())
    return float(np.sqrt((np.where(ok, x, 0.0).astype(np.float64) ** 2).sum() / n)) if n else float("nan")


def build_effects(T_all, T_prod, R, w, share) -> tuple[dict, dict]:
    """The arms' effects [targets, genes] (NaN where the arm's baseline is undefined) and what was measured on them."""
    okA, okP = np.isfinite(T_all), np.isfinite(T_prod)
    spec, com = split_common(R, okA)
    c = dose_factor(spec, com, share)
    dose = (spec + c * com).astype(F32)
    full = (spec + com).astype(F32)
    eff = {"all": T_all, "all_w0": HL.hybrid(T_all, full, 0.0), "all_wR": HL.hybrid(T_all, R, w),
           "all_wRspec": HL.hybrid(T_all, spec, w), "all_wRcom": HL.hybrid(T_all, com, w),
           "all_wRdose": HL.hybrid(T_all, dose, w),
           "prod": T_prod, "prod_wR": HL.hybrid(T_prod, R, w), "prod_wRspec": HL.hybrid(T_prod, spec, w),
           "prod_wRcom": HL.hybrid(T_prod, com, w), "prod_wRdose": HL.hybrid(T_prod, dose, w),
           "prod_x15": X15 * T_prod, "prod_wR_x15": X15 * HL.hybrid(T_prod, R, w)}
    both = okA & okP
    Rz = np.where(okA, np.nan_to_num(R, nan=0.0), 0.0)
    diag = {"targets": int(T_all.shape[0]), "targets_without_T_all": int((~okA.any(1)).sum()),
            "targets_without_T_prod": int((~okP.any(1)).sum()),
            "common_share_R": common_share(Rz), "common_share_dose": common_share(dose), "dose_factor": c,
            "dose_share_requested": share,
            "rms": {"R": rms(Rz, okA), "T_all": rms(T_all, okA), "T_prod": rms(T_prod, okP), "R_bar": rms(com, okA),
                    "R_spec": rms(spec, okA)},
            "cos_mean": {"T_all_vs_T_prod": float(np.nanmean(row_cos(T_all, T_prod, both))),
                         "R_vs_T_all": float(np.nanmean(row_cos(Rz, T_all, okA))),
                         "R_vs_T_prod": float(np.nanmean(row_cos(Rz, T_prod, both))),
                         "R_vs_T_prod_minus_T_all": float(np.nanmean(row_cos(Rz, T_prod - T_all, both)))},
            "w_mean": float(np.mean(w))}
    return eff, diag


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("run", "cube", "protocol", "target-keys", "splits", "anchors-manifest", "weights", "real", "targets",
                 "out"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--held-group", required=True)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--gen-seed", type=int, default=20260912)
    p.add_argument("--dose-share", type=float, default=0.65)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    import scipy.sparse as sp
    from vcc2026.bench import Bench
    from vcc2026.config import challenge
    from vcc2026.inference import trial01_cells
    S = HL.Setup(a)
    W = HL.load_weights(a.weights)
    z = np.load(a.real, allow_pickle=False)
    x = sp.csr_matrix((z["data"], z["indices"], z["indptr"]), shape=tuple(z["shape"]))
    lab, genes = z["labels"].astype(str), z["genes"].astype(str)
    targets = [t for t in json.loads(a.targets.read_text(encoding="utf-8")) if (lab == t["symbol"]).sum() >= 4]
    labels = [t["symbol"] for t in targets]
    tkeys = [t["target_key"] for t in targets]
    target_rows = {t: np.flatnonzero(lab == t) for t in labels}
    ctrl_rows = np.flatnonzero(lab == "non-targeting")
    a.out.mkdir(parents=True)
    bench = Bench(x, target_rows, ctrl_rows, genes, a.out / "bench", seed=a.seed)
    bench.anchors()
    ctrl_x = x[ctrl_rows]
    basal = np.asarray(ctrl_x.sum(0), dtype=np.float64).ravel()
    libs = np.asarray(ctrl_x.sum(1)).ravel().astype(np.int64)
    ch = challenge()
    cpos = pd.Index(S.cube.genes).get_indexer(genes)
    have = cpos >= 0
    mcol = pd.Index(S.model_genes).get_indexer(genes)
    if (mcol < 0).any():
        raise SystemExit(f"{int((mcol < 0).sum())} real genes are not model genes")
    gi_of = {(g["key"], g["symbol"]): i for i, g in enumerate(S.groups)}
    gis = [gi_of[(t["key"], t["symbol"])] for t in targets]
    if any(S.groups[i]["class"] != "C" for i in gis):
        raise SystemExit("lane B targets must be C groups")

    def on_real(name):
        s, _ = transfer_for(S.cubes[name], tkeys, S.sources[name], S.commons)
        lfc = np.full((len(tkeys), genes.size), np.nan, F32)
        lfc[:, have] = (s * AMPLITUDE_T25)[:, cpos[have]]
        return lfc

    T_all, T_prod = on_real("transfer_all_J"), on_real("transfer_prod_J")
    R = (S.pred[ARM][gis][:, mcol] - S.pred["ancora_sola"][gis][:, mcol]).astype(F32)
    w = HL.arm_weights(W, ARM, tkeys)
    effects, diag = build_effects(T_all, T_prod, R, w, a.dose_share)
    cells_of = {}
    for name, lfc_raw in effects.items():
        obs = np.isfinite(lfc_raw)
        lfc = np.where(obs, np.nan_to_num(lfc_raw), 0.0).astype(F32)
        stream = np.random.default_rng(a.gen_seed)
        blocks, labs = [], []
        for i, t in enumerate(labels):
            n = bench.n_pred(t)
            cells, _ = trial01_cells(basal, lfc[i], obs[i], libs, n, stream,
                                     max_stored_per_cell=ch.max_stored_per_cell,
                                     max_counts_per_cell=ch.max_counts_per_cell)
            blocks.append(cells)
            labs.append(np.full(n, t))
        mat = sp.vstack(blocks).tocsr()
        if name in ("all", "all_w0"):
            cells_of[name] = mat
        bench.score(name, mat, np.concatenate(labs), {"observed_share": float(obs.mean())})
    d = (cells_of["all"] != cells_of["all_w0"])
    parity = {"cells_equal": bool(d.nnz == 0), "differing_entries": int(d.nnz),
              "rule": "all_w0 = T_all + 0 R must give the cells of `all` exactly"}
    bench.finish(dict(stage=f"t30 diagnostic lane B {S.held}", targets=labels, target_keys=tkeys,
                      genes=int(genes.size), real=str(a.real), real_sha256=sha256(a.real), seed=a.seed,
                      gen_seed=a.gen_seed, commons={"regime": "J", "keys_kept_out": len(S.forbidden)}, parity=parity,
                      weights={"path": str(a.weights), "sha256": sha256(a.weights)}, effects=diag,
                      sources={k: S.sources[k] for k in ("transfer_all_J", "transfer_prod_J")},
                      generator="trial-01, one seed stream per arm", run=str(a.run)))
    S.check_reads()
    write_json(a.out / "effects_diagnostics.json", {"written_utc": now_utc(), "held_group": S.held, **diag,
                                                    "sources": {k: S.sources[k] for k in ("transfer_all_J",
                                                                                           "transfer_prod_J")}})
    write_json(a.out / "parity.json", parity)
    write_json(a.out / "run.json", dict(written_utc=now_utc(), arguments={k: str(v) for k, v in vars(a).items()},
                                        inputs=S.inputs, code_sha256=sha256(Path(__file__))))
    if not parity["cells_equal"]:
        raise SystemExit(f"parity failed: {parity}")
    print(json.dumps({"held": S.held, "targets": len(labels), "parity": parity["cells_equal"]}))


if __name__ == "__main__":
    main()
