"""Target priors that need no measurement of the target: the CRISPRi cis head and network partners.

Used by stage 100 (the ``cis`` and ``association`` blocks of a recipe) and stage 104 (features of
the learned magnitude channel). Evidence: reports/modulo_cis_2026-09-26/ and
reports/bersagli_nuovi_2026-09-26/.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .predictor_sc import CisModel

__all__ = ["cis_prior", "add_cis", "partner_effects"]


def cis_prior(pairs: pd.DataFrame, panel: list[str]) -> CisModel:
    """`CisModel.from_pairs` on stage 77's neighbour pairs, with every panel target removed."""
    keep = ~pairs["target"].astype(str).isin(set(panel))
    return CisModel.from_pairs(pairs[keep], value="log2fc", log_base=2.0)


def add_cis(eff: np.ndarray, observed: np.ndarray, targets: list[str], axis: np.ndarray, model: CisModel,
            coords: pd.DataFrame, max_distance_bp: int, scale: float) -> dict:
    """Add ``scale`` x the cis prior to each target's neighbours within ``max_distance_bp``, in
    place, and mark those pairs observed. Returns how many pairs and targets it touched."""
    if not 0 < max_distance_bp <= model.edges[-1]:
        raise ValueError(f"max_distance_bp must be in (0, {model.edges[-1]}], got {max_distance_bp}")
    pairs = with_pair = 0
    for i, t in enumerate(targets):
        pos, dist = model.neighbours(t, axis, coords)
        near = dist < max_distance_bp
        if near.any():
            eff[i, pos[near]] += scale * model.prior(dist[near])
            observed[i, pos[near]] = True
            pairs += int(near.sum())
            with_pair += 1
    return {"pairs": pairs, "targets_with_a_neighbour": with_pair}


def partner_effects(targets: list[str], universe: Path, links: Path, info: Path, min_score: int,
                    axis: np.ndarray, exclude: frozenset = frozenset()) -> tuple[dict, dict]:
    """{target: centred mean universe effect of its STRING partners} for ``targets`` that have one.

    ``universe`` holds stage-98-format npz chunks and an ``index.csv``; the effects are the chunks'
    ``shrunk`` arrays on the official axis (unmeasured genes count as 0), centred on the mean over
    every universe target. A target is never its own partner, and a partner's own gene is left out
    of its contribution: its knockdown of itself is not a response to the target. ``exclude`` names
    targets whose outcomes must not be used at all, as partners or in the centre (a bench's
    held-out targets); production leaves it empty."""
    axis_pos = {g: i for i, g in enumerate(np.asarray(axis).astype(str))}
    n_genes = len(axis_pos)
    def gz(path: Path):   # the STRING files of 14 September are gzip without the extension
        with open(path, "rb") as fh:
            return "gzip" if fh.read(2) == b"\x1f\x8b" else None

    names = pd.read_csv(info, sep="\t", usecols=[0, 1], compression=gz(info))
    sym = dict(zip(names.iloc[:, 0], names.iloc[:, 1]))
    edges = pd.read_csv(links, sep=" ", compression=gz(links))
    edges = edges[edges["combined_score"] >= min_score]
    pairs = pd.DataFrame({"a": edges["protein1"].map(sym), "b": edges["protein2"].map(sym)}).dropna()
    pairs = pairs[pairs["a"].isin(set(targets)) & (pairs["a"] != pairs["b"])]
    index = pd.read_csv(universe / "index.csv")
    in_universe = set(index["target"].astype(str)) - set(exclude)
    partners = {t: sorted(set(g) & in_universe) for t, g in pairs.groupby("a")["b"]}
    partners = {t: g for t, g in partners.items() if g}
    need = {g for gs in partners.values() for g in gs}
    rows, total, count = {}, np.zeros(n_genes), 0
    for chunk in sorted(index["chunk"].unique()):
        z = np.load(universe / chunk, allow_pickle=False)
        names_z = z["targets"].astype(str)
        eff = np.nan_to_num(z["shrunk"]).astype(np.float64)[~np.isin(names_z, list(exclude))]
        names_z = names_z[~np.isin(names_z, list(exclude))]
        total += eff.sum(axis=0)
        count += eff.shape[0]
        for i, name in enumerate(names_z):
            if name in need:
                rows[name] = eff[i]
    centre = total / max(count, 1)
    out = {}
    for t, gs in partners.items():
        # a partner's own knockdown is not a response to t: its own gene is left out of the mean
        s, n = np.zeros(n_genes), np.zeros(n_genes)
        for g in gs:
            use = np.ones(n_genes, dtype=bool)
            if g in axis_pos:
                use[axis_pos[g]] = False
            s[use] += rows[g][use]
            n[use] += 1
        out[t] = (np.divide(s, n, out=np.zeros(n_genes), where=n > 0) - centre).astype(np.float32)
    return out, {"targets_with_partners": len(out), "universe_targets": count,
                 "partners_used": int(sum(len(g) for g in partners.values()))}
