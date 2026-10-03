"""Verify a narrow allowlist against independent Kaggle hashes; never delete files."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ALLOWED = {
    f"{folder}/{name}.npy"
    for folder in ("kaggle/rete_data_r1", "processed/rete_contesti_r1", "processed/rete_contesti_r2")
    for name in ("raw", "se", "shrunk")
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--archive-run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    root = args.root.resolve(strict=True)
    inventory_path = args.archive_run / "local_hashes.tsv"
    inventory = {r["rel"]: r for r in csv.DictReader(inventory_path.open(encoding="utf-8"), delimiter="\t")}
    proof_path = args.archive_run / "kaggle_verify_r2/compare_full.json"
    proofs = defaultdict(list)
    for record in json.loads(proof_path.read_text(encoding="utf-8"))["results"]:
        if record.get("status") == "match":
            proofs[record["sha256_kaggle"]].append(record)
    rows, physical = [], {}
    for rel in sorted(ALLOWED):
        path = (root / rel).resolve(strict=True)
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise ValueError(f"Unsafe path: {rel}")
        before = path.stat()
        old = inventory[rel]
        if before.st_size != int(old["bytes"]):
            raise ValueError(f"Changed size: {rel}")
        expected = old["sha256"]
        matching = [p for p in proofs[expected] if int(p["bytes"]) == before.st_size]
        if not matching:
            raise ValueError(f"No independent remote proof: {rel}")
        file_id = f"{before.st_dev}:{before.st_ino}"
        if file_id not in physical:
            print(f"Hashing {rel} ({before.st_size / 2**30:.3f} GiB)", flush=True)
            if sha256(path) != expected:
                raise ValueError(f"Hash mismatch: {rel}")
            physical[file_id] = {"bytes": before.st_size, "links": before.st_nlink, "paths": []}
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError(f"Changed while hashing: {rel}")
        physical[file_id]["paths"].append(rel)
        rows.append({"rel": rel, "path": str(path), "bytes": before.st_size, "mtime_ns": before.st_mtime_ns,
                     "file_id": file_id, "nlink": before.st_nlink, "sha256": expected, "remote_proofs": matching})
        print(f"Verified {rel}", flush=True)
    if any(p["links"] != len(p["paths"]) for p in physical.values()):
        raise ValueError("Unaccounted hard links: no removal plan produced")
    result = {"verified_utc": datetime.now(timezone.utc).isoformat(), "root": str(root),
              "proof_path": str(proof_path), "proof_sha256": sha256(proof_path),
              "inventory_path": str(inventory_path), "inventory_sha256": sha256(inventory_path),
              "rows": rows, "unique_bytes": sum(p["bytes"] for p in physical.values()),
              "physical_files": len(physical), "paths": len(rows), "operation": "verified_local_copy_candidates_only"}
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}), flush=True)


if __name__ == "__main__":
    main()
