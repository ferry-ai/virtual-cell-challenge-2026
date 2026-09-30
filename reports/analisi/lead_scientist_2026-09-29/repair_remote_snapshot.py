"""Replace only the audited serialization repair in an immutable remote snapshot."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

p = argparse.ArgumentParser()
p.add_argument("--source", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
p.add_argument("--reason", default="pickle-free Unicode gene axis; regression test; no scoring occurred in r1")
a = p.parse_args()
repo = Path(__file__).resolve().parents[3]
prefix = "reports/analisi/lead_scientist_2026-09-29/"
replace = {prefix + name for name in ("generator_bench.py", "test_generator_bench.py")}
a.out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((a.source / "input_manifest.json").read_text())
archive = a.out / "code_snapshot.tar.gz"
seen = set()
with tarfile.open(a.source / "code_snapshot.tar.gz", "r:gz") as src, tarfile.open(archive, "w:gz") as dest:
    for member in src.getmembers():
        if not member.isfile() or Path(member.name).is_absolute() or ".." in Path(member.name).parts:
            raise ValueError(member.name)
        content = (repo / member.name).read_bytes() if member.name in replace else src.extractfile(member).read()
        if member.name in replace:
            seen.add(member.name)
            for row in manifest["code_files"]:
                if row["relative_path"] == member.name:
                    row.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        member.size = len(content)
        dest.addfile(member, io.BytesIO(content))
assert seen == replace, seen
if "repair" in manifest:
    manifest.setdefault("previous_repairs", []).append(manifest["repair"])
manifest["repair"] = {"reason": a.reason, "changed_files": sorted(replace)}
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
manifest["code_archive"] = {"name": archive.name, "bytes": archive.stat().st_size, "sha256": digest}
(a.out / "input_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest["code_archive"]))
