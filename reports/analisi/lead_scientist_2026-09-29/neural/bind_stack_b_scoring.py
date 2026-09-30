"""Bind completed Kaggle B outputs to a reviewed CPU job and full preflight.

Only creates a new local setup; never uploads, queues, scores, or submits.
"""
import argparse
import json
from pathlib import Path
import sys
import stack_pilot as pilot

HERE = Path(__file__).resolve().parent
SETUP_NAME = "lead_stack_scoring_b_setup_2026-09-29_r1"
PRED_NAME = "lead_stack_kaggle_b_prediction_2026-09-29_r1"
RUNTIME = "/content/drive/MyDrive/vcc2026"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--drive", type=Path, required=True)
    parser.add_argument("--truth-local", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    base = HERE / "stack_b_scoring_setup_r1"
    archive = base / "scoring_snapshot.tar.gz"
    if pilot.sha(archive) != "6e216f900a606656c182bb7f520e351bb7805358a0e2943a226ce3a105071dcb":
        raise ValueError("Frozen B scoring code changed")
    producer = json.loads((args.prediction / "reports/prediction_hashes.json").read_text())
    inputs, transfers = [], []
    def entry(identity, source, relative, expected=None, publish=False):
        digest, size = pilot.sha(source), source.stat().st_size
        if expected is not None and (digest != expected["sha256"] or size != expected["bytes"]):
            raise ValueError("Recorded input hash/size differs: " + identity)
        destination = args.drive / relative
        inputs.append({"id": identity, "paths": {"local": str(destination), "runtime": RUNTIME + "/" + relative},
                       "bytes": size, "sha256": digest})
        if publish:
            transfers.append({"source": str(source), "destination": str(destination), "sha256": digest, "bytes": size})
        return digest
    prediction_hashes = {}
    for name in ["prediction_stack.h5ad", "prediction_transfer.h5ad", "finished.json", "inference_manifest.json"]:
        source = args.prediction / name if name.endswith(".h5ad") else args.prediction / "reports/prediction" / name
        prediction_hashes[name] = entry(name, source, f"runs/{PRED_NAME}/{name}", producer[name], True)
    inference = json.loads((args.prediction / "reports/prediction/inference_manifest.json").read_text())
    if (inference.get("adapter_sha256") != "a85b752dbd5042fde45611e80a6a942733bb19de6c4a00a03ab71db33a90d2a4"
            or inference.get("ab_protocol_sha256") != "181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506"
            or inference.get("input_axis_policy") != "own_measured_support"):
        raise ValueError("These are not the frozen B predictions")
    bundle_relative = "runs/lead_stack_2026-09-29_r2/bundle"
    bundle_file = args.drive / bundle_relative / "bundle.json"
    if pilot.sha(bundle_file) != "16cf30126a7c46ec651c8ed8262b19353e1a3ab07c4dd445590a8a040e36fc29":
        raise ValueError("Common pilot preparation changed")
    bundle = json.loads(bundle_file.read_text())
    entry("bundle", bundle_file, bundle_relative + "/bundle.json")
    for name in ["destination_controls.h5ad", "transfer.npz"]:
        source = args.drive / bundle_relative / name
        if pilot.sha(source) != bundle["files"][name]:
            raise ValueError("Prepared control/effect input changed")
        entry(name, source, bundle_relative + "/" + name)
    if args.truth_local.stat().st_size != bundle["destination_size"]:
        raise ValueError("Public truth size differs from preparation")
    entry("public_truth", args.truth_local, "data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad")
    entry("scoring_snapshot", archive, f"runs/{SETUP_NAME}/scoring_snapshot.tar.gz", publish=True)
    guard = HERE.parent / "learning/preflight.py"
    guard_hash = entry("preflight_code", guard, f"runs/{SETUP_NAME}/preflight.py", publish=True)
    contract = {"schema_version": 1, "job_id": "084_stack_b_development_scoring_r1", "inputs": inputs,
        "outputs": [{"id": "score", "paths": {"local": str(args.drive / "runs/lead_stack_score_b_2026-09-29_r1"),
            "runtime": RUNTIME + "/runs/lead_stack_score_b_2026-09-29_r1"}, "must_be_absent": True}],
        "target_checks": [{"input_id": "transfer.npz", "npz_key": "targets", "required": bundle["targets"]}],
        "environment": {"python": {"paths": {"local": sys.executable,
            "runtime": "/content/lead_candidate_environment_r2/venv/bin/python"}},
            "packages": dict.fromkeys(["cell-eval2", "scanpy", "numpy", "scipy", "pandas", "anndata", "h5py"]),
            "imports": ["numpy", "scipy", "anndata", "h5py"], "probes": ["h5ad_nullable_roundtrip"],
            "allow_write_nullable_strings": True}}
    args.out.mkdir(parents=True)
    contract_path = args.out / "job_contract.json"
    pilot.write_json(contract_path, contract)
    contract_sha = pilot.sha(contract_path)
    # The contract cannot include its own hash; the immutable launcher binds it.
    transfers.append({"source": str(contract_path), "destination": str(args.drive / f"runs/{SETUP_NAME}/job_contract.json"),
                      "sha256": contract_sha, "bytes": contract_path.stat().st_size})
    launcher = (base / "084_lead_stack_score_b_r1.sh.template").read_text()
    replacements = {"INPUT_RECEIPT_BOUND=false": "INPUT_RECEIPT_BOUND=true",
        "__APPROVED_COMPLETE_B_PREDICTION_DIR__": RUNTIME + "/runs/" + PRED_NAME,
        "__PREDICTION_STACK_SHA256__": prediction_hashes["prediction_stack.h5ad"],
        "__PREDICTION_TRANSFER_SHA256__": prediction_hashes["prediction_transfer.h5ad"],
        "__FINISHED_JSON_SHA256__": prediction_hashes["finished.json"],
        "__INFERENCE_MANIFEST_SHA256__": prediction_hashes["inference_manifest.json"]}
    for old, new in replacements.items():
        if launcher.count(old) != 1:
            raise ValueError("Template marker changed")
        launcher = launcher.replace(old, new)
    bootstrap_checks = (f'  echo "{guard_hash}  $SETUP/preflight.py" | sha256sum -c - || return 1\n'
                        f'  echo "{contract_sha}  $SETUP/job_contract.json" | sha256sum -c - || return 1\n')
    if launcher.count('inputs_ready() {\n') != 1 or launcher.count('mkdir -p "$CODE_DIR"\n') != 1:
        raise ValueError("Template preflight insertion point changed")
    launcher = launcher.replace('inputs_ready() {\n', 'inputs_ready() {\n' + bootstrap_checks)
    command = ('"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/job_contract.json" --site runtime '
               '--receipt "$SETUP/preflight_runtime_receipt.json" --attempts 45 --interval-seconds 20\n')
    launcher = launcher.replace('mkdir -p "$CODE_DIR"\n', command + 'mkdir -p "$CODE_DIR"\n')
    launch_path = args.out / "084_lead_stack_score_b_r1.sh"
    with launch_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(launcher)
    pilot.write_json(args.out / "publish_plan.json", {"transfers": transfers, "launcher_sha256": pilot.sha(launch_path),
        "launcher": str(launch_path), "queue": str(args.drive / "runs/queue/084_lead_stack_score_b_r1.sh"),
        "local_preflight_required_before_queue": True, "runtime_preflight_required_before_scoring": True,
        "authorization": "owner authorized all necessary uploads/runs in current lead task"})
    print(json.dumps({"setup": str(args.out), "contract_sha256": contract_sha, "launcher_sha256": pilot.sha(launch_path)}))


if __name__ == "__main__":
    main()
