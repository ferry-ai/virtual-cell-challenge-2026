"""Read small technical receipts from completed Kaggle runs, without downloading models.

Requires the owner's configured Kaggle account in KAGGLE_CONFIG_DIR.
Does not start, modify, or stop a remote job; never writes signed URLs or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit("Refusing to replace an existing receipt")
    import requests
    from kaggle.api.kaggle_api_extended import KaggleApi, ApiListKernelSessionOutputRequest

    api = KaggleApi()
    api.authenticate()
    result = {"utc": datetime.now(timezone.utc).isoformat(), "kind": "read_only_technical_receipts", "runs": {}}
    allowed = {"kernel_done.json", "done.json", "coverage.json", "health.json", "verify.json"}
    for slug in ("rcell-anchored-train-h1-r1", "rcell-anchored-train-hepg2-r1"):
        run = {"files": [], "receipts": {}}
        with api.build_kaggle_client() as client:
            request = ApiListKernelSessionOutputRequest()
            request.user_name = "davideferrante11"
            request.kernel_slug = slug
            request.page_size = 200
            while True:
                response = client.kernels.kernels_api_client.list_kernel_session_output(request)
                for item in response.files:
                    name = item.file_name
                    run["files"].append(name)
                    if Path(name).name not in allowed:
                        continue
                    raw = bytearray()
                    with requests.get(item.url, stream=True, timeout=(30, 60)) as r:
                        r.raise_for_status()
                        for chunk in r.iter_content(65536):
                            raw.extend(chunk)
                            if len(raw) > 2_000_000:
                                raise RuntimeError("Technical receipt exceeds 2 MB")
                    run["receipts"][name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "content": json.loads(raw)}
                if not response.next_page_token:
                    break
                request.page_token = response.next_page_token
        result["runs"][slug] = run
        print(slug, "files", len(run["files"]), "receipts", list(run["receipts"]), flush=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
