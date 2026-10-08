"""Serialize reviewed PIE adapter output to per-context stage-100 files.

No fitting, normalization, amplitude/cis correction or emission scaling occurs.
Only a verified adapter receipt is accepted; native ESM2 predictions need a
separate reviewed bridge and cannot be relabeled as final effects here.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from pie_adapter import sha256, unique, validate_contract


def export_stage100(source, out):
    source, out = Path(source), Path(out)
    if out.exists():
        raise FileExistsError(out)
    receipt = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    contract = receipt["contract"]
    validate_contract(contract, contract["requests"])
    if receipt.get("quantity") != "ln_fold_change":
        raise ValueError("final natural-log effects required")
    payload = source / "effects.npz"
    if sha256(payload) != receipt["output_sha256"]:
        raise ValueError("adapter payload checksum differs")
    with np.load(payload, allow_pickle=False) as data:
        genes = unique(data["genes"].tolist(), "genes")
        effects, observed = data["effects"], data["mask"]
        axes = {name: data[name].tolist() for name in ("dataset", "context", "perturbation")}
    if genes != contract["genes"]:
        raise ValueError("gene axis differs from reviewed contract")
    for name, axis in axes.items():
        if axis != [row[name] for row in contract["requests"]]:
            raise ValueError("row axis differs from reviewed contract")
    if effects.shape != (len(axes["context"]), len(genes)) or observed.shape != effects.shape or observed.dtype != bool:
        raise ValueError("effect axes or boolean mask mismatch")
    if not np.isfinite(effects[observed]).all() or np.any(np.abs(effects[observed]) > np.finfo(np.float32).max):
        raise ValueError("observed effects cannot be represented as finite float32")
    values = np.zeros(effects.shape, dtype=np.float32)
    values[observed] = effects[observed]
    groups = {}
    for i, key in enumerate(zip(axes["dataset"], axes["context"])):
        groups.setdefault(key, []).append(i)
    for rows in groups.values():
        unique([axes["perturbation"][i] for i in rows], "context targets")
    out.mkdir(parents=True, exist_ok=False)
    files = []
    for index, ((dataset, context), rows) in enumerate(groups.items()):
        # Numeric filenames keep external context identifiers out of filesystem paths.
        path = out / f"context_{index:04d}.npz"
        np.savez_compressed(path, targets=np.asarray([axes["perturbation"][i] for i in rows]),
                            genes=np.asarray(genes), lfc=values[rows], observed=observed[rows])
        files.append(dict(file=path.name, dataset=dataset, context=context,
                          rows=len(rows), observed_pairs=int(observed[rows].sum()), sha256=sha256(path)))
    result = dict(schema_version=1, files=files, quantity="ln_fold_change",
                  stage="final_effect_before_emitter", emission_scale_applied=False,
                  postprocess=dict(gain=1.0, center=False, cis=False),
                  source_receipt_sha256=sha256(source / "manifest.json"),
                  source_payload_sha256=sha256(payload), exporter_sha256=sha256(__file__),
                  float_conversion="float32", missing_serialization="zero with observed=False",
                  scientific_benefit="not_evaluated")
    (out / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(export_stage100(args.source, args.out), indent=2))
