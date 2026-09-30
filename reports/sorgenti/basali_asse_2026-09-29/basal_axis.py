"""Basal profiles of the sources with the official axis as CPM denominator (R-REV, action 5).

The source columns of processed/basal_sources_2026-09-2x.csv are CPM over all the genes of each file, restricted to
the axis afterwards (trasferimento_appreso_2026-09-26/basal_profiles.py, universo_nuovi_2026-09-27/basal_from_*.py);
A/B/C are on the Flex axis already. This script, as fixed in RISULTATI.md before it ran:

1. checks that the columns shared by the four basal files are identical, then writes
   processed/basal_sources_axis_2026-09-29.csv (and .json): every column of basal_sources_2026-09-28.csv divided by
   its sum over the axis genes it measures, x 1e6; cd4_mix is the mean of the three new CD4 columns, as in the old file;
2. recomputes, from the raw control counts restricted to the axis, the four sources of basal_profiles.py (row choice
   copied from it: K562 non-targeting rows weighted by cells, CD4 non-targeting rows per condition, Orion control
   pools) and compares them with the rescaled columns (tolerance 1e-9 relative on genes with CPM > 0);
3. splits the off-axis mass of those four by family (RPL/RPS, MT-, other) and lists the ten largest off-axis genes;
4. counts genes >= 5 CPM before and after, gives detectable_threshold's ratio 1/sqrt(factor), and estimates the mass
   the partial-support columns (k562, k562ess, rpe1) lack from the full-support 3' columns (an estimate from other
   lines).

    scripts/py.cmd reports/sorgenti/basali_asse_2026-09-29/basal_axis.py --out reports/sorgenti/basali_asse_2026-09-29/r1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

DATA = config.paths().data_root
BASALS = ["basal_sources_2026-09-26", "basal_sources_2026-09-27", "basal_sources_2026-09-27_r2",
          "basal_sources_2026-09-28"]
CD4 = ("cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr")
FULL_3P = ("orion_hct116", "orion_hek293t", "kolf")
PARTIAL = ("k562", "k562ess", "rpe1")
TOL = 1e-9


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def family(name: str) -> str:
    if re.match(r"^RP[LS]\d", name):
        return "RPL/RPS"
    if name.startswith("MT-"):
        return "MT-"
    return "other"


def split_axis(values: np.ndarray, names, axis_pos: dict) -> tuple[np.ndarray, np.ndarray]:
    """(values on the axis, first occurrence of a name as basal_profiles.to_axis does; NaN elsewhere),
    mask of the file's entries that did not land on the axis."""
    out = np.full(len(axis_pos), np.nan)
    off = np.ones(len(values), dtype=bool)
    seen = set()
    for i, n in enumerate(np.asarray(names).astype(str)):
        if n in axis_pos and n not in seen:
            out[axis_pos[n]] = values[i]
            off[i] = False
            seen.add(n)
    return out, off


