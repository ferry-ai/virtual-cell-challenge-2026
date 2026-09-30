"""Copy only the four reviewed t25 files to a new own-Drive folder; never generate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import traceback


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    report = Path(__file__).resolve().parent
    manifest_file = report / "input_manifest_r1.json"
    expected_manifest = "18dc29195d818cbfc8cb4a5442850e4e9581b60d8cba585afad65daf85a99bae"
    if sha(manifest_file) != expected_manifest:
        raise ValueError("Input manifest changed since review")
    prefix = "data/processed/effects_t25_2026-09-27/"
    names = ["effects_A.npz", "effects_B.npz", "effects_C.npz", "manifest.json"]
    inputs = json.loads(manifest_file.read_text(encoding="utf-8"))
    entries = {e["drive_relative"]: e for e in inputs["files"]}
    selected = [entries[prefix + name] for name in names]
    if sum(e["bytes"] for e in selected) != 52892600:
        raise ValueError("Allowlist byte total changed")
    source_root = Path("C:/Users/ferra/vcc2026-data/processed/effects_t25_2026-09-27").resolve()
    destination = Path("G:/Il mio Drive/vcc2026/data/processed/effects_t25_2026-09-27").resolve()
    transfer_report = report / "transfer_manifest_r1.json"
    if destination.exists() or transfer_report.exists():
        raise FileExistsError("Destination or evidence already exists")
    for name, entry in zip(names, selected, strict=True):
        source = source_root / name
        if source.stat().st_size != entry["bytes"] or sha(source) != entry["sha256"]:
            raise ValueError(f"Source mismatch before transfer: {name}")
    result = {"started_utc": datetime.now(timezone.utc).isoformat(),
              "input_manifest_sha256": expected_manifest, "destination": str(destination),
              "authorization": "Exact four-file own-Drive transfer approved by main session; no generation or submission",
              "files": [], "status": "started"}
    destination.mkdir()
    try:
        for name, entry in zip(names, selected, strict=True):
            source = source_root / name
            target = destination / name
            if not target.resolve().is_relative_to(destination):
                raise ValueError("Unexpected path escape")
            print("copy", name, entry["bytes"], flush=True)
            with source.open("rb") as inp, target.open("xb") as out:
                shutil.copyfileobj(inp, out, 8 * 1024**2)
            actual = sha(target)
            if target.stat().st_size != entry["bytes"] or actual != entry["sha256"]:
                raise ValueError(f"Drive readback mismatch: {name}")
            result["files"].append({"name": name, "bytes": target.stat().st_size,
                                    "source_sha256": entry["sha256"], "drive_sha256": actual,
                                    "comparison": "full SHA256 identical"})
        if sha(manifest_file) != expected_manifest:
            raise ValueError("Input manifest changed during transfer")
        result["status"] = "complete"
    except Exception:
        result.update({"status": "failed", "exception": traceback.format_exc()})
        raise
    finally:
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        with transfer_report.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
