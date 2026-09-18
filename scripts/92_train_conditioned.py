"""Stage 92: train the target- and context-conditioned predictors and export their effects.

Three splits, fixed by `configs/conditioned_rule.yaml` before any training:

* ``C`` -- unseen CONTEXT: HepG2 is never a training context (its controls only); targets may
  have been perturbed in K562 (mode A). The case of a real submission: 272/300 official
  targets have a K562 response, none has one in A, B or C.
* ``J`` -- JOINT: HepG2 unseen AND the evaluated targets removed from every training label
  (mode B: no source response, only descriptors).
* ``T`` -- unseen TARGETS in a seen context: the official panel targets, removed from K562's
  labels, predicted in K562.

Training contexts are K562 (genome-wide bulk) and RPE1 (bulk); labels are EB-shrunk ln fold
changes (`effects_from_bulk`) on the genes all three contexts measure. Each model family gets
the same budget: 8 configurations, chosen on a validation set that mimics its test (held-out
RPE1 targets for C and J -- no second unseen context exists to validate on --, held-out K562
targets for T). Everything that is fitted -- PCA basis, feature standardisation, neighbour
pools -- sees training rows only.

Outputs, per split: `pred_<split>_<model>[_ctxperm].npz` (targets, genes, ln FC) for the
benches (`--effects` in stages 73 and 75), baselines `pred_<split>_nbr.npz` (STRING-neighbour
mean) and `pred_T_k562mean.npz`, the effect-space evaluation, and a manifest.

    python scripts/92_train_conditioned.py --k562-bulk <gwps bulk> --rpe1-bulk <rpe1 bulk> \
        --hepg2 <h5ad> --string-links <gz> --string-info <gz> --panels <dir> --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.bench import log  # noqa: E402
from vcc2026.conditioned import (  # noqa: E402
    ConditionedNet,
    ConditionedRidge,
    Encoder,
    PairBlock,
    log_cpm,
    neighbour_mean,
    string_partners,
)
from vcc2026.predictor_sc import effects_from_bulk  # noqa: E402
from vcc2026.sc_effects import eb_shrink, fraction_stats, log_effect  # noqa: E402
from vcc2026.sc_stream import read_frame  # noqa: E402

NET_GRID = [{"hidden": h, "k": k, "l2": l2} for h in (64, 128) for k in (16, 32) for l2 in (1e-5, 1e-4)]
RIDGE_GRID = [0.1, 1.0, 10.0, 100.0, 1e3, 1e4, 1e5, 1e6]


def read_bulk(path: Path):
    with h5py.File(path, "r") as f:
        labels = np.array([s.decode() for s in f["obs/gene_transcript"][:]])
        means = f["X"][:]
        cells = f["obs/num_cells_filtered"][:]
        names = read_frame(f["var"])["gene_name"].astype(str).to_numpy()
    ntc = np.array(["non-targeting" in lab for lab in labels])
    sym = np.array(["non-targeting" if nt else lab.split("_")[1] for lab, nt in zip(labels, ntc)])
    return means, cells, sym, ntc, names


def bulk_basal(means, cells, ntc, names) -> pd.Series:
    """Pooled control fraction per gene: cell-weighted mean of the NTC rows, normalised to 1."""
    w = np.where(np.isfinite(cells[ntc]), cells[ntc], 0.0)
    mu = (means[ntc] * w[:, None]).sum(axis=0) / max(w.sum(), 1.0)
    s = pd.Series(log_cpm(mu / mu.sum()), index=names)
    return s[~s.index.duplicated()]


def read_rows(path: Path, rows: np.ndarray, block: int = 4096) -> sp.csr_matrix:
    out = []
    with h5py.File(path, "r") as f:
        x = f["X"]
        for i in range(0, rows.size, block):
            out.append(sp.csr_matrix(x[np.sort(rows[i:i + block])]))
    return sp.vstack(out).tocsr()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--k562-bulk", type=Path, required=True)
    p.add_argument("--rpe1-bulk", type=Path, required=True)
    p.add_argument("--hepg2", type=Path, required=True)
    p.add_argument("--string-links", type=Path, required=True)
    p.add_argument("--string-info", type=Path, required=True)
    p.add_argument("--panels", type=Path, required=True,
                   help="hepg2_val.txt, hepg2_test.txt, k562_val.txt, k562_test.txt, official.txt")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--string-min-score", type=int, default=400)
    p.add_argument("--val-fraction", type=float, default=0.2)
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--batch", type=int, default=256)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--quick", action="store_true", help="tiny grids and few steps: a smoke test only")
    p.add_argument("--max-source-targets", type=int, default=None,
                   help="smoke tests only: keep the panel targets plus this many random others per source")
    args = p.parse_args()
    if (args.out / "manifest.json").exists():
        raise SystemExit(f"{args.out} already holds a training run; choose a new --out")
    args.out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(args.seed)
    net_grid = NET_GRID[:2] if args.quick else NET_GRID
    ridge_grid = RIDGE_GRID[2:4] if args.quick else RIDGE_GRID
    steps = 300 if args.quick else args.steps

    panel = {n: [ln.strip() for ln in (args.panels / f"{n}.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
             for n in ("hepg2_val", "hepg2_test", "k562_val", "k562_test", "official")}

    # ---- sources, basal profiles, gene universe -------------------------------------------
    k_means, k_cells, k_sym, k_ntc, k_names = read_bulk(args.k562_bulk)
    r_means, r_cells, r_sym, r_ntc, r_names = read_bulk(args.rpe1_bulk)
    basal = {"K562": bulk_basal(k_means, k_cells, k_ntc, k_names), "RPE1": bulk_basal(r_means, r_cells, r_ntc, r_names)}
    with h5py.File(args.hepg2, "r") as f:
        h_obs = read_frame(f["obs"])
        h_names = read_frame(f["var"]).index.astype(str).to_numpy()
    h_sym = h_obs["gene"].astype(str).to_numpy()
    h_ntc_rows = np.flatnonzero(h_sym == "non-targeting")
    h_ctrl = read_rows(args.hepg2, h_ntc_rows)
    h_frac = np.asarray(h_ctrl.sum(axis=0)).ravel()
    basal["HepG2"] = pd.Series(log_cpm(h_frac / h_frac.sum()), index=h_names)
    basal["HepG2"] = basal["HepG2"][~basal["HepG2"].index.duplicated()]
    genes = sorted(set(basal["K562"].index) & set(basal["RPE1"].index) & set(basal["HepG2"].index))
    G = len(genes)
    log(f"gene universe {G} (K562 {len(basal['K562'])}, RPE1 {len(basal['RPE1'])}, HepG2 {len(basal['HepG2'])})")

    def on_universe(eff):
        pos = pd.Index(eff.genes).get_indexer(genes)
        if (pos < 0).any():
            raise SystemExit("a universe gene is missing from a source")
        return {t: eff.shrunk[i, pos].astype(np.float32) for i, t in enumerate(eff.targets)}

    k_targets = sorted(set(k_sym[~k_ntc]))
    r_targets = sorted(set(r_sym[~r_ntc]))
    if args.max_source_targets:
        keep = {t for v in panel.values() for t in v}
        pick = np.random.default_rng(args.seed + 7)
        k_targets = sorted((keep & set(k_targets)) | set(pick.choice(k_targets, args.max_source_targets, replace=False)))
        r_targets = sorted((keep & set(r_targets)) | set(pick.choice(r_targets, args.max_source_targets, replace=False)))
    log(f"estimating effects: K562 {len(k_targets)} targets, RPE1 {len(r_targets)}")
    def effects_blockwise(means, cells, sym, ntc, names, targets, block=1500):
        """The same numbers as one call (shrinkage is per target), a fraction of the peak memory."""
        out = {}
        for i in range(0, len(targets), block):
            out.update(on_universe(effects_from_bulk(means, cells, sym, ntc, names, targets=targets[i:i + block])))
        return out

    K = effects_blockwise(k_means, k_cells, k_sym, k_ntc, k_names, k_targets)
    R = effects_blockwise(r_means, r_cells, r_sym, r_ntc, r_names, r_targets)
    del k_means, r_means
    partners = string_partners(args.string_links, args.string_info, min_score=args.string_min_score)
    log(f"STRING partners for {len(partners)} symbols (score >= {args.string_min_score}); "
        f"{time.time() - t0:.0f}s")

    def phi_of(ctx):
        q = basal[ctx].reindex(genes).to_numpy()
        s = basal["K562"].reindex(genes).to_numpy()
        return np.stack([q, s, q - s], axis=1)

    def target_basal(ctx, targets):
        return basal[ctx].reindex(targets).fillna(0.0).to_numpy()

    def block(ctx, targets, labels, source, nbr_pool, *, mode_b=frozenset(), phi_ctx=None):
        """Pairs of one context. `source`: K562 labels usable as input (never on K562 rows)."""
        n = len(targets)
        y_src = np.zeros((n, G), dtype=np.float32)
        m_src = np.zeros(n)
        if ctx != "K562":
            for i, t in enumerate(targets):
                if t in source and t not in mode_b:
                    y_src[i], m_src[i] = source[t], 1.0
        nbr, cnt = neighbour_mean(targets, partners, nbr_pool, G)
        y = None if labels is None else np.stack([labels[t] for t in targets]).astype(np.float32)
        pc = phi_ctx or ctx
        return PairBlock(ctx, list(targets), y_src, m_src, nbr, (cnt > 0).astype(float),
                         target_basal(pc, targets), target_basal("K562", targets), phi_of(pc), y)

    official = set(panel["official"])
    hv, ht = panel["hepg2_val"], panel["hepg2_test"]
    splits = {}
    # C: HepG2 unseen; every K562/RPE1 label usable; validate on held-out RPE1 targets (mode A)
    r_pool = [t for t in r_targets if t not in set(hv) | set(ht)]
    r_val_c = sorted(rng.choice(r_pool, int(args.val_fraction * len(r_pool)), replace=False).tolist())
    splits["C"] = {"k562_train": k_targets, "rpe1_train": [t for t in r_targets if t not in set(r_val_c)],
                   "val": ("RPE1", r_val_c), "mode_b": set(), "tests": {"hepg2_val": ("HepG2", hv), "hepg2_test": ("HepG2", ht)}}
    # J: HepG2 unseen AND evaluated targets unseen anywhere (validation targets too)
    r_val_j = r_val_c
    removed_j = set(hv) | set(ht) | set(r_val_j)
    splits["J"] = {"k562_train": [t for t in k_targets if t not in removed_j],
                   "rpe1_train": [t for t in r_targets if t not in removed_j],
                   "val": ("RPE1", r_val_j), "mode_b": removed_j,
                   "tests": {"hepg2_val": ("HepG2", hv), "hepg2_test": ("HepG2", ht)}}
    # T: official targets unseen in K562 (their only screen); validate on held-out K562 targets
    k_pool = [t for t in k_targets if t not in official]
    k_val_t = sorted(rng.choice(k_pool, int(0.1 * len(k_pool)), replace=False).tolist())
    removed_t = official | set(k_val_t)
    splits["T"] = {"k562_train": [t for t in k_targets if t not in removed_t], "rpe1_train": r_targets,
                   "val": ("K562", k_val_t), "mode_b": removed_t,
                   "tests": {"k562_val": ("K562", panel["k562_val"]), "k562_test": ("K562", panel["k562_test"])}}

    manifest = {"stage": "92_train_conditioned", "args": {k: str(v) for k, v in vars(args).items()},
                "gene_universe": G, "n_targets": {"K562": len(K), "RPE1": len(R)},
                "string_symbols": len(partners), "splits": {}, "leakage_checks": {}}
    evaluation = {}
    for name, sp_ in splits.items():
        ts = time.time()
        k_lab = {t: K[t] for t in sp_["k562_train"]}
        r_lab = {t: R[t] for t in sp_["rpe1_train"]}
        # leakage checks, recorded and enforced
        test_targets = {t for _, (_, tl) in sp_["tests"].items() for t in tl}
        chk = {"val_in_train": len(set(sp_["val"][1]) & (set(k_lab) if sp_["val"][0] == "K562" else set(r_lab)))}
        if name in ("J", "T"):
            chk["test_in_any_train_label"] = len(test_targets & (set(k_lab) | set(r_lab)))
        if name == "C":
            chk["hepg2_rows_in_train"] = 0
        if any(chk.values()):
            raise SystemExit(f"split {name}: leakage check failed {chk}")
        manifest["leakage_checks"][name] = chk
        train_blocks = [block("K562", sp_["k562_train"], k_lab, k_lab, k_lab),
                        block("RPE1", sp_["rpe1_train"], r_lab, k_lab, k_lab)]
        vctx, vt = sp_["val"]
        vlab = K if vctx == "K562" else R
        val_block = block(vctx, vt, vlab, k_lab, k_lab, mode_b=sp_["mode_b"])
        enc = Encoder(k=32).fit(np.stack(list(k_lab.values())), train_blocks, seed=args.seed)

        def coverage(b):
            return {"context": b.context, "n": len(b.targets), "with_source": int(b.m_src.sum()),
                    "with_neighbours": int(b.m_nbr.sum())}
        cov = {"train": [coverage(b) for b in train_blocks], "val": coverage(val_block), "tests": {}}

        def rows(b):
            return (enc.x(b), enc.phi(b), b.y_src, b.m_src, b.y)

        tr_rows = [rows(b) for b in train_blocks]
        va_rows = [rows(val_block)]

        def sampler(rs=tr_rows, g=np.random.default_rng(args.seed + 1)):
            def draw():
                x, phi, ys, ms, y = rs[g.integers(len(rs))]
                i = g.choice(x.shape[0], min(args.batch, x.shape[0]), replace=False)
                return x[i], phi, ys[i], ms[i], y[i]
            return draw

        # ridge: 8 alphas; network: 8 configurations -- the same budget, the same validation
        ridge_scores, best_r = [], None
        for a in ridge_grid:
            r = ConditionedRidge(alpha=a).fit(tr_rows)
            v = float(np.mean((r.forward(*va_rows[0][:4]) - va_rows[0][4]) ** 2))
            ridge_scores.append({"alpha": a, "val_mse": v})
            if best_r is None or v < best_r[0]:
                best_r = (v, r)
        net_scores, best_n = [], None
        for i, cfg in enumerate(net_grid):
            net = ConditionedNet(tr_rows[0][0].shape[1], G, hidden=cfg["hidden"], k=cfg["k"], seed=args.seed + i)
            fit = net.fit(sampler(), va_rows, lr=3e-3, l2=cfg["l2"], steps=steps, check_every=100, patience=6)
            net_scores.append(cfg | {"val_mse": fit["best_val_mse"], "steps_run": fit["steps_run"]})
            log(f"{name} net {cfg}: val {fit['best_val_mse']:.5f} ({fit['steps_run']} steps)")
            if best_n is None or fit["best_val_mse"] < best_n[0]:
                best_n = (fit["best_val_mse"], net)
        null_val = float(np.mean(va_rows[0][4] ** 2))
        transfer_val = float(np.mean((va_rows[0][2] * va_rows[0][3][:, None] - va_rows[0][4]) ** 2))
        manifest["splits"][name] = {"train_rows": {"K562": len(k_lab), "RPE1": len(r_lab)}, "val": [vctx, len(vt)],
                                    "encoder": enc.info, "ridge": ridge_scores, "net": net_scores,
                                    "val_mse_null": null_val, "val_mse_plain_transfer": transfer_val,
                                    "chosen": {"ridge_alpha": best_r[1].alpha, "net": best_n[1].config,
                                               "net_params": best_n[1].n_params(), "ridge_params": best_r[1].n_params()},
                                    "seconds": time.time() - ts}
        log(f"{name}: val mse null {null_val:.5f} transfer {transfer_val:.5f} ridge {best_r[0]:.5f} net {best_n[0]:.5f}")

        # predictions: every test panel, with the right context and with another context's controls
        for tname, (tctx, tl) in sp_["tests"].items():
            b = block(tctx, tl, None, k_lab, k_lab, mode_b=sp_["mode_b"])
            other = "RPE1"
            b_perm = block(tctx, tl, None, k_lab, k_lab, mode_b=sp_["mode_b"], phi_ctx=other)
            cov["tests"][tname] = coverage(b)
            preds = {"ridge": best_r[1].forward(*rows(b)[:4]), "net": best_n[1].forward(*rows(b)[:4]),
                     "net_ctxperm": best_n[1].forward(*rows(b_perm)[:4]), "nbr": b.nbr}
            if tctx == "K562":
                preds["k562mean"] = np.tile(np.mean(np.stack(list(k_lab.values())), axis=0), (len(tl), 1))
            for model, arr in preds.items():
                np.savez_compressed(args.out / f"pred_{name}_{tname}_{model}.npz", targets=np.array(tl),
                                    genes=np.array(genes), lfc=arr.astype(np.float32))
            # effect-space evaluation where a truth exists without the benches: K562 official
            if tctx == "K562":
                truth = np.stack([K[t] for t in tl])
                evaluation[f"{name}_{tname}"] = effect_space(preds, truth, rng)
        manifest["splits"][name]["coverage"] = cov
    # HepG2 effect-space truth for the test panel, from its cells (pooled fractions, EB-shrunk)
    ht_rows = {t: np.flatnonzero(h_sym == t) for t in ht}
    h_pos = pd.Index(h_names).get_indexer(genes)
    ctrl_stats = fraction_stats(h_ctrl)
    truth = []
    for t in ht:
        st = fraction_stats(read_rows(args.hepg2, ht_rows[t]))
        e, s = log_effect(st, ctrl_stats)
        truth.append(eb_shrink(e, s, ctrl_stats.mean > 0)[0][h_pos])
    truth = np.stack(truth)
    for name in ("C", "J"):
        preds = {m: np.load(args.out / f"pred_{name}_hepg2_test_{m}.npz")["lfc"] for m in ("ridge", "net", "net_ctxperm", "nbr")}
        if name == "C":
            preds["transfer"] = np.stack([K.get(t, np.zeros(G, np.float32)) for t in ht])
        evaluation[f"{name}_hepg2_test"] = effect_space(preds, truth, rng)
    (args.out / "effect_space.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["seconds_total"] = time.time() - t0
    manifest["panels_sha256"] = {n: hashlib.sha256("\n".join(v).encode()).hexdigest() for n, v in panel.items()}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    log(f"done in {time.time() - t0:.0f}s")


def effect_space(preds: dict, truth: np.ndarray, rng, n_boot: int = 2000) -> dict:
    """Per-target Pearson r and MSE against a truth that no training label contains."""
    out = {}
    for m, pr in preds.items():
        pr = np.asarray(pr, dtype=np.float64)
        r = np.array([np.corrcoef(a, b)[0, 1] if a.std() > 0 and b.std() > 0 else 0.0 for a, b in zip(pr, truth)])
        mse = ((pr - truth) ** 2).mean(axis=1)
        idx = rng.integers(0, len(r), (n_boot, len(r)))
        out[m] = {"pearson_mean": float(r.mean()), "pearson_ci95": np.quantile(r[idx].mean(1), [0.025, 0.975]).tolist(),
                  "mse_mean": float(mse.mean()), "mse_ci95": np.quantile(mse[idx].mean(1), [0.025, 0.975]).tolist(),
                  "n_targets": int(len(r))}
    return out


if __name__ == "__main__":
    main()
