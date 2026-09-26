"""Stage 104: a learned magnitude channel reweights the per-context effects of a stage-100 run.

The effects of a stage-100 run (``--direction``) carry each target's transferred direction. A
gradient-boosting model (`vcc2026.transfer_model`) predicts from features of the sources and of the
context's basal expression how much each gene moves for each target; the effects are reweighted
by that magnitude profile and rescaled to move as many detectable genes as the input. With
``--reweight transfer`` (the default) only the transferred part is reweighted: the cis head of the
direction run's recipe and each target's own gene keep their values,

    lfc_out = s x (lfc_in - cis) x w + cis,   w = (|m| / mean over genes of |m|) ^ exponent (1 on the own gene)

and with ``--reweight all`` every entry is (lfc_out = s x lfc_in x w; the first t21 build, which
multiplied bidirectional-promoter neighbours of the cis head by up to 4). ``s`` is chosen so that
the median count of genes above 4 / sqrt(400 mu) (mu: expected UMI per cell at 20,000, genes at
>= 5 CPM in the context's controls) equals the input's.

The model sees public sources only: each of ``--train-tasks`` is a held-out source, predicted
from the ``--train-sources`` of the other families (family = name before the first underscore),
with labels centred per gene over targets (the target-specific part) and weights (x/(1+x))^2,
x = 0.05 CPM of the gene in that source's controls; early stopping is validated on a tenth of
the (task, target) groups held out whole. No A/B/C measurement is a label; A/B/C enter only
through their controls (``--basal``). Features of a context use ``--sources``. The cis prior
and its scale come from the direction run's recipe (manifest ``cis``); STRING partners
(`vcc2026.priors.partner_effects`) exclude every panel target. Evidence:
reports/trasferimento_appreso_2026-09-26/RISULTATI.md (r3-r5; r5 is the bench isolated as the
audit of 26 September asks).

Writes ``effects_<CTX>.npz`` (targets, genes, lfc, observed: the direction's) and a manifest;
refuses an existing ``--out``.

    python scripts/104_learned_reweighting.py --direction <data_root>/processed/effects_t20_2026-09-26 \
        --cache <data_root>/processed/multisource_2026-09-23_r5 --out <data_root>/processed/effects_t21_2026-09-26_tx
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.multisource import AxisTable  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.priors import add_cis, cis_prior, partner_effects  # noqa: E402
from vcc2026.transfer_model import (  # noqa: E402
    detectable_threshold, fit_magnitude_model, gene_priors, match_detectable, mixture_se, own_gene_mask,
    pair_features, predict_magnitude, reweight, training_rows,
)

REPO = Path(__file__).resolve().parents[1]
DATA_ROOT = config.paths().data_root


def family(name: str) -> str:
    return name.split("_")[0]


def load(cache: Path, name: str) -> tuple[AxisTable, AxisTable]:
    """(raw, shrunk) views of a stage-98 source, as stage 100's load_table reads them."""
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    targets = z["targets"].astype(str).tolist()
    raw = AxisTable(name, targets, z["raw"], z["raw"], z["se"], z["n_cells"], meta)
    shr = AxisTable(name, targets, z["shrunk"], z["raw"], z["se"], z["n_cells"], meta)
    return raw, shr


