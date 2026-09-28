"""PCA baseline: the same context_embeddings.npz as pretrain.py, from a PCA of the same corpus (numpy and pandas).

    python pca_baseline.py --corpus OURS1 [--corpus OURS2 ...] --out NEW --reference-corpora 2 \
        --exclude-preset orion --require k562,...,A,B,C --expect-excluded orion_hct116,orion_hek293t [--d-emb 32]

Same data arguments and the same corpus.prepare as pretrain.py: same exclusions, genes, normalisation, training
profiles and statistics weights, so the two differ only by the map from a profile to its embedding.

* Fit: the training profiles' standardised values (a gene the profile does not measure counts as the training
  mean, 0), each row weighted by sqrt(its statistics weight: its context's sampling probability over its
  profiles); the first --d-emb right singular vectors W.
* Embed: every profile's coordinates by least squares on the genes it measures, (W_m' W_m + ridge I)^-1 W_m' x_m
  (the plain projection W'x when it measures every model gene); a context's embedding is the mean over its
  profiles, excluded ones included.
* Reconstruction on held-out profiles: the same fixed masks as pretrain.py (corpus.eval_views with the same
  rows and seeds): coordinates from the visible genes, then W z on the hidden ones. A linear reference for the
  encoder's numbers.

Outputs in --out (a new folder): context_embeddings.npz, manifest.json (method "pca", explained variance),
pca_model.npz (W, mean, SD, genes), genes.txt, log.txt.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import corpus as CO  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    CO.add_data_arguments(ap)
    ap.add_argument("--out", type=Path, default=None, help="new output folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--d-emb", type=int, default=32, help="components")
    ap.add_argument("--ridge", type=float, default=1e-6)
    ap.add_argument("--mask-frac", type=float, default=0.3, help="as pretrain.py, for the reconstruction report")
    ap.add_argument("--eval-profiles", type=int, default=2000)
    return ap


def fit_pca(prep: CO.Prepared, k: int) -> tuple[np.ndarray, np.ndarray]:
    """(W [G, k], explained variance share of each component) from the weighted training profiles."""
    rows = prep.train_rows
    w = prep.profile_weight[rows]
    X = np.nan_to_num(prep.z[rows]).astype(np.float64) * np.sqrt(w / w.sum())[:, None]
    _, S, Vt = np.linalg.svd(X, full_matrices=False)
    k = min(k, Vt.shape[0])
    total = float((S ** 2).sum())
    return Vt[:k].T.copy(), (S[:k] ** 2 / total) if total > 0 else np.zeros(k)


def project(Z: np.ndarray, W: np.ndarray, ridge: float) -> np.ndarray:
    """Least-squares coordinates of each row of Z on W over its finite entries (rows with the same pattern of
    finite entries are solved together)."""
    n, k = Z.shape[0], W.shape[1]
    out = np.zeros((n, k))
    fin = np.isfinite(Z)
    keys = np.packbits(fin, axis=1)
    groups: dict = {}
    for i in range(n):
        groups.setdefault(keys[i].tobytes(), []).append(i)
    eye = np.eye(k)
    for members in groups.values():
        idx = np.asarray(members, dtype=np.int64)
        m = fin[idx[0]]
        if not m.any():
            continue
        Wm = W[m]
        B = Z[np.ix_(idx, np.flatnonzero(m))].astype(np.float64) @ Wm
        out[idx] = np.linalg.solve(Wm.T @ Wm + ridge * eye, B.T).T
    return out


def run(argv=None, log=None) -> dict:
    args = build_parser().parse_args(argv)
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
    W, explained = fit_pca(prep, args.d_emb)
    log(f"PCA: {W.shape[1]} components on {prep.train_rows.size} training profiles x {prep.G} genes; explained "
        f"{float(explained.sum()):.3f} of the weighted variance")
    Zp = project(prep.z, W, args.ridge).astype(np.float32)
    recon = {}
    src = prep.meta["source"].to_numpy()
    for label, (set_id, rows) in prep.eval_sets(args.eval_profiles, args.seed).items():
        if rows.size == 0:
            recon[label] = None
            continue
        views = CO.eval_views(prep, rows, args.seed, set_id, args.mask_frac)
        visible = np.where(views["vis"], prep.z[rows], np.nan)
        xhat = (project(visible, W, args.ridge) @ W.T).astype(np.float32)
        recon[label] = CO.recon_metrics(xhat, views["target"], views["scored"], src[rows])
    geometry = CO.embedding_geometry(Zp, prep)
    emb_meta = {"method": "pca", "stage": "encoder_contesto_2026-09-28/pca_baseline.py", "created_utc": started,
                "d_emb": int(W.shape[1]), "norm": prep.mode, "genes": prep.G, "seed": args.seed,
                "excluded_contexts": prep.report["contexts"]["excluded"]}
    written = CO.write_embeddings(out, prep, Zp, emb_meta)
    with open(out / "pca_model.npz", "xb") as fh:
        np.savez_compressed(fh, components=W.astype(np.float32), explained=explained, mu=prep.mu, sd=prep.sd,
                            genes_axis=prep.genes)
    (out / "genes.txt").write_text("\n".join(str(int(g)) for g in prep.genes) + "\n", encoding="utf-8")
    manifest = {
        "format": CO.EMB_FORMAT, "method": "pca", "stage": "encoder_contesto_2026-09-28/pca_baseline.py",
        "claim_type": "linear embeddings of basal profiles; a reference for the encoder, not evidence about "
                      "perturbations",
        "created_utc": started, "args": vars(args), "numpy": np.__version__, **prep.report,
        "pca": {"components": int(W.shape[1]), "explained": explained, "explained_total": float(explained.sum()),
                "ridge": args.ridge},
        "reconstruction": recon, "geometry": geometry, "embeddings": written, "seconds": round(time.time() - t0, 1)}
    manifest["bytes"] = {p.name: p.stat().st_size for p in sorted(out.iterdir()) if p.is_file()}
    CO.write_json(out / "manifest.json", manifest)
    v = recon.get("val") or {}
    log(f"done: {out}; masked-gene R2 against the mean on validation {v.get('r2_vs_mean')}")
    if own_log:
        log.close()
    return {"out": out, "prep": prep, "W": W, "Zp": Zp, "manifest": manifest, "exit": 0}


def main() -> None:
    sys.exit(run()["exit"])


if __name__ == "__main__":
    main()
