"""Kaggle CPU kernel of the nested-samples study (nested_samples.py; R-DATI step 3; PROTOCOLLO §10.1), no GPU quota.

Why Kaggle CPU and not Colab (CLAUDE.md prefers Colab for CPU work): as for kaggle_fast.py, the shards are Kaggle
datasets of davidmaisterx and the compact twins are outputs of Kaggle kernels; on Kaggle nothing is transferred.

The kernel mounts the corpus datasets (the h5ad shards, read only for the obs columns cell_key, library, guides), the
build kernels of the twins, the prepass kernel of one fold and the code dataset of the trainings (cellnet.py,
cell_data.py, train_cellnet.py, balanced.py, fastshard.py). nested_samples.py travels inside run.py and is written out
with its sha256 checked. Before the study the kernel checks on its own runtime (ERRORI, "Prima del prossimo job"):
- the modules of the code dataset against the sha256 the launcher read from the files of this folder;
- the prepass state against the sha256 given (PROTOCOLLO.md §2);
- every shard of the state (bytes and sha256 of the state) and every twin (bytes and sha256 of the package manifests),
  re-read here (E-20260929-005: a hash computed by the runtime that wrote a file can come from its cache).
A failed check ends the kernel before the study and before its output folder exists. Outputs in /kaggle/working:
env.json, verify.json, nested.log, nested/ (summary.json, groups.csv.gz, selection/, manifest.json), kernel_done.json.
INPUT and OUT can be moved by environment variables (VCC_KAGGLE_INPUT, VCC_KAGGLE_OUT): test_kaggle_nested.py runs the
kernel's own run.py on a mock input tree.

    python kaggle_nested.py --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --slug rcell-v4-nested-h1-r1 --prepass-kernel rcell-prepass-h1-r1 --prepass-sha256 <hex> \
        [--caps 32 64 128] [--workers 4] [--launch-log <jsonl>] [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_FILES = ("cellnet.py", "cell_data.py", "train_cellnet.py", "balanced.py", "fastshard.py")
DATASETS = ("rlab-k562-gwps-r3", "rlab-rpe1-r2", "rlab-kolf-small", "rlab-hipsci-targeted19", "rlab-jurkat-nadig",
            "rlab-hepg2-nadig", "rlab-tian-norman", "rlab-a549", "rlab-h1-vcc2025-trainval", "rlab-k562-essential-r2",
            "rlab-kolf-strong")                                    # the corpus of the pilot (lancio_fast_r1.json)
FAST_KERNELS = ("rcell-v4-fast-a-r1", "rcell-v4-fast-b-r1", "rcell-v4-fast-c-r1")

KERNEL = r'''
import base64, hashlib, json, os, pickle, platform, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
P = json.loads(r"""__PARAMS__""")
INPUT = Path(os.environ.get("VCC_KAGGLE_INPUT", "/kaggle/input"))
OUT = Path(os.environ.get("VCC_KAGGLE_OUT", "/kaggle/working"))
t0 = time.time()


def mount(slug):
    for p in (INPUT / slug, INPUT / "datasets" / P["owner"] / slug, INPUT / "notebooks" / P["owner"] / slug,
              INPUT / "kernels" / P["owner"] / slug):
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts: {hits[:3]}")
    return hits[0]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(16 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


env = {"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
       "memory": sh("free -m"), "disk": sh("df -h . | tail -1"),
       "input_tree": sh(f"find {INPUT} -maxdepth 4 -type d | head -60")}
(OUT / "env.json").write_text(json.dumps(env, indent=1))
CODE, PRE = mount(P["code_slug"]), mount(P["prepass_kernel"]) / "prepass"
report = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "code": str(CODE), "prepass": str(PRE),
          "problems": []}
for name, want in P["code_sha256"].items():
    if not (CODE / name).is_file() or sha(CODE / name) != want:
        report["problems"].append(f"code dataset: {name} is not the launcher's file")
state = PRE / "prepass.pkl"
report["prepass_sha256"] = sha(state) if state.is_file() else None
if report["prepass_sha256"] != P["prepass_sha256"]:
    report["problems"].append("the prepass state is not the one given")
source = base64.b64decode(P["nested_b64"])
if hashlib.sha256(source).hexdigest() != P["nested_sha256"]:
    report["problems"].append("nested_samples.py inside run.py is not the launcher's file")
if not report["problems"]:
    sys.path.insert(0, str(CODE))
    import train_cellnet as TC
    with open(state, "rb") as fh:
        st = pickle.load(fh)
    shards = [(p, s["sha256"], int(s["bytes"])) for p, s in zip(TC.resolve_shards(st["shards"], [INPUT]), st["shards"])]
    twins = TC.resolve_twins(st["shards"], [INPUT])
    report["cells"] = int(sum(int(s["n"]) for s in st["shards"]))
    del st
    for what, files in (("shards", shards if P["hash_shards"] else []), ("twins", twins)):
        t1 = time.time()
        with ThreadPoolExecutor(P["hash_threads"]) as ex:
            got = list(ex.map(lambda f: (os.path.getsize(f[0]), sha(f[0])), files))
        bad = [f[0] for f, g in zip(files, got) if g != (f[2], f[1])]
        report[what] = {"files": len(files), "bytes": int(sum(f[2] for f in files)), "differ": bad,
                        "seconds": round(time.time() - t1, 1)}
        report["problems"] += [f"{what}: {b} differs" for b in bad[:5]]
        print(json.dumps({what: {k: v for k, v in report[what].items() if k != "differ"}, "differ": len(bad)}), flush=True)
    report["shards_resolved"], report["twins_resolved"] = len(shards), len(twins)
report["verify_seconds"] = round(time.time() - t0, 1)
(OUT / "verify.json").write_text(json.dumps(report, indent=1))
if report["problems"]:
    raise SystemExit(f"preflight failed, nothing computed: {report['problems'][:5]}")
work = OUT / "code"
work.mkdir()
(work / "nested_samples.py").write_bytes(source)
cmd = [sys.executable, str(work / "nested_samples.py"), "--prepass", str(PRE), "--shard-roots", str(INPUT),
       "--fast-roots", str(INPUT), "--caps", *map(str, P["caps"]), "--workers", str(P["workers"] or os.cpu_count() or 1),
       "--out", str(OUT / "nested")]
print(" ".join(cmd), flush=True)
with open(OUT / "nested.log", "w") as fh:
    code = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                          env={**os.environ, "PYTHONPATH": str(CODE)}).returncode
(OUT / "kernel_done.json").write_text(json.dumps({"return_code": code, "seconds": round(time.time() - t0, 1)}))
if code:
    raise SystemExit(f"the study failed with code {code}: see nested.log")
'''


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def params(owner, code_slug, prepass_kernel, prepass_sha256, caps, workers, hash_shards=True, hash_threads=4) -> dict:
    source = (HERE / "nested_samples.py").read_bytes()
    return {"owner": owner, "code_slug": code_slug, "prepass_kernel": prepass_kernel, "prepass_sha256": prepass_sha256,
            "caps": list(caps), "workers": workers, "hash_shards": bool(hash_shards), "hash_threads": hash_threads,
            "code_sha256": {f: sha256_file(HERE / f) for f in CODE_FILES},
            "nested_sha256": hashlib.sha256(source).hexdigest(), "nested_b64": base64.b64encode(source).decode("ascii")}


def kernel_text(p: dict) -> str:
    text = KERNEL.replace("__PARAMS__", json.dumps(p, indent=1))
    compile(text, "run.py", "exec")
    return text


def kaggle(args, config_dir):
    exe = shutil.which("kaggle") or str(Path(sys.executable).parent / "kaggle.exe")
    return subprocess.run([exe, *args], env={**os.environ, "KAGGLE_CONFIG_DIR": config_dir}, capture_output=True,
                          text=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--data-owner", default="davidmaisterx")
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--slug", required=True)
    p.add_argument("--code-slug", default="rcell-v4-code-r1")
    p.add_argument("--prepass-kernel", required=True)
    p.add_argument("--prepass-sha256", required=True)
    p.add_argument("--caps", nargs="+", type=int, default=[32, 64, 128])
    p.add_argument("--workers", type=int, default=0, help="0 = the CPUs of the runtime")
    p.add_argument("--no-hash-shards", action="store_true", help="check the h5ad shards by name and bytes only")
    p.add_argument("--launch-log", type=Path)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.stage.exists():
        sys.exit(f"refusing: {a.stage} exists")
    prm = params(a.owner, a.code_slug, a.prepass_kernel, a.prepass_sha256, a.caps, a.workers,
                 hash_shards=not a.no_hash_shards)
    text = kernel_text(prm)
    a.stage.mkdir(parents=True)
    (a.stage / "run.py").write_text(text, encoding="utf-8", newline="\n")
    meta = {"id": f"{a.owner}/{a.slug}", "title": a.slug, "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False,
            "dataset_sources": [f"{a.owner}/{a.code_slug}"] + [f"{a.data_owner}/{d}" for d in DATASETS],
            "kernel_sources": [f"{a.owner}/{a.prepass_kernel}"] + [f"{a.owner}/{k}" for k in FAST_KERNELS],
            "competition_sources": []}
    (a.stage / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    record = {"slug": f"{a.owner}/{a.slug}", "stage": a.stage.as_posix(), "run_sha256": sha256_file(a.stage / "run.py"),
              "nested_samples_sha256": prm["nested_sha256"], "code_sha256": prm["code_sha256"],
              "prepass_kernel": a.prepass_kernel, "prepass_sha256": a.prepass_sha256, "caps": a.caps,
              "dataset_sources": meta["dataset_sources"], "kernel_sources": meta["kernel_sources"]}
    if a.dry_run:
        print(f"dry run: {a.stage / 'run.py'} compiles; nothing pushed\n{json.dumps(record)}")
        return
    r = kaggle(["kernels", "push", "-p", str(a.stage)], a.config_dir)
    answer = ((r.stdout or "") + (r.stderr or "")).strip()
    accepted = r.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer
    record.update(pushed_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), returncode=r.returncode,
                  accepted=accepted, answer=answer[-600:])
    print(json.dumps({k: record[k] for k in ("slug", "accepted", "answer")}))
    if a.launch_log:
        with open(a.launch_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    if not accepted:
        sys.exit("the push failed or an input is not a valid source")


if __name__ == "__main__":
    main()
