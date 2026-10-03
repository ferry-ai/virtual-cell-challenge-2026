"""Effects of the source-attention network for the competition contexts, in the stage-45 layout (M4 candidate).

For each context (A, B, C now; D, E, F on 22 October) the line L has no perturbed cells, only controls:
* its basal profile is computed exactly as `dati.py` does for a key: log1p(1e4 x the controls' pooled fraction), on the
  official axis;
* its sources are the network's training keys (``split.json``), the configuration the real-scorer vote measured;
  ``--sources all`` adds the validation and test keys too, which no vote has measured;
* the amplitude rule (norm-match) is applied once over the context's covered targets, as `rete.export_effects` does.

Writes ``effects_<CTX>.npz`` with ``targets`` (every target of ``--targets-csv``, in its order), ``genes`` (the axis),
``lfc`` (ln fold change, float32) and ``observed`` (a gene some source measures for that target). A target no source
covers gets lfc 0 and observed False on every gene; how many is written in ``export_abc.json``. The controls and the
target list are private competition data: the outputs go to the data root, never into the repository.

    python esporta_abc.py --keys <chiavi> --run <rete run> --controls <dir with context_X.h5ad> \\
        --targets-csv <pert_counts.csv> --axis <gene_names.csv> --out <data root>/processed/effects_t30_<date>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import rete


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def read_axis(path: Path) -> np.ndarray:
    axis = pd.read_csv(path, header=None).iloc[:, 0].astype(str).to_numpy().astype(str)   # unicode, never object:
    return axis[1:] if axis[0].lower() in ("gene", "gene_name", "genes", "symbol") else axis  # stage 45 loads no pickles


def read_targets(path: Path) -> list[str]:
    df = pd.read_csv(path)
    col = "target_gene" if "target_gene" in df.columns else df.columns[0]
    return df[col].astype(str).tolist()


def context_key(controls: Path, axis: np.ndarray, ctx: str) -> rete.Key:
    """The context as a key with no targets: basal from the pooled control counts on the official axis."""
    import anndata as ad
    import scipy.sparse as sp

    a = ad.read_h5ad(controls)
    pos = pd.Index(a.var_names.astype(str)).get_indexer(axis)
    if (pos < 0).any():
        raise SystemExit(f"{controls}: {(pos < 0).sum()} axis genes missing from the controls")
    X = a.X
    col = np.asarray(X.sum(axis=0)).ravel() if sp.issparse(X) else X.sum(axis=0)
    counts = np.asarray(col, np.float64)[pos]
    G = axis.size
    basal = np.log1p(1e4 * counts / counts.sum()).astype(np.float32)
    return rete.Key(f"vcc2026_context|{ctx}", f"context_{ctx}", "unknown", np.array([], str),
                    np.zeros((0, G), np.float16), basal, np.ones(G, bool))


def export_context(model, L: rete.Key, sources: list[rete.Key], targets: list[str], chunk: int = 50) -> dict:
    """lfc and observed for every target; the amplitude rule over the covered targets only."""
    G = L.basal.size
    genes = np.arange(G)
    covered = [t for t in targets if any(t in k.row for k in sources)]
    lfc = np.zeros((len(targets), G), np.float32)
    observed = np.zeros((len(targets), G), bool)
    if not covered:
        return {"lfc": lfc, "observed": observed, "covered": 0, "A0": None, "amplitude": None}
    full = rete.episode(L, sources, None, 0, 0, targets=covered, genes=genes)
    A0 = full["A0"]
    del full
    row = {t: i for i, t in enumerate(targets)}
    amp = None
    with torch.no_grad():
        for i in range(0, len(covered), chunk):
            part = covered[i:i + chunk]
            ep = rete.episode(L, sources, None, 0, 0, targets=part, genes=genes)
            t = rete.to_t(ep)
            y, _, A = model(t["E"], t["avail"], t["basal_L"], t["basal_S"], t["genes"], A0, t["prior"])
            amp = float(A)
            idx = [row[x] for x in part]
            lfc[idx] = y.numpy().astype(np.float32)
            observed[idx] = ep["avail"].any(0)
    return {"lfc": lfc, "observed": observed, "covered": len(covered), "A0": float(A0), "amplitude": amp}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--keys", type=Path, required=True, help="the chiavi/ folder dati.py wrote")
    p.add_argument("--run", type=Path, required=True, help="the training folder (split.json, norm.npz, checkpoints)")
    p.add_argument("--checkpoint", default="ckpt_best.pt")
    p.add_argument("--controls", type=Path, required=True, help="folder holding context_<CTX>.h5ad")
    p.add_argument("--contexts", nargs="+", default=["A", "B", "C"])
    p.add_argument("--targets-csv", type=Path, required=True)
    p.add_argument("--axis", type=Path, required=True)
    p.add_argument("--sources", choices=["train", "all"], default="train")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    if any(a.out.glob("effects_*.npz")):
        raise SystemExit(f"{a.out} already holds effects; choose a new --out")
    axis, targets = read_axis(a.axis), read_targets(a.targets_csv)
    keys = rete.load_keys(a.keys)
    split = json.loads((a.run / "split.json").read_text())
    cfg = rete.Config(**{k: (tuple(v) if k == "keep_steps" else v) for k, v in split["config"].items()})
    pool = [k for k in keys if k.key in set(split["train"])] if a.sources == "train" else keys
    nz = np.load(a.run / "norm.npz")
    if int(nz["n_genes"]) != axis.size:
        raise SystemExit(f"the run has {int(nz['n_genes'])} genes, the axis {axis.size}")
    model = rete.SourceAttention(int(nz["n_genes"]), nz["panel"], nz["mu"], nz["sd"], cfg)
    model.load_state_dict(torch.load(a.run / a.checkpoint))
    model.eval()

    report = {"created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "checkpoint": a.checkpoint,
              "checkpoint_sha256": sha256(a.run / a.checkpoint), "sources_mode": a.sources,
              "sources": sorted(k.key for k in pool), "targets": len(targets), "axis_genes": int(axis.size),
              "contexts": {}}
    for ctx in a.contexts:
        controls = a.controls / f"context_{ctx}.h5ad"
        L = context_key(controls, axis, ctx)
        sources = rete.allowed_sources(L, pool)
        res = export_context(model, L, sources, targets)
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=np.asarray(axis, dtype=str),
                            lfc=res["lfc"], observed=res["observed"])
        obs = res["observed"]
        report["contexts"][ctx] = {
            "controls_sha256": sha256(controls), "sources": len(sources), "targets_covered": res["covered"],
            "targets_fallback_zero": len(targets) - res["covered"], "A0": res["A0"], "amplitude": res["amplitude"],
            "genes_observed_any": int(obs.any(0).sum()), "observed_share": float(obs.mean()),
            "lfc_abs_mean_observed": float(np.abs(res["lfc"][obs]).mean()) if obs.any() else None,
            "file": path.name, "sha256": sha256(path)}
        rete.log(f"{ctx}: {res['covered']}/{len(targets)} targets covered, amplitude {res['amplitude']}")
    (a.out / "export_abc.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
