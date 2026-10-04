"""Build a CPU-only bench-v2 kernel using the frozen D-056 input mounts; dry run by default.

Run through scripts/py.cmd. --launch explicitly pushes one new kernel, without polling/retry loops.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ME = HERE.relative_to(REPO).as_posix()
HYBRID = "reports/modelli/ibrido_selettivo_2026-10-04"
DIAG = "reports/modelli/diagnosi_t30_2026-10-04"
BENCH = "reports/generatore_e_banchi/banco_v2_2026-10-04/bench_v2.py"
sys.path.insert(0, str(REPO / HYBRID))
import kaggle_hybrid as KH
from input_contract import build, verify

OLD_STEPS = '''    steps = {"laneA": ["hybrid_lanes.py", "laneA", *common, "--weights", weights, "--out", OUT / "laneA"],
             "laneB": ["hybrid_lanes.py", "laneB", *common, "--weights", weights, "--real", REAL / P["real_file"],
                       "--targets", REAL / P["targets_file"], "--out", OUT / "laneB"]}
'''
NEW_STEPS = '''    eff = OUT / "effects"
    shared = ["--real", REAL / P["real_file"], "--targets", REAL / P["targets_file"]]
    arms = sum((["--arm", f"{n}={eff / (n + '.npz')}"] for n in ("all", "all_wR", "prod", "prod_wR")), [])
    expected = repo / "__DIAG__" / "esito" / ("diag_" + P["held"].lower() + "_r1") / "run.json"
    steps = {"effects": [repo / "__ME__/export_effects.py", *common, "--weights", weights, *shared,
                         "--expected", expected, "--out", eff],
             "bench_v2": [repo / "__BENCH__", *shared, *arms, "--pair", "prod_wR:prod",
                          "--pair", "all_wR:all", "--n-pred", "400", "--gen-seeds", "5",
                          "--emission", "t28", "--out", OUT / "bench_v2"]}
'''.replace("__ME__", ME).replace("__DIAG__", DIAG).replace("__BENCH__", BENCH)


def configure(contract=None):
    original = KH.snapshot

    def snapshot():
        _, names = original()
        names += [BENCH, f"{ME}/export_effects.py", f"{ME}/PROTOCOLLO.md", f"{ME}/input_contract.py"]
        names += [f"{DIAG}/esito/diag_{line}_r1/run.json" for line in ("h1", "hepg2", "rpe1", "jurkat", "k562")]
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
            for n in names:
                info = zipfile.ZipInfo(n, date_time=(2026, 10, 4, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, (REPO / n).read_bytes())
        return data.getvalue(), names

    if KH.KERNEL.count(OLD_STEPS) != 1:
        raise ValueError("archived launcher changed")
    KH.snapshot = snapshot
    KH.KERNEL = KH.KERNEL.replace(OLD_STEPS, NEW_STEPS)
    if contract is not None:
        raw = json.dumps(contract, sort_keys=True).encode()
        block = '''
import importlib.util
contract_raw = base64.b64decode("__CONTRACT__")
if hashlib.sha256(contract_raw).hexdigest() != "__CONTRACT_SHA__":
    raise SystemExit("input contract corrupted")
spec = importlib.util.spec_from_file_location("contract", repo / "__ME__/input_contract.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
contract = json.loads(contract_raw)
receipt = checker.verify(contract, {"train": TRAIN, "prepass": SPLITS.parent, "anchors": MANIFEST.parent,
                                   "keys": KEYS.parent, "real": REAL, "cube": cube, "source": src,
                                   "working": OUT, "repo": repo})
(OUT / "input_contract.json").write_bytes(contract_raw)
(OUT / "preflight_runtime.json").write_text(json.dumps(receipt, indent=2))
print(json.dumps({"preflight": "passed", "files": receipt["files"]}), flush=True)
'''.replace("__CONTRACT__", base64.b64encode(raw).decode()).replace("__CONTRACT_SHA__", hashlib.sha256(raw).hexdigest()).replace("__ME__", ME)
        KH.KERNEL = KH.KERNEL.replace('done = {}', block + '\ndone = {}')
    # Stop after a failed producer; never run a scorer on partial effects.
    marker = '    print(json.dumps({name: done[name]}), flush=True)'
    KH.KERNEL = KH.KERNEL.replace(marker, marker + '\n    if code:\n        break')
    # Measure this actual runtime before the first scientific step.
    marker = 'done = {}'
    KH.KERNEL = KH.KERNEL.replace(marker, '''import psutil
resources = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cpus": os.cpu_count(),
             "available_ram_bytes": psutil.virtual_memory().available,
             "free_disk_bytes": shutil.disk_usage(OUT).free, "accelerator": "CPU"}
(OUT / "resources.json").write_text(json.dumps(resources, indent=2))
print(json.dumps(resources), flush=True)
if resources["available_ram_bytes"] < 8 * 2**30 or resources["free_disk_bytes"] < 8 * 2**30:
    raise SystemExit("insufficient measured runtime resources")
done = {}''')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--held", choices=["H1", "HepG2", "RPE1", "Jurkat", "K562"], required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--launch", action="store_true")
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--data-root", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    a = p.parse_args()
    records = [json.loads(s) for s in (REPO / DIAG / "lancio_diag_r1.jsonl").read_text().splitlines()]
    r = next(r for r in records if r["held"] == a.held and r["accepted"])
    owner = r["slug"].split('/')[0]
    prior = json.loads((REPO / DIAG / "esito" / f"diag_{a.held.lower()}_r1/run.json").read_text())["arguments"]
    args = ["--config-dir", a.config_dir, "--owner", owner, "--stage", str(a.stage),
            "--slug", f"rcell-benchv2-{a.held.lower()}-t28-r1", "--mode", "lanes", "--held-group", a.held,
            "--train-kernel", r["kernel_sources"][0].split('/')[1],
            "--prepass-kernel", r["kernel_sources"][1].split('/')[1],
            "--anchors-kernel", r["kernel_sources"][2].split('/')[1],
            "--anchors-dir", Path(prior["anchors_manifest"]).parent.name,
            "--real-kernel", r["kernel_sources"][3].split('/')[1],
            "--real-file", Path(prior["real"]).name, "--targets-file", Path(prior["targets"]).name,
            "--weights", str(REPO / r["weights"].replace('\\', '/')),
            "--cube-owner", r["dataset_sources"][0].split('/')[0]]
    if a.launch_log:
        args += ["--launch-log", str(a.launch_log)]
    if not a.launch:
        args.append("--dry-run")
    contract = build(REPO, a.data_root, a.inputs, a.held, r, prior)
    receipt = verify(contract)
    configure(contract)
    if a.launch:
        # Persistent receipt/lock: even an ambiguous failed response must be inspected before a retry.
        lock = a.stage.parent / f"rcell-benchv2-{a.held.lower()}-t28-r1.launch.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("x", encoding="utf-8") as f:
            json.dump({"held": a.held, "stage": str(a.stage), "owner": owner}, f)
    sys.argv = [sys.argv[0], *args]
    KH.main()
    (a.stage / "input_contract.json").write_text(json.dumps(contract, indent=2))
    (a.stage / "preflight_local.json").write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
