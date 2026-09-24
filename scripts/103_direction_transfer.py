"""Stage 103: how often a transferred effect has the right sign, on the genes it would call.

Written on 2026-09-24 after t14 (CP-0032): with a generator that makes no spurious calls,
the official direction fidelity fell to 0.447 instead of rising. The scorer judges each gene
we call by the sign of its real fold change, so the question is how often the sign of a
transferred effect is right on the genes with the largest predicted effect.

Each stage-98 source in turn plays a new context. The predictor is the recipe mixture of
the others (`vcc2026.multisource.mix`: equal weights, reliability n/(n+100), raw effects,
gamma 0 and 1); the truth is the held-out source's raw effect, not centred, because the
official fold change is taken against real controls. Per target and for each k, the share
of the top-k genes by |prediction| with the same sign as the truth
(`topk_sign_agreement`, target gene excluded). A consensus variant keeps only genes on which
every contributing source has the same sign.

Claim type: measurement in effect space between public sources, not a VCC score. The
official base of the fidelity member (0.5123, `reports/anchors_2026-09-17/anchors.json`)
is reported beside it only as a reference line.

    python scripts/103_direction_transfer.py --cache <stage-98 cache> --out <report dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, mix, topk_sign_agreement  # noqa: E402

DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")
SOURCES = ("k562", "cd4_mix", "orion_hct116", "orion_hek293t")
KS = (25, 50, 100, 200, 500)
FIDELITY_BASE = 0.5123


def load_raw(cache: Path, name: str) -> AxisTable:
    """A stage-98 source with its raw effects where `mix` reads, as stage 100 does."""
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    return AxisTable(name, z["targets"].astype(str).tolist(), z["raw"], z["raw"], z["se"], z["n_cells"],
                     json.loads(str(z["meta"])))


def consensus_mask(tables, target: str, gamma: float, G: int, commons: dict) -> np.ndarray:
    """Genes on which every contributing source has the same non-zero sign (at least two)."""
    signs = []
    for tab in tables:
        j = tab.index().get(target)
        if j is None:
            continue
        row = tab.shrunk[j].astype(np.float64) - gamma * commons[tab.name]
        signs.append(np.where(np.isfinite(row), np.sign(row), np.nan))
    if len(signs) < 2:
        return np.zeros(G, dtype=bool)
    s = np.vstack(signs)
    finite = np.isfinite(s).all(axis=0)
    first = s[0]
    return finite & (first != 0) & (s == first).all(axis=0)


def summarise(values: list[float]) -> dict:
    v = np.asarray(values, dtype=float)
    if v.size == 0:
        return {"targets": 0}
    return {"targets": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
            "share_above_fidelity_base": float((v > FIDELITY_BASE).mean())}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "direction.json").exists():
        raise FileExistsError(args.out / "direction.json")
    args.out.mkdir(parents=True, exist_ok=True)

    axis = list(official_axis().symbols)
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    tables = {n: load_raw(args.cache, n) for n in SOURCES}
    commons = {n: np.nan_to_num(t.common()) for n, t in tables.items()}
    report = {"stage": "103_direction_transfer", "cache": str(args.cache), "sources": list(SOURCES),
              "ks": list(KS), "fidelity_base_reference": FIDELITY_BASE,
              "claim_type": "measurement in effect space between public sources; not a VCC score",
              "held_out": {}}
    for held in SOURCES:
        others = [tables[n] for n in SOURCES if n != held]
        truth_tab = tables[held]
        tidx = truth_tab.index()
        entry = {}
        for gamma in (0.0, 1.0):
            pred, w = mix(others, panel, gamma=gamma, reliability_scale=100.0)
            per_k = {k: [] for k in KS}
            per_k_cons = {k: [] for k in KS}
            pooled = {k: [0, 0] for k in KS}
            for i, t in enumerate(panel):
                j = tidx.get(t)
                if j is None or not (w[i] > 0).any():
                    continue
                truth = truth_tab.raw[j]
                excl = [col[t]] if t in col else []
                row = np.where(w[i] > 0, pred[i], np.nan)
                got = topk_sign_agreement(row, truth, KS, exclude=excl)
                cons = topk_sign_agreement(row, truth, KS, exclude=excl,
                                           keep=consensus_mask(others, t, gamma, len(axis), commons))
                for k in KS:
                    a, n = got[k]
                    if n:
                        per_k[k].append(a / n)
                        pooled[k][0] += a
                        pooled[k][1] += n
                    a, n = cons[k]
                    if n:
                        per_k_cons[k].append(a / n)
            entry[f"gamma_{gamma:g}"] = {
                "predictor": [o.name for o in others],
                "top_k": {k: {**summarise(per_k[k]), "pooled": pooled[k][0] / pooled[k][1] if pooled[k][1] else None}
                          for k in KS},
                "top_k_consensus": {k: summarise(per_k_cons[k]) for k in KS},
            }
            g1 = entry[f"gamma_{gamma:g}"]["top_k"]
            log(f"held out {held:<14} gamma {gamma:g}: " + "  ".join(
                f"k{k} {g1[k].get('median', float('nan')):.3f}" for k in KS))
        report["held_out"][held] = entry
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (args.out / "direction.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    log(f"wrote {args.out / 'direction.json'}")


if __name__ == "__main__":
    main()
