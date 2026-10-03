"""Audit recorded, small metadata only; never open expression matrices or train."""
import argparse
import csv
import gzip
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.out.exists():
        raise FileExistsError(args.out)
    inputs = []

    def read(path):
        data = (root / path).read_bytes()
        inputs.append({"path": str(path).replace("\\", "/"), "bytes": len(data),
                       "sha256": hashlib.sha256(data).hexdigest()})
        return data

    base = Path("reports/modelli/rete_cellulare_2026-10-03/esito")
    support, caps, coverages = [], [], {}
    for fold in ("h1", "hepg2", "rpe1"):
        folder = base / "matrix_r1" / fold
        rows = list(csv.DictReader(gzip.decompress(read(folder / "target_by_group.csv.gz")).decode().splitlines()))
        eval_rows = list(csv.DictReader(read(folder / "eval_support.csv").decode().splitlines()))
        assert len({(r["symbol"], r["group"], r["modality"]) for r in rows}) == len(rows)
        assert all(int(r["training_cells"]) > 0 for r in rows)
        assert all(r["group"].lower() != fold for r in rows)
        for mode in ("all", "CRISPRi"):
            counts = Counter()
            for row in rows:
                if mode == "all" or row["modality"] == mode:
                    counts[row["symbol"], row["group"]] += int(row["training_cells"])
            for minimum in (1, 20, 50):
                groups = Counter(symbol for (symbol, group), n in counts.items() if n >= minimum)
                for cls in ("C", "J"):
                    targets = [r["symbol"] for r in eval_rows if r["class"] == cls]
                    assert len(targets) == len(set(targets))
                    bins = Counter(groups[t] for t in targets)
                    support.append({"fold": fold, "mode": mode, "minimum_cells": minimum,
                                    "class": cls, "targets": len(targets),
                                    "zero_groups": bins[0], "le_two_groups": sum(v for k, v in bins.items() if k <= 2),
                                    "ge_three_groups": sum(v for k, v in bins.items() if k >= 3),
                                    "group_histogram": json.dumps(dict(sorted(bins.items())))})
            # This collapses donor/state/study/guide: a lower bound if each finer stratum gets its own cap.
            total = sum(counts.values())
            for cap in (32, 64, 128):
                selected = sum(min(n, cap) for n in counts.values())
                caps.append({"fold": fold, "mode": mode, "cap": cap,
                             "group_target_pairs": len(counts), "recorded_cells": total,
                             "coarse_capped_cells_lower_bound": selected,
                             "coarse_fraction": selected / total})
        coverage = json.loads(read(base / f"train_{fold}_r3" / "coverage.json"))
        coverages[fold] = {k: coverage[k] for k in ("steps", "batch", "epochs_done", "admitted_training_cells", "draws", "distinct_cells_seen", "throughput")}
    outcomes = {}
    for lane, path in (("A", "decision_r3/decision.json"), ("B", "decision_laneB_r3/decision_lane_b.json")):
        outcomes[lane] = json.loads(read(base / path))["outcome"]
    manifest = json.loads(read(Path("reports/analisi/generalizzazione_contesti_2026-10-02/p0_r2/input_manifest.json")))
    sizes = defaultdict(lambda: {"files": 0, "bytes": 0})
    for item in manifest["files"]:
        sizes[item["table"]]["files"] += 1
        sizes[item["table"]]["bytes"] += item["bytes"]
    total = sum(item["bytes"] for item in manifest["files"])
    result = {
        "written_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "scope": "Reanalysis of recorded metadata; no current raw-data integrity check, no training, no new VCC score.",
        "limitations": ["Cell counts may represent admitted training appearances, not deduplicated biological cells across releases.",
                        "Coarse caps collapse donors/states/studies/guides and exclude controls; they are lower bounds for per-stratum caps, not recommended training sizes.",
                        "20/50-cell filters are descriptive sensitivity checks, not validated eligibility thresholds.",
                        "Input manifest sizes describe an earlier snapshot and do not measure the full cellular archive."],
        "recorded_effect_manifest": {"written_utc": manifest["written_utc"], "files": len(manifest["files"]),
                                     "bytes": total, "GB_decimal": total / 1e9, "GiB": total / 2**30,
                                     "recorded_hash_mismatches": manifest["hash_mismatches"], "by_table": dict(sizes)},
        "pilot_coverage": coverages, "pilot_outcomes": outcomes, "inputs": inputs,
    }
    args.out.mkdir(parents=True)
    (args.out / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, records in (("support.csv", support), ("coarse_caps.csv", caps)):
        with (args.out / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    print(json.dumps({"out": str(args.out), "input_files": len(inputs), "input_bytes": sum(i["bytes"] for i in inputs),
                      "effect_snapshot_GB": result["recorded_effect_manifest"]["GB_decimal"]}, indent=2))


if __name__ == "__main__":
    main()
