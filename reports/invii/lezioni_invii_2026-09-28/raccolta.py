"""Gather every official result the repository saved, one row per scored entry, with the six members.

Reads `reports/invii/trial_*/status_*.json` and `reports/invii/trial_*/submit_*_raw.json` (utf-8 with or without BOM; a single
object, a list of objects, or an object wrapping them), keeps the entries that carry a score, merges what the files
say about the same entry id, and writes `invii.csv`: entry, date, trial (from the model name), mean, rank, the six
scaled members and the six raw ones. What a file lacks stays empty: nothing is filled in by hand.

    scripts/py.cmd reports/invii/lezioni_invii_2026-09-28/raccolta.py --out reports/invii/lezioni_invii_2026-09-28/invii.csv
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCALED = ["score_pds", "score_mse", "score_nmae", "score_fid", "score_reach", "score_jac"]
RAW = ["pds_cosine", "expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae",
       "de_wilcoxon_direction_fidelity_yield_raw", "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard"]


def entries(obj):
    """Yield every dict that looks like an entry (has an entry id)."""
    if isinstance(obj, dict):
        if "entry_id" in obj or ("id" in obj and "model_name" in obj):
            yield obj
        for v in obj.values():
            if isinstance(v, (dict, list)):
                yield from entries(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from entries(v)


def trial_of(name: str) -> str:
    m = re.search(r"trial-(\d+)", name or "")
    return f"t{int(m.group(1)):02d}" if m else ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists")
    merged: dict[str, dict] = {}
    for f in sorted(glob.glob(str(REPO / "reports/invii/trial_*/status_*.json")) +
                    glob.glob(str(REPO / "reports/invii/trial_*/submit_*_raw.json"))):
        try:
            obj = json.loads(Path(f).read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        for e in entries(obj):
            eid = e.get("entry_id") or e.get("id")
            row = merged.setdefault(eid, {"entry_id": eid, "files": []})
            row["files"].append(str(Path(f).relative_to(REPO)).replace("\\", "/"))
            for k in ["model_name", "submission_date", "score_avg", "rank", "status"] + SCALED + RAW:
                if e.get(k) is not None and row.get(k) is None:
                    row[k] = e[k]
    table = pd.DataFrame(merged.values())
    table = table[table["score_avg"].notna()].copy()
    table["trial"] = table["model_name"].map(trial_of)
    table["files"] = table["files"].map(lambda v: ";".join(sorted(set(v))))
    cols = ["trial", "entry_id", "submission_date", "score_avg", "rank"] + SCALED + RAW + ["model_name", "files"]
    table = table.reindex(columns=cols).sort_values("submission_date")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)
    pd.set_option("display.width", 220)
    print(table[["trial", "submission_date", "score_avg", "rank"] + SCALED].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
