"""Offline refusal checks for exact protocol options and seed-0 input identities."""
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

from neural_postgate_runner_r2 import (FAMILIES, TRAINING_OPTIONS, check_dataset_identity,
                                     gate_passes, train_command, validate_seed0_options)

HERE = Path(__file__).resolve().parent


def refuses(callback, *args):
    try:
        callback(*args)
    except ValueError:
        return
    raise AssertionError("Changed protocol or input was accepted")


def main():
    options = {**TRAINING_OPTIONS, "seed": 0, "holdout": "k562", "device": "cuda",
               "data": "/seed0/data", "out": "/seed0/fold"}
    assert validate_seed0_options(options)
    option_cases = 0
    for key, value in TRAINING_OPTIONS.items():
        changed = copy.deepcopy(options)
        changed[key] = "changed" if type(value) not in (float, int) else value + 1
        refuses(validate_seed0_options, changed)
        missing = copy.deepcopy(options)
        del missing[key]
        refuses(validate_seed0_options, missing)
        option_cases += 2
    refuses(validate_seed0_options, {**options, "extra_hyperparameter": 1})
    refuses(validate_seed0_options, {**options, "seed": 1})
    option_cases += 2

    # The command values are those in the original r1 launcher, not an independently
    # handwritten second list that could silently drift with the new implementation.
    tree = ast.parse((HERE / "neural_kaggle_runner.py").read_text())
    original = next(node for node in ast.walk(tree) if isinstance(node, ast.List)
                    and any(isinstance(item, ast.Constant) and item.value == "--selection-seed"
                            for item in node.elts))
    original_values = {original.elts[i].value: original.elts[i + 1].value
                       for i in range(len(original.elts) - 1)
                       if isinstance(original.elts[i], ast.Constant)
                       and str(original.elts[i].value).startswith("--")
                       and isinstance(original.elts[i + 1], ast.Constant)}
    command = train_command(Path("report"), Path("data"), Path("out"), "k562", 0)
    for flag, value in original_values.items():
        assert command[command.index(flag) + 1] == value, flag
    assert "--predict-contexts" not in command and "--plan-only" not in command

    with tempfile.TemporaryDirectory(prefix="neural-postgate-guard-") as temp:
        dataset = Path(temp)
        original_bytes = {"manifest.json": b'{"test":true}', "genes.txt": b"GENE1\n"}
        expected = {}
        for name, data in original_bytes.items():
            (dataset / name).write_bytes(data)
            expected[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        assert check_dataset_identity(dataset, expected) == expected
        (dataset / "genes.txt").write_bytes(b"GENE2\n")  # Same size, different content.
        refuses(check_dataset_identity, dataset, expected)
        (dataset / "genes.txt").write_bytes(b"GENE1\nEXTRA\n")
        refuses(check_dataset_identity, dataset, expected)
        (dataset / "genes.txt").write_bytes(original_bytes["genes.txt"])
        refuses(check_dataset_identity, dataset, {"manifest.json": expected["manifest.json"]})
        refuses(check_dataset_identity, dataset, {**expected, "absent.txt": expected["genes.txt"]})
        bad_hash = copy.deepcopy(expected)
        bad_hash["genes.txt"]["sha256"] = None
        refuses(check_dataset_identity, dataset, bad_hash)

        gate = {"verified_families": FAMILIES, "seed": 0, "fold_evidence": {f: {} for f in FAMILIES},
                "seed0_options": options, "seed0_data_files": expected,
                "verdict": {"eligible_for_cell_scorer": True, "regime": "C", "training_seed": 0,
                            "contrasts": {"transfer": {"macro_family_delta": .012, "ci95": [.001, .02],
                                                        "per_family": {f: .012 for f in FAMILIES}}}}}
        assert gate_passes(gate)
        for key in ("seed0_options", "seed0_data_files"):
            missing = copy.deepcopy(gate)
            del missing[key]
            refuses(gate_passes, missing)
        drift = copy.deepcopy(gate)
        drift["seed0_options"]["selection_seed"] += 1
        refuses(gate_passes, drift)

    plan = HERE / "kaggle_neural_postgate/plan_r2"
    manifest = json.loads((plan / "plan_manifest.json").read_text())
    payload = (plan / "runtime_payload.tar.gz").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest["payload_sha256"]
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        frozen = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
    previous_path = HERE / "kaggle_neural_postgate/plan_r1/runtime_payload.tar.gz"
    with tarfile.open(previous_path, mode="r:gz") as archive:
        previous = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
    for name, data in frozen.items():
        if not name.endswith("/neural_postgate_runner_r2.py"):
            assert previous[name] == data, name
        if name.endswith(".py"):
            compile(data, name, "exec")
    assert not list(plan.rglob("*.ipynb"))
    print(json.dumps({"passed": True, "invalid_option_cases": option_cases,
                      "invalid_dataset_cases": 5, "invalid_gate_identity_cases": 3,
                      "unchanged_other_payload_files": len(frozen) - 1,
                      "original_r1_cli_values_match": True, "notebooks_created": False}))


if __name__ == "__main__":
    main()
