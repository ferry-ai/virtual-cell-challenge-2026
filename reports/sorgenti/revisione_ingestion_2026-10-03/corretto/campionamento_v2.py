"""Outcome-blind cell samples, version 2: the Orion design made explicit, tranches that never discard, CD4 checks.

Version 1 (`archivio_cloud_2026-10-02/campionamento.py`) is untouched. Its Orion code takes, per (line, target), the
first k cells by hash rank over all GEM files; its prose says "allocated across GEM files in proportion". These are
two designs with the same first-order inclusion probability and different joint behaviour, so here each has a name
and the manifest records which one was used:

  srs_line_target    v1's code: a simple random sample without replacement of the pooled stratum (line, target).
                     pi = min(1, k/n). Cells per GEM file are hypergeometric: proportional only in expectation.
  proportional_gem   stratified by GEM file with proportional allocation. Inside (line, target, GEM) cells are
                     ordered by hash rank; the cell at position p of the n_g cells gets the score (p + v_g) / n_g,
                     v_g in [0, 1) a hash of (salt, line, target, GEM); it is selected when score < k/n. Each score
                     is uniform, so pi = min(1, k/n) exactly, and a GEM file gives floor or ceil of its share
                     k*n_g/n. The number selected per target is random around k (never a fixed total).

Both are nested in k: a larger k keeps every cell already selected, so k is a tranche size, not a decision to
discard the rest. `window=(k0, k1)` selects the tranche between two sizes with pi = (min(k1,n) - min(k0,n)) / n.
Selection reads only identity and guide columns; no count or depth column is used. Controls: all, pi = 1, in the
first tranche. Excluded cells stay in the table with pi = 0 and a reason.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

DESIGNS = ("srs_line_target", "proportional_gem")


def _u64(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def rank(salt: str, tag: str, cells) -> np.ndarray:
    """sha256(salt:tag:cell) as uint64: the rank of version 1, so equal salts give equal orders."""
    return np.array([_u64(f"{salt}:{tag}:{c}") for c in cells], dtype=np.uint64)


def _window(window, k):
    k0, k1 = (0, k) if window is None else window
    if not 0 <= k0 < k1:
        raise ValueError("window must be 0 <= k0 < k1")
    return int(k0), int(k1)


def _pi(n, k0, k1):
    n = np.asarray(n, dtype=np.int64)
    return (np.minimum(k1, n) - np.minimum(k0, n)) / np.maximum(n, 1)


def select_orion(obs: pd.DataFrame, line: str, salt: str, k: int, design: str, window=None) -> pd.DataFrame:
    """One row per cell of a line. `obs`: index = cell id unique in the line, columns gem_file, target,
    pass_guide_filter, is_control."""
    if design not in DESIGNS:
        raise ValueError(f"design must be one of {DESIGNS}")
    need = {"gem_file", "target", "pass_guide_filter", "is_control"}
    if need - set(obs.columns):
        raise ValueError(f"obs lacks {sorted(need - set(obs.columns))}")
    if not obs.index.is_unique:
        raise ValueError("cell ids are not unique in the line")
    k0, k1 = _window(window, k)
    t = pd.DataFrame({"cell": obs.index.astype(str), "line": line, "gem_file": obs["gem_file"].astype(str).values,
                      "target": obs["target"].astype(str).values})
    ok = (obs["pass_guide_filter"] == 1).to_numpy()
    ctl = obs["is_control"].astype(bool).to_numpy()
    t["role"] = np.where(~ok, "excluded", np.where(ctl, "control", "targeted"))
    t["reason"] = np.where(~ok, "pass_guide_filter != 1", "")
    t["rank"] = rank(salt, line, t["cell"])
    tg = t[t["role"] == "targeted"].sort_values(["target", "gem_file", "rank", "cell"], kind="mergesort").copy()
    tg["n_stratum"] = tg.groupby("target")["cell"].transform("size").astype(np.int64)
    if design == "srs_line_target":
        tg = tg.sort_values(["target", "rank", "cell"], kind="mergesort")
        pos = tg.groupby("target").cumcount().to_numpy()
        tg["n_gem"] = tg.groupby(["target", "gem_file"])["cell"].transform("size").astype(np.int64)
        tg["selected"] = (pos >= k0) & (pos < k1)
    else:
        tg["n_gem"] = tg.groupby(["target", "gem_file"])["cell"].transform("size").astype(np.int64)
        pos = tg.groupby(["target", "gem_file"]).cumcount().to_numpy(dtype=np.int64)
        pairs = tg[["target", "gem_file"]].drop_duplicates()
        v = {(a, b): _u64(f"{salt}:gem:{line}:{a}:{b}") >> 32 for a, b in zip(pairs["target"], pairs["gem_file"])}
        v32 = np.array([v[(a, b)] for a, b in zip(tg["target"], tg["gem_file"])], dtype=np.int64)
        n, ng = tg["n_stratum"].to_numpy(), tg["n_gem"].to_numpy()
        if len(tg) and int(pos.max() + 1) * int(n.max()) >= 2 ** 31:
            raise OverflowError("stratum too large for the exact integer comparison")
        lhs = (pos * 2 ** 32 + v32) * n                    # (p + v) / n_g < k / n  <=>  (p*2^32 + v32)*n < k*n_g*2^32
        hi = np.minimum(k1, n) * ng * 2 ** 32
        lo = np.minimum(k0, n) * ng * 2 ** 32
        tg["selected"] = (lhs >= lo) & (lhs < hi)
    tg["pi"] = _pi(tg["n_stratum"], k0, k1)
    c = t[t["role"] == "control"].copy()
    c["n_stratum"] = c.groupby("gem_file")["cell"].transform("size").astype(np.int64)
    c["n_gem"] = c["n_stratum"]
    c["selected"], c["pi"] = k0 == 0, float(k0 == 0)
    e = t[t["role"] == "excluded"].copy()
    e["n_stratum"], e["n_gem"], e["selected"], e["pi"] = 0, 0, False, 0.0
    out = pd.concat([c, tg, e]).sort_values("cell", kind="mergesort").reset_index(drop=True)
    out["design"] = design
    return out


def cd4_crosstab(obs: pd.DataFrame) -> dict:
    """Counts of guide_group x guide_type x (gene id class), the intersection the sample relies on."""
    g = obs["guide_group"].astype("string").fillna("<NA>")
    y = obs["guide_type"].astype("string").fillna("<NA>")
    gene = obs["perturbed_gene_id"].astype("string").fillna("<NA>")
    cls = np.where(gene == "NTC", "NTC", np.where(gene == "<NA>", "<NA>", "gene"))
    tab = pd.DataFrame({"g": g.values, "y": y.values, "c": cls}).value_counts()
    return {"|".join(k): int(v) for k, v in tab.items()}


def check_cd4_crosstab(tab: dict) -> list[str]:
    """Problems of the intersection, empty when it is the one the eligibility rule assumes: the group 'targeting
    single sgRNA' holds the targeting cells AND the single-guide non-targeting controls, and nothing else; 'no sgRNA'
    has no type and no gene; 'multi sgRNA' has no gene. The marginals of 30/09 are compatible with this in all twelve
    files, but they do not prove it: the cross-tabulation does."""
    allowed = {"targeting single sgRNA|targeting|gene", "targeting single sgRNA|non-targeting|NTC",
               "no sgRNA|<NA>|<NA>", "multi sgRNA|targeting|<NA>"}
    bad = [f"unexpected cells {k}: {v}" for k, v in sorted(tab.items()) if k not in allowed and v]
    if not tab.get("targeting single sgRNA|non-targeting|NTC"):
        bad.append("no single-guide non-targeting control in 'targeting single sgRNA'")
    return bad


def summary(sample: pd.DataFrame) -> dict:
    by = sample.groupby(["role", "reason"]).agg(cells=("cell", "size"), selected=("selected", "sum"))
    tg = sample[sample["role"] == "targeted"]
    per_target = tg.groupby("target")["selected"].sum() if len(tg) else pd.Series(dtype=float)
    return {"cells": int(len(sample)), "selected": int(sample["selected"].sum()),
            "by_role": {f"{r}|{w}": {"cells": int(v.cells), "selected": int(v.selected)} for (r, w), v in by.iterrows()},
            "targets": int(tg["target"].nunique()),
            "selected_per_target": {"min": float(per_target.min()) if len(per_target) else 0.0,
                                    "median": float(per_target.median()) if len(per_target) else 0.0,
                                    "max": float(per_target.max()) if len(per_target) else 0.0},
            "expected_selected_targeted": float(tg["pi"].sum())}
