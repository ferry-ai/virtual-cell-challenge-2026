"""Push one prepared CPU kernel once; retain the lock on ambiguous outcomes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from input_contract import sha

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--stage", type=Path, required=True)
p.add_argument("--log", type=Path, required=True)
a = p.parse_args()
m = json.loads((a.stage / "kernel-metadata.json").read_text())
r = json.loads((a.stage / "preflight_local.json").read_text())
if m["enable_gpu"] or m["enable_tpu"] or not r["ok"]:
    raise SystemExit("requires CPU and passed local preflight")
owner, slug = m["id"].split('/')
config = Path.home() / (".kaggle" if owner == "davidmaisterx" else ".kaggle-davideferrante11")
record = {"job": m["id"], "stage": str(a.stage), "utc": datetime.now(timezone.utc).isoformat(),
          "run_sha256": sha(a.stage / "run.py"), "contract_sha256": sha(a.stage / "input_contract.json"),
          "preflight_sha256": sha(a.stage / "preflight_local.json")}
with (a.stage.parent / (slug + ".launch.lock")).open("x", encoding="utf-8") as f:
    json.dump(record, f)
result = subprocess.run([str(Path(sys.executable).with_name("kaggle.exe")), "kernels", "push", "-p", str(a.stage)],
                        env={**os.environ, "KAGGLE_CONFIG_DIR": str(config)}, capture_output=True, text=True)
answer = (result.stdout + result.stderr).strip()
record.update(returncode=result.returncode, answer=answer,
              accepted=result.returncode == 0 and "successfully pushed" in answer and "not valid" not in answer)
with a.log.open("a", encoding="utf-8") as f:
    f.write(json.dumps(record) + "\n")
print(json.dumps(record))
if not record["accepted"]:
    raise SystemExit(1)
