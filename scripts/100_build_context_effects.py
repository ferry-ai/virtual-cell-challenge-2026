"""Stage 100: per-context panel effects for stage 76, from a written recipe over stage-98 sources.

A recipe is a JSON file fixed BEFORE generation:

    {"name": "t08", "gamma": 0.5, "reliability_scale": 100,
     "contexts": {"A": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 2}},
                  "B": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 1}},
                  "C": {...}},
     "why": "free text: the evidence the weights come from"}

For each context this writes ``effects_<CTX>.npz`` with ``targets``, ``genes`` (the official
axis) and ``lfc`` (ln fold change, amplitude applied), the format stage 76 reads through
``--effects CTX=PATH``. A (target, gene) pair no source measured stays exactly 0 and is
counted as such in the manifest; a target no source covers is refused unless
``allow_missing_targets`` is true in the recipe (stage 76 would refuse it anyway).

    python scripts/100_build_context_effects.py --recipe configs/recipes/t08.json \
        --cache <stage-98 cache> --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable, mix  # noqa: E402

DATA_ROOT = Path("C:/Users/ferra/vcc2026-data")


def load_table(cache: Path, name: str) -> AxisTable:
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    return AxisTable(name, z["targets"].astype(str).tolist(), z["shrunk"], z["raw"], z["se"], z["n_cells"],
                     json.loads(str(z["meta"])))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recipe", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if (args.out / "manifest.json").exists():
        raise FileExistsError(f"{args.out} already holds effects; choose a new --out")
    args.out.mkdir(parents=True, exist_ok=True)
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    axis = np.asarray(official_axis().symbols)
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    gamma = float(recipe.get("gamma", 0.0))
    scale = float(recipe.get("reliability_scale", 100.0))
    names = sorted({s for c in recipe["contexts"].values() for s in c["weights"]})
    tables = [load_table(args.cache, n) for n in names]
    summary = {}
    for ctx, spec in recipe["contexts"].items():
        weights = {k: float(v) for k, v in spec["weights"].items()}
        eff, w = mix([t for t in tables if weights.get(t.name, 0) > 0], panel, weights=weights,
                     gamma=gamma, reliability_scale=scale)
        eff *= float(spec.get("amplitude", 1.0))
        covered = (w > 0).any(axis=1)
        missing = [t for t, c in zip(panel, covered) if not c]
        if missing and not recipe.get("allow_missing_targets", False):
            raise SystemExit(f"context {ctx}: no source covers {len(missing)} targets, e.g. {missing[:5]}")
        path = args.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(panel), genes=axis, lfc=eff.astype(np.float32),
                            observed=(w > 0))
        nz = (eff != 0).sum(axis=1)
        summary[ctx] = {"weights": weights, "amplitude": spec.get("amplitude", 1.0),
                        "targets_covered": int(covered.sum()), "targets_missing": missing,
                        "genes_nonzero_median": float(np.median(nz)),
                        "abs_lfc_q99_median": float(np.median(np.quantile(np.abs(eff), 0.99, axis=1))),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        log(f"{ctx}: {covered.sum()}/{len(panel)} targets, median {np.median(nz):.0f} genes moved, "
            f"median q99 |ln fc| {summary[ctx]['abs_lfc_q99_median']:.3f}")
    manifest = {"stage": "100_build_context_effects", "written_utc": datetime.now(timezone.utc).isoformat(),
                "recipe": recipe, "recipe_sha256": hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
                "cache": str(args.cache), "gamma": gamma, "reliability_scale": scale, "contexts": summary,
                "units": "ln fold change on the official axis; unmeasured pairs are exactly 0"}
    with open(args.out / "manifest.json", "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"wrote {args.out}")


if __name__ == "__main__":
    main()
