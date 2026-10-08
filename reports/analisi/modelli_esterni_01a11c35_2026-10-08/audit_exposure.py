"""Inspect published PIE split identifiers only, never response values or weights."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from audit_public import PINS


def audit(out):
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    receipts, folds = [], {}
    _, repo, revision = PINS["splits"]
    for fold in ("hepg2", "jurkat", "k562", "rpe1"):
        roles = {}
        for role in ("train", "val"):
            url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/replogle_wdataset/unseen_ctx/{fold}/{role}.json"
            with urlopen(Request(url, headers={"User-Agent":"VCC2026-provenance-audit"}), timeout=60) as stream:
                raw = stream.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("metadata size guard exceeded")
            data = json.loads(raw)
            if not isinstance(data, dict) or not all(isinstance(v, list) for v in data.values()):
                raise ValueError("unexpected split format")
            roles[role] = data
            receipts.append(dict(fold=fold, role=role, url=url, bytes=len(raw),
                                 sha256=hashlib.sha256(raw).hexdigest()))
        contexts = sorted({c for role in roles.values() for c in role})
        targets = sorted({t for role in roles.values() for ts in role.values() for t in ts})
        folds[fold] = dict(published_label_roles=roles,
                           published_contexts=contexts, published_target_symbols=targets,
                           role_rows={r:sum(len(v) for v in data.values()) for r,data in roles.items()},
                           status="published_identifiers_not_independent_exposure_review",
                           complete_label_inventory=False,
                           unresolved=["checkpoint payload not inspected",
                                       "upstream test-driven architecture/model choice unknown",
                                       "canonical alias/component reconciliation pending",
                                       "knowledge sources are distinct exposures needing review"])
    result = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), pins=PINS,
                  fetched_metadata=receipts, folds=folds,
                  downloaded_weights_or_response_arrays=False,
                  protected_h1_test_read=False,
                  admission="pending VALIDAZIONE; do not copy this ledger as reviewed")
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({fold: {k:v for k,v in data.items() if k in {"published_contexts", "role_rows"}}
                      for fold,data in folds.items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    audit(parser.parse_args().out)
