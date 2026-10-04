"""Share private datasets of one Kaggle account with another account as reader; they stay private.

A copy of reports/modelli/risposta_contesto_2026-10-02/kaggle_sums/share_datasets.py with the owner as an argument:
`kaggle datasets metadata <ref> --update` rewrites a dataset's settings from its metadata file, and a file without
isPrivate: true makes the dataset PUBLIC (kaggle 2.2.4), so isPrivate is set to true explicitly and read back.
The owner's token is read from KAGGLE_CONFIG_DIR; no key is printed.

    KAGGLE_CONFIG_DIR=<owner dir> python share_to.py --owner davideferrante11 --readers davidmaisterx \
        --datasets rlead-bench-cube-r2 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--owner", required=True)
    p.add_argument("--readers", nargs="+", required=True)
    p.add_argument("--datasets", nargs="+", required=True)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    for slug in a.datasets:
        ref = f"{a.owner}/{slug}"
        with tempfile.TemporaryDirectory() as d:
            meta_file = Path(api.dataset_metadata(ref, path=d))
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            info = meta.get("info", meta)
            before = dict(isPrivate=info.get("isPrivate"), collaborators=info.get("collaborators"))
            collab = {c["username"]: c for c in (info.get("collaborators") or [])}
            for r in a.readers:
                collab.setdefault(r, {"username": r, "role": "reader"})
            info["collaborators"] = list(collab.values())
            info["isPrivate"] = True
            if "info" in meta:
                meta["info"] = info
            else:
                meta = info
            print(json.dumps({"dataset": ref, "before": before,
                              "after": {"isPrivate": True, "collaborators": info["collaborators"]}}))
            if a.dry_run:
                continue
            meta_file.write_text(json.dumps(meta), encoding="utf-8")
            api.dataset_metadata_update(ref, d)
            check = json.loads(Path(api.dataset_metadata(ref, path=d)).read_text(encoding="utf-8"))
            check = check.get("info", check)
            print(json.dumps({"dataset": ref, "now": {"isPrivate": check.get("isPrivate"),
                                                      "collaborators": check.get("collaborators")}}))
            if check.get("isPrivate") is not True:
                raise SystemExit(f"{ref} is not private after the update: stop and check by hand")


if __name__ == "__main__":
    main()
