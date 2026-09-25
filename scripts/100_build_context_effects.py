"""Stage 100: per-context panel effects for stage 76, from a written recipe over stage-98 sources.

A recipe is a JSON file fixed BEFORE generation:

    {"name": "t08", "effect": "raw", "gamma": 0.5, "reliability_scale": 100,
     "contexts": {"A": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 2}},
                  "B": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 1}},
                  "C": {...}},
     "why": "free text: the evidence the weights come from"}

``effect`` picks what `mix` averages: ``shrunk`` (the stage-98 array, the default), ``raw``,
or ``zshrink``, which recomputes each source's local shrinkage from its raw effect and SE with
the recipe's ``shrink_k``: ``raw * z^2 / (z^2 + shrink_k)`` (`multisource.z_shrink`). For the
pseudobulk sources the stage-98 ``shrunk`` array is not that formula at k = 4 applied to the
pooled effect, so ``zshrink`` with ``shrink_k`` 4 differs from ``shrunk``.

For each context this writes ``effects_<CTX>.npz`` with ``targets``, ``genes`` (the official
axis) and ``lfc`` (ln fold change, amplitude applied), the format stage 76 reads through
``--effects CTX=PATH``. A (target, gene) pair no source measured stays exactly 0 and is
counted as such in the manifest; a target no source covers is refused unless
``allow_missing_targets`` is true in the recipe (stage 76 would refuse it anyway).

The manifest records the recipe itself and two hashes of its file: ``recipe_sha256`` of the
bytes, which depends on the checkout's line endings, and ``recipe_sha256_lf`` with CRLF folded
to LF, which does not (D-043).

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

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.manifest import text_sha256  # noqa: E402
from vcc2026.multisource import AxisTable, mix, zshrink_mixture, zshrink_table  # noqa: E402

DATA_ROOT = config.paths().data_root  # VCC2026_DATA_ROOT, else configs/config.yaml
EFFECTS = ("shrunk", "raw", "zshrink")


def load_table(cache: Path, name: str, effect: str = "shrunk", shrink_k: float | None = None) -> AxisTable:
    """A stage-98 source, with the effect `mix` reads: stage-98 ``shrunk``, ``raw``, or
    ``zshrink`` recomputed from raw and SE at ``shrink_k``. Unmeasured pairs stay NaN.

    A mixture saved without SE (``cd4_mix``: meta ``from`` lists its parts) is rebuilt from
    its parts under ``zshrink``, each shrunk with its own SE; any other source lacking a
    finite SE on a measured pair is refused rather than turned into votes for zero."""
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    tab = AxisTable(name, z["targets"].astype(str).tolist(), z["shrunk"], z["raw"], z["se"], z["n_cells"], meta)
    if effect == "raw":
        tab.shrunk = tab.raw
    elif effect == "zshrink":
        if shrink_k is None or not shrink_k > 0:
            raise ValueError(f"effect 'zshrink' needs a positive shrink_k, got {shrink_k!r}")
        measured = np.isfinite(tab.raw)
        if not np.isfinite(tab.se[measured]).any() and meta.get("from"):
            parts = [load_table(cache, part, "raw") for part in meta["from"]]
            return zshrink_mixture(name, parts, tab.targets, float(shrink_k))
        tab = zshrink_table(tab, float(shrink_k))
    return tab


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
    effect = recipe.get("effect", "shrunk")
    if effect not in EFFECTS:
        raise SystemExit(f"recipe effect must be one of {EFFECTS}, got {effect!r}")
    shrink_k = recipe.get("shrink_k")
    if effect == "zshrink" and not (isinstance(shrink_k, (int, float)) and shrink_k > 0):
        raise SystemExit(f"recipe effect 'zshrink' needs a positive number shrink_k, got {shrink_k!r}")
    tables = [load_table(args.cache, n, effect, shrink_k) for n in names]
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
                "recipe_sha256_lf": text_sha256(args.recipe),
                "cache": str(args.cache), "gamma": gamma, "reliability_scale": scale, "contexts": summary,
                "units": "ln fold change on the official axis; unmeasured pairs are exactly 0"}
    with open(args.out / "manifest.json", "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"wrote {args.out}")


if __name__ == "__main__":
    main()
