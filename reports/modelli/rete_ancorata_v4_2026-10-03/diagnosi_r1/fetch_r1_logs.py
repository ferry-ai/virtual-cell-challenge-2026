"""Fetch the technical logs of the two finished anchored trainings (v3, r1), never their results.

    python fetch_r1_logs.py --config-dir ~/.kaggle-davideferrante11 --raw <new dir in the data root> --out <new dir>

Reads the output listing of rcell-anchored-train-h1-r1 and -hepg2-r1 (owner davideferrante11) and downloads only an
allowlist of technical files: environment, plan, config, coverage, health, verification, the resolved shards and the
two logs. Never the evaluation (eval.json, eval_shifts.npz, eval_observed.npz, eval_groups.json), models or
checkpoints. The raw files go to --raw, with their sha256; the logs are copied to --out without the lines whose
message is "eval" (the per-arm summaries written after the evaluation), so that a protocol can be frozen before any
result of these runs is read. Does not start, change or stop a remote job; never writes signed URLs or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

SLUGS = ("rcell-anchored-train-h1-r1", "rcell-anchored-train-hepg2-r1")
OWNER = "davideferrante11"
ALLOWED = {"env.json", "kernel_done.json", "verify.json", "train.log", "train/plan.json", "train/config.json",
           "train/coverage.json", "train/done.json", "train/health.json", "train/verify.json",
           "train/shards_resolved.json", "train/train_log.jsonl"}
LOGS = {"train.log", "train/train_log.jsonl"}
RESULT_MESSAGES = {"eval"}
MAX_BYTES = 60_000_000


def strip_results(raw: bytes) -> tuple[bytes, int]:
    """The log without its result lines: a line that parses as JSON with msg in RESULT_MESSAGES is dropped."""
    kept, dropped = [], 0
    for line in raw.decode("utf-8", errors="replace").splitlines():
        try:
            msg = json.loads(line).get("msg")
        except (ValueError, AttributeError):
            msg = None
        if msg in RESULT_MESSAGES:
            dropped += 1
            continue
        kept.append(line)
    return ("\n".join(kept) + "\n").encode("utf-8"), dropped


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    for d in (a.raw, a.out):
        if d.exists():
            raise SystemExit(f"refusing: {d} exists")
    os.environ["KAGGLE_CONFIG_DIR"] = str(Path(a.config_dir).expanduser())
    import requests
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest, KaggleApi

    api = KaggleApi()
    api.authenticate()
    receipt = {"utc": datetime.now(timezone.utc).isoformat(), "kind": "read_only_technical_logs",
               "allowed": sorted(ALLOWED), "result_messages_dropped_from_logs": sorted(RESULT_MESSAGES), "runs": {}}
    for slug in SLUGS:
        run = {"listed": [], "fetched": {}}
        with api.build_kaggle_client() as client:
            request = ApiListKernelSessionOutputRequest()
            request.user_name, request.kernel_slug, request.page_size = OWNER, slug, 200
            while True:
                response = client.kernels.kernels_api_client.list_kernel_session_output(request)
                for item in response.files:
                    name = item.file_name
                    run["listed"].append(name)
                    if name not in ALLOWED:
                        continue
                    raw = bytearray()
                    with requests.get(item.url, stream=True, timeout=(30, 120)) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(1 << 16):
                            raw.extend(chunk)
                            if len(raw) > MAX_BYTES:
                                raise RuntimeError(f"{slug}/{name} exceeds {MAX_BYTES} bytes")
                    raw = bytes(raw)
                    dest = a.raw / slug / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(raw)
                    entry = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "raw": str(dest)}
                    if name in LOGS:
                        clean, dropped = strip_results(raw)
                        target = a.out / slug / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(clean)
                        entry.update({"report_copy": str(target), "result_lines_dropped": dropped,
                                      "report_copy_sha256": hashlib.sha256(clean).hexdigest()})
                    elif not name.startswith("train/shards_resolved"):
                        target = a.out / slug / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(raw)
                        entry["report_copy"] = str(target)
                    run["fetched"][name] = entry
                if not response.next_page_token:
                    break
                request.page_token = response.next_page_token
        receipt["runs"][slug] = run
        print(slug, "listed", len(run["listed"]), "fetched", sorted(run["fetched"]), flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "fetch_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
