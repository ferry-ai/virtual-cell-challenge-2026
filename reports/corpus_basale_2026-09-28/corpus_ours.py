"""A corpus of basal (control) profiles on the official axis, for pre-training a context encoder.

One NEW folder per source group, each with `profiles.npz` (`counts` float32 N x 18,533, NaN where the source does not
measure a gene; `library` float64, the profile's counts over all genes of its source) and `meta.csv`
(`profile_id, source, context, family, study, platform, kind, n_cells`). Several profiles per context, so an encoder
can learn what is stable within a context and what separates contexts. `family` and `study` are the units a design
holds out together: every K562 experiment (Replogle 3', VIPerturb Flex) is family `k562`, the two Orion lines are
family `orion`, the CD4 donors and conditions family `cd4`.

Groups:
* `ours`: the controls of our CRISPRi sources:
  - K562, K562 essential, RPE1: Replogle's per-guide non-targeting rows (per-cell means x cells);
  - CD4: the non-targeting pseudobulk rows by donor and condition;
  - HCT116, HEK293T: the non-targeting pool rows;
  - KOLF2.1J, A549 (knockout screen), VIPerturb-seq (Flex), HIPSCI (the genome-wide screens' pooled lines, and each
    line of the targeted screen), Southard Hs27: the NTC groups of their sums archives, one profile per pool.
* `vcc_abc`: the competition's A, B, C controls (10x Flex), as sums of random non-overlapping subsets of
  --cells-per-subset cells.
* `depmap`: DepMap bulk expression (log1p TPM of protein-coding genes, back to TPM), one profile per cell line; the
  lines in --exclude-lines (case- and punctuation-insensitive, e.g. our test lines) are left out and listed.

    scripts/py.cmd reports/corpus_basale_2026-09-28/corpus_ours.py --group ours --out <new dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "reports" / "universo_kolf_2026-09-27"))
sys.path.insert(0, str(REPO / "reports" / "trasferimento_appreso_2026-09-26"))

from basal_profiles import read_frame  # noqa: E402
from kolf_effects import Sums  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

DATA = Path("C:/Users/ferra/vcc2026-data")
AXIS = np.asarray(official_axis().symbols)
COL = {g: i for i, g in enumerate(AXIS)}


def on_axis(values: np.ndarray, names) -> np.ndarray:
    out = np.full(AXIS.size, np.nan, dtype=np.float32)
    seen = set()
    for v, n in zip(values, names):
        n = str(n)
        if n in COL and n not in seen:
            out[COL[n]] = v
            seen.add(n)
    return out


class Collector:
    def __init__(self, prefix: str = "p"):
        self.counts, self.library, self.meta, self.prefix = [], [], [], prefix

    def add(self, counts, library, **meta):
        self.counts.append(np.asarray(counts, dtype=np.float32))
        self.library.append(float(library))
        # the group in the id: encoder_contesto's corpus.py refuses ids repeated across corpora
        self.meta.append({"profile_id": f"{self.prefix}_{len(self.meta):06d}", **meta})

    def write(self, out: Path, info: dict):
        out.mkdir(parents=True, exist_ok=False)
        np.savez(out / "profiles.npz", counts=np.vstack(self.counts), library=np.asarray(self.library))
        meta = pd.DataFrame(self.meta)
        meta.to_csv(out / "meta.csv", index=False)
        summary = meta.groupby(["source", "context"]).agg(profiles=("profile_id", "size"),
                                                         cells=("n_cells", "sum")).reset_index()
        with (out / "manifest.json").open("x", encoding="utf-8") as fh:
            json.dump({"stage": "corpus_basale_2026-09-28/corpus_ours.py", "profiles": len(meta),
                       "per_context": summary.to_dict(orient="records"), **info}, fh, indent=1, default=str)
        print(summary.to_string(index=False), flush=True)


def replogle_bulk(col: Collector, path: Path, context: str, family: str):
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        ntc = np.flatnonzero(np.array(["non-targeting" in lab for lab in labels]))
        cells = np.nan_to_num(f["obs/num_cells_filtered"][:][ntc])
        means = f["X"][ntc]
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    for i in range(ntc.size):
        if cells[i] < 1:
            continue
        sums = means[i] * cells[i]
        col.add(on_axis(sums, names), sums.sum(), source="replogle", context=context, family=family,
                study=f"replogle_{context}", platform="10x3", kind="guide", n_cells=int(cells[i]))
    print(f"replogle {context}: {ntc.size} non-targeting guides", flush=True)


def panel_rows(col: Collector, path: Path, source: str, context_of, family: str, pattern: str, study: str):
    a = ad.read_h5ad(path)                # in memory: row reads of a backed sparse matrix are slow
    obs = a.obs
    tcol = "guide_type" if "guide_type" in obs.columns else "target"
    mask = obs[tcol].astype(str).str.lower().str.contains(pattern).to_numpy()
    rows = np.flatnonzero(mask)
    names = np.asarray(a.var_names).astype(str)
    X = a.X[rows]
    X = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)
    for i, r in enumerate(rows):
        x = X[i].ravel()
        n = obs["n_cells"].iloc[r] if "n_cells" in obs.columns else np.nan
        col.add(on_axis(x, names), x.sum(), source=source, context=context_of(obs.iloc[r]), family=family, study=study,
                platform="10x3", kind="donor" if source == "cd4" else "pool", n_cells=float(n) if n == n else np.nan)
    print(f"{source} {path.name}: {rows.size} control rows", flush=True)


def sums_archive(col: Collector, path: Path, source: str, context, family: str, platform: str, ctx_key=None,
                 block: int = 512):
    """The NTC groups of a sums archive. The matrix is in Fortran order: a gene's column over all groups is one
    contiguous stretch, so the file is read once, sequentially, a block of genes at a time (Sums.window); reading a
    group's row directly would touch every page of the file per row.

    `context` is the corpus context of every NTC group, or a dict {archive context: corpus context} for an archive
    with several contexts (groups of archive contexts not in the dict are left out); `ctx_key` keeps one archive
    context."""
    s = Sums(path)
    if not (s.genes == AXIS).all():
        raise ValueError(f"{path}: the archive's gene axis is not the official axis")
    keep = s.target == "NTC"
    if ctx_key and s.context is not None:
        keep &= s.context == ctx_key
    if isinstance(context, dict):
        keep &= np.isin(s.context, list(context))
    rows = np.flatnonzero(keep)
    x = np.empty((rows.size, s.na), dtype=np.float32)
    for a in range(0, s.na, block):
        b = min(a + block, s.na)
        x[:, a:b] = np.asarray(s.window(a, b)[:, rows], dtype=np.float32).T
    # genes the source's file lacks are NaN, never 0 (D-009)
    x[:, s.file_columns < 0] = np.nan
    for i, r in enumerate(rows):
        ctx = context[s.context[r]] if isinstance(context, dict) else context
        col.add(x[i], s.total[r], source=source, context=ctx, family=family, study=source, platform=platform,
                kind="pool", n_cells=int(s.n_cells[r]))
    print(f"{source}: {rows.size} NTC groups from {path.name} ({s.ng} groups)", flush=True)


def group_ours(col: Collector):
    replogle_bulk(col, DATA / "external/K562_gwps_raw_bulk_01.h5ad", "k562", "k562")
    replogle_bulk(col, DATA / "external/K562_essential_raw_bulk_01.h5ad", "k562ess", "k562")
    replogle_bulk(col, DATA / "external/rpe1_raw_bulk_01.h5ad", "rpe1", "rpe1")
    panel_rows(col, DATA / "external/cd4/panel_rows_2026-09-22.h5ad", "cd4",
               lambda o: f"cd4_{o['condition']}", "cd4", "non-targeting", "gse314342")
    for name, path in (("orion_hct116", DATA / "external/orion/hct116_panel_pools_2026-09-23.h5ad"),
                       ("orion_hek293t", DATA / "external/orion/hek293t_panel_pools_2026-09-23.h5ad")):
        panel_rows(col, path, "orion", lambda o, n=name: n, "orion", "non-targeting|non_targeting|ntc|control", "x_atlas_orion")
    sums_archive(col, DATA / "interim/kolf_sums/sums.npz", "kolf", "kolf", "kolf", "10x3")
    sums_archive(col, DATA / "interim/a549_sums_r2/sums.npz", "a549", "a549", "a549", "10x3")
    sums_archive(col, DATA / "interim/viperturb_sums/sums_p8.npz", "viperturb", "viperturb", "k562", "flex")
    sums_archive(col, DATA / "interim/southard_sums/hs27_sums_p8.npz", "southard", "southard_hs27", "southard_hs27", "10x3")
    for part in ("gw_fitness_ua1", "gw_nonfitness_ua1"):
        p = DATA / f"interim/hipsci_sums/{part}/sums.npz"
        if p.exists():
            sums_archive(col, p, "hipsci", "hipsci_pooled", "hipsci", "10x5", ctx_key="pooled")
    # the targeted screen, line by line (8 NTC pools per line); its `pooled` context is left out, so that no cell
    # enters twice
    p = DATA / "interim/hipsci_sums/targeted/sums.npz"
    if p.exists():
        lines = sorted(set(Sums(p).context.tolist()) - {"pooled"})
        sums_archive(col, p, "hipsci", {c: f"hipsci_{c}" for c in lines}, "hipsci", "10x5")


def group_vcc(col: Collector, per_subset: int, seed: int):
    rng = np.random.default_rng(seed)
    for c in ("A", "B", "C"):
        a = ad.read_h5ad(DATA / f"raw/controls/context_{c}.h5ad")
        X = a.X.tocsr() if hasattr(a.X, "tocsr") else a.X
        names = np.asarray(a.var_names).astype(str)
        order = rng.permutation(X.shape[0])
        for k in range(X.shape[0] // per_subset):
            idx = np.sort(order[k * per_subset:(k + 1) * per_subset])
            x = np.asarray(X[idx].sum(axis=0)).ravel()
            col.add(on_axis(x, names), x.sum(), source="vcc", context=c, family=f"vcc_{c}", study="vcc2026",
                    platform="flex", kind="cells_subset", n_cells=per_subset)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def group_depmap(col: Collector, exclude: list[str]):
    models = pd.read_csv(DATA / "external/depmap_24q4/Model.csv")
    expr = pd.read_csv(DATA / "external/depmap_24q4/OmicsExpressionProteinCodingGenesTPMLogp1.csv", index_col=0)
    genes = [c.split(" (")[0] for c in expr.columns]
    name_of = dict(zip(models["ModelID"], models["StrippedCellLineName"].astype(str)))
    lineage = dict(zip(models["ModelID"], models.get("OncotreeLineage", pd.Series(dtype=str)).astype(str)))
    ex = {norm(e) for e in exclude}
    dropped = []
    for mid, row in expr.iterrows():
        nm = name_of.get(mid, str(mid))
        if norm(nm) in ex:
            dropped.append(nm)
            continue
        tpm = np.expm1(row.to_numpy(dtype=np.float64))
        # n_cells unknown for bulk: NaN (an empty field), which corpus.py keeps under any --min-cells
        col.add(on_axis(tpm, genes), tpm.sum(), source="depmap", context=f"depmap_{nm}", family=f"depmap_{nm}",
                study="depmap_24q4", platform="bulk", kind="bulk", n_cells=np.nan, cell_line=nm,
                tissue=lineage.get(mid, ""))
    return {"excluded_lines": sorted(set(dropped)), "lineages": sorted({str(v) for v in lineage.values()})[:50]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", choices=["ours", "vcc_abc", "depmap"], required=True)
    ap.add_argument("--cells-per-subset", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--exclude-lines", default="K562,HCT116,HEK293T,HEK293,HEKTE,A549,HEPG2,JURKAT,RPE1,HTERTRPE1,KOLF21J")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    col, info = Collector(args.group), {"group": args.group}
    if args.group == "ours":
        group_ours(col)
    elif args.group == "vcc_abc":
        group_vcc(col, args.cells_per_subset, args.seed)
        info["cells_per_subset"] = args.cells_per_subset
    else:
        info.update(group_depmap(col, args.exclude_lines.split(",")))
    col.write(args.out, info)


if __name__ == "__main__":
    main()
