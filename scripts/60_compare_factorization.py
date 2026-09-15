"""Exact vs randomized truncated SVD, on the matrices the benchmark actually uses.

Two jobs, kept apart:

1. Factorisation on a real training matrix: time, peak RSS, reconstruction,
   explained variance, canonical angles, seed-to-seed spread. Singular vectors
   are not compared elementwise.
2. If two pilot directories are given, the paired prediction comparison on
   identical splits: pooled primary metric and mean of per-target ratios,
   labelled as different aggregations.

Does not download, does not submit, does not touch the generator or scorer.

    scripts/py.cmd scripts/60_compare_factorization.py --out reports/svd_2026-09-15
    scripts/py.cmd scripts/60_compare_factorization.py --out reports/svd_2026-09-15 ^
        --exact-run <artifact>/s001 --randomized-run <artifact>/s002
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.benchmark.evaluate import (
    paired_difference,
    paired_pooled_difference,
)
from vcc2026.benchmark.factorization import (
    FactorizationSpec,
    factorize,
    ranks_compatible_with_shape,
    relative_reconstruction_error,
)
from vcc2026.benchmark.protocol import load_yaml_config, make_split
from vcc2026.benchmark.run import (
    _stack,
    _stack_rows,
    _targets_of,
    jsonable,
)
from vcc2026.benchmark.universe import common_measured_universe
from vcc2026.manifest import RunManifest
from vcc2026.registry import load_registry
from vcc2026.resources import peak_rss_bytes, snapshot
from vcc2026.signatures import SignatureSet


def _canonical_angles(vt_a: np.ndarray, vt_b: np.ndarray) -> dict:
    """Principal angles between two row-spaces. Not an elementwise comparison."""
    try:
        from scipy.linalg import subspace_angles
    except ImportError:
        return {"skipped": "scipy.linalg.subspace_angles not importable"}
    angles = subspace_angles(vt_a.T, vt_b.T)
    return {
        "n": int(angles.size),
        "max_radians": float(np.max(angles)) if angles.size else None,
        "median_radians": float(np.median(angles)) if angles.size else None,
        "max_degrees": float(np.degrees(np.max(angles))) if angles.size else None,
    }


def _time_factorize(Yc, rank, spec, repeat: int = 3) -> dict:
    times = []
    last = None
    rss0 = peak_rss_bytes()
    for _ in range(repeat):
        t0 = time.perf_counter()
        last = factorize(Yc, rank, spec)
        times.append(time.perf_counter() - t0)
    rss1 = peak_rss_bytes()
    return {
        "best_seconds": float(min(times)),
        "median_seconds": float(np.median(times)),
        "repeat": repeat,
        "rss_bytes_before": rss0,
        "peak_rss_bytes_after": rss1,
        "result": last,
    }


def _worker_main(args: argparse.Namespace) -> None:
    Yc = np.load(args.matrix)
    spec = FactorizationSpec(
        method=args.method,
        n_oversamples=args.n_oversamples,
        n_iter=args.n_iter,
        seed=None if args.method == "exact" else int(args.seed),
    )
    rss0 = peak_rss_bytes()
    t0 = time.perf_counter()
    fac = factorize(Yc, int(args.rank), spec)
    seconds = time.perf_counter() - t0
    rss1 = peak_rss_bytes()
    out = {
        "method_used": fac.method_used,
        "fallback": fac.fallback,
        "k": fac.k,
        "seconds": seconds,
        "rss_bytes_before": rss0,
        "peak_rss_bytes_after": rss1,
        "nbytes_U": int(fac.U.nbytes),
        "nbytes_Vt": int(fac.Vt.nbytes),
        "nbytes_Yc": int(Yc.nbytes),
        "singular_values": [float(x) for x in fac.S],
    }
    np.savez_compressed(args.out_factors, U=fac.U, S=fac.S, Vt=fac.Vt)
    Path(args.out_json).write_text(json.dumps(out), encoding="utf-8")
    print(json.dumps(out))


def _run_worker(matrix_path: Path, dest: Path, *, method: str, rank: int,
                seed: int, n_oversamples: int, n_iter: int) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    factors = dest / f"{method}_k{rank}_seed{seed}.npz"
    report = dest / f"{method}_k{rank}_seed{seed}.json"
    env = os.environ.copy()
    src = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable, str(Path(__file__).resolve()),
        "--worker",
        "--matrix", str(matrix_path),
        "--method", method,
        "--rank", str(rank),
        "--seed", str(seed),
        "--n-oversamples", str(n_oversamples),
        "--n-iter", str(n_iter),
        "--out-factors", str(factors),
        "--out-json", str(report),
    ]
    subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["factors"] = str(factors)
    return payload


def _build_training_matrix(cfg: dict, signatures_dirs: list[Path], *,
                           direction_id: str, protocol: str, seed: int) -> dict:
    """One fold's centred Y, the matrix MaskedLowRank actually factorises."""
    search_dirs = signatures_dirs
    source_npz = {}
    for sid in cfg["signatures"]["sources"]:
        found = next(
            (d / f"{sid}.npz" for d in search_dirs if (d / f"{sid}.npz").exists()),
            None,
        )
        if found is None:
            raise FileNotFoundError(
                f"signatures for {sid} in none of {[str(d) for d in search_dirs]}"
            )
        source_npz[sid] = found
    shared_from = cfg["signatures"].get("shared_targets_from") or list(
        cfg["signatures"]["sources"]
    )
    shared = sorted(set.intersection(
        *[_targets_of(source_npz[sid]) for sid in shared_from]
    ))
    max_t = cfg["pilot"].get("max_targets")
    rng = np.random.default_rng(int(cfg["pilot"]["seeds"][0]))
    if max_t and len(shared) > int(max_t):
        pick = rng.choice(len(shared), size=int(max_t), replace=False)
        shared_used = sorted(shared[int(i)] for i in pick)
    else:
        shared_used = shared
    direction = next(d for d in cfg["directions"] if d["id"] == direction_id)
    split = make_split(
        protocol=protocol,
        direction=direction,
        shared_targets=shared_used,
        seed=int(seed),
        unseen_fraction=float(cfg["unseen_fraction"]),
        inner_val_fraction=float(cfg["inner_val_fraction"]),
        uses_query_ntc=True,
    )
    train_by_source = {}
    for sid in split.train_sources:
        have = _targets_of(source_npz[sid])
        want = [t for t in split.train_targets if t in have]
        train_by_source[sid] = SignatureSet.read_npz(
            source_npz[sid], targets=want
        ).collapse_guides()
    test_sid = split.test_source
    have = _targets_of(source_npz[test_sid])
    want = [t for t in split.test_targets if t in have]
    test_sigs = SignatureSet.read_npz(source_npz[test_sid], targets=want).collapse_guides()
    universe_sets = dict(train_by_source)
    universe_sets[test_sid] = test_sigs
    universe = common_measured_universe(universe_sets)
    registry = load_registry()
    context_of_source = {
        sid: (registry[sid].cell_context or sid) for sid in split.train_sources
    }
    if len(split.train_sources) > 1:
        by_source_map = {
            sid: {s.target: s for s in train_by_source[sid]}
            for sid in split.train_sources
        }
        rows_pairs = [
            (t, sid)
            for sid in split.train_sources
            for t in split.train_targets
            if t in by_source_map[sid]
        ]
        Y, _ = _stack_rows(by_source_map, rows_pairs, universe)
    else:
        train_sigs = SignatureSet(
            [s for sid in split.train_sources for s in train_by_source[sid]]
        )
        Y, _, _, _ = _stack(train_sigs, list(split.train_targets), universe)
    mean = Y.mean(axis=0, keepdims=True)
    Yc = Y - mean
    return {
        "Yc": Yc,
        "mean": mean,
        "n_rows": int(Yc.shape[0]),
        "n_genes": int(Yc.shape[1]),
        "n_official": int(universe.n_official),
        "n_dropped": int(universe.n_dropped),
        "protocol": protocol,
        "direction_id": direction_id,
        "seed": int(seed),
        "n_train_targets": len(split.train_targets),
        "n_test_targets": len(split.test_targets),
        "frobenius": float(np.linalg.norm(Yc, ord="fro")),
    }


