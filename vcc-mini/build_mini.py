"""Build the mini cross-line CRISPRi dataset from raw/ into mini/.

Five public CRISPRi Perturb-seq experiments, four cell lines, one shared essential-gene
library (plus the K562 genome-wide screen):

    K562_ess, K562_gw  -> line K562 (two experiments of the same line, never source for each other)
    RPE1, HepG2, Jurkat

Every experiment is reduced to pseudobulk: for each perturbation the mean counts per cell,
normalised to 1e4 per cell over *all* the experiment's genes, then log1p. The effect of a
knockdown is delta = log1p(cpm_pert) - log1p(cpm_ctrl) on the genes common to all five
experiments. This is a log of means, not the scorer's mean of logs: the Replogle bulk files
hold means only, and one estimator for every source keeps the lines comparable.

    python build_mini.py --inspect      # print obs/var columns of each raw file, write nothing
    python build_mini.py                # write mini/

Outputs (mini/):
    genes.csv            gene symbols of the common axis, in column order
    lines.csv            line key, context group, control cells, targets kept
    basal.npy            [L, G] float32 log1p(cpm) of the controls, library over all the experiment's genes
    basal_common.npy     [L, G] the same with the library over the common genes (model features, P4)
    effects_<key>.npz    delta [T, G] float32, targets, n_cells, kd (on-target delta), target_basal
    targets.csv          union of targets: presence per line, fold (md5 of symbol mod 5), in_axis
    manifest.json        inputs with md5, counts, overlaps, thresholds, script sha256
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parent
# Data folder: raw/ is read from here and mini/ written here (Colab sets it to a local VM folder).
DATA = Path(os.environ.get("VCC_MINI_DATA", ROOT))

# Column choices. Replogle bulk files have no target column: the target is the second field of
# obs `gene_transcript` (also the obs index), and every row containing "non-targeting" is a control
# guide. This is how the team's stage 98 reads the same file (scripts/98_multisource_effects.py,
# k562_table); on 28/09 the Colab inspection showed the gene_transcript index, num_cells_filtered
# and non-integer X (per-cell means) in K562_ess and K562_gw.
SPEC = {
    "K562_ess": dict(group="K562", kind="bulk", target_col="gene_transcript", ctrl="non-targeting"),
    "K562_gw": dict(group="K562", kind="bulk", target_col="gene_transcript", ctrl="non-targeting"),
    "RPE1": dict(group="RPE1", kind="bulk", target_col="gene_transcript", ctrl="non-targeting"),
    "HepG2": dict(group="HepG2", kind="singlecell", target_col="perturbation", ctrl="control"),
    "Jurkat": dict(group="Jurkat", kind="singlecell", target_col="perturbation", ctrl="control"),
}
N_CELLS_COLS = ["num_cells_filtered", "num_cells", "n_cells", "cell_count"]
SYMBOL_COLS = ["gene_name", "gene_symbol", "symbol"]
MIN_CELLS = 20       # a perturbation with fewer cells is dropped (bulk: when the count is known)
MIN_CTRL_CELLS = 500
N_FOLDS = 5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gene_symbols(var: pd.DataFrame) -> np.ndarray:
    for c in SYMBOL_COLS:
        if c in var.columns:
            return var[c].astype(str).to_numpy()
    return var.index.astype(str).to_numpy()


def inspect(sources: list[dict]) -> None:
    for e in sources:
        path = DATA / "raw" / e["file"]
        a = ad.read_h5ad(path, backed="r")
        print(f"\n=== {e['key']}  {a.n_obs} x {a.n_vars}  X={type(a.X).__name__}")
        print("obs columns:", list(a.obs.columns))
        print(a.obs.head(3).to_string()[:1500])
        print("var columns:", list(a.var.columns), "| var index head:", list(a.var.index[:5]))
        col = SPEC[e["key"]]["target_col"]
        if col in a.obs.columns:
            vc = a.obs[col].astype(str).value_counts()
            print(f"{col}: {len(vc)} levels; top:", vc.head(5).to_dict())
            print("control label present:", SPEC[e["key"]]["ctrl"] in vc.index)
        block = a.X[: min(256, a.n_obs)]
        block = block.toarray() if sp.issparse(block) else np.asarray(block)
        print("X sample: min", block.min(), "max", block.max(),
              "integer share", float(np.mean(block == np.round(block))))


def read_bulk(path: Path, spec: dict) -> tuple[np.ndarray, list[str], np.ndarray, np.ndarray, dict]:
    """Replogle raw bulk: one row per targeted transcript, X = mean counts per cell."""
    a = ad.read_h5ad(path)
    col = spec["target_col"]
    raw = (a.obs[col] if col in a.obs.columns else a.obs.index.to_series()).astype(str).to_numpy()
    is_ntc = np.array([spec["ctrl"] in s for s in raw])
    labels = np.array([spec["ctrl"] if nt else s.split("_")[1] for s, nt in zip(raw, is_ntc)])
    assert is_ntc.sum() > 0, (path.name, "no control rows")
    ncol = next((c for c in N_CELLS_COLS if c in a.obs.columns), None)
    n = a.obs[ncol].to_numpy(float) if ncol else np.full(len(labels), np.nan)
    X = a.X.toarray() if sp.issparse(a.X) else np.asarray(a.X, dtype=np.float64)
    # Several transcripts of one gene: counts-weighted sum of the per-cell means.
    uniq, inv = np.unique(labels, return_inverse=True)
    w = np.where(np.isnan(n), 1.0, n)
    M = sp.csr_matrix((w, (inv, np.arange(len(labels)))), shape=(len(uniq), len(labels)))
    sums = np.asarray(M @ X)
    n_g = np.bincount(inv, weights=w, minlength=len(uniq))
    means = sums / n_g[:, None]
    n_out = n_g if ncol else np.full(len(uniq), np.nan)
    info = {"n_cells_column": ncol, "rows": int(a.n_obs), "genes": int(a.n_vars),
            "label_source": col if col in a.obs.columns else "obs index", "control_rows": int(is_ntc.sum())}
    return means, list(uniq), n_out, gene_symbols(a.var), info


def read_singlecell(path: Path, spec: dict, chunk: int = 4096):
    """Stream cells in row blocks; sums per perturbation through a sparse indicator."""
    a = ad.read_h5ad(path, backed="r")
    assert spec["target_col"] in a.obs.columns, (path.name, list(a.obs.columns))
    labels = a.obs[spec["target_col"]].astype(str).to_numpy()
    uniq, inv = np.unique(labels, return_inverse=True)
    sums = np.zeros((len(uniq), a.n_vars), np.float64)
    neg = 0
    nonint = 0
    for s in range(0, a.n_obs, chunk):
        X = a.X[s: s + chunk]
        X = X.toarray() if sp.issparse(X) else np.asarray(X)
        neg += int((X < 0).sum())
        if s == 0:
            nonint = float(np.mean(X != np.round(X)))
        rows = inv[s: s + chunk]
        M = sp.csr_matrix((np.ones(len(rows)), (rows, np.arange(len(rows)))), shape=(len(uniq), len(rows)))
        sums += M @ X
        print(f"\r{path.name}: {min(s + chunk, a.n_obs):,} / {a.n_obs:,} cells", end="", flush=True)
    print()
    n = np.bincount(inv, minlength=len(uniq)).astype(float)
    info = {"cells": int(a.n_obs), "genes": int(a.n_vars), "negative_entries": neg,
            "noninteger_share_first_block": nonint}
    return sums / n[:, None], list(uniq), n, gene_symbols(a.var), info


def build(sources: list[dict]) -> None:
    out = DATA / "mini"
    out.mkdir(exist_ok=True)
    per = {}
    for e in sources:
        spec = SPEC[e["key"]]
        path = DATA / "raw" / e["file"]
        reader = read_bulk if spec["kind"] == "bulk" else read_singlecell
        means, labels, n, symbols, info = reader(path, spec)
        assert spec["ctrl"] in labels, (e["key"], "control label missing")
        # Unique, non-empty symbols only: a duplicated symbol cannot be placed on one axis.
        s = pd.Series(symbols)
        keep_gene = (~s.duplicated(keep=False)) & (s.str.len() > 0) & (s != "nan")
        lib = means.sum(1, keepdims=True)                       # over ALL the experiment's genes
        logm = np.log1p(means / lib * 1e4)
        ci = labels.index(spec["ctrl"])
        info["control_cells"] = None if np.isnan(n[ci]) else float(n[ci])
        per[e["key"]] = dict(logm=logm, ctrl_means=means[ci], labels=labels, n=n, ci=ci, symbols=np.asarray(symbols),
                             keep_gene=keep_gene.to_numpy(), info=info, spec=spec, entry=e)
        print(e["key"], info)

    common = set.intersection(*[set(p["symbols"][p["keep_gene"]]) for p in per.values()])
    genes = np.array(sorted(common))
    G = len(genes)
    lines_rows, basal, basal_common = [], [], []
    targets_by_line = {}
    for key, p in per.items():
        col = {g: i for i, g in enumerate(p["symbols"]) if p["keep_gene"][i]}
        cols = np.array([col[g] for g in genes])
        base_full = p["logm"][p["ci"]]
        basal.append(base_full[cols].astype(np.float32))
        # P4: controls with the library summed over the common genes only, for the model features.
        cm = p["ctrl_means"][cols]
        basal_common.append(np.log1p(cm / cm.sum() * 1e4).astype(np.float32))
        keep = [i for i, t in enumerate(p["labels"]) if i != p["ci"]
                and (np.isnan(p["n"][i]) or p["n"][i] >= MIN_CELLS)]
        tg = [p["labels"][i] for i in keep]
        delta = (p["logm"][keep][:, cols] - base_full[cols]).astype(np.float32)
        kd = np.array([p["logm"][i, col[t]] - base_full[col[t]] if t in col else np.nan
                       for i, t in zip(keep, tg)], np.float32)
        tb = np.array([base_full[col[t]] if t in col else np.nan for t in tg], np.float32)
        np.savez_compressed(out / f"effects_{key}.npz", delta=delta, targets=np.array(tg),
                            n_cells=p["n"][keep].astype(np.float32), kd=kd, target_basal=tb)
        targets_by_line[key] = set(tg)
        ctrl = p["info"]["control_cells"]
        if p["spec"]["kind"] == "singlecell":
            assert ctrl is not None and ctrl >= MIN_CTRL_CELLS, (key, ctrl)
        lines_rows.append(dict(line=key, group=p["spec"]["group"], control_cells=ctrl,
                               targets=len(tg), targets_with_kd=int(np.isfinite(kd).sum()),
                               median_kd=float(np.nanmedian(kd))))
    np.save(out / "basal.npy", np.stack(basal))
    np.save(out / "basal_common.npy", np.stack(basal_common))
    pd.DataFrame({"gene": genes}).to_csv(out / "genes.csv", index=False)
    pd.DataFrame(lines_rows).to_csv(out / "lines.csv", index=False)

    allt = sorted(set.union(*targets_by_line.values()))
    gset = set(genes)
    tdf = pd.DataFrame({"target": allt})
    for key, ts in targets_by_line.items():
        tdf[f"in_{key}"] = tdf.target.isin(ts)
    tdf["n_groups"] = sum(
        tdf[[f"in_{k}" for k in per if per[k]["spec"]["group"] == grp]].any(axis=1).astype(int)
        for grp in sorted({p["spec"]["group"] for p in per.values()}))
    tdf["in_axis"] = tdf.target.isin(gset)
    tdf["fold"] = [int(hashlib.md5(t.encode()).hexdigest(), 16) % N_FOLDS for t in allt]
    tdf.to_csv(out / "targets.csv", index=False)

    keys = list(per)
    overlap = {a: {b: len(targets_by_line[a] & targets_by_line[b]) for b in keys} for a in keys}
    manifest = dict(
        written_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        script_sha256=sha256(Path(__file__)),
        estimator="delta = log1p(1e4*mean/lib) pert - ctrl; lib over all genes of the experiment",
        thresholds=dict(min_cells=MIN_CELLS, min_ctrl_cells=MIN_CTRL_CELLS, n_folds=N_FOLDS),
        n_genes=G, n_targets_union=len(allt),
        targets_in_all_groups=int((tdf.n_groups == tdf.n_groups.max()).sum()),
        target_overlap=overlap,
        lines=lines_rows,
        inputs=[dict(key=p["entry"]["key"], file=p["entry"]["file"], md5=p["entry"]["md5"],
                     source=p["entry"]["source"], license=p["entry"]["license"], **p["info"])
                for p in per.values()],
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({k: manifest[k] for k in ("n_genes", "n_targets_union", "targets_in_all_groups")}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()
    sources = json.loads((ROOT / "sources.json").read_text())
    assert_verified(sources)
    inspect(sources) if args.inspect else build(sources)


def assert_verified(sources: list[dict]) -> None:
    """Every input needs a verified md5: from fetch.py's log (local) or drive_fetch.py's sidecar."""
    raw = DATA / "raw"
    log_path = raw / "fetch_log.json"
    log = {r["key"]: r for r in json.loads(log_path.read_text())} if log_path.exists() else {}
    bad = []
    for e in sources:
        side = raw / (e["file"] + ".verified.json")
        if side.exists():
            ok = json.loads(side.read_text()).get("checksum") == e["md5"]
        else:
            ok = bool(log.get(e["key"], {}).get("md5_ok"))
        if not ok:
            bad.append(e["key"])
    assert not bad, f"md5 not verified for {bad}: run fetch.py or drive_fetch.py first"


if __name__ == "__main__":
    main()
