"""H6 on Mixscale: does basal similarity between two cell lines predict how well effects transfer?

Today every source weighs the same in every context; the final set brings three new lines. If
knockdown effects transfer better between lines whose unperturbed transcriptomes are alike, the
sources should be weighted per context by similarity (H6, reports/ipotesi_trasferimento_2026-09-24).
Mixscale (Jiang et al. 2025, zenodo 14518762; local DE archive, md5 checked as in
reports/dld1_audit_2026-09-24/analyze_mixscale.py) has the same ~218 targets in six lines (A549,
BXPC3, HAP1, HT29, K562, MCF7) under five stimuli: a clean place to test it.

1. Transfer between two lines: for each stimulus and ordered pair (source s, line c), the PDS
   proxy of predicting c's log2FC rows from s's rows (cosine, rank of the true target among the
   stimulus' targets, mid-rank ties, genes finite in both, panel targets and screened targets
   removed as readouts as in the original analysis); averaged over stimuli; symmetrised.
2. Basal similarity: Spearman correlation of the two lines' DepMap 24Q4 expression
   (OmicsExpressionProteinCodingGenesTPMLogp1, rows read in chunks), on genes with log1p TPM > 1
   in at least one of the six lines, and on the 2,000 most variable of those.
3. Mantel test: Spearman between the 15 similarities and the 15 transfer values, exact
   permutation of the six line labels (720 permutations).
4. Weighting: for each held-out line c, the prediction is the weighted mean of the five other
   lines' rows, weights proportional to exp(beta * z), z the similarity standardised over the
   five; beta = 0 is equal weights. PDS proxy per held-out line and stimulus, beta 0-8.
Effect-space proxies on another assay (CRISPR knockout, pathway panels), not VCC scores.

    scripts/py.cmd reports/contesti_2026-09-26/h6_mixscale.py --out reports/contesti_2026-09-26/r1
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vcc2026.config import paths  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402

LINES = ["A549", "BXPC3", "HAP1", "HT29", "K562", "MCF7"]
DEPMAP_NAMES = {"A549": "A549", "BXPC3": "BXPC3", "HAP1": "HAP1", "HT29": "HT29", "K562": "K562", "MCF7": "MCF7"}
BETAS = (0.0, 1.0, 2.0, 4.0, 8.0)


def pds(pred: np.ndarray, truth: np.ndarray) -> float:
    """Mean over targets of 1 - rank/(n-1) of the true target by cosine; mid-rank ties."""
    na = np.linalg.norm(pred, axis=1)
    nb = np.linalg.norm(truth, axis=1)
    cos = (pred @ truth.T) / np.maximum(np.outer(na, nb), 1e-12)
    d = np.diag(cos)
    n = cos.shape[0]
    greater = (cos > d[:, None]).sum(axis=1)
    ties = (cos == d[:, None]).sum(axis=1) - 1
    return float(np.mean(1.0 - (greater + 0.5 * ties) / max(n - 1, 1)))


def load_mixscale(archive: Path) -> dict:
    """{stimulus: (targets, genes, arr[target, line, gene])}, genes as analyze_mixscale.py keeps them."""
    root = paths().data_root
    official = set(official_axis().symbols)
    panel = set(pd.read_csv(root / "raw/controls/pert_counts.csv").iloc[:, 0])
    cols = ["log2FC_" + c for c in LINES]
    out = {}
    with zipfile.ZipFile(archive) as z:
        files = []
        for name in z.namelist():
            m = re.fullmatch(r"(.+)_(IFNB|IFNG|INS|TGFB1|TNFA)_pathway_DE_results.txt", Path(name).name)
            if m and not name.startswith("__MACOSX/"):
                files.append((name, m[1], m[2]))
        excluded = panel | {t for _, t, _ in files}
        for stim in sorted({s for _, _, s in files}):
            frames, targets = [], []
            for name, target, s in files:
                if s != stim:
                    continue
                with z.open(name) as f:
                    df = pd.read_csv(f, sep=r"\s+").set_index("gene_ID")[cols]
                frames.append(df)
                targets.append(target)
            genes = sorted(set().union(*(set(f.index) for f in frames)) & official - excluded)
            arr = np.stack([f.reindex(genes).to_numpy(float).T for f in frames])
            out[stim] = (targets, genes, arr)
    return out


def depmap_similarity(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    models = pd.read_csv(folder / "Model.csv", usecols=["ModelID", "StrippedCellLineName"])
    ids = {}
    for line, name in DEPMAP_NAMES.items():
        hit = models.loc[models["StrippedCellLineName"].str.upper() == name, "ModelID"].tolist()
        if len(hit) != 1:
            raise SystemExit(f"{line}: {len(hit)} DepMap models named {name}")
        ids[line] = hit[0]
    want = set(ids.values())
    rows = []
    for chunk in pd.read_csv(folder / "OmicsExpressionProteinCodingGenesTPMLogp1.csv", chunksize=64, index_col=0):
        keep = chunk.loc[chunk.index.isin(want)]
        if len(keep):
            rows.append(keep)
    expr = pd.concat(rows)
    expr = expr.loc[[ids[l] for l in LINES]]
    expr.index = LINES
    expressed = expr.columns[(expr > 1.0).any(axis=0)]
    var = expr[expressed].var(axis=0).sort_values(ascending=False)
    sims = {}
    for label, genes in (("expressed", expressed), ("top2000_variable", var.index[:2000])):
        sims[label] = expr[genes].T.rank().corr(method="pearson")      # Spearman = Pearson of ranks
    return sims["expressed"], sims["top2000_variable"], {"model_ids": ids, "genes_expressed": int(len(expressed))}


def main() -> None:
    root = paths().data_root
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", type=Path, default=root / "external/mixscale_zenodo14518762/DE_results_all_pathway.zip")
    ap.add_argument("--depmap", type=Path, default=root / "external/depmap_24q4")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with args.archive.open("rb") as f:
        md5 = hashlib.file_digest(f, "md5").hexdigest()
    if md5 != "f077cba680a1affc599f5153d99b0e45":
        raise SystemExit("unexpected Mixscale archive checksum")
    data = load_mixscale(args.archive)
    sim_expr, sim_var, info = depmap_similarity(args.depmap)
    print(sim_expr.round(3).to_string(), flush=True)

    # 1. pairwise transfer, averaged over stimuli
    T = pd.DataFrame(np.nan, index=LINES, columns=LINES)
    per_stim = []
    for s_i, c_i in itertools.permutations(range(6), 2):
        vals = []
        for stim, (targets, genes, arr) in data.items():
            ok = np.isfinite(arr[:, s_i, :]).all(axis=0) & np.isfinite(arr[:, c_i, :]).all(axis=0)
            if ok.sum() < 100:
                continue
            v = pds(arr[:, s_i, ok], arr[:, c_i, ok])
            vals.append(v)
            per_stim.append({"source": LINES[s_i], "line": LINES[c_i], "stimulus": stim, "targets": len(targets),
                             "genes": int(ok.sum()), "pds": v})
        T.iloc[s_i, c_i] = float(np.mean(vals))
    pairs = list(itertools.combinations(range(6), 2))
    tsym = np.array([(T.iloc[a, b] + T.iloc[b, a]) / 2 for a, b in pairs])

    # 3. Mantel: exact permutation of line labels
    def spearman(x, y):
        return float(pd.Series(x).rank().corr(pd.Series(y).rank()))
    mantel = {}
    for label, S in (("expressed", sim_expr), ("top2000_variable", sim_var)):
        s = np.array([S.iloc[a, b] for a, b in pairs])
        obs = spearman(s, tsym)
        null = []
        for perm in itertools.permutations(range(6)):
            sp = np.array([S.iloc[perm[a], perm[b]] for a, b in pairs])
            null.append(spearman(sp, tsym))
        null = np.array(null)
        mantel[label] = {"spearman": obs, "p_one_sided": float((null >= obs - 1e-12).mean()), "permutations": len(null)}
    print(mantel, flush=True)

    # 4. similarity-weighted pooling per held-out line
    wrows = []
    for c_i in range(6):
        src = [i for i in range(6) if i != c_i]
        z = np.array([sim_expr.iloc[i, c_i] for i in src])
        z = (z - z.mean()) / (z.std() + 1e-12)
        for beta in BETAS:
            w = np.exp(beta * z)
            w /= w.sum()
            vals = []
            for stim, (targets, genes, arr) in data.items():
                ok = np.isfinite(arr[:, src + [c_i], :]).all(axis=(0, 1))
                if ok.sum() < 100:
                    continue
                pred = np.tensordot(w, arr[:, src, :][:, :, ok], axes=([0], [1]))
                vals.append(pds(pred, arr[:, c_i, ok]))
            wrows.append({"line": LINES[c_i], "beta": beta, "pds": float(np.mean(vals)),
                          "weights": {LINES[i]: round(float(x), 3) for i, x in zip(src, w)}})
    W = pd.DataFrame(wrows)
    T.to_csv(args.out / "transfer_pds.csv")
    sim_expr.to_csv(args.out / "similarity_expressed.csv")
    sim_var.to_csv(args.out / "similarity_top2000.csv")
    pd.DataFrame(per_stim).to_csv(args.out / "transfer_per_stimulus.csv", index=False)
    W.to_csv(args.out / "weighting.csv", index=False)
    with (args.out / "measurements.json").open("x", encoding="utf-8") as f:
        json.dump({"stage": "contesti_2026-09-26/h6_mixscale.py", "archive_md5": md5, "depmap": info,
                   "claim_type": "effect-space proxies on Mixscale (CRISPR knockout, pathway panels); not VCC scores",
                   "mantel": mantel, "pairs": [{"a": LINES[a], "b": LINES[b], "transfer_sym": float(t),
                                                "sim_expressed": float(sim_expr.iloc[a, b]),
                                                "sim_top2000": float(sim_var.iloc[a, b])}
                                               for (a, b), t in zip(pairs, tsym)],
                   "weighting": wrows}, f, indent=1)
    pd.set_option("display.width", 200)
    print(T.round(3).to_string())
    print(W.pivot(index="line", columns="beta", values="pds").round(4).to_string())


if __name__ == "__main__":
    main()
