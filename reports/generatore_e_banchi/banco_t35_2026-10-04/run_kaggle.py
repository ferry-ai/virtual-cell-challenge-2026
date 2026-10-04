"""Kaggle CPU kernel of the t35 bench (PROTOCOLLO.md in this folder), modelled on the route C kernel.

Finds the code dataset (code.zip or its auto-extracted files), checks it against code_manifest.json, installs
cell_eval2 0.16.0 from its wheel, then runs banco_t35.py on every shard below /kaggle/input."""
import hashlib, json, os, platform, subprocess, sys, time, zipfile
from pathlib import Path

INPUT, OUT = Path("/kaggle/input"), Path("/kaggle/working")


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


def find(name):
    return sorted(INPUT.rglob(name))


env = {"python": sys.version.split()[0], "cpus": os.cpu_count(), "platform": platform.platform(),
       "memory": sh("free -m"), "disk": sh("df -h /kaggle/working | tail -1"),
       "input_tree": sh("find /kaggle/input -maxdepth 4 -type d | head -60"),
       "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
(OUT / "env.json").write_text(json.dumps(env, indent=1))

manifest = json.loads(find("code_manifest.json")[0].read_text())
code = OUT / "code"
zips = find("code.zip")
if zips:
    zipfile.ZipFile(zips[0]).extractall(code)
else:
    code = find("banco_t35.py")[0].parent
bad = [n for n, h in manifest["files"].items() if hashlib.sha256((code / n).read_bytes()).hexdigest() != h]
if bad:
    raise SystemExit(f"code differs from code_manifest.json: {bad}")

wheel = find("cell_eval2-0.16.0-py3-none-any.whl")[0]
print(sh(f"{sys.executable} -m pip install -q {wheel}"), flush=True)
print(sh(f"{sys.executable} -c \"import cell_eval2, anndata, scanpy, polars, numba; print('scorer ok')\""), flush=True)

axis = [p for p in find("gene_names.csv") if "rlead-assets" in str(p)] or find("gene_names.csv")
obiettivi = find("obiettivi.json")[0].parent
cmd = [sys.executable, "-u", str(code / "banco_t35.py"), "--inputs", str(INPUT), "--axis", str(axis[0]),
       "--obiettivi", str(obiettivi), "--out", str(OUT / "out"), "--code", str(code / "src")]
print(" ".join(cmd), flush=True)
with open(OUT / "banco.log", "w") as fh:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        if "de_lfc_nmae: omitted" in line:
            continue
        fh.write(line); fh.flush()
        print(line, end="", flush=True)
    rc = p.wait()
(OUT / "kernel_done.json").write_text(json.dumps({"returncode": rc, "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                   "repo_commit": manifest["repo_commit"]}, indent=1))
if rc:
    raise SystemExit(rc)