def raw_sources(axis_pos: dict) -> dict:
    """Control counts of the four basal_profiles.py sources: {name: (all values, names)}."""
    out = {}
    with h5py.File(DATA / "external/K562_gwps_raw_bulk_01.h5ad", "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        ntc = np.flatnonzero(np.array(["non-targeting" in lab for lab in labels]))
        means = f["X"][ntc]
        cells = np.nan_to_num(f["obs/num_cells_filtered"][:][ntc])
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    out["k562"] = ((means * cells[:, None]).sum(axis=0) / cells.sum(), names)
    a = ad.read_h5ad(DATA / "external/cd4/panel_rows_2026-09-22.h5ad", backed="r")
    obs = a.obs
    for cond in ("Rest", "Stim8hr", "Stim48hr"):
        rows = np.flatnonzero((obs["guide_type"] == "non-targeting").to_numpy() & (obs["condition"] == cond).to_numpy())
        x = a.X[np.sort(rows)]
        x = np.asarray(x.sum(axis=0)).ravel() if hasattr(x, "sum") else x.sum(axis=0)
        out[f"cd4_{cond}"] = (np.asarray(x, dtype=np.float64), np.asarray(a.var_names).astype(str))
    a.file.close()
    for name, rel in (("orion_hct116", "external/orion/hct116_panel_pools_2026-09-23.h5ad"),
                      ("orion_hek293t", "external/orion/hek293t_panel_pools_2026-09-23.h5ad")):
        a = ad.read_h5ad(DATA / rel, backed="r")
        tgt = a.obs["target"].astype(str).str.lower()
        rows = np.flatnonzero(tgt.str.contains("non-targeting|non_targeting|ntc|control").to_numpy())
        x = a.X[np.sort(rows)]
        x = np.asarray(x.sum(axis=0)).ravel() if hasattr(x, "sum") else x.sum(axis=0)
        out[name] = (np.asarray(x, dtype=np.float64), np.asarray(a.var_names).astype(str))
        a.file.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new", type=Path, default=DATA / "processed/basal_sources_axis_2026-09-29.csv")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.new.exists() or args.new.with_suffix(".json").exists():
        raise SystemExit(f"{args.new} exists")
    args.out.mkdir(parents=True, exist_ok=False)
    axis = np.asarray(official_axis().symbols)
    axis_pos = {g: i for i, g in enumerate(axis)}
    tables = {b: pd.read_csv(DATA / "processed" / f"{b}.csv").set_index("gene_name") for b in BASALS}
    for b, t in tables.items():
        if list(t.index) != list(axis):
            raise SystemExit(f"{b}: rows are not the official axis in order")

    # 1. shared columns identical across the four files
    base = tables[BASALS[-1]]
    identical = {}
    for b in BASALS[:-1]:
        for c in tables[b].columns:
            x, y = tables[b][c].to_numpy(), base[c].to_numpy()
            identical[f"{b}:{c}"] = bool(np.array_equal(np.isnan(x), np.isnan(y)) and np.array_equal(x[~np.isnan(x)], y[~np.isnan(y)]))
    if not all(identical.values()):
        raise SystemExit(f"columns differ across basal files: {[k for k, v in identical.items() if not v]}")

    new, rows = {}, []
    for c in base.columns:
        v = base[c].to_numpy(dtype=np.float64)
        s = float(np.nansum(v))
        new[c] = v / s * 1e6
    new["cd4_mix"] = np.nanmean(np.vstack([new[c] for c in CD4]), axis=0)
    new = pd.DataFrame(new, index=pd.Index(axis, name="gene_name"))[list(base.columns)]
    for c in base.columns:
        old = base[c].to_numpy(dtype=np.float64)
        nw = new[c].to_numpy(dtype=np.float64)
        ok = np.isfinite(old) & (old > 0)
        factor = float(np.median(nw[ok] / old[ok]))
        spread = float(np.max(np.abs(nw[ok] / old[ok] / factor - 1.0)))
        rows.append({"column": c, "genes_measured": int(np.isfinite(old).sum()), "sum_on_axis_old": float(np.nansum(old)),
                     "factor": factor, "factor_spread_rel": spread, "share_of_library_on_axis": 1.0 / factor,
                     "above5_before": int((old >= 5).sum()), "above5_after": int((nw >= 5).sum()),
                     "detectable_threshold_ratio": 1.0 / np.sqrt(factor)})
    fac = pd.DataFrame(rows)
    abc_same = {c: float(np.nanmax(np.abs(new[c] - base[c]) / np.where(base[c] > 0, base[c], 1.0))) for c in ("A", "B", "C")}
    manifests = {}
    for b in BASALS[1:]:
        j = json.loads((DATA / "processed" / f"{b}.json").read_text(encoding="utf-8"))
        for name, info in j.get("added", {}).items():
            if "share_of_library_on_axis" in info:
                manifests[name] = info["share_of_library_on_axis"]
    fac["share_in_manifest"] = fac["column"].map(manifests)

    # 2-3. raw check and off-axis mass
    raw = raw_sources(axis_pos)
    checks, fams, top = [], [], []
    for name, (vals, names) in raw.items():
        on, off = split_axis(vals, names, axis_pos)
        axis_cpm = on / np.nansum(on) * 1e6
        nw = new[name].to_numpy(dtype=np.float64)
        ok = np.isfinite(axis_cpm) & (axis_cpm > 0)
        rel = np.abs(nw[ok] - axis_cpm[ok]) / axis_cpm[ok]
        checks.append({"source": name, "genes_compared": int(ok.sum()), "max_rel_diff": float(rel.max()),
                       "passes": bool(rel.max() <= TOL and np.array_equal(np.isfinite(axis_cpm), np.isfinite(nw)))})
        total = float(np.sum(vals))
        offv, offn = vals[off], np.asarray(names).astype(str)[off]
        row = {"source": name, "genes_in_file": int(len(vals)), "genes_off_axis": int(off.sum()),
               "share_on_axis": float(np.nansum(on) / total)}
        for fam in ("RPL/RPS", "MT-", "other"):
            m = np.array([family(n) == fam for n in offn], dtype=bool)
            row[f"off_{fam}"] = float(offv[m].sum() / total)
        fams.append(row)
        order = np.argsort(-offv)[:10]
        for r, i in enumerate(order, 1):
            top.append({"source": name, "rank": r, "gene": offn[i], "share_of_library": float(offv[i] / total)})

    # 4. partial support: mass of the axis genes a partial column lacks, in the full-support 3' columns
    partial = []
    for p in PARTIAL:
        missing = ~np.isfinite(new[p].to_numpy())
        for f in FULL_3P:
            v = new[f].to_numpy()
            partial.append({"partial": p, "missing_axis_genes": int(missing.sum()), "full_3p": f,
                            "missing_genes_measured_there": int((missing & np.isfinite(v)).sum()),
                            "their_share_of_axis_mass": float(np.nansum(v[missing]) / 1e6)})

    new.to_csv(args.new)
    info = {"script": "reports/sorgenti/basali_asse_2026-09-29/basal_axis.py",
            "written_utc": datetime.now(timezone.utc).isoformat(),
            "from": f"processed/{BASALS[-1]}.csv", "from_sha256": sha256(DATA / "processed" / f"{BASALS[-1]}.csv"),
            "rule": "each column divided by its sum over the axis genes it measures, x 1e6; cd4_mix = mean of the "
                    "three new CD4 columns; genes a source does not measure stay NaN",
            "factors": {r["column"]: r["factor"] for r in rows}, "sha256": sha256(args.new)}
    with args.new.with_suffix(".json").open("x", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
    fac.to_csv(args.out / "fattori.csv", index=False)
    pd.DataFrame(checks).to_csv(args.out / "controllo_grezzo.csv", index=False)
    pd.DataFrame(fams).to_csv(args.out / "fuori_asse.csv", index=False)
    pd.DataFrame(top).to_csv(args.out / "fuori_asse_top.csv", index=False)
    pd.DataFrame(partial).to_csv(args.out / "supporto_parziale.csv", index=False)
    summary = {"stage": "sorgenti/basali_asse_2026-09-29/basal_axis.py", "new_file": str(args.new),
               "new_sha256": info["sha256"], "shared_columns_identical": all(identical.values()),
               "shared_columns_checked": len(identical), "abc_max_rel_change": abc_same,
               "raw_check_passes": all(c["passes"] for c in checks)}
    with (args.out / "summary.json").open("x", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    pd.set_option("display.width", 200)
    print(fac.round(4).to_string(index=False))
    print(pd.DataFrame(checks).to_string(index=False))
    print(pd.DataFrame(fams).round(4).to_string(index=False))
    print(pd.DataFrame(top).to_string(index=False))
    print(pd.DataFrame(partial).round(4).to_string(index=False))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
