"""Nested-family training of biological source attention, using r2 memmaps.

CPU or CUDA, no network access, no edits to historical code/data. One --holdout family
per new output folder; use --holdout none for production after independent validation.
Run from a local disk copy of r2 on the remote runner (not mmap across a Drive mount).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
import numpy as np
import pandas as pd
import torch

from neural_sources import P, SourceView, SourceAttention, directional_loss, cis_hidden, finite_mean, HERE


def json_default(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, Path):
        return str(x)
    raise TypeError(type(x).__name__)


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=json_default), encoding="utf-8")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fixed_rows(pool, contexts, count, seed):
    out = {}
    for c in contexts:
        rows = pool.ctx_rows[c]
        rows = rows[~pool.tgt_panel[pool.row_target[rows]]]
        rng = np.random.default_rng([seed, int(c)])
        out[int(c)] = np.sort(rng.choice(rows, min(count, len(rows)), replace=False))
    return out


def design(pool, args):
    usable = np.flatnonzero(pool.ctx_modality == "crispri")
    if args.holdout != "none" and args.holdout not in pool.family_names:
        raise ValueError(f"Unknown family {args.holdout}; choose {pool.family_names}")
    held = [c for c in usable if pool.family_names[pool.ctx_family[c]] == args.holdout]
    visible_ctx = np.setdiff1d(usable, held)
    test = fixed_rows(pool, held, args.test_targets, args.selection_seed)
    hidden_targets = np.array([], int)
    if args.regime == "J":
        if not test:
            raise ValueError("J needs a held-out family")
        hidden_targets = cis_hidden(pool, np.unique(pool.row_target[np.concatenate(list(test.values()))]))
    visible = np.concatenate([pool.ctx_rows[c] for c in visible_ctx])
    visible = visible[~np.isin(pool.row_target[visible], hidden_targets)]
    families = sorted(set(pool.ctx_family[pool.row_context[visible]]))
    if len(families) < 3:
        raise ValueError("At least three visible families required for nested validation")
    counts = sorted((int((pool.ctx_family[pool.row_context[visible]] == f).sum()), int(f)) for f in families)
    val_family = counts[len(counts) // 2][1]
    val_contexts = [c for c in visible_ctx if pool.ctx_family[c] == val_family]
    val = fixed_rows(pool, val_contexts, args.validation_targets, args.selection_seed + 1)
    val = {c: r[~np.isin(pool.row_target[r], hidden_targets)] for c, r in val.items()}
    train = visible[pool.ctx_family[pool.row_context[visible]] != val_family]
    inner_hidden = np.array([], int)
    if args.regime == "J":
        inner_hidden = cis_hidden(pool, np.unique(pool.row_target[np.concatenate(list(val.values()))]))
        train = train[~np.isin(pool.row_target[train], inner_hidden)]
    return {"train": train, "refit": visible, "validation": val, "test": test,
            "hidden_contexts": held, "validation_family": pool.family_names[val_family],
            "hidden_targets": hidden_targets, "inner_hidden_targets": inner_hidden}


def truth_arrays(view, rows, genes):
    raw = np.asarray(view.pool.arrays["raw"][np.ix_(rows, genes)], np.float32)
    # Truth-side centring is used only in evaluation, never as a model feature.
    centre = np.zeros(view.pool.G, np.float32)
    centre[genes] = finite_mean(raw, axis=0)
    c = int(view.pool.row_context[rows[0]])
    return view.labels(rows, genes, truth=True, centres={c: centre})


@torch.no_grad()
def predict(view, model, targets, basal, family, genes, args, *, blind=False, swap=None, perm=None, frozen=False):
    model.eval()
    pred = np.zeros((len(targets), len(genes)), np.float32)
    support = np.zeros(pred.shape, bool)
    for start in range(0, len(targets), args.batch):
        ts = targets[start:start + args.batch]
        for gstart in range(0, len(genes), args.gene_batch):
            g = genes[gstart:gstart + args.gene_batch]
            b = view.batch(ts, np.full(len(ts), basal), np.full(len(ts), family), g, device=args.device,
                           blind=blind, swap_basal=swap, prior_permutation=perm)
            out = model(b, frozen=frozen)
            pred[start:start + len(ts), gstart:gstart + len(g)] = out["prediction"].cpu().numpy()
            support[start:start + len(ts), gstart:gstart + len(g)] = out["support"].cpu().numpy()
    return pred, support


def metrics(pred, truth, keep, baseline):
    common = keep.all(0)
    if common.sum() < 10:
        raise ValueError(f"Only {common.sum()} common measured genes; cannot interpret rank discrimination")
    p, y, base = pred[:, common].astype(float), truth[:, common].astype(float), baseline[:, common].astype(float)
    pn, yn = np.linalg.norm(p, axis=1), np.linalg.norm(y, axis=1)
    cor = (p / np.maximum(pn[:, None], 1e-12)) @ (y / np.maximum(yn[:, None], 1e-12)).T
    own = np.diag(cor)
    rank = (cor > own[:, None]).sum(1) + .5 * ((cor == own[:, None]).sum(1) - 1)
    pds = 1 - rank / max(len(p) - 1, 1)
    base_norm = np.linalg.norm(base, axis=1)
    return {"rank": pds, "cosine": own,
            "nmse": ((p - y) ** 2).sum(1) / np.maximum((y ** 2).sum(1), 1e-12),
            "norm_ratio": pn / np.maximum(base_norm, 1e-12),
            "zero_prediction": pn < 1e-12, "zero_baseline": base_norm < 1e-12,
            "common_genes": int(common.sum())}


def validation(view, model, sets, args, *, blind=False):
    genes = np.sort(np.random.default_rng(args.selection_seed + 2).choice(
        view.pool.G, min(args.validation_genes, view.pool.G), replace=False))
    scores = []
    for c, rows in sets.items():
        if len(rows) < 2:
            continue
        pool = view.pool
        pred, support = predict(view, model, pool.row_target[rows], pool.ctx_basal[c], pool.ctx_family[c], genes, args, blind=blind)
        y, keep, _ = truth_arrays(view, rows, genes)
        m = metrics(pred, y, keep, pred)
        scores.append(float(m["rank"].mean()))
    if not scores:
        raise ValueError("No validation context has two targets")
    return float(np.mean(scores))


def fit(view, args, steps, *, blind=False, val=None, logger=print):
    torch.manual_seed(args.seed)
    if args.device.startswith("cuda"):
        torch.cuda.manual_seed_all(args.seed)
    rng = np.random.default_rng(args.seed)
    model = SourceAttention(view.n_priors).to(args.device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    best_state, best_step, best_score = copy.deepcopy(model.state_dict()), 0, -np.inf
    history, stale, skipped = [], 0, 0
    if val is not None:
        best_score = validation(view, model, val, args, blind=blind)
        history.append({"step": 0, "validation_rank": best_score})
        logger(f"{'blind' if blind else 'true'} step=0 validation_rank={best_score:.6f}")
    pool = view.pool
    families = np.unique(pool.ctx_family[view.contexts])
    for step in range(1, steps + 1):
        f = rng.choice(families)
        c = int(rng.choice(view.contexts[pool.ctx_family[view.contexts] == f]))
        candidates = view.rows[pool.row_context[view.rows] == c]
        rows = rng.choice(candidates, min(args.batch, len(candidates)), replace=False)
        if len(np.unique(pool.row_target[rows])) != len(rows):
            raise ValueError("Duplicate target in a contrastive batch")
        genes = np.sort(rng.choice(pool.G, min(args.gene_batch, pool.G), replace=False))
        batch = view.batch(pool.row_target[rows], pool.ctx_basal[pool.row_context[rows]],
                           pool.ctx_family[pool.row_context[rows]], genes, device=args.device, blind=blind)
        y, keep, _ = view.labels(rows, genes)
        model.train()
        out = model(batch)
        loss, n = directional_loss(out, torch.as_tensor(y, device=args.device), torch.as_tensor(keep, device=args.device))
        if loss is None:
            skipped += 1
        else:
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            opt.step()
        if step % args.eval_every == 0 or step == steps:
            rec = {"step": step, "loss": float(loss.detach()) if loss is not None else None,
                   "usable_rows": n, "skipped_batches": skipped}
            if val is not None:
                score = validation(view, model, val, args, blind=blind)
                rec["validation_rank"] = score
                if score > best_score + 1e-6:
                    best_score, best_step, best_state, stale = score, step, copy.deepcopy(model.state_dict()), 0
                else:
                    stale += 1
            history.append(rec)
            logger(f"{'blind' if blind else 'true'} {json.dumps(rec)}")
            if val is not None and stale >= args.patience:
                break
    if val is not None:
        model.load_state_dict(best_state)
    else:
        best_step = steps
    return model, history, best_step


def paired_bootstrap(values, seed, n=2000):
    x = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return {"mean": float(x.mean()), "ci95": np.quantile(means, [.025, .975]).tolist(), "targets": len(x)}


def evaluate(view, models, sets, args, out_dir):
    pool, genes = view.pool, np.arange(view.pool.G)
    rows_out, contrasts, grouped_delta = [], {}, {}
    perm = np.random.default_rng(args.selection_seed + 4).permutation(len(pool.target_names))
    for c, rows in sets.items():
        if len(rows) < 2:
            continue
        targets = pool.row_target[rows]
        basal = pool.ctx_basal[c]
        swap = int(pool.ctx_basal[view.contexts[0]])
        arms, support = {}, None
        specs = [("net", models["true"], {}), ("blind", models["blind"], {"blind": True}),
                 ("swap", models["true"], {"swap": swap}), ("prior_permuted", models["true"], {"perm": perm}),
                 ("transfer", models["true"], {"frozen": True})]
        for name, model, kw in specs:
            arms[name], mask = predict(view, model, targets, basal, pool.ctx_family[c], genes, args, **kw)
            support = mask if support is None else support & mask
        arms["null"] = np.zeros_like(arms["transfer"])
        y, keep, _ = truth_arrays(view, rows, genes)
        stats = {name: metrics(x, y, keep, arms["transfer"]) for name, x in arms.items()}
        for name, values in stats.items():
            for i, t in enumerate(targets):
                rows_out.append({"context": pool.context_names[c], "family": pool.family_names[pool.ctx_family[c]],
                                 "target": pool.target_names[t], "arm": name,
                                 "source_supported_genes": int(support[i].sum()), "no_source_prediction": bool(~support[i].any()),
                                 **{k: v[i].item() if isinstance(v, np.ndarray) else v for k, v in values.items()}})
        contrasts[pool.context_names[c]] = {}
        for reference in ("transfer", "blind", "swap", "prior_permuted", "null"):
            d = stats["net"]["rank"] - stats[reference]["rank"]
            contrasts[pool.context_names[c]][reference] = paired_bootstrap(d, args.selection_seed + c)
        grouped_delta[pool.context_names[c]] = stats["net"]["rank"] - stats["transfer"]["rank"]
        full = {}
        for name, x in arms.items():
            full[name] = np.full((len(targets), len(pool.axis)), np.nan, np.float32)
            # Keep all train-supported output genes, with zero for absent source predictions.
            # Own/cis and globally unmodelled genes remain holes for an explicit later adapter.
            modeled = np.stack([view.gene_keep & ~view._exclusion(t, genes) for t in targets])
            full[name][:, pool.genes_axis] = np.where(modeled, x, np.nan)
        np.savez_compressed(out_dir / f"pred_{pool.context_names[c]}.npz", targets=np.asarray([pool.target_names[t] for t in targets], dtype=str),
                            genes=np.asarray(pool.axis, dtype=str), **full)
    pd.DataFrame(rows_out).to_csv(out_dir / "per_target.csv", index=False)
    write_json(out_dir / "contrasts.json", contrasts)
    # Equal context weights; root combines independent outer folds with equal family weights.
    rng = np.random.default_rng(args.selection_seed + 5)
    boots = np.zeros(2000)
    for d in grouped_delta.values():
        boots += d[rng.integers(0, len(d), (2000, len(d)))].mean(1) / len(grouped_delta)
    summary = {"scope": "one outer family; not the cross-family promotion verdict", "contexts": contrasts,
               "rank_delta_macro_context": float(np.mean([x.mean() for x in grouped_delta.values()])) if grouped_delta else None,
               "ci95_stratified_targets": np.quantile(boots, [.025, .975]).tolist() if grouped_delta else None,
               "not_vcc_score": True}
    write_json(out_dir / "summary.json", summary)
    return summary


def run(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    pool = P.Pool.from_dir(args.data, mmap=True)
    plan = design(pool, args)
    args.out.mkdir(parents=True)
    small_files = [HERE / "PROTOCOLLO_NEURALE.md", HERE / "neural_sources.py", Path(__file__), Path(P.__file__)]
    data_files = {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p) if p.stat().st_size < 30_000_000 else None}
                  for p in sorted(args.data.iterdir()) if p.is_file()}
    manifest = {"status": "registered_before_training", "options": vars(args),
                "data_files": data_files, "large_array_identity": "size plus dataset manifest; arrays not individually rehashed",
                "code_hashes": {str(p): sha256(p) for p in small_files},
                "design": plan, "context_names": pool.context_names, "family_names": pool.family_names,
                "prior_columns": pool.prior_cols, "torch_version": torch.__version__,
                "dimensions": {"genes": pool.G, "contexts": len(pool.context_names), "rows": pool.n_rows,
                               "token_features_per_batch_float32_bytes": args.batch * len(pool.context_names) * args.gene_batch * 20 * 4}}
    write_json(args.out / "manifest.json", manifest)
    if args.plan_only:
        print(json.dumps({"manifest": str(args.out / "manifest.json"), "dimensions": manifest["dimensions"],
                          "validation_family": plan["validation_family"], "no_outcomes_read": True}, default=json_default), flush=True)
        return manifest
    started = time.time()
    log_path = args.out / "log.txt"
    def log(message):
        line = f"[{time.time() - started:.1f}s] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    log(f"data {pool.n_rows} rows; outer {args.holdout}; inner {plan['validation_family']}; regime {args.regime}")
    cache = {}
    view = SourceView(pool, plan["train"], centres_cache=cache)
    models, best_steps, histories = {}, {}, {}
    for name in ("true", "blind"):
        _, history, best_step = fit(view, args, args.steps, blind=name == "blind", val=plan["validation"], logger=log)
        best_steps[name], histories[name] = best_step, history
        write_json(args.out / "training_selection.json", {"best_steps": best_steps, "history": histories})
    del view
    view = SourceView(pool, plan["refit"], centres_cache=cache)
    for name in ("true", "blind"):
        model, history, _ = fit(view, args, best_steps[name], blind=name == "blind", logger=log)
        models[name] = model
        torch.save({"state_dict": model.state_dict(), "n_priors": view.n_priors, "selected_steps": best_steps[name],
                    "options": vars(args), "visible_rows": plan["refit"]}, args.out / f"model_{name}.pt")
        write_json(args.out / f"refit_{name}.json", history)
    summary = evaluate(view, models, plan["test"], args, args.out)
    if args.predict_contexts:
        if not args.predict_targets:
            raise ValueError("--predict-contexts requires --predict-targets")
        names = [s.strip() for s in args.predict_targets.read_text(encoding="utf-8").splitlines() if s.strip()]
        targets = np.array([pool.target_index[t] for t in names if t in pool.target_index], int)
        for context in args.predict_contexts.split(","):
            basal = pool.basal_index[context]
            values = {}
            for name, model, kw in (("net", models["true"], {}), ("blind", models["blind"], {"blind": True}),
                                    ("transfer", models["true"], {"frozen": True})):
                pred, support = predict(view, model, targets, basal, -1, np.arange(pool.G), args, **kw)
                values[name] = np.full((len(targets), len(pool.axis)), np.nan, np.float32)
                modeled = np.stack([view.gene_keep & ~view._exclusion(t, np.arange(pool.G)) for t in targets])
                values[name][:, pool.genes_axis] = np.where(modeled, pred, np.nan)
            np.savez_compressed(args.out / f"pred_{context}.npz", targets=np.asarray([pool.target_names[t] for t in targets], dtype=str),
                                genes=np.asarray(pool.axis, dtype=str), **values)
    summary.update({"seconds_measured": time.time() - started, "best_steps": best_steps,
                    "parameters": sum(p.numel() for p in models["true"].parameters())})
    write_json(args.out / "summary.json", summary)
    log(f"complete {json.dumps(summary, default=json_default)}")
    return summary


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--holdout", required=True, help="family name, or none for the separately authorized production fit")
    ap.add_argument("--regime", choices=["C", "J"], default="C")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--selection-seed", type=int, default=20260929)
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--eval-every", type=int, default=50)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--gene-batch", type=int, default=1024)
    ap.add_argument("--validation-genes", type=int, default=2048)
    ap.add_argument("--test-targets", type=int, default=512)
    ap.add_argument("--validation-targets", type=int, default=128)
    ap.add_argument("--lr", type=float, default=.001)
    ap.add_argument("--predict-contexts", default="")
    ap.add_argument("--predict-targets", type=Path)
    ap.add_argument("--plan-only", action="store_true", help="metadata and split only; no effect reads, training or score")
    return ap


if __name__ == "__main__":
    run(parser().parse_args())
