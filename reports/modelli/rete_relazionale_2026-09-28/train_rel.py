"""r1's train.py with the relational network (--arch rel) or r1's own network (--arch r1) on the same schedule;
--selftest runs selftest_rel.py (CPU, synthetic data, nothing kept).

train.py, net.py and pool.py (reports/modelli/rete_contesti_2026-09-27/) are imported by path and not edited
(RETE_CONTESTI_CODE, this folder, or ../rete_contesti_2026-09-27). relnet.install() routes four of train.py's names
-- fit, net_config, and for --arch rel pool.Phase and predict_arms (plus write_predictions and ARM_PAIRS for the
extra arms) -- and train.run_design does everything else: design, calibration, training, validation, refit,
prediction, diagnostics, outputs. So the outputs are r1's (config.json, log.txt, history.csv, metrics.json,
test_targets.txt, checkpoints/, pred_<context>.npz with the same keys), and score_pred.py, compare.py and
to_effects.py read them unchanged. Added here:
* predrel_<context>.npz (--arch rel): the arms tperm, norel, cardnb (relnet.py) on the full axis;
* rel_config.json: the arguments, the relational settings, the cards of every phase (profiles, singular values,
  explained share, targets with a card and with neighbours), the parameter count, the learned scalars, and the
  sha256 of the r1 files and of this folder's files. config.json keeps r1's "stage" label (train.py writes it):
  rel_config.json is what identifies the run. The run is done when rel_config.json exists.
Defaults differ from train.py only in the schedule the registered rule fixes (RISULTATI.md, 28/09 19:58): a
validation at step 0, then every 25 steps (--eval-every 25), patience 12, at most 3,000 steps (--steps 3000).
--val-m as-train (not in the rule; default keep = train.py) withholds m from the validation rows when training
withholds it from every row (J): with train.py's validation the calibrated start wins in J (selftest_rel.py, check 4).

    python train_rel.py --selftest
    python train_rel.py --data DATASET --out NEW --hold-out k562 --arch r1                  # none
    python train_rel.py --data DATASET --out NEW --hold-out k562 --arch rel                 # rel0
    python train_rel.py --data DATASET --out NEW --hold-out k562 --arch rel --rel-cards learned   # rel1
    python train_rel.py --data DATASET --out NEW --regime J --hold-out orion_hct116 --arch rel
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import relnet as RN
import relphase as RP
import pool as P  # noqa: E402  (relphase put the r1 folder on sys.path)
import train as T  # noqa: E402

HERE = Path(__file__).resolve().parent
OWN_FILES = ("relphase.py", "relnet.py", "train_rel.py", "selftest_rel.py")
R1_FILES = ("net.py", "pool.py", "train.py")


def build_parser():
    ap = T.build_parser()
    ap.description = __doc__
    RN.add_args(ap)
    ap.set_defaults(steps=3000, eval_every=25, patience=12)
    return ap


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def run(args, pool=None, log=None) -> dict:
    """train.run_design with the relational pieces installed; writes rel_config.json beside its outputs."""
    t0 = time.time()
    RN.install(args)
    try:
        res = T.run_design(args, pool=pool, log=log)
    finally:
        RN.uninstall()
    model = res["model"]
    info = {"stage": "rete_relazionale_2026-09-28/train_rel.py", "run_label": args.run_label, "arch": args.arch,
            "condition": ("none" if args.arch == "r1" else ("rel1" if args.rel_cards == "learned" else "rel0")),
            "schedule": {"eval_step0": args.eval_step0, "eval_every": args.eval_every, "patience": args.patience,
                         "steps": args.steps, "val_m": args.val_m},
            "settings": RN.settings_from_args(args).to_dict() if args.arch == "rel" else None,
            "lambdas": RN.lambdas(args) if args.arch == "rel" else None,
            "learning_rates": ({"small": args.rel_lr, "card": args.rel_lr_card} if args.arch == "rel"
                               else {"all": args.lr}),
            "net_config": res["config"]["net_config"], "parameters": res["config"]["parameters"],
            "validation": res["config"]["validation"], "final_steps": res["config"]["final_steps"],
            "calibration": res["calibration"],
            "learned": model.summary() if isinstance(model, RN.RelNet) else None,
            "phases": [dict(p) for p in RP.CREATED],
            "cardnb": getattr(res["phase"], "_cardnb", None),
            "sha256": {**{f"rete_contesti_2026-09-27/{f}": sha256(RP.NET_DIR / f) for f in R1_FILES},
                       **{f"rete_relazionale_2026-09-28/{f}": sha256(HERE / f) for f in OWN_FILES}},
            "seconds": round(time.time() - t0, 1)}
    with (Path(args.out) / "rel_config.json").open("x", encoding="utf-8") as fh:
        json.dump(T.jsonable(info), fh, indent=1)
    res["rel_config"] = info
    return res


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.selftest:
        import selftest_rel
        return selftest_rel.main()
    if args.data is None or args.out is None:
        raise SystemExit("--data and --out are required (or --selftest)")
    if args.arch == "rel" and args.rel_nb < 0:
        raise SystemExit("--rel-nb must be >= 0")
    pool = P.Pool.from_dir(args.data)
    run(args, pool)
    return 0


if __name__ == "__main__":
    sys.exit(main())
