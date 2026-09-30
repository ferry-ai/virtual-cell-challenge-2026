"""Offline gate and immutable-code checks; no CUDA, training, network or fake run outputs."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tarfile
from neural_postgate_runner import FAMILIES, gate_passes, train_command

HERE = Path(__file__).resolve().parent


def main():
    gate = {"verified_families": FAMILIES, "seed": 0, "fold_evidence": {f: {} for f in FAMILIES},
            "verdict": {"eligible_for_cell_scorer": True, "regime": "C", "training_seed": 0,
                        "contrasts": {"transfer": {"macro_family_delta": .012, "ci95": [.001, .02],
                                                    "per_family": {f: .012 for f in FAMILIES}}}}}
    assert gate_passes(gate)
    cases = []
    for key, value in [("seed", 1), ("verified_families", FAMILIES[:-1]), ("fold_evidence", {})]:
        case = copy.deepcopy(gate)
        case[key] = value
        cases.append(case)
    for key, value in [("eligible_for_cell_scorer", False), ("regime", "J"), ("training_seed", 1)]:
        case = copy.deepcopy(gate)
        case["verdict"][key] = value
        cases.append(case)
    for key, value in [("macro_family_delta", .009), ("ci95", [-.001, .02]),
                       ("per_family", {**{f: .02 for f in FAMILIES}, "ipsc": -.02})]:
        case = copy.deepcopy(gate)
        case["verdict"]["contrasts"]["transfer"][key] = value
        cases.append(case)
    for case in cases:
        try:
            gate_passes(case)
        except ValueError:
            pass
        else:
            raise AssertionError("Incomplete, incompatible or failing evidence was accepted")
    plan = HERE / "kaggle_neural_postgate/plan_r1"
    manifest = json.loads((plan / "plan_manifest.json").read_text())
    payload = (plan / "runtime_payload.tar.gz").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest["payload_sha256"]
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        frozen = {m.name: archive.extractfile(m).read() for m in archive.getmembers()}
    original = json.loads((HERE / "kaggle_neural_r1/review/review_manifest.json").read_text())
    for item in original["code_allowlist"]:
        if not item["path"].endswith("/read_neural_sources.py"):
            assert hashlib.sha256(frozen[item["path"]]).hexdigest() == item["sha256"]
    for name, data in frozen.items():
        if name.endswith(".py"):
            compile(data, name, "exec")
    command = train_command(Path("report"), Path("data"), Path("out"), "none", 0)
    assert command[command.index("--holdout") + 1] == "none"
    assert command[command.index("--seed") + 1] == "0"
    assert "--predict-contexts" not in command
    assert not list(plan.rglob("*.ipynb"))
    print("PASS: nine invalid gates refused; original four training/protocol files unchanged; all frozen Python parses; plan has no notebook")


if __name__ == "__main__":
    main()
