"""Write runs.json: the comparison of context descriptions for the network, every condition on the same held-out
designs, test targets and seeds (DISEGNO.md §9). Standard library (corpus.py is read only to copy the explicit
exclusion lists into runs.json, when numpy is there).

    python make_runs.py --out runs.json --code /kaggle/input/enc/encoder_contesto_2026-09-28 \
        --data /kaggle/input/rete-contesti-r1 --work /tmp/enc --keep /kaggle/working/enc \
        --corpus-ours /kaggle/input/corpus-crispri --corpus-ours /kaggle/input/corpus-abc \
        --corpus-ours /kaggle/input/corpus-depmap --corpus-tahoe /kaggle/input/corpus-tahoe \
        --corpus-scbasecount /kaggle/input/corpus-scbasecount
    then in Kaggle session k (0 and 1):   python run_list.py --runs runs.json --shard k --keep-small

Runs (kind): pretrain (pretrain.py: one encoder per exclusion group, data condition and seed), pca
(pca_baseline.py: one per exclusion group and data condition), network (train.py for `none`, train_emb.py for the
others: one per design, condition and seed), compare (compare.py at the end of each shard, with the
seed-averaged folders for score_pred.py). The designs that hold out the same family share their encoders:
e1_orion and e2_orion both hold out HCT116 and HEK293T. Every network run of a design gets the same arguments
except the context description, so the test targets (drawn by train.py from --test-seed) and the seeds are the
same; compare.py fails if they are not.

Shards: exclusion groups are dealt to the shards so that each shard pretrains what its own network runs read
(sessions do not share disks). Within a shard: the PCA runs, then seed by seed the encoders and the network runs
(`none` first), so that a session cut short leaves complete comparisons for the first seeds.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

DESIGNS = {
    "e1_k562": {"kind": "E1", "hold_out": "k562", "preset": "k562", "hidden": ["k562"]},
    "e1_orion": {"kind": "E1", "hold_out": "orion_hct116", "preset": "orion",
                 "hidden": ["orion_hct116", "orion_hek293t"]},
    "e1_cd4": {"kind": "E1", "hold_out": "cd4_Rest", "preset": "cd4",
               "hidden": ["cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"]},
    "e2_orion": {"kind": "E2", "hold_out": "orion_hct116,orion_hek293t", "preset": "orion",
                 "hidden": ["orion_hct116", "orion_hek293t"]},
    "e1_kolf": {"kind": "E1", "hold_out": "kolf", "preset": "ipsc", "hidden": ["kolf"]},
    "e2_cd4": {"kind": "E2", "hold_out": "cd4_Rest,cd4_Stim48hr", "preset": "cd4",
               "hidden": ["cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr"]},
}
DEFAULT_DESIGNS = ("e1_k562", "e1_orion", "e1_cd4", "e2_orion")
CONDITIONS = {                      # method, corpus groups
    "none": (None, ()),
    "pca": ("pca", ("ours",)),
    "ours": ("encoder", ("ours",)),
    "ours+tahoe": ("encoder", ("ours", "tahoe")),
    "ours+scbasecount": ("encoder", ("ours", "scbasecount")),
    "ours+both": ("encoder", ("ours", "tahoe", "scbasecount")),
    "pca+both": ("pca", ("ours", "tahoe", "scbasecount")),
    "ours-ft": ("finetune", ("ours",)),      # fine-tunes the `ours` encoder of the same group and seed
}
DEFAULT_CONDITIONS = ("none", "pca", "ours", "ours+tahoe", "ours+scbasecount", "ours+both")
REQUIRED = ("k562", "cd4_Rest", "cd4_Stim8hr", "cd4_Stim48hr", "orion_hct116", "orion_hek293t", "kolf", "A", "B", "C")


def explicit_presets() -> dict:
    try:
        sys.path.insert(0, str(HERE))
        import corpus
        return corpus.PRESETS
    except Exception as exc:          # numpy absent: record the names only
        return {"note": f"corpus.PRESETS not read ({exc}); see corpus.py"}


def build(args) -> dict:
    designs = [d.strip() for d in args.designs.split(",") if d.strip()]
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    for d in designs:
        if d not in DESIGNS:
            raise SystemExit(f"unknown design {d!r} (known: {sorted(DESIGNS)})")
    for c in conditions:
        if c not in CONDITIONS:
            raise SystemExit(f"unknown condition {c!r} (known: {sorted(CONDITIONS)})")
    corpora = {"ours": list(args.corpus_ours), "tahoe": list(args.corpus_tahoe),
               "scbasecount": list(args.corpus_scbasecount)}
    if not corpora["ours"] and any(c != "none" for c in conditions):
        raise SystemExit("--corpus-ours is required for every condition but none")
    skipped = []
    for c in list(conditions):
        missing = [g for g in CONDITIONS[c][1] if not corpora[g]]
        if missing:
            skipped.append({"condition": c, "missing_corpora": missing})
            conditions.remove(c)
    if "ours-ft" in conditions and "ours" not in conditions:
        conditions.insert(conditions.index("ours-ft"), "ours")
    required = [s.strip() for s in args.require.split(",") if s.strip()]
    code, net_code = args.code.rstrip("/"), (args.net_code or f"{args.code.rstrip('/')}/../rete_contesti_2026-09-27")
    work, keep = args.work.rstrip("/"), args.keep.rstrip("/")
    groups: dict = {}
    for d in designs:
        groups.setdefault(DESIGNS[d]["preset"], []).append(d)
    weight = {p: sum(2 if DESIGNS[d]["kind"] == "E2" else 1 for d in ds) for p, ds in groups.items()}
    load, shard_of = [0] * args.shards, {}
    for p in sorted(groups, key=lambda p: (-weight[p], p)):
        k = min(range(args.shards), key=lambda i: (load[i], i))
        shard_of[p] = k
        load[k] += weight[p]
    hidden_of = {p: sorted({h for d in ds for h in DESIGNS[d]["hidden"]}) for p, ds in groups.items()}
    n_ref = len(corpora["ours"])
    train_extra, emb_extra = shlex.split(args.train_args), shlex.split(args.emb_args)
    pre_extra, pca_extra = shlex.split(args.pretrain_args), shlex.split(args.pca_args)

    def data_argv(preset: str, groups_: tuple, seed: int) -> list:
        argv = []
        for g in groups_:
            for c in corpora[g]:
                argv += ["--corpus", c]
        argv += ["--reference-corpora", str(n_ref), "--exclude-preset", preset, "--require", ",".join(required),
                 "--seed", str(seed)]
        if not args.no_expect_excluded:
            argv += ["--expect-excluded", ",".join(hidden_of[preset])]
        return argv

    def enc_seed(seed: int) -> int:
        return seed if args.encoder_seeds == "paired" else int(args.encoder_seeds)

    def pre_id(preset: str, cond: str, seed: int) -> tuple[str, str]:
        method = CONDITIONS[cond][0]
        if method == "pca":
            return f"pca:{preset}:{cond}", f"{work}/pre/{preset}/{cond}"
        src = "ours" if method == "finetune" else cond
        s = enc_seed(seed)
        return f"pre:{preset}:{src}:s{s}", f"{work}/pre/{preset}/{src}/seed{s}"

    runs, seen = [], set()

    def add(run: dict) -> None:
        if run["id"] not in seen:
            seen.add(run["id"])
            runs.append(run)

    for k in range(args.shards):
        presets = sorted(p for p in groups if shard_of[p] == k)
        net_ids = []
        for p in presets:
            for cond in conditions:
                if CONDITIONS[cond][0] == "pca":
                    rid, out = pre_id(p, cond, 0)
                    add({"id": rid, "kind": "pca", "shard": k, "preset": p, "condition": cond, "out": out,
                         "done": f"{out}/manifest.json", "after": [],
                         "argv": ["{python}", f"{code}/pca_baseline.py", "--out", out]
                                 + data_argv(p, CONDITIONS[cond][1], 0) + pca_extra})
        for seed in seeds:
            for p in presets:
                for cond in conditions:
                    if CONDITIONS[cond][0] != "encoder":
                        continue
                    rid, out = pre_id(p, cond, seed)
                    add({"id": rid, "kind": "pretrain", "shard": k, "preset": p, "condition": cond,
                         "seed": enc_seed(seed), "out": out, "done": f"{out}/manifest.json", "after": [],
                         "argv": ["{python}", f"{code}/pretrain.py", "--out", out]
                                 + data_argv(p, CONDITIONS[cond][1], enc_seed(seed)) + pre_extra})
            for p in presets:
                for d in groups[p]:
                    for cond in conditions:
                        out = f"{work}/net/{d}/{cond}/seed{seed}"
                        common = ["--data", args.data, "--out", out, "--hold-out", DESIGNS[d]["hold_out"],
                                  "--seed", str(seed)] + train_extra
                        method = CONDITIONS[cond][0]
                        after = []
                        if method is None:
                            argv = ["{python}", f"{net_code}/train.py"] + common
                        else:
                            pid, pout = pre_id(p, cond, seed)
                            after = [pid]
                            argv = ["{python}", f"{code}/train_emb.py"] + common + \
                                ["--run-label", f"design={d} condition={cond} seed={seed}"] + emb_extra
                            if method == "finetune":
                                argv += ["--finetune-encoder", pout]
                                for c in corpora["ours"]:
                                    argv += ["--finetune-corpus", c]
                            else:
                                argv += ["--context-embeddings", f"{pout}/context_embeddings.npz"]
                        rid = f"net:{d}:{cond}:s{seed}"
                        done = f"{out}/test_targets.txt" if method is None else f"{out}/emb_config.json"
                        add({"id": rid, "kind": "network", "shard": k, "design": d, "condition": cond, "seed": seed,
                             "preset": p, "out": out, "done": done, "after": after, "argv": argv})
        if presets:
            cout = f"{keep}/compare_shard{k}"
            add({"id": f"compare:shard{k}", "kind": "compare", "shard": k, "out": cout, "done": f"{cout}/summary.json",
                 "after": [], "argv": ["{python}", f"{code}/compare.py", "--runs-json", "{runs_json}",
                                       "--data", args.data, "--out", cout, "--shard", str(k),
                                       "--write-averaged", f"{keep}/averaged_shard{k}"]})
    counts: dict = {}
    for r in runs:
        key = f"shard{r['shard']}:{r['kind']}"
        counts[key] = counts.get(key, 0) + 1
    return {"format": "encoder_contesto_runs/1", "created_utc": datetime.now(timezone.utc).isoformat(),
            "generator": "encoder_contesto_2026-09-28/make_runs.py", "argv": sys.argv[1:],
            "paths": {"code": code, "net_code": net_code, "data": args.data, "work": work, "keep": keep,
                      "corpora": corpora},
            "designs": {d: DESIGNS[d] for d in designs}, "conditions": {c: list(CONDITIONS[c][1]) for c in conditions},
            "methods": {c: CONDITIONS[c][0] for c in conditions}, "seeds": seeds,
            "encoder_seeds": args.encoder_seeds, "required_contexts": required,
            "exclusion_groups": {p: {"designs": ds, "hidden": hidden_of[p], "shard": shard_of[p]}
                                 for p, ds in groups.items()},
            "presets": explicit_presets(), "skipped": skipped, "counts": counts, "runs": runs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="runs.json to write (refused if it exists)")
    ap.add_argument("--code", required=True, help="this folder, where the runs will read it")
    ap.add_argument("--net-code", default="", help="reports/modelli/rete_contesti_2026-09-27 (default: CODE/../rete_contesti_2026-09-27)")
    ap.add_argument("--data", required=True, help="the network dataset (rete_contesti format)")
    ap.add_argument("--work", required=True, help="scratch root for every run folder")
    ap.add_argument("--keep", required=True, help="root kept at the end of the session (compare outputs, small files)")
    ap.add_argument("--corpus-ours", action="append", default=[], help="the planned sources: repeat per corpus")
    ap.add_argument("--corpus-tahoe", action="append", default=[])
    ap.add_argument("--corpus-scbasecount", action="append", default=[])
    ap.add_argument("--designs", default=",".join(DEFAULT_DESIGNS))
    ap.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--encoder-seeds", default="paired", help="paired (encoder seed = network seed) or one seed")
    ap.add_argument("--require", default=",".join(REQUIRED), help="contexts every corpus condition must embed")
    ap.add_argument("--no-expect-excluded", action="store_true",
                    help="do not require the held-out contexts to be found and removed in the corpora")
    ap.add_argument("--shards", type=int, default=2)
    ap.add_argument("--train-args", default="", help="extra arguments of every network run, e.g. '--n-test 1000'")
    ap.add_argument("--emb-args", default="", help="extra arguments of the embedding runs")
    ap.add_argument("--pretrain-args", default="", help="extra arguments of pretrain.py")
    ap.add_argument("--pca-args", default="", help="extra arguments of pca_baseline.py")
    args = ap.parse_args(argv)
    spec = build(args)
    with args.out.open("x", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)
    print(f"{len(spec['runs'])} runs written to {args.out}: {spec['counts']}")
    for s in spec["skipped"]:
        print(f"skipped condition {s['condition']}: no corpus for {s['missing_corpora']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