def source_se(cache: Path, tab: AxisTable, targets: list[str], n_genes: int) -> np.ndarray:
    """SE rows of a source on ``targets``; a mixture saved without SE (meta ``from``) gets its
    parts' reliability-weighted SE."""
    ix = tab.index()
    measured = np.isfinite(tab.raw)
    if tab.meta.get("from") and not np.isfinite(tab.se[measured]).any():
        return mixture_se([load(cache, p)[0] for p in tab.meta["from"]], targets, n_genes)
    se = np.full((len(targets), n_genes), np.nan, dtype=np.float32)
    for i, t in enumerate(targets):
        if t in ix:
            se[i] = tab.se[ix[t]]
    return se


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--direction", type=Path, required=True, help="a stage-100 output folder")
    p.add_argument("--cache", type=Path, required=True, help="the stage-98 cache the direction run used")
    p.add_argument("--basal", type=Path, default=DATA_ROOT / "processed/basal_sources_2026-09-26.csv")
    p.add_argument("--universe", type=Path, default=DATA_ROOT / "processed/universe_k562_2026-09-26")
    p.add_argument("--coords", type=Path, default=DATA_ROOT / "external/annotation/gene_coordinates_gencode_v50.tsv")
    p.add_argument("--links", type=Path, default=DATA_ROOT / "interim/encoder_inputs_2026-09-14/string_physical_links")
    p.add_argument("--info", type=Path, default=DATA_ROOT / "interim/encoder_inputs_2026-09-14/string_protein_info")
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--sources", nargs="+", default=["k562", "cd4_mix", "orion_hct116"])
    p.add_argument("--train-sources", nargs="+", default=["k562", "cd4_mix", "orion_hct116", "orion_hek293t"])
    p.add_argument("--train-tasks", nargs="+", default=["k562", "cd4_mix", "orion_hct116", "orion_hek293t"])
    p.add_argument("--exponent", type=float, default=0.25)
    p.add_argument("--reweight", choices=["transfer", "all"], default="transfer",
                   help="reweight only the transferred part (cis head and own gene kept) or every entry")
    p.add_argument("--genes-per-target", type=int, default=1500)
    p.add_argument("--seed", type=int, default=20260926)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; choose a new --out")
    t0 = time.time()
    rng = np.random.default_rng(args.seed)
    axis = np.asarray(official_axis().symbols)
    G = axis.size
    col = {g: i for i, g in enumerate(axis)}
    panel = pd.read_csv(args.targets_csv).iloc[:, 0].astype(str).tolist()
    panel_cols = np.array([col[g] for g in panel if g in col])
    basal = pd.read_csv(args.basal).set_index("gene_name").reindex(axis)
    dman = json.loads((args.direction / "manifest.json").read_text(encoding="utf-8"))
    cis_spec = dman["recipe"].get("cis")
    coords = load_coordinates(args.coords)
    cis_model = cis_prior(pd.read_csv(REPO / cis_spec["pairs"]), panel) if cis_spec else None

    def cis_matrix(targets):
        m = np.zeros((len(targets), G), dtype=np.float32)
        if cis_model is not None:
            add_cis(m, np.zeros((len(targets), G), dtype=bool), targets, axis, cis_model, coords,
                    int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
        return m

    idx = pd.read_csv(args.universe / "index.csv")
    priors = gene_priors((np.load(args.universe / c, allow_pickle=False) for c in sorted(idx["chunk"].unique())),
                         set(panel), G)
    assoc, assoc_counts = partner_effects(panel, args.universe, args.links, args.info, 700, axis,
                                          exclude=frozenset(panel))
    tables = {n: load(args.cache, n) for n in sorted(set(args.train_sources) | set(args.sources))}
    log(f"priors, partners and {len(tables)} sources ready ({time.time() - t0:.0f}s)")

    def features(pred_names, targets, context_cpm):
        raws = [tables[n][0] for n in pred_names]
        return pair_features(raws, [tables[n][1] for n in pred_names],
                             [source_se(args.cache, t, targets, G) for t in raws], targets, col, context_cpm,
                             [basal[n].to_numpy() for n in pred_names], priors, cis_matrix(targets),
                             np.stack([assoc.get(t, np.zeros(G, dtype=np.float32)) for t in targets]), panel_cols)

    Xs, ys, ws, gs, task_info = [], [], [], [], {}
    for ti, held in enumerate(args.train_tasks):
        preds = [n for n in args.train_sources if family(n) != family(held)]
        truth = tables[held][0]
        tix = truth.index()
        targets = [t for t in panel if t in tix and any(t in tables[n][0].index() for n in preds)]
        F = features(preds, targets, basal[held].to_numpy())
        y = truth.raw[np.array([tix[t] for t in targets])].astype(np.float32)
        x = 0.05 * np.nan_to_num(basal[held].to_numpy())
        X, yy, ww, rows = training_rows(F, y, ((x / (1 + x)) ** 2).astype(np.float32), args.genes_per_target, rng,
                                        with_rows=True)
        Xs.append(X)
        ys.append(yy)
        ws.append(ww)
        gs.append(ti * 100000 + rows)
        task_info[held] = {"predictors": preds, "targets": len(targets), "rows": int(len(yy))}
        log(f"task {held}: {len(targets)} targets, {len(yy)} rows ({time.time() - t0:.0f}s)")
        del F
    model = fit_magnitude_model(np.vstack(Xs), np.concatenate(ys), np.concatenate(ws), args.seed,
                                groups=np.concatenate(gs))
    del Xs, ys, ws, gs
    log(f"model fitted: {model.n_iter_} iterations ({time.time() - t0:.0f}s)")

    args.out.mkdir(parents=True)
    summary = {}
    for path in sorted(args.direction.glob("effects_*.npz")):
        ctx = path.stem.split("_", 1)[1]
        z = np.load(path)
        targets = z["targets"].astype(str).tolist()
        if list(z["genes"].astype(str)) != list(axis):
            raise SystemExit(f"{path}: gene axis differs from the official axis")
        lfc, observed = z["lfc"].astype(np.float32), z["observed"]
        cpm = basal[ctx].to_numpy()
        F = features(args.sources, targets, cpm)
        m = predict_magnitude(model, F, len(targets), G)
        del F
        if args.reweight == "transfer":
            cis = cis_matrix(targets)
            keep = own_gene_mask(targets, col, G)
            out, scale = match_detectable(reweight(lfc - cis, m, args.exponent, keep=keep), lfc,
                                          detectable_threshold(cpm), cpm >= 5.0, offset=cis)
        else:
            out, scale = match_detectable(reweight(lfc, m, args.exponent), lfc, detectable_threshold(cpm), cpm >= 5.0)
        out_path = args.out / f"effects_{ctx}.npz"
        np.savez_compressed(out_path, targets=np.array(targets), genes=axis, lfc=out, observed=observed)
        thr, gate = detectable_threshold(cpm), cpm >= 5.0
        det = lambda E: float(np.median(((np.abs(E) > thr[None, :]) & gate[None, :]).sum(axis=1)))
        summary[ctx] = {"scale": scale, "detectable_median_in": det(lfc), "detectable_median_out": det(out),
                        "abs_lfc_q99_median": float(np.median(np.quantile(np.abs(out), 0.99, axis=1))),
                        "direction_sha256": sha256(path), "sha256": sha256(out_path)}
        log(f"{ctx}: scale {scale:.3f}, detectable {summary[ctx]['detectable_median_in']:.0f} -> "
            f"{summary[ctx]['detectable_median_out']:.0f}")
    manifest = {"stage": "104_learned_reweighting", "written_utc": datetime.now(timezone.utc).isoformat(),
                "args": {k: str(v) for k, v in vars(args).items()}, "direction_recipe": dman["recipe"],
                "exponent": args.exponent, "reweight": args.reweight, "model": {"n_iter": int(model.n_iter_), "tasks": task_info},
                "partners": assoc_counts, "basal_sha256": sha256(args.basal), "contexts": summary,
                "units": "ln fold change on the official axis; observed mask of the direction run"}
    with open(args.out / "manifest.json", "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"wrote {args.out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
