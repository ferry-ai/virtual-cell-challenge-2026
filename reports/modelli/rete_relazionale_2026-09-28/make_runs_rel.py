"""Write runs.json for the first round of the relational network (RISULTATI.md, rule of 28/09 19:58). Standard
library only. Modelled on reports/modelli/encoder_contesto_2026-09-28/make_runs.py (not edited): the same
runs.json format, read by that folder's run_list.py and by compare_rel.py.

    python make_runs_rel.py --out runs.json --code /kaggle/working/code --data /kaggle/input/<r2 dataset> \
        --work /tmp/rel --keep /kaggle/working/rel --test-targets-dir /kaggle/working/code
    then in Kaggle session k (0 and 1):   python run_list.py --runs runs.json --shard k --keep-small

The round, as registered:
* designs (whole families out, as r1 and r2): e1_k562 (hold out k562: k562, k562ess and viperturb leave), e1_cd4
  (cd4_Rest: the three CD4 conditions leave), e2_orion (orion_hct116 + orion_hek293t; both truths also count as E1
  truths), j_k562 and j_hct116 (--regime J), e2_lab (k562 + viperturb, same line, another lab and chemistry;
  descriptive);
* test targets: for e1_k562, e1_cd4 and e2_orion the r2 round's lists (--test-targets DIR/tt_<design>.txt, the
  files r2 read); for the J designs and e2_lab those train.py draws with --test-seed 0 (its default);
* conditions, all through train_rel.py on the same schedule (validation at step 0 and every 25 steps, patience 12,
  at most 3,000 steps, refit as in r1): none (--arch r1), rel0 (--arch rel --rel-cards svd), rel1 (--arch rel
  --rel-cards learned, exploratory);
* seeds: none and rel0 0, 1, 2 on the first five designs; e2_lab seed 0 only; rel1 seed 0 on e1_k562, e1_cd4 and
  e2_orion: 35 network runs;
* shards: 0 = e1_k562, e2_orion, e2_lab; 1 = e1_cd4, j_k562, j_hct116. Within a shard, seed by seed, design by
  design, none first: a session cut short leaves complete seeds. The last run of each shard is compare_rel.py,
  with the seed-averaged folders (float16) that score_pred.py and score_pair.py read.
A network run is done when its rel_config.json exists. --train-args and --j-args add arguments (none in the
registered round); --j-args '--val-m as-train' is the change the self-test motivates for J (train_rel.py --help).
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

DESIGNS = {
    "e1_k562": {"kind": "E1", "hold_out": "k562", "regime": "C", "r2_targets": True,
                "hidden": ["k562", "k562ess", "viperturb"]},
    "e1_cd4": {"kind": "E1", "hold_out": "cd4_Rest", "regime": "C", "r2_targets": True,
               "hidden": ["cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"]},
    "e2_orion": {"kind": "E2", "hold_out": "orion_hct116,orion_hek293t", "regime": "C", "r2_targets": True,
                 "hidden": ["orion_hct116", "orion_hek293t"]},
    "j_k562": {"kind": "J", "hold_out": "k562", "regime": "J", "r2_targets": False,
               "hidden": ["k562", "k562ess", "viperturb"]},
    "j_hct116": {"kind": "J", "hold_out": "orion_hct116", "regime": "J", "r2_targets": False,
                 "hidden": ["orion_hct116", "orion_hek293t"]},
    "e2_lab": {"kind": "E2", "hold_out": "k562,viperturb", "regime": "C", "r2_targets": False,
               "hidden": ["k562", "k562ess", "viperturb"], "descriptive": True},
}
CONDITIONS = {
    "none": ["--arch", "r1"],
    "rel0": ["--arch", "rel", "--rel-cards", "svd"],
    "rel1": ["--arch", "rel", "--rel-cards", "learned"],
}
PLAN = {                                  # design -> condition -> seeds (RISULTATI.md)
    "e1_k562": {"none": [0, 1, 2], "rel0": [0, 1, 2], "rel1": [0]},
    "e1_cd4": {"none": [0, 1, 2], "rel0": [0, 1, 2], "rel1": [0]},
    "e2_orion": {"none": [0, 1, 2], "rel0": [0, 1, 2], "rel1": [0]},
    "j_k562": {"none": [0, 1, 2], "rel0": [0, 1, 2]},
    "j_hct116": {"none": [0, 1, 2], "rel0": [0, 1, 2]},
    "e2_lab": {"none": [0], "rel0": [0]},
}
SHARDS = {0: ["e1_k562", "e2_orion", "e2_lab"], 1: ["e1_cd4", "j_k562", "j_hct116"]}
SCHEDULE = ["--eval-step0", "--eval-every", "25", "--patience", "12", "--steps", "3000"]


def build(args) -> dict:
    code, net_code = args.code.rstrip("/"), (args.net_code or f"{args.code.rstrip('/')}/../rete_contesti_2026-09-27")
    run_list_code = args.run_list_code or code
    work, keep = args.work.rstrip("/"), args.keep.rstrip("/")
    designs = [d.strip() for d in args.designs.split(",") if d.strip()]
    for d in designs:
        if d not in DESIGNS:
            raise SystemExit(f"unknown design {d!r} (known: {sorted(DESIGNS)})")
    if any(DESIGNS[d]["r2_targets"] for d in designs) and not args.test_targets_dir:
        raise SystemExit("--test-targets-dir is required: e1_k562, e1_cd4 and e2_orion read the r2 round's lists")
    extra, j_extra = shlex.split(args.train_args), shlex.split(args.j_args)
    runs = []
    for k, shard_designs in SHARDS.items():
        mine = [d for d in shard_designs if d in designs]
        for seed in (0, 1, 2):
            for d in mine:
                for cond in ("none", "rel0", "rel1"):
                    if seed not in PLAN[d].get(cond, []):
                        continue
                    out = f"{work}/net/{d}/{cond}/seed{seed}"
                    spec = DESIGNS[d]
                    argv = ["{python}", f"{code}/train_rel.py", "--data", args.data, "--out", out,
                            "--hold-out", spec["hold_out"], "--seed", str(seed)]
                    if spec["regime"] != "C":
                        argv += ["--regime", spec["regime"]]
                    if spec["r2_targets"]:
                        argv += ["--test-targets", f"{args.test_targets_dir.rstrip('/')}/tt_{d}.txt"]
                    argv += CONDITIONS[cond] + SCHEDULE + ["--run-label", f"design={d} condition={cond} seed={seed}"]
                    argv += extra + (j_extra if spec["regime"] == "J" else [])
                    runs.append({"id": f"net:{d}:{cond}:s{seed}", "kind": "network", "shard": k, "design": d,
                                 "condition": cond, "seed": seed, "out": out, "done": f"{out}/rel_config.json",
                                 "after": [], "argv": argv})
        if mine:
            cout = f"{keep}/compare_shard{k}"
            runs.append({"id": f"compare:shard{k}", "kind": "compare", "shard": k, "out": cout,
                         "done": f"{cout}/summary.json", "after": [],
                         "argv": ["{python}", f"{code}/compare_rel.py", "--runs-json", "{runs_json}",
                                  "--data", args.data, "--out", cout, "--shard", str(k),
                                  "--write-averaged", f"{keep}/averaged_shard{k}", "--averaged-dtype", "float16"]})
    counts: dict = {}
    for r in runs:
        key = f"shard{r['shard']}:{r['kind']}"
        counts[key] = counts.get(key, 0) + 1
    return {"format": "rete_relazionale_runs/1", "created_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "rete_relazionale_2026-09-28/make_runs_rel.py", "argv": sys.argv[1:],
            "paths": {"code": code, "net_code": net_code, "run_list_code": run_list_code, "data": args.data,
                      "work": work, "keep": keep, "test_targets_dir": args.test_targets_dir},
            "train_args": args.train_args, "j_args": args.j_args,
            "designs": {d: DESIGNS[d] for d in designs}, "conditions": CONDITIONS,
            "plan": {d: PLAN[d] for d in designs}, "shards": SHARDS, "schedule": SCHEDULE,
            "counts": counts, "runs": runs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="runs.json to write (refused if it exists)")
    ap.add_argument("--code", required=True, help="the folder holding train_rel.py, compare_rel.py (and, flat on "
                                                  "Kaggle, the r1 files)")
    ap.add_argument("--net-code", default="", help="where net.py, pool.py, train.py are (recorded only; train_rel.py "
                                                   "finds them through RETE_CONTESTI_CODE or beside itself)")
    ap.add_argument("--run-list-code", default="", help="where run_list.py is (recorded only)")
    ap.add_argument("--data", required=True, help="the network dataset (rete_contesti format; the r2 dataset)")
    ap.add_argument("--work", required=True, help="scratch root for every run folder")
    ap.add_argument("--keep", required=True, help="root kept at the end of the session")
    ap.add_argument("--test-targets-dir", default="", help="folder with tt_e1_k562.txt, tt_e1_cd4.txt, tt_e2_orion.txt")
    ap.add_argument("--designs", default=",".join(DESIGNS))
    ap.add_argument("--train-args", default="", help="extra arguments of every network run (none in the round)")
    ap.add_argument("--j-args", default="", help="extra arguments of the J designs' runs only, e.g. '--val-m "
                                                 "as-train' (not in the registered rule: a declared change)")
    args = ap.parse_args(argv)
    spec = build(args)
    with args.out.open("x", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)
    n_net = sum(1 for r in spec["runs"] if r["kind"] == "network")
    print(f"{len(spec['runs'])} runs ({n_net} network runs) written to {args.out}: {spec['counts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
