"""Derive profile-only confirmation inference from the frozen pilot function."""
import ast
import hashlib
from pathlib import Path

from build_stack_resume_r2 import replace_once

HERE = Path(__file__).resolve().parent


def main():
    original = (HERE / "stack_pilot.py").read_bytes()
    if hashlib.sha256(original).hexdigest() != "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508":
        raise ValueError("Frozen pilot adapter changed")
    source = original.decode("utf-8")
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "infer")
    function = "\n".join(source.splitlines()[node.lineno - 1:node.end_lineno])
    function = replace_once(function, '    import anndata as ad\n',
        '    import anndata as ad\n'
        '    if sha(pilot.__file__) != FROZEN_PILOT_SHA:\n'
        '        raise ValueError("Scientific helper differs from the frozen pilot")\n')
    function = replace_once(function,
        '    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))',
        '    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))\n'
        '    if bundle["targets"] != EXPECTED:\n'
        '        raise ValueError("Confirmation target set differs from the frozen registration")\n'
        '    if sha(__file__) != bundle["inference_adapter_sha256"] or bundle["protocol_sha256"] != PROTOCOL_SHA:\n'
        '        raise ValueError("Confirmation inference adapter or protocol differs from plan")')
    function = replace_once(function,
        '"bundle_sha256": sha(args.bundle / "bundle.json"), "adapter_sha256": sha(__file__),',
        '"bundle_sha256": sha(args.bundle / "bundle.json"), "adapter_sha256": sha(__file__),\n'
        '        "preparation_adapter_sha256": bundle["adapter_sha256"], "protocol_sha256": PROTOCOL_SHA,')
    function = replace_once(function,
        '    generated, transferred, diagnostics, cached_controls = [], [], [], {}',
        '    profiles = {"transfer": [], "stack": []}\n    diagnostics, cached_controls = [], {}')
    function = replace_once(function,
        'Same Stack seed for paired prompt and synthetic control; final target-specific IID draws',
        'Same Stack seed for paired prompt and synthetic control; profiles exported before final draws')
    function = replace_once(function,
        '''            for profile, dest in [(baseline, transferred), (corrected, generated)]:
                rng = rng_for(f"output:{target}")
                libs = rng.choice(libraries, N_OUTPUT, replace=True)
                dest.append(sample_counts(profile, libs, rng, max_stored_per_cell=12000,
                                          max_counts_per_cell=1000000))''',
        '''            # Record exact model-derived profiles before any final-cell draws.
            profiles["transfer"].append(np.asarray(baseline, dtype=np.float64).copy())
            profiles["stack"].append(np.asarray(corrected, dtype=np.float64).copy())''')
    start = function.index('    for arm, blocks in [("transfer", transferred), ("stack", generated)]:')
    function = function[:start] + '''    np.savez_compressed(args.out / "profiles.npz", targets=np.asarray(bundle["targets"], dtype=str),
        genes=np.asarray(controls_full.var_names, dtype=str),
        transfer=np.stack(profiles["transfer"]), stack=np.stack(profiles["stack"]),
        basal=basal.astype(np.float64), library_sizes=libraries.astype(np.float64),
        shared=np.array([g in shared for g in controls_full.var_names], dtype=bool))
    write_json(args.out / "finished.json", {"targets": bundle["targets"],
        "status": "profiles_exported_no_final_cells_no_scores", "diagnostics": diagnostics,
        "profile_sha256": sha(args.out / "profiles.npz"), "profile_dtype": "float64",
        "stack_seed": SEED, "final_poisson_seeds": [1, 2, 3], "protocol_sha256": PROTOCOL_SHA,
        "claim": "One frozen Stack inference; exact profiles before final sampling; no pretraining holdout claim"})
'''
    header = '''"""Confirmation profile export: same Stack inference, no final cells or scoring.

Derived from the frozen pilot's infer function. Model inputs, calls, cache,
baseline and paired-control correction are unchanged. This adapter records the
two float64 profiles instead of sampling final cells; CPU scoring samples them.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import scipy.sparse as sp
import stack_pilot as pilot
from stack_confirmation_pack import EXPECTED
from stack_pilot import (CONTROL, SEED, CHECKPOINT_SHA, GENELIST_SHA, sha, write_json,
    GeneListUnpickler, align_shared, pick, call_model, memory_shapes,
    predicted_profile, corrected_profile)

FROZEN_PILOT_SHA = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"


'''
    footer = '''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "checkpoint", "genelist", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("Batch size must be positive")
    infer(args)


if __name__ == "__main__":
    main()
'''
    result = header + function + footer
    ast.parse(result)
    path = HERE / "stack_confirmation_infer.py"
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(result)
    print(hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
