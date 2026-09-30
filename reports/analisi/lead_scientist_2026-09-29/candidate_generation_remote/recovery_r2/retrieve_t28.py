"""Recover only a completed, validated t28 container; no submission."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

GENERATION_SHA = "123ce93f4d8d21c107215c96f726a6b7121545c1329948f431234eabce80f40e"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    complete = read(args.source / "completion.json")
    transfer = read(args.source / "transfer_verification.json")
    packaging = read(args.source / "pack/packaging.json")
    verified = packaging["verification"]
    expected = verified["archive_sha256"]
    size = verified["archive_bytes"]
    if (complete.get("status") != "complete" or complete.get("prediction_sha256") != GENERATION_SHA
            or complete.get("vcc_sha256") != expected or transfer.get("sha256") != expected
            or transfer.get("bytes") != size or packaging.get("exit_code") != 0
            or verified.get("official_container_validator") != "passed"
            or not isinstance(verified.get("payload_vs_input"), dict)
            or transfer.get("local_vs_drive_full_sha256") != "identical"):
        raise ValueError("Remote container is not completely verified")
    source = args.source / "prediction.vcc"
    if source.stat().st_size != size:
        raise ValueError("Incomplete source VCC size")
    if shutil.disk_usage(args.out.parent).free < size + 1024**3:
        raise ValueError("Insufficient local free disk for verified retrieval")
    args.out.mkdir()
    pending = args.out / "prediction.vcc.partial"
    shutil.copyfile(source, pending)
    digest = sha(pending)
    if pending.stat().st_size != size or digest != expected:
        raise ValueError("Local VCC copy differs; partial retained, no ready receipt")
    pending.rename(args.out / "prediction.vcc")
    files = ["completion.json", "transfer_verification.json", "pack/packaging.json",
             "pack/manifest_48_package_prediction.json", "gen/generation_diagnostics.json",
             "gen/manifest_45_generate_prediction.json"]
    hashes = {}
    for name in files:
        destination = args.out / Path(name).name
        shutil.copyfile(args.source / name, destination)
        hashes[name] = sha(destination)
    receipt = {"status": "local_container_ready_not_submitted", "utc": datetime.now(timezone.utc).isoformat(),
               "source": str(source), "destination": str(args.out / "prediction.vcc"),
               "bytes": size, "sha256": expected, "generation_sha256": GENERATION_SHA,
               "metadata_sha256": hashes, "submission": False}
    with (args.out / "retrieval.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2); stream.write("\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