def _compact_to_per_target(compact: dict) -> list[dict]:
    targets = compact["targets"]
    sse = compact["sse"]
    sst = compact["sst"]
    ratios = compact["mse_vs_null"]
    out = []
    for i, t in enumerate(targets):
        out.append({
            "target": t,
            "sse": sse[i],
            "sst": sst[i],
            "mse_vs_null": ratios[i],
        })
    return out


def compare_prediction_runs(exact_dir: Path, rand_dir: Path, *, n_boot: int,
                            band: float) -> dict:
    exact = json.loads((exact_dir / "results.json").read_text(encoding="utf-8"))
    rand = json.loads((rand_dir / "results.json").read_text(encoding="utf-8"))
    by_e = {
        (r["protocol"], r["direction_id"], r["seed"], r["model"]): r
        for r in exact["rows"]
    }
    by_r = {
        (r["protocol"], r["direction_id"], r["seed"], r["model"]): r
        for r in rand["rows"]
    }
    shared = sorted(set(by_e) & set(by_r))
    missing_e = sorted(set(by_r) - set(by_e))
    missing_r = sorted(set(by_e) - set(by_r))
    rows = []
    all_inside = True
    any_outside = False
    any_too_wide = False
    for key in shared:
        er, rr = by_e[key], by_r[key]
        per_e = _compact_to_per_target(er["per_target_compact"])
        per_r = _compact_to_per_target(rr["per_target_compact"])
        pooled = paired_pooled_difference(per_r, per_e, n_boot=n_boot, seed=int(key[2]))
        mean_ratio = paired_difference(
            per_r, per_e, key="mse_vs_null", n_boot=n_boot, seed=int(key[2])
        )
        lo, hi = pooled.get("ci95") or [None, None]
        inside = (
            lo is not None and hi is not None
            and (-band) <= lo and hi <= band
        )
        entirely_outside = pooled.get("ci95_excludes_zero") and (
            lo is not None and (hi < -band or lo > band)
        )
        too_wide = lo is not None and hi is not None and (hi - lo) > 2 * band
        all_inside = all_inside and inside
        any_outside = any_outside or bool(entirely_outside)
        any_too_wide = any_too_wide or bool(too_wide)
        rows.append({
            "protocol": key[0],
            "direction_id": key[1],
            "seed": key[2],
            "model": key[3],
            "pooled_exact": er.get("pooled_mse_vs_null"),
            "pooled_randomized": rr.get("pooled_mse_vs_null"),
            "train_seconds_exact": er.get("train_seconds"),
            "train_seconds_randomized": rr.get("train_seconds"),
            "peak_rss_exact": er.get("peak_rss_bytes"),
            "peak_rss_randomized": rr.get("peak_rss_bytes"),
            "chosen_rank_exact": (er.get("selection") or {}).get("chosen"),
            "chosen_rank_randomized": (rr.get("selection") or {}).get("chosen"),
            "diff_paired_pooled": pooled,
            "diff_mean_per_target_ratio": mean_ratio,
            "inside_band": inside,
            "entirely_outside_band": entirely_outside,
            "interval_wider_than_band": too_wide,
        })
    if not shared:
        verdict = "no_shared_rows"
    elif any_outside:
        verdict = "not_compatible"
    elif any_too_wide or not all_inside:
        verdict = "inconclusive"
    else:
        verdict = "compatible_within_band"
    return {
        "n_shared_rows": len(shared),
        "missing_from_exact": [list(x) for x in missing_e],
        "missing_from_randomized": [list(x) for x in missing_r],
        "band": band,
        "verdict": verdict,
        "verdict_note": (
            "compatible_within_band is the pre-specified substitution rule, "
            "not a non-inferiority claim and not an architecture adoption."
        ),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--matrix", type=Path, default=None)
    parser.add_argument("--method", default=None)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--n-oversamples", type=int, default=10)
    parser.add_argument("--n-iter", type=int, default=2)
    parser.add_argument("--out-factors", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--signatures", type=Path, nargs="*", default=None)
    parser.add_argument("--direction", default="k562_rpe1_to_hepg2")
    parser.add_argument("--protocol", default="new_context_seen_target")
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--ranks", type=int, nargs="*", default=[16, 32, 64, 128])
    parser.add_argument("--factorization-seeds", type=int, nargs="*",
                        default=[2026, 2027, 2028])
    parser.add_argument("--exact-run", type=Path, default=None)
    parser.add_argument("--randomized-run", type=Path, default=None)
    parser.add_argument("--band", type=float, default=0.01)
    parser.add_argument("--n-boot", type=int, default=200)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    if args.worker:
        _worker_main(args)
        return

    if args.out is None:
        raise SystemExit("--out is required")
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "factorization_comparison.json"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out")

    cfg_path = args.config or (
        Path(__file__).resolve().parents[1] / "configs" / "benchmark_svd_exact.yaml"
    )
    cfg = load_yaml_config(cfg_path)
    if args.signatures:
        sig_dirs = [Path(p) for p in args.signatures]
    else:
        sig_dirs = [
            config.artifact_root() / "e001" / "signatures",
            config.artifact_root() / "e003" / "signatures",
        ]

    fold = _build_training_matrix(
        cfg, sig_dirs,
        direction_id=args.direction, protocol=args.protocol, seed=args.split_seed,
    )
    Yc = fold.pop("Yc")
    mean = fold.pop("mean")
    usable = ranks_compatible_with_shape(args.ranks, Yc.shape)
    skipped = [r for r in args.ranks if r not in usable]

    exact_full = _time_factorize(Yc, min(Yc.shape) - 1, FactorizationSpec(method="exact"))
    exact_fac = exact_full["result"]
    total_ss = float(np.sum(np.square(exact_fac.S)))
    # Variance explained by prefixes of the exact spectrum.
    explained = []
    for k in usable:
        share = float(np.sum(np.square(exact_fac.S[:k])) / total_ss) if total_ss else None
        explained.append({
            "rank": int(k),
            "explained_variance_ratio_exact": share,
            "note": (
                "fraction of Frobenius squared captured by the leading k "
                "exact components; not a prediction score"
            ),
        })

    work = Path(tempfile.mkdtemp(prefix="vcc2026-svd-"))
    matrix_path = work / "Yc.npy"
    np.save(matrix_path, Yc)

    isolated = []
    workers_dir = args.out / "workers"
    for rank in usable:
        exact_w = _run_worker(
            matrix_path, workers_dir, method="exact", rank=rank,
            seed=args.seed, n_oversamples=args.n_oversamples, n_iter=args.n_iter,
        )
        rand_w = _run_worker(
            matrix_path, workers_dir, method="randomized", rank=rank,
            seed=args.seed, n_oversamples=args.n_oversamples, n_iter=args.n_iter,
        )
        exact_npz = np.load(exact_w["factors"])
        rand_npz = np.load(rand_w["factors"])
        recon_e = relative_reconstruction_error(Yc, exact_npz["U"], exact_npz["S"], exact_npz["Vt"])
        recon_r = relative_reconstruction_error(Yc, rand_npz["U"], rand_npz["S"], rand_npz["Vt"])
        recon_vs_exact = float(
            np.linalg.norm(
                (exact_npz["U"] * exact_npz["S"]) @ exact_npz["Vt"]
                - (rand_npz["U"] * rand_npz["S"]) @ rand_npz["Vt"],
                ord="fro",
            )
            / max(np.linalg.norm((exact_npz["U"] * exact_npz["S"]) @ exact_npz["Vt"], ord="fro"),
                  1e-12)
        )
        s_rel = None
        if exact_npz["S"].size == rand_npz["S"].size and np.min(exact_npz["S"]) > 0:
            s_rel = float(np.mean(np.abs(rand_npz["S"] - exact_npz["S"]) / exact_npz["S"]))
        isolated.append({
            "rank": int(rank),
            "exact_worker": {k: v for k, v in exact_w.items() if k != "factors"},
            "randomized_worker": {k: v for k, v in rand_w.items() if k != "factors"},
            "speedup_exact_over_randomized": (
                None if rand_w["seconds"] <= 0
                else float(exact_w["seconds"] / rand_w["seconds"])
            ),
            "reconstruction_error_exact": recon_e,
            "reconstruction_error_randomized": recon_r,
            "reconstruction_randomized_vs_exact_rankk": recon_vs_exact,
            "mean_relative_singular_value_error": s_rel,
            "canonical_angles": _canonical_angles(exact_npz["Vt"], rand_npz["Vt"]),
            "singular_value_error_is_not_the_adoption_rule": True,
        })
        exact_npz.close()
        rand_npz.close()

    seed_spread = []
    k_ref = min(16, max(usable))
    ref_npz = np.load(workers_dir / f"randomized_k{k_ref}_seed{args.seed}.npz")
    ref_vt = np.array(ref_npz["Vt"])
    ref_recon = (ref_npz["U"] * ref_npz["S"]) @ ref_npz["Vt"]
    ref_npz.close()
    for seed in args.factorization_seeds:
        w = _run_worker(
            matrix_path, workers_dir, method="randomized", rank=k_ref,
            seed=int(seed), n_oversamples=args.n_oversamples, n_iter=args.n_iter,
        )
        npz = np.load(w["factors"])
        recon = relative_reconstruction_error(Yc, npz["U"], npz["S"], npz["Vt"])
        vs_ref = float(
            np.linalg.norm(ref_recon - (npz["U"] * npz["S"]) @ npz["Vt"], ord="fro")
            / max(np.linalg.norm(ref_recon, ord="fro"), 1e-12)
        )
        seed_spread.append({
            "seed": int(seed),
            "seconds": w["seconds"],
            "reconstruction_error": recon,
            "reconstruction_vs_seed_ref": vs_ref,
            "canonical_angles_vs_seed_ref": _canonical_angles(ref_vt, npz["Vt"]),
        })
        npz.close()

    prediction_cmp = None
    if args.exact_run or args.randomized_run:
        if not (args.exact_run and args.randomized_run):
            raise SystemExit("give both --exact-run and --randomized-run")
        prediction_cmp = compare_prediction_runs(
            Path(args.exact_run), Path(args.randomized_run),
            n_boot=args.n_boot, band=args.band,
        )

    report = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": (
            "does a randomized rank-k SVD replace the full SVD on the "
            "benchmark's real training matrix, and does that swap move "
            "out-of-sample pooled_mse_vs_null outside a pre-specified band"
        ),
        "fold": fold,
        "matrix_nbytes": int(Yc.nbytes),
        "column_mean_norm": float(np.linalg.norm(mean)),
        "ranks_requested": list(args.ranks),
        "ranks_compatible": usable,
        "ranks_skipped": skipped,
        "n_oversamples": args.n_oversamples,
        "n_iter": args.n_iter,
        "exact_full_svd": {
            "best_seconds": exact_full["best_seconds"],
            "median_seconds": exact_full["median_seconds"],
            "k_computed": exact_fac.k,
            "rss_bytes_before": exact_full["rss_bytes_before"],
            "peak_rss_bytes_after": exact_full["peak_rss_bytes_after"],
            "note": "one full economy SVD; truncating it to k is free afterwards",
        },
        "explained_variance_exact_prefixes": explained,
        "isolated_workers": isolated,
        "randomized_seed_spread": seed_spread,
        "prediction_comparison": prediction_cmp,
        "machine": snapshot(args.out).as_dict(),
        "not_a_vcc_score": True,
        "do_not_compare_singular_vectors_elementwise": True,
    }
    dest.write_text(json.dumps(jsonable(report), indent=2), encoding="utf-8")

    man = RunManifest(
        run_id=args.out.name, stage="60_compare_factorization",
        config={k: str(v) for k, v in vars(args).items() if k != "worker"},
        seed=args.seed,
    )
    man.add_output("report", dest)
    if prediction_cmp is not None:
        man.metrics = {
            "prediction_verdict": prediction_cmp["verdict"],
            "n_shared_rows": prediction_cmp["n_shared_rows"],
        }
    man.note(
        "Reconstruction and canonical angles diagnose the subspace. "
        "Adoption of randomized SVD as a drop-in uses the pre-specified "
        "pooled band on identical splits, not the singular values."
    )
    man.write(args.out / "manifest_60_compare_factorization.json",
              allow_overwrite=args.allow_overwrite)
    print(json.dumps({
        "out": str(dest),
        "n_rows": fold["n_rows"],
        "n_genes": fold["n_genes"],
        "ranks": usable,
        "prediction_verdict": None if prediction_cmp is None else prediction_cmp["verdict"],
    }, indent=2))


if __name__ == "__main__":
    main()
