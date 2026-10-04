"""Independently check the six published scores in existing local status receipts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FILES = {
    "t25": "reports/invii/trial_2026-09-27/status_ekxW6wo83Csum25pkddl.json",
    "t28": "reports/invii/trial_2026-09-29/status_ZvrYZ4UazadAyuq4AsDB_20260929T2305.json",
    "t30": "reports/invii/trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json",
}
MEMBERS = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]


def main():
    out = HERE / "score_audit_r1.json"
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    records, inputs = {}, {}
    for name, relative in FILES.items():
        raw = (ROOT / relative).read_bytes()
        record = json.loads(raw)
        assert record["status"] == "published"
        mean = sum(record[m] for m in MEMBERS) / len(MEMBERS)
        assert abs(mean - record["score_avg"]) < 1e-12
        records[name] = record
        inputs[name] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
                        "entry_id": record["entry_id"], "score_avg": record["score_avg"],
                        "mean_of_six": mean}
    assert len({r["panel_id"] for r in records.values()}) == 1
    assert len({r["anchor_version"] for r in records.values()}) == 1
    delta = {m: records["t30"][m] - records["t25"][m] for m in MEMBERS}
    d25 = records["t30"]["score_avg"] - records["t25"]["score_avg"]
    assert abs(sum(delta.values()) / 6 - d25) < 1e-12
    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
        "t30_minus_t25": d25,
        "t30_minus_t28": records["t30"]["score_avg"] - records["t28"]["score_avg"],
        "members": {m: {"t25": records["t25"][m], "t30": records["t30"][m],
                        "delta": delta[m], "contribution_to_score_delta": delta[m] / 6} for m in MEMBERS},
        "registered_branch": "a" if d25 >= 0.005 else "c" if d25 <= -0.005 else "b",
        "pds_raw": {n: records[n]["pds_cosine"] for n in ("t25", "t30")},
        "mse_raw": {n: records[n]["expr_mse_unbiased_capped_norm"] for n in ("t25", "t30")},
        "limit": "Aggregate statuses do not identify per-context causes; no new score request or submission.",
    }
    with out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
