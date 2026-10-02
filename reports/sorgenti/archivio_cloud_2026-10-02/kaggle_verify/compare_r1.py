"""Compare the sha256 computed on Kaggle (verify_kaggle.json) with the publish receipts on Drive and the local hashes.

Shards are compared with the sha256 in the latest publish receipt of their dataset (read by name from Drive);
files of the vcc-* datasets with a local file of the same name and size in the folder they were published from.
Writes one JSON, refusing to overwrite.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--kaggle-json", required=True, type=Path)
p.add_argument("--drive-listing", required=True, type=Path)
p.add_argument("--local-hashes", type=Path, default=None)
p.add_argument("--out", required=True, type=Path)
a = p.parse_args()
if a.out.exists():
    sys.exit(f"refusing: {a.out} exists")
k = json.loads(a.kaggle_json.read_text(encoding="utf-8"))
drive_root = Path(r"G:\Il mio Drive\vcc2026")
rows = [l.split("\t") for l in a.drive_listing.read_text(encoding="utf-8").splitlines()]
receipts = sorted(r[0] for r in rows if len(r) == 3 and "\\receipts\\" in r[0] and "publish_rlab-" in r[0])
expected: dict[str, dict[str, dict]] = {}
for rel in receipts:  # later setup folders sort later: the last receipt of a dataset wins
    d = json.loads((drive_root / rel).read_text(encoding="utf-8"))
    expected[d["dataset"]] = {f["file"]: f for f in d["files"]}
# Local folders the vcc-* datasets were published from (registry rows and corpus_basale notes).
LOCAL_FOR = {"vcc-rete-contesti-r1": "processed/rete_contesti_r1/", "vcc-rete-contesti-r2": "processed/rete_contesti_r2/",
             "vcc-corpus-basale-r1": "kaggle/corpus_basale_r1/", "vcc-corpus-tahoe-r1": "kaggle/corpus_tahoe_r1/",
             "vcc-stack-prompts-r1": "interim/kaggle_stack_prompts_r1/"}
local = {}
if a.local_hashes and a.local_hashes.exists():
    with a.local_hashes.open(encoding="utf-8") as fh:
        local = {r["rel"]: r for r in csv.DictReader(fh, delimiter="\t") if r["sha256"]}
results = []
for f in k["files"]:
    parts = f["path"].split("/")
    ds = "/".join(parts[1:3]) if parts[0] == "datasets" else parts[0]
    name = "/".join(parts[3:]) if parts[0] == "datasets" else "/".join(parts[1:])
    rec = {"dataset": ds, "file": name, "bytes": f["bytes"], "sha256_kaggle": f["sha256"]}
    exp = expected.get(ds, {}).get(name)
    slug = ds.split("/")[-1]
    if exp:
        rec["reference"] = "publish receipt"
        rec["status"] = "match" if exp["sha256"] == f["sha256"] and exp["bytes"] == f["bytes"] else "MISMATCH"
    elif slug in LOCAL_FOR:
        lrel = LOCAL_FOR[slug] + name
        lh = local.get(lrel)
        if lh:
            rec["reference"] = f"local {lrel}"
            rec["status"] = "match" if lh["sha256"] == f["sha256"] else "MISMATCH"
        else:
            rec["reference"] = f"local {lrel}"
            rec["status"] = "no_local_hash"
    else:
        rec["status"] = "no_reference"
    results.append(rec)
by_ds = defaultdict(Counter)
for r in results:
    by_ds[r["dataset"]][r["status"]] += 1
missing = []
for ds, files in expected.items():
    if ds.startswith("davidmaisterx/") and ds.split("/")[1] in {x.split("/")[-1] for x in by_ds}:
        seen = {r["file"] for r in results if r["dataset"] == ds}
        missing += [f"{ds}/{n}" for n in files if n not in seen]
doc = {"kaggle_json": str(a.kaggle_json), "summary": {d: dict(c) for d, c in sorted(by_ds.items())},
       "receipt_files_not_found_on_kaggle": missing, "results": results}
a.out.write_text(json.dumps(doc, indent=0), encoding="utf-8")
tot = Counter(r["status"] for r in results)
print(json.dumps({"total": dict(tot), "missing_from_kaggle": len(missing)}))
for d, c in sorted(by_ds.items()):
    print(f"  {d:45s} {dict(c)}")
