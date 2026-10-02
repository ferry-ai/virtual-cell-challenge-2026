
import fnmatch, hashlib, json, os, platform, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")
OWNERS = ['alfredo2003bit', 'davidmaisterx']
CODE_SLUG, ASSETS_SLUG = 'rlead-cellnet-code', 'rlead-assets'
DATASETS = ["rlab-hepg2-nadig", "rlab-jurkat-nadig", "rlab-h1-vcc2025-trainval", "rlab-hipsci-gwfit", "rlab-hipsci-gwnonfit", "rlab-hipsci-targeted19"]
GLOBS = {}
PREPASS_ARGS = None
PREPASS_FROM = 'rlead-prepass-r1'
ARMS = [["ident", "identity"], ["gen", "generic"]]
TRAIN_ARGS = ["--epochs", "10", "--batch", "256", "--ctrl-k", "64", "--buffer-shards", "4", "--dim", "128", "--rank", "128", "--lr", "0.001", "--seed", "0", "--workers", "3", "--roles", "3", "--prefetch", "8", "--budget-minutes", "150", "--reserve-export-minutes", "5", "--checkpoint-minutes", "15", "--keep-checkpoints", "3", "--measure-steps", "300", "--eval-chunk", "512", "--eval-reserve-seconds", "120", "--log-every", "100", "--eval-workers", "3", "--eval-partial", "0.08"]
CYCLE = [100, 200]
GPU = True
t0 = time.time()


def mount(slug):
    """Where Kaggle mounted an input: /kaggle/input/<slug>, /kaggle/input/datasets/<owner>/<slug> (seen on 29/09),
    /kaggle/input/notebooks/<owner>/<slug>, for either owner, or the one folder of that name below /kaggle/input."""
    for p in [INPUT / slug] + [INPUT / kind / o / slug for o in OWNERS for kind in ("datasets", "notebooks", "kernels")]:
        if p.is_dir():
            return p
    hits = [p for p in INPUT.glob(f"**/{slug}") if p.is_dir()]
    if len(hits) != 1:
        raise SystemExit(f"{slug}: {len(hits)} mounts below {INPUT}: {hits[:3]}")
    return hits[0]


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


env = {"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
        "gpus": sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"), "memory": sh("free -m"),
        "disk": sh("df -h /kaggle/working | tail -1"), "input_tree": sh("find /kaggle/input -maxdepth 4 -type d | head -40")}
try:
    import torch
    env["torch"], env["cuda"] = torch.__version__, torch.cuda.is_available()
except ImportError:
    pass
(OUT / "env.json").write_text(json.dumps(env, indent=1))
CODE, ASSETS = mount(CODE_SLUG), mount(ASSETS_SLUG)
roots = {d: mount(d) for d in DATASETS}
report = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mounts": {d: str(r) for d, r in roots.items()},
           "code": str(CODE), "assets": str(ASSETS), "datasets": {}, "bad": []}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(16 << 20), b""):
            h.update(b)
    return h.hexdigest()


code_manifest = json.loads((CODE / "code_manifest.json").read_text())
report["code_files"] = code_manifest["files"]
report["bad"] += [f"{CODE_SLUG}/{f}" for f, h in code_manifest["files"].items() if digest(CODE / f) != h]
chosen = {}
for d, root in roots.items():
    files = json.loads((root / "files.json").read_text())
    # a pattern may hold alternatives separated by "|" (1/10: the units of one dataset kept apart from the others)
    chosen[d] = [f for f in files if any(fnmatch.fnmatch(f["file"], p) for p in GLOBS.get(d, "*.h5ad").split("|"))]
    report["datasets"][d] = {"files": len(files), "chosen": len(chosen[d]), "cells": sum(f["cells"] for f in chosen[d])}
shards = [str(roots[d] / f["file"]) for d in DATASETS for f in chosen[d]]
if PREPASS_ARGS is not None:
    # the prepass reads every chosen shard: hash them all against files.json first (CPU, no GPU quota at stake)
    for d, root in roots.items():
        with ThreadPoolExecutor(4) as ex:
            got = list(ex.map(lambda f: ((root / f["file"]).stat().st_size if (root / f["file"]).is_file() else -1,
                                         digest(root / f["file"]) if (root / f["file"]).is_file() else None), chosen[d]))
        report["bad"] += [f"{d}/{f['file']}" for f, (size, h) in zip(chosen[d], got)
                          if size != f["bytes"] or h != f["sha256"]]
    report["verify_seconds"] = round(time.time() - t0, 1)
