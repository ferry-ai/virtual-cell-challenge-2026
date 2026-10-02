"""Manifest of data that were already only on Drive before the migration, with the sha256 recorded when written.

Corpus shards: every unit manifest `data/processed/corpus_cellulare_2026-09-30/<job>/<unit>/manifest.json`
of a job that wrote its `complete.json`, read by name from the Drive mount (small files), lists its shards with
bytes and sha256 computed by the job on Colab. Raw files: their fetch records on Drive. The output has the shape
verify_drive.py reads ({"files": [{"rel", "bytes", "sha256"}]}, paths relative to the data root) and a sidecar.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--drive-listing", required=True, type=Path)
p.add_argument("--drive-root", default=r"G:\Il mio Drive\vcc2026", type=Path)
p.add_argument("--out", required=True, type=Path)
a = p.parse_args()
if a.out.exists():
    sys.exit(f"refusing: {a.out} exists")
rows = [l.split("\t") for l in a.drive_listing.read_text(encoding="utf-8").splitlines()]
paths = {r[0].replace("\\", "/"): int(r[1]) for r in rows if len(r) == 3 and r[0] != "ERROR"}
prefix = "data/processed/corpus_cellulare_2026-09-30/"
complete_jobs = {p_.split("/")[3] for p_ in paths if p_.startswith(prefix) and p_.endswith("/complete.json")
                 and p_.count("/") == 4}
files, skipped = [], []
for rel in sorted(paths):
    parts = rel.split("/")
    if not (rel.startswith(prefix) and len(parts) == 6 and parts[-1] == "manifest.json"):
        continue
    job, unit = parts[3], parts[4]
    if job not in complete_jobs:
        skipped.append({"manifest": rel, "reason": "job without complete.json"})
        continue
    m = json.loads((a.drive_root / rel).read_text(encoding="utf-8"))
    for s in m["shards"]:
        # A shard reused from an earlier attempt keeps its original location in `path`.
        colab = "/content/drive/MyDrive/vcc2026/"
        srel = s["path"][len(colab):] if s.get("path", "").startswith(colab) else f"{prefix}{job}/{unit}/{s['shard']}.h5ad"
        if srel not in paths:
            skipped.append({"shard": srel, "reason": "listed by the unit manifest, absent from the Drive listing"})
            continue
        files.append({"rel": srel[len("data/"):], "bytes": s["bytes"], "sha256": s["sha256"],
                      "source": f"unit manifest {rel}"})
for fetch_rel in sorted(x for x in paths if x.startswith("data/raw/") and x.endswith(".fetch.json")):
    rec = json.loads((a.drive_root / fetch_rel).read_text(encoding="utf-8"))
    target = fetch_rel[: -len(".fetch.json")]
    sha = rec.get("sha256")
    if sha and target in paths:
        files.append({"rel": target[len("data/"):], "bytes": paths[target], "sha256": sha,
                      "source": f"fetch record {fetch_rel}", "fetch_record": rec})
    else:
        skipped.append({"fetch": fetch_rel, "reason": "no sha256 in the record or target absent", "record": rec})
doc = {"files": files, "skipped": skipped, "complete_jobs": sorted(complete_jobs)}
a.out.write_text(json.dumps(doc, indent=0), encoding="utf-8")
digest = hashlib.sha256(a.out.read_bytes()).hexdigest()
Path(str(a.out.with_suffix("")) + ".sha256").write_text(f"{digest}  {a.out.name}\n", encoding="utf-8")
print(json.dumps({"files": len(files), "GiB": round(sum(f["bytes"] for f in files) / 2**30, 2),
                  "skipped": len(skipped), "jobs": len(complete_jobs), "sha256": digest}))
