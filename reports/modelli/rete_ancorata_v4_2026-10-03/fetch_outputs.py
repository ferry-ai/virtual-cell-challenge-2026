"""Fetch the small files of a finished Kaggle kernel's output (manifests, logs, receipts), never its bulk.

    python fetch_outputs.py --config-dir ~/.kaggle-davideferrante11 --slug rcell-v4-anchors-r1 \
        --pattern "*manifest.json" --pattern "*.log" --out <new dir> [--max-bytes 5000000] [--exclude "*/eval*"]

Lists the kernel's output files and downloads those whose path matches a --pattern (fnmatch) and no --exclude, refusing
any file above --max-bytes. Writes the files under --out with their relative paths and fetch_receipt.json (path, bytes,
sha256 of each, and the full listing with sizes when the API gives them). Never starts, changes or stops a job; never
writes signed URLs or credentials.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config-dir", required=True)
    p.add_argument("--owner", default="davideferrante11")
    p.add_argument("--slug", required=True)
    p.add_argument("--pattern", action="append", required=True)
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--max-bytes", type=int, default=5_000_000)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    os.environ["KAGGLE_CONFIG_DIR"] = str(Path(a.config_dir).expanduser())
    import requests
    from kaggle.api.kaggle_api_extended import ApiListKernelSessionOutputRequest, KaggleApi

    api = KaggleApi()
    api.authenticate()
    receipt = {"utc": datetime.now(timezone.utc).isoformat(), "kernel": f"{a.owner}/{a.slug}", "patterns": a.pattern,
               "exclude": a.exclude, "listed": [], "fetched": {}}
    with api.build_kaggle_client() as client:
        request = ApiListKernelSessionOutputRequest()
        request.user_name, request.kernel_slug, request.page_size = a.owner, a.slug, 200
        while True:
            response = client.kernels.kernels_api_client.list_kernel_session_output(request)
            for item in response.files:
                name = item.file_name
                size = getattr(item, "total_bytes", None) or getattr(item, "size", None)
                receipt["listed"].append({"path": name, "bytes": size})
                if not any(fnmatch.fnmatch(name, pat) for pat in a.pattern):
                    continue
                if any(fnmatch.fnmatch(name, pat) for pat in a.exclude):
                    continue
                raw = bytearray()
                with requests.get(item.url, stream=True, timeout=(30, 120)) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(1 << 16):
                        raw.extend(chunk)
                        if len(raw) > a.max_bytes:
                            raise RuntimeError(f"{name} exceeds {a.max_bytes} bytes")
                dest = a.out / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(bytes(raw))
                receipt["fetched"][name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            if not response.next_page_token:
                break
            request.page_token = response.next_page_token
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "fetch_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"listed": len(receipt["listed"]), "fetched": sorted(receipt["fetched"])}))


if __name__ == "__main__":
    main()