(OUT / "verify.json").write_text(json.dumps(report, indent=1))
if report["bad"]:
    raise SystemExit(f"code or shards differ from their manifests: {report['bad'][:5]}")
PY, TC = sys.executable, str(CODE / "train_cellnet.py")


def run(cmd, log):
    print(" ".join(map(str, cmd)), flush=True)
    with open(OUT / log, "w") as fh:
        return subprocess.Popen(list(map(str, cmd)), stdout=fh, stderr=subprocess.STDOUT)


if PREPASS_ARGS is not None:
    if run([PY, TC, "prepass", "--shards", *shards, "--axis", ASSETS / "gene_names.csv", "--out", OUT / "prepass",
            *PREPASS_ARGS], "prepass.log").wait() != 0:
        raise SystemExit("prepass failed: see prepass.log")
    prepass = OUT / "prepass"
else:
    prepass = mount(PREPASS_FROM) / "prepass"
# training finds the shards of the prepass state by name and size below /kaggle/input and hashes them against the
# state in a background thread (train_cellnet.resolve_shards, HashCheck): the GPU does not wait on it
ARM_FLAGS = []
for i, (name, code) in enumerate(ARMS):
    ARM_FLAGS += ["--arm", f"{name}={code}@" + (f"cuda:{i}" if GPU else "cpu")]
train = lambda out, extra=(): [PY, TC, "train", "--prepass", prepass, "--out", OUT / out,
                               *(["--descriptors", ASSETS] if (ASSETS / "descriptors.npy").is_file() else []),
                               "--shard-roots", INPUT, *ARM_FLAGS, *TRAIN_ARGS, *extra]
if CYCLE:
    s1, s2 = CYCLE
    checks = {"arms": ARM_FLAGS, "steps": [s1, s2]}
    for tag, extra in (("ref", ["--stop-after-steps", s2]), ("a", ["--stop-after-steps", s1]),
                       ("b", ["--resume", OUT / "cycle_a", "--stop-after-steps", s2])):
        # the short runs of the cycle skip the shard hashes: the training that follows checks them
        checks[f"rc_{tag}"] = run(train(f"cycle_{tag}", list(map(str, extra)) + ["--no-verify"]),
                                   f"cycle_{tag}.log").wait()
    import torch
    ref = torch.load(OUT / "cycle_ref" / "checkpoints" / f"ckpt_{s2:07d}.pt", map_location="cpu", weights_only=False)
    res = torch.load(OUT / "cycle_b" / "checkpoints" / f"ckpt_{s2:07d}.pt", map_location="cpu", weights_only=False)
    pairs = [(ref["models"][m][k], res["models"][m][k]) for m in ref["models"] for k in ref["models"][m]]
    diff = max(float((u.float() - v.float()).abs().max()) for u, v in pairs)
    scale = max(float(u.float().abs().max()) for u, _ in pairs)
    checks.update({"batch_chain_equal": ref["batch_chain"] == res["batch_chain"],
                   "seen_equal": bool((ref["seen"] == res["seen"]).all()), "draws_equal": ref["draws"] == res["draws"],
                   "n_drawn_equal": ref["n_drawn"] == res["n_drawn"],
                   "models_compared": sorted(ref["models"]), "model_max_abs_diff": diff, "model_max_abs": scale,
                   "model_equal": all(torch.equal(u, v) for u, v in pairs),
                   "rule": "the data sequence must be equal; parameters within 1e-5 of the largest parameter on CPU "
                           "(sums over several threads: cycle r2 of 1/10 differed by 7.2e-7 on 74.5) and within 1e-3 "
                           "on GPU (atomic sums are not deterministic)"})
    checks["passed"] = (checks["batch_chain_equal"] and checks["seen_equal"] and checks["draws_equal"]
                        and checks["n_drawn_equal"] and diff <= (1e-3 if GPU else 1e-5) * scale)
    (OUT / "resume_check.json").write_text(json.dumps(checks, indent=1, default=str))
    print("resume check", checks, flush=True)
    if not checks["passed"]:
        raise SystemExit("the resume check failed: see resume_check.json")
code = run(train("train"), "train.log").wait() if ARMS else None      # a prepass kernel trains nothing
(OUT / "kernel_done.json").write_text(json.dumps({"arms": ARMS, "return_code": code,
                                                   "seconds": round(time.time() - t0, 1)}, indent=1))
if code:
    raise SystemExit(f"the training failed with code {code}: see train.log")
