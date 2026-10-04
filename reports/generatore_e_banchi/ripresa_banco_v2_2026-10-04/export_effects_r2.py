"""Export the frozen D-056 C-lane arms for bench v2; no fitting or scoring."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "reports/modelli/ibrido_selettivo_2026-10-04"))
import hybrid_lanes as HL
from arms import AMPLITUDE_T25
from fitting import transfer_for
from common import sha256



def validate_coverage(name, raw, production, targets):
    """Keep genuine production no-transfer rows, identically masked in both paired arms."""
    missing = ~np.isfinite(raw).any(axis=1)
    if missing.any():
        if name not in ("prod", "prod_wR") or np.isfinite(production[missing]).any():
            raise ValueError(f"{name}: unexpected target with no observed genes")
    return [targets[i] for i in np.flatnonzero(missing)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("run", "cube", "protocol", "target-keys", "splits", "anchors-manifest", "weights", "real",
                 "targets", "expected", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--held-group", required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    expected = json.loads(a.expected.read_text(encoding="utf-8"))
    S = HL.Setup(a)
    if S.inputs != expected["inputs"]:
        raise ValueError("D-056 inputs differ from the archived diagnostic run")
    W = HL.load_weights(a.weights)
    with np.load(a.real, allow_pickle=False) as z:
        labs, genes = z["labels"].astype(str), z["genes"].astype(str)
    targets = [t for t in json.loads(a.targets.read_text()) if (labs == t["symbol"]).sum() >= 4]
    names = [t["symbol"] for t in targets]
    keys = [t["target_key"] for t in targets]
    if not names or len(set(names)) != len(names) or len(set(genes)) != len(genes):
        raise ValueError("empty or duplicated target/gene axis")
    cpos = pd.Index(S.cube.genes).get_indexer(genes)
    mpos = pd.Index(S.model_genes).get_indexer(genes)
    if (mpos < 0).any():
        raise ValueError("real genes absent from model")
    gi_of = {(g["key"], g["symbol"]): i for i, g in enumerate(S.groups)}
    gis = [gi_of[(t["key"], t["symbol"])] for t in targets]
    if any(S.groups[i]["class"] != "C" for i in gis):
        raise ValueError("only the frozen C targets may enter this bench")
    R = (S.pred["ibrido"][gis][:, mpos] - S.pred["ancora_sola"][gis][:, mpos]).astype(np.float32)
    w = HL.arm_weights(W, "ibrido", keys)
    effects = {}
    for name, source in (("all", "transfer_all_J"), ("prod", "transfer_prod_J")):
        s, _ = transfer_for(S.cubes[source], keys, S.sources[source], S.commons)
        T = np.full((len(names), len(genes)), np.nan, np.float32)
        have = cpos >= 0
        T[:, have] = (s * AMPLITUDE_T25)[:, cpos[have]]
        effects[name] = T
        effects[name + "_wR"] = HL.hybrid(T, R, w)
        if not np.array_equal(T, HL.hybrid(T, R, 0), equal_nan=True):
            raise ValueError("zero correction changes the baseline")
    S.check_reads()
    a.out.mkdir(parents=True)
    files = {}
    for name, raw in effects.items():
        observed = np.isfinite(raw)
        missing = validate_coverage(name, raw, effects["prod"], names)
        dest = a.out / (name + ".npz")
        np.savez_compressed(dest, targets=np.asarray(names), genes=genes,
                            lfc=np.where(observed, raw, 0).astype(np.float32), observed=observed)
        files[name] = {"baseline_only_targets": missing, "sha256": sha256(dest), "bytes": dest.stat().st_size}
    record = {"held": S.held, "targets": names, "target_keys": keys, "inputs": S.inputs,
              "real_sha256": sha256(a.real), "targets_sha256": sha256(a.targets),
              "weights_sha256": sha256(a.weights), "sources": S.sources, "files": files,
              "zero_correction_parity": True, "leakage_check": "passed"}
    (a.out / "manifest.json").write_text(json.dumps(record, indent=2))
    print(json.dumps({"held": S.held, "targets": len(names), "arms": list(files)}), flush=True)


if __name__ == "__main__":
    main()
