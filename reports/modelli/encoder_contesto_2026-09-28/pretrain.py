"""Pre-train the context encoder (encoder.py) on basal profiles and write one embedding per context.

    python pretrain.py --corpus OURS1 [--corpus OURS2 ...] [--corpus TAHOE] --out NEW --reference-corpora 2 \
        --exclude-preset orion --require k562,cd4_Rest,...,A,B,C --expect-excluded orion_hct116,orion_hek293t
    python pretrain.py --corpus ... --out NEW --dry-run     read, exclude, choose genes, report; write nothing
    python pretrain.py --selftest                          the encoder part of selftest_emb.py (CPU)

Order (corpus.prepare, shared with pca_baseline.py so that the two differ only by the map from profile to
embedding): read the tables; drop profiles of other kinds or with too few cells; apply the exclusions (contexts,
families, studies, cell-line names; --exclude-preset expands to the explicit lists of corpus.PRESETS); check
--require and --expect-excluded; draw the validation contexts among those neither excluded nor required; choose
the genes on the first --reference-corpora corpora (so every data condition of a design gets the same genes);
normalise within each profile and standardise with statistics of the training profiles only.

Training: batches of --batch-contexts training contexts, drawn without replacement with equal mass per study
(--balance), --views profiles of each (with replacement: a context with one profile gives two augmented views of
it); each view gets a per-gene log bias (--platform-sd) on its inputs, a random mask (--mask-frac) and, with
probability --mask-borrow, the measured-gene pattern of another training profile. Loss: masked-gene
reconstruction + --lam-con x the consistency term (encoder.supcon). Early stopping on the validation contexts'
reconstruction (fixed masks), best state kept. Then every profile is embedded -- excluded ones included, since a
held-out context needs its embedding -- and averaged per context.

Outputs in --out (a new folder):
    encoder.pt               config, weights, normalisation (genes, means, SDs, mode, platforms)
    context_embeddings.npz   contexts, embeddings, n_profiles, status, profile-level embeddings (corpus.py)
    manifest.json            sources with sizes and hashes, exclusions and what they removed, genes, loss curves,
                             reconstruction on held-out profiles (validation contexts and excluded contexts) with the
                             predict-the-mean reference, embedding geometry, parameters
    history.csv, genes.txt, log.txt
The reconstruction numbers describe the encoder, not its use: success is measured on the network (DISEGNO.md).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import corpus as CO  # noqa: E402
import encoder as ENC  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    CO.add_data_arguments(ap)
    ap.add_argument("--out", type=Path, default=None, help="new output folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="the encoder checks of selftest_emb.py, on CPU")
    g = ap.add_argument_group("encoder and training")
    g.add_argument("--d-emb", type=int, default=32)
    g.add_argument("--d-hidden", type=int, default=512)
    g.add_argument("--dropout", type=float, default=0.1)
    g.add_argument("--no-platform-decoder", action="store_true", help="the decoder does not see the platform")
    g.add_argument("--mask-frac", type=float, default=0.3)
    g.add_argument("--mask-borrow", type=float, default=0.3)
    g.add_argument("--platform-sd", type=float, default=0.3, help="per-gene log bias on the training inputs")
    g.add_argument("--lam-con", type=float, default=0.1)
    g.add_argument("--temperature", type=float, default=0.2)
    g.add_argument("--views", type=int, default=2)
    g.add_argument("--batch-contexts", type=int, default=64)
    g.add_argument("--steps", type=int, default=20000, help="maximum steps (exact steps without validation)")
    g.add_argument("--eval-every", type=int, default=250)
    g.add_argument("--patience", type=int, default=10)
    g.add_argument("--lr", type=float, default=1e-3)
    g.add_argument("--weight-decay", type=float, default=1e-4)
    g.add_argument("--grad-clip", type=float, default=1.0)
    g.add_argument("--eval-profiles", type=int, default=2000, help="profiles per evaluation set, at most")
    g.add_argument("--device", default="auto")
    return ap


def resolve_device(name: str) -> str:
    if name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return name


def train_views(prep: CO.Prepared, idx: np.ndarray, rng, args) -> tuple:
    """Inputs, targets, scored mask and platform of one training batch (numpy)."""
    meas = prep.measured[idx]
    clean = prep.z[idx]
    if args.platform_sd > 0:
        eps = rng.normal(0.0, args.platform_sd, meas.shape).astype(np.float32)
        noisy = prep.standardise(prep.values(prep.cpm[idx] * np.exp(eps)))
    else:
        noisy = clean
    vis = meas & (rng.random(meas.shape) >= args.mask_frac)
    if args.mask_borrow > 0:
        pick = np.flatnonzero(rng.random(idx.size) < args.mask_borrow)
        if pick.size:
            other = rng.choice(prep.train_rows, size=pick.size)
            vis[pick] = vis[pick] & prep.measured[other]
    scored = meas & ~vis
    x_in = np.where(vis, noisy, 0.0).astype(np.float32)
    target = np.where(meas, clean, 0.0).astype(np.float32)
    return x_in, target, scored, prep.platform_index[idx]


@torch.no_grad()
def reconstruct(model: ENC.ContextEncoder, views: dict, dev, chunk: int = 512) -> np.ndarray:
    model.eval()
    n = views["x_in"].shape[0]
    out = np.empty(views["target"].shape, dtype=np.float32)
    for a in range(0, n, chunk):
        x = torch.from_numpy(views["x_in"][a:a + chunk]).to(dev)
        pl = torch.from_numpy(views["platform"][a:a + chunk]).to(dev)
        out[a:a + chunk] = model.decode(model(x), pl).float().cpu().numpy()
    return out


@torch.no_grad()
def embed_profiles(model: ENC.ContextEncoder, prep: CO.Prepared, dev, rows: np.ndarray | None = None,
                   chunk: int = 512) -> np.ndarray:
    """z of every profile (or of `rows`), every measured gene visible, no augmentation."""
    model.eval()
    rows = np.arange(prep.N) if rows is None else np.asarray(rows, dtype=np.int64)
    out = np.empty((rows.size, model.cfg.d_emb), dtype=np.float32)
    for a in range(0, rows.size, chunk):
        r = rows[a:a + chunk]
        x = np.where(prep.measured[r], prep.z[r], 0.0).astype(np.float32)
        out[a:a + chunk] = model(torch.from_numpy(x).to(dev)).float().cpu().numpy()
    return out


def train_encoder(prep: CO.Prepared, args, log=print):
    """Train from a fixed seed; early stopping on the validation contexts when there are some. Returns
    (model, history, best_step, steps_run)."""
    dev = torch.device(resolve_device(args.device))
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    rng = np.random.default_rng([args.seed, 5])
    cfg = ENC.EncoderConfig(n_genes=prep.G, d_emb=args.d_emb, d_hidden=args.d_hidden,
                            n_platforms=0 if args.no_platform_decoder else len(prep.platforms), dropout=args.dropout)
    model = ENC.ContextEncoder(cfg).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    n_ctx = int(prep.train_ctx.size)
    P = min(args.batch_contexts, n_ctx)
    sets = prep.eval_sets(args.eval_profiles, args.seed)
    set_id, vrows = sets["val"]
    val = CO.eval_views(prep, vrows, args.seed, set_id, args.mask_frac) if vrows.size else None
    log(f"encoder: {ENC.count_parameters(model)['total']} parameters; {n_ctx} training contexts, {P} per batch x "
        f"{args.views} views; validation {vrows.size} profiles" + ("" if val is not None else " (none: exact steps)"))
    history, bad, step = [], 0, 0
    best = {"loss": math.inf, "step": 0, "state": None}
    sums = [0.0, 0.0, 0]
    for step in range(1, args.steps + 1):
        pick = rng.choice(n_ctx, size=P, replace=False, p=prep.train_ctx_weight)
        idx = np.concatenate([rng.choice(prep.train_ctx_rows[j], size=args.views, replace=True) for j in pick])
        labels = np.repeat(np.arange(P, dtype=np.int64), args.views)
        x_in, target, scored, plat = train_views(prep, idx, rng, args)
        x = torch.from_numpy(x_in).to(dev)
        t = torch.from_numpy(target).to(dev)
        s = torch.from_numpy(scored).to(dev)
        pl = torch.from_numpy(plat).to(dev)
        lab = torch.from_numpy(labels).to(dev)
        model.train()
        z = model(x)
        rec = ENC.masked_mse(model.decode(z, pl), t, s)
        con = ENC.supcon(z, lab, args.temperature) if args.lam_con > 0 else rec.new_zeros(())
        loss = rec + args.lam_con * con
        if not math.isfinite(float(loss.detach())):
            raise FloatingPointError(f"non-finite loss at step {step}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        opt.step()
        sums[0] += float(rec.detach())
        sums[1] += float(con.detach())
        sums[2] += 1
        if step % args.eval_every == 0 or step == args.steps:
            rec_ = {"step": step, "train_rec": sums[0] / max(sums[2], 1), "train_con": sums[1] / max(sums[2], 1)}
            sums = [0.0, 0.0, 0]
            if val is not None:
                vm = CO.recon_metrics(reconstruct(model, val, dev), val["target"], val["scored"])
                rec_["val_mse"], rec_["val_r2"] = vm.get("masked_mse"), vm.get("r2_vs_mean")
                if vm.get("masked_mse") is not None and vm["masked_mse"] < best["loss"]:
                    best = {"loss": vm["masked_mse"], "step": step,
                            "state": {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}}
                    bad = 0
                else:
                    bad += 1
            history.append(rec_)
            log("step " + ", ".join(f"{k} {v:.5g}" if isinstance(v, float) else f"{k} {v}" for k, v in rec_.items()))
            if val is not None and bad >= args.patience:
                log(f"early stop at step {step}: no validation gain in {args.patience} evaluations; "
                    f"best step {best['step']}")
                break
    if val is not None and best["state"] is not None:
        model.load_state_dict(best["state"])
        return model, history, best["step"], step
    return model, history, step, step


def run(argv=None, log=None) -> dict:
    """The command line as a function (the self-test calls it)."""
    args = build_parser().parse_args(argv)
    if args.selftest:
        import selftest_emb
        return {"exit": selftest_emb.main(network=False)}
    if not args.corpus:
        raise SystemExit("--corpus is required")
    if args.out is None and not args.dry_run:
        raise SystemExit("--out is required (or --dry-run)")
    started, t0 = datetime.now(timezone.utc).isoformat(), time.time()
    out = None
    if not args.dry_run:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=False)
    own_log = log is None
    log = log or CO.Logger(None if out is None else out / "log.txt")
    prep = CO.prepare(args, log)
    if args.dry_run:
        log(json.dumps(CO.jsonable(prep.report), indent=1))
        return {"prep": prep, "exit": 0}
    model, history, best_step, steps_run = train_encoder(prep, args, log)
    dev = next(model.parameters()).device
    Zp = embed_profiles(model, prep, dev)
    recon = {}
    src = prep.meta["source"].to_numpy()
    for label, (set_id, rows) in prep.eval_sets(args.eval_profiles, args.seed).items():
        if rows.size == 0:
            recon[label] = None
            continue
        views = CO.eval_views(prep, rows, args.seed, set_id, args.mask_frac)
        recon[label] = CO.recon_metrics(reconstruct(model, views, dev), views["target"], views["scored"], src[rows])
    geometry = CO.embedding_geometry(Zp, prep)
    norm = prep.norm_payload()
    norm_t = {k: (torch.from_numpy(np.ascontiguousarray(v)) if isinstance(v, np.ndarray) else v) for k, v in norm.items()}
    ENC.save_encoder(out / "encoder.pt", model, norm_t, {"created_utc": started})
    emb_meta = {"method": "encoder", "stage": "encoder_contesto_2026-09-28/pretrain.py", "created_utc": started,
                "d_emb": args.d_emb, "norm": prep.mode, "genes": prep.G, "seed": args.seed,
                "excluded_contexts": prep.report["contexts"]["excluded"]}
    written = CO.write_embeddings(out, prep, Zp, emb_meta)
    (out / "genes.txt").write_text("\n".join(str(int(g)) for g in prep.genes) + "\n", encoding="utf-8")
    pd.DataFrame(history).to_csv(out / "history.csv", index=False)
    manifest = {
        "format": CO.EMB_FORMAT, "method": "encoder", "stage": "encoder_contesto_2026-09-28/pretrain.py",
        "claim_type": "unsupervised embeddings of basal profiles; the reconstruction numbers describe the encoder "
                      "and are not evidence that the embeddings help predict perturbations",
        "created_utc": started, "args": vars(args), "torch": torch.__version__, "numpy": np.__version__,
        "device": str(dev), **prep.report,
        "encoder": {"config": model.cfg.to_dict(), "parameters": ENC.count_parameters(model),
                    "best_step": int(best_step), "steps_run": int(steps_run)},
        "history": history, "reconstruction": recon, "geometry": geometry, "embeddings": written,
        "seconds": round(time.time() - t0, 1)}
    manifest["bytes"] = {p.name: p.stat().st_size for p in sorted(out.iterdir()) if p.is_file()}
    CO.write_json(out / "manifest.json", manifest)
    v = recon.get("val") or {}
    x = recon.get("excluded") or {}
    log(f"done: {out}; best step {best_step}; masked-gene R2 against the mean: validation {v.get('r2_vs_mean')}, "
        f"excluded {x.get('r2_vs_mean')}; within/between ratio {(geometry.get('all') or {}).get('ratio')}")
    if own_log:
        log.close()
    return {"out": out, "prep": prep, "model": model, "Zp": Zp, "manifest": manifest, "exit": 0}


def main() -> None:
    sys.exit(run()["exit"])


if __name__ == "__main__":
    main()
