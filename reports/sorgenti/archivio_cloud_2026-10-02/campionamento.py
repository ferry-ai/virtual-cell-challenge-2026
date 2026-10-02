"""Explicit, outcome-blind cell samples for CD4 (Marson 2025) and Orion (X-Atlas), with inclusion probabilities.

The sample is decided from metadata only, before any count is read: eligibility from the guide columns, then a
deterministic rank sha256(salt:file:cell) inside each stratum. Every cell gets a role, a reason, the size of its
stratum and its inclusion probability pi; excluded cells stay in the table with pi = 0, so what was left out is
counted, never silent. Count columns are not read: selection cannot depend on outcomes.

CD4 (one row of obs per cell of one `D<n>_<condition>.assigned_guide.h5ad`; columns measured remotely on 30/09):
  excluded       low_quality, "no sgRNA", "multi sgRNA"
  control        guide_group == "targeting single sgRNA" and guide_type == "non-targeting": all, pi = 1
  targeted       single sgRNA and guide_type == "targeting": per (file, guide_id) the first k by rank,
                 pi = min(1, k / n)
Orion (one row per cell with its GEM file and target):
  excluded       pass_guide_filter != 1
  control        non-targeting: all, pi = 1
  targeted       per (line, target) the first k by rank over all GEM files (simple random sample without
                 replacement), pi = min(1, k / n); the GEM file stays on every row

    py -3 campionamento.py cd4 --obs <obs.parquet> --file D1_Rest --salt <salt> --k 10 --out <sample.parquet>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _rank(salt: str, tag: str, cells: pd.Series) -> np.ndarray:
    return np.array([int.from_bytes(hashlib.sha256(f"{salt}:{tag}:{c}".encode()).digest()[:8], "big") for c in cells],
                    dtype=np.uint64)


def _take_first_k(df: pd.DataFrame, key: list[str], k: int) -> pd.DataFrame:
    df = df.sort_values(key + ["rank", "cell"], kind="mergesort")
    df["n_stratum"] = df.groupby(key, observed=True)["cell"].transform("size")
    df["pos"] = df.groupby(key, observed=True).cumcount()
    df["selected"] = df["pos"] < k
    df["pi"] = np.minimum(1.0, k / df["n_stratum"])
    return df.drop(columns="pos")


def select_cd4(obs: pd.DataFrame, file_tag: str, salt: str, k: int) -> pd.DataFrame:
    need = {"guide_group", "guide_type", "guide_id", "lane_id", "low_quality", "perturbed_gene_id"}
    missing = need - set(obs.columns)
    if missing:
        raise ValueError(f"obs lacks {sorted(missing)}")
    t = pd.DataFrame({"cell": obs.index.astype(str), "file": file_tag, "lane_id": obs["lane_id"].astype(str).values,
                      "guide_id": obs["guide_id"].astype("string").fillna("<NA>").values,
                      "target": obs["perturbed_gene_id"].astype("string").fillna("<NA>").values})
    low = obs["low_quality"].fillna(True).astype(bool).values
    single = (obs["guide_group"].astype("string") == "targeting single sgRNA").fillna(False).values
    gtype = obs["guide_type"].astype("string").fillna("<NA>").values
    t["role"] = np.where(low, "excluded", np.where(~single, "excluded",
                         np.where(gtype == "non-targeting", "control", np.where(gtype == "targeting", "targeted", "excluded"))))
    t["reason"] = np.where(low, "low_quality", np.where(~single, obs["guide_group"].astype(str).values,
                           np.where(np.isin(gtype, ["non-targeting", "targeting"]), "", "guide_type " + gtype.astype(str))))
    t["rank"] = _rank(salt, file_tag, t["cell"])
    tg = _take_first_k(t[t["role"] == "targeted"].copy(), ["file", "guide_id"], k)
    ctl = t[t["role"] == "control"].copy()
    ctl["n_stratum"] = ctl.groupby(["file", "lane_id"])["cell"].transform("size")
    ctl["selected"], ctl["pi"] = True, 1.0
    exc = t[t["role"] == "excluded"].copy()
    exc["n_stratum"], exc["selected"], exc["pi"] = 0, False, 0.0
    return pd.concat([ctl, tg, exc]).sort_values("cell", kind="mergesort").reset_index(drop=True)


def select_orion(obs: pd.DataFrame, line: str, salt: str, k: int) -> pd.DataFrame:
    need = {"gem_file", "target", "pass_guide_filter", "is_control"}
    missing = need - set(obs.columns)
    if missing:
        raise ValueError(f"obs lacks {sorted(missing)}")
    t = pd.DataFrame({"cell": obs.index.astype(str), "line": line, "gem_file": obs["gem_file"].astype(str).values,
                      "target": obs["target"].astype(str).values})
    ok = (obs["pass_guide_filter"] == 1).values
    ctl = obs["is_control"].astype(bool).values
    t["role"] = np.where(~ok, "excluded", np.where(ctl, "control", "targeted"))
    t["reason"] = np.where(~ok, "pass_guide_filter != 1", "")
    t["rank"] = _rank(salt, line, t["cell"])
    tg = _take_first_k(t[t["role"] == "targeted"].copy(), ["line", "target"], k)
    c = t[t["role"] == "control"].copy()
    c["n_stratum"] = c.groupby(["line", "gem_file"])["cell"].transform("size")
    c["selected"], c["pi"] = True, 1.0
    e = t[t["role"] == "excluded"].copy()
    e["n_stratum"], e["selected"], e["pi"] = 0, False, 0.0
    return pd.concat([c, tg, e]).sort_values("cell", kind="mergesort").reset_index(drop=True)


def summary(sample: pd.DataFrame) -> dict:
    by = sample.groupby(["role", "reason"], dropna=False).agg(cells=("cell", "size"), selected=("selected", "sum"))
    return {"cells": int(len(sample)), "selected": int(sample["selected"].sum()),
            "by_role": {f"{r}|{why}": {"cells": int(v.cells), "selected": int(v.selected)} for (r, why), v in by.iterrows()},
            "targeted_strata": int(sample.loc[sample["role"] == "targeted"].groupby(
                [c for c in ("file", "line") if c in sample.columns] + (["guide_id"] if "guide_id" in sample.columns else ["target"])).ngroups)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=["cd4", "orion"])
    p.add_argument("--obs", required=True, type=Path, help="parquet or csv of the metadata, one row per cell")
    p.add_argument("--file", help="CD4 file tag, e.g. D1_Rest")
    p.add_argument("--line", help="Orion line, e.g. HCT116")
    p.add_argument("--salt", required=True)
    p.add_argument("--k", required=True, type=int)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    obs = pd.read_parquet(a.obs) if a.obs.suffix == ".parquet" else pd.read_csv(a.obs, index_col=0)
    s = select_cd4(obs, a.file, a.salt, a.k) if a.kind == "cd4" else select_orion(obs, a.line, a.salt, a.k)
    s.to_parquet(a.out, index=False)
    digest = hashlib.sha256(a.out.read_bytes()).hexdigest()
    a.out.with_suffix(".json").write_text(json.dumps({"sample": a.out.name, "sha256": digest, "salt": a.salt, "k": a.k,
                                                      "kind": a.kind, **summary(s)}, indent=1), encoding="utf-8")
    print(digest)


if __name__ == "__main__":
    main()
