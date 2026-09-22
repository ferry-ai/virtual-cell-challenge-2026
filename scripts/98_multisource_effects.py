"""Stage 98: panel effects from every same-target source, and how they predict one another.

Sources, all put on the official axis by `vcc2026.multisource.AxisTable`:

* ``k562``: the K562 genome-wide bulk (Replogle 2022), `effects_from_bulk`, as stage 76;
  its per-gene shrinkage is replaced by `z_shrink`, the one every source gets here;
* ``cd4_Rest``, ``cd4_Stim8hr``, ``cd4_Stim48hr``: the CD4 pseudobulk rows of stage 97,
  one fold change per donor against that donor's controls, averaged over donors;
* ``cd4_halfA`` / ``cd4_halfB``: CD4 Stim48hr split by donors (two against two), used only
  as a replicate ceiling for the CD4 comparisons.

Transfer reports (`transfer_report`, effect-space proxies, not scores): each source
predicting each other one on the panel targets both measured, panel genes excluded, with
the source's own mean response removed at gamma 0, 0.5 and 1. The question they answer is
"how much of a target's response in one cell type is visible in another", for THESE 300
targets -- the only regime the official panel can be scored in.

Outputs: one npz per source on the official axis under ``--cache`` (data root, D-001) and
``transfer.json`` / ``coverage.json`` in ``--report-dir``. Nothing is overwritten.

    python scripts/98_multisource_effects.py --cd4-rows <stage-97 h5ad> \
        --cache <data_root>/processed/multisource_2026-09-22 --report-dir reports/multisource_2026-09-22
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import (  # noqa: E402
    AxisTable, effects_from_pseudobulk, mix, shared_signal, transfer_report, z_shrink,
)
from vcc2026.predictor_sc import effects_from_bulk  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")


def k562_table(path: Path, targets: list[str], axis) -> AxisTable:
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        is_ntc = np.array(["non-targeting" in lab for lab in labels])
        symbols = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, is_ntc)])
        rows = np.flatnonzero(is_ntc | np.isin(symbols, targets))
        means = f["X"][rows]
        n_cells = f["obs/num_cells_filtered"][:][rows]
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    src = effects_from_bulk(means, n_cells, symbols[rows], is_ntc[rows], names, targets=targets)
    # the same local shrinkage as every other source, in place of the single-normal prior
    src.shrunk = z_shrink(src.raw, src.se).astype(np.float32)
    return AxisTable.from_source("k562", src, axis)


def save_table(tab: AxisTable, cache: Path) -> Path:
    path = cache / f"{tab.name}.npz"
    if path.exists():
        raise FileExistsError(path)
    np.savez_compressed(path, targets=np.array(tab.targets), shrunk=tab.shrunk, raw=tab.raw, se=tab.se,
                        n_cells=tab.n_cells, meta=json.dumps(tab.meta, default=str))
    return path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--k562-bulk", type=Path, default=DATA_ROOT / "external/K562_gwps_raw_bulk_01.h5ad")
    p.add_argument("--cd4-rows", type=Path, required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--report-dir", type=Path, required=True)
    p.add_argument("--gammas", type=float, nargs="+", default=[0.0, 0.5, 1.0])
    args = p.parse_args()
    for path in (args.report_dir / "transfer.json", args.cache):
        if path.exists():
            raise FileExistsError(f"{path} exists; new runs go to a new destination")
    args.cache.mkdir(parents=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    axis = np.asarray(official_axis().symbols)
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    panel_cols = np.flatnonzero(np.isin(axis, panel))

    tables: dict[str, AxisTable] = {}
    log("K562 bulk effects for the panel")
    tables["k562"] = k562_table(args.k562_bulk, panel, axis)
    log(f"reading CD4 rows {args.cd4_rows}")
    cd4 = ad.read_h5ad(args.cd4_rows)
    obs = cd4.obs[["target", "donor", "condition", "n_cells"]].copy()
    for cond in sorted(obs["condition"].unique()):
        src = effects_from_pseudobulk(cd4.X, obs, cd4.var_names, targets=panel, condition=cond)
        tables[f"cd4_{cond}"] = AxisTable.from_source(f"cd4_{cond}", src, axis)
        log(f"  cd4 {cond}: {len(src.targets)} targets")
    donors = sorted(obs["donor"].unique())
    halves = {"cd4_halfA": donors[: len(donors) // 2], "cd4_halfB": donors[len(donors) // 2:]}
    for name, ds in halves.items():
        m = obs["donor"].isin(ds).to_numpy()
        src = effects_from_pseudobulk(cd4.X[m], obs[m], cd4.var_names, targets=panel, condition="Stim48hr")
        tables[name] = AxisTable.from_source(name, src, axis)
    del cd4
    # The three culture conditions as one CD4 source: reliability-weighted mean, gamma 0.
    conds = [n for n in tables if n.startswith("cd4_") and not n.startswith("cd4_half")]
    eff, w = mix([tables[n] for n in conds], panel, gamma=0.0)
    have = (w > 0).any(axis=1)
    cells = np.array([sum(tables[n].n_cells[tables[n].index()[t]] for n in conds if t in tables[n].index())
                      for t in panel])
    mixed = np.where(w > 0, eff, np.nan).astype(np.float32)[have]
    tables["cd4_mix"] = AxisTable("cd4_mix", [t for t, h in zip(panel, have) if h], mixed, mixed,
                                  np.full_like(mixed, np.nan), cells[have],
                                  {"from": conds, "how": "reliability-weighted mean of the conditions, gamma 0"})

    coverage = {}
    for name, tab in tables.items():
        save_table(tab, args.cache)
        measured = np.isfinite(tab.shrunk).any(axis=0)
        coverage[name] = {"targets": len(tab.targets), "genes_on_axis": int(measured.sum()),
                          "median_cells": float(np.median(tab.n_cells)) if len(tab.n_cells) else 0,
                          "meta": tab.meta}
    commons = {n: t.common() for n, t in tables.items()}
    common_corr = {}
    names = list(tables)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ok = np.isfinite(tables[a].shrunk).any(0) & np.isfinite(tables[b].shrunk).any(0)
            ok[panel_cols] = False
            if ok.sum() > 50:
                common_corr[f"{a}~{b}"] = float(np.corrcoef(commons[a][ok], commons[b][ok])[0, 1])

    shared = {}
    for a, b in [("k562", "cd4_mix"), ("k562", "cd4_Rest"), ("k562", "cd4_Stim8hr"), ("k562", "cd4_Stim48hr"),
                 ("cd4_Rest", "cd4_Stim48hr"), ("cd4_halfA", "cd4_halfB")]:
        for g in args.gammas:
            shared[f"{a}~{b}|gamma={g}"] = shared_signal(tables[a], tables[b], panel, exclude_cols=panel_cols, gamma=g)
            s = shared[f"{a}~{b}|gamma={g}"]
            log(f"  shared {a}~{b} g={g}: corr {s['corr']:.3f}, w_{a} {s['weight_a']:.2f}, amp {s['amplitude']:.3f}")

    # cd4_mix is only ever a predictor, and only of K562: it contains every CD4 condition.
    pairs = [(a, b) for a in names for b in names
             if a != b and b != "cd4_mix" and (a != "cd4_mix" or b == "k562")
             and not (a.startswith("cd4_half") ^ b.startswith("cd4_half"))]
    reports = []
    for a, b in pairs:
        for g in args.gammas:
            pred, w = mix([tables[a]], panel, gamma=g)
            rep = transfer_report(pred, w, tables[b], panel, exclude_cols=panel_cols)
            reports.append({"from": a, "to": b, "gamma": g, **rep})
            log(f"  {a:>12} -> {b:<12} g={g:.1f} r={rep['median']['pearson']:.3f} "
                f"rc={rep['median']['pearson_centred']:.3f} top10={rep['median']['purity_top10']:.3f} "
                f"reach~{rep['median']['reach_proxy']:.3f} pds~{rep['pds_proxy_mean']:.3f} "
                f"a*={rep['amplitude_star']:.3f} skill={rep['skill_at_amplitude_star']:.3f}")
    stamp = datetime.now(timezone.utc).isoformat()
    (args.report_dir / "coverage.json").write_text(json.dumps(
        {"stage": "98_multisource_effects", "written_utc": stamp, "sources": coverage,
         "common_response_correlation": common_corr, "shared_signal": shared,
         "cache": str(args.cache)}, indent=2, default=str),
        encoding="utf-8")
    with open(args.report_dir / "transfer.json", "x", encoding="utf-8") as fh:
        json.dump({"stage": "98_multisource_effects", "written_utc": stamp,
                   "claim_type": "measurement in effect space (pseudobulk ln fold changes); proxies, not VCC scores",
                   "panel_genes_excluded": int(panel_cols.size), "reports": reports}, fh, indent=2)
    log(f"wrote {args.report_dir}")


if __name__ == "__main__":
    main()
