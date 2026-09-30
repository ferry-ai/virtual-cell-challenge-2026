"""Prospective generator factorial on frozen K562 effects and held-out HepG2.

Prepare freezes targets, controls, source masks and input hashes before scoring.
Run scores one arm at a time, with 400 generated cells per target. The primary
five-member official-anchor projection is NOT an official VCC score.

scripts/py.cmd <this.py> --phase prepare --truth full --out <new-output>
scripts/py.cmd <this.py> --phase run --out <prepared-output> --split development
scripts/py.cmd <this.py> --phase run --out <prepared-output> --split confirmation --arms 1:0 bins:1

No live project module is modified. The legacy stage-75 g0 path is NOT reused:
observed masks, compositional shift and log2 clipping follow stage 45 instead.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "src"))
from vcc2026 import config
from vcc2026.bench import Bench, SCORED, log, to_anndata
from vcc2026.de_tools import ReferencePool, fast_scorer_de, scorer_config
from vcc2026.inference import predicted_profile
from vcc2026.resources import peak_rss_bytes, snapshot
from vcc2026.sampling import fit_gene_dispersion, resample_library_sizes, sample_counts
from vcc2026.sc_stream import read_frame

DATA = config.paths().data_root
CONTROL = "non-targeting"
AMP_GRID = (1.0, 1.5, 2.0)
PHI_GRID = (0.0, 0.25, 0.5, 1.0)
MSE = "expr_mse_unbiased_capped_norm"
FIVE = tuple(m for m in SCORED if m != MSE)
REGISTERED_ARMS = tuple((a, p, "pooled") for a in AMP_GRID for p in PHI_GRID) + (
    (1.0, 0.0, "bins"), (2.0, 0.0, "bins"))
REFERENCE = (1.0, 0.0, "pooled")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, obj) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False, default=str)
        stream.write("\n")


def numeric_token(value: float) -> str:
    return f"{value:g}".replace(".", "p")


def arm_name(amplitude: float, phi_scale: float, seed: int, generator: str = "pooled") -> str:
    if generator == "bins":
        return f"bins_a{numeric_token(amplitude)}_s{seed}"
    return f"a{numeric_token(amplitude)}_p{numeric_token(phi_scale)}_s{seed}"


def parse_arm(value: str) -> tuple[float, float, str]:
    if value.startswith("bins:"):
        amplitude = float(value.split(":", 1)[1])
        arm = (amplitude, 0.0, "bins")
        if arm not in REGISTERED_ARMS:
            raise ValueError(f"Bins arm outside the registered grid: {value}")
        return arm
    try:
        amplitude, phi_scale = map(float, value.split(":"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Arm must be AMPLITUDE:PHI_SCALE, got {value!r}") from exc
    if amplitude not in AMP_GRID or phi_scale not in PHI_GRID:
        raise ValueError(f"Arm outside the registered grid: {value}")
    return amplitude, phi_scale, "pooled"


def arm_cli(arm) -> str:
    amplitude, phi_scale, generator = arm
    return f"bins:{amplitude:g}" if generator == "bins" else f"{amplitude:g}:{phi_scale:g}"


def joint_shortlist(comparisons):
    """One shortlist across all families; no family-specific second chance."""
    chosen_arms, available = [], [c for c in comparisons if c["delta_projection"] > 0]
    while available and len(chosen_arms) < 2:
        best = max(c["delta_projection"] for c in available)
        near = [c for c in available if best - c["delta_projection"] < 0.002]
        chosen = min(near, key=lambda c: (abs(c["amplitude"] - 1), c["phi_scale"],
                                          c["generator"] != "pooled"))
        chosen_arms.append([chosen["amplitude"], chosen["phi_scale"], chosen["generator"]])
        available.remove(chosen)
    return chosen_arms


def relocated_path(filename: str, manifest: dict, data_root: Path | None) -> Path:
    """Resolve Windows-prepared manifests on a remote checkout without rewriting them."""
    normal = filename.replace("\\", "/")
    roots = manifest.get("path_roots", {})
    for key, destination in (("repo", REPO), ("data", data_root)):
        original = roots.get(key, "").replace("\\", "/").rstrip("/")
        if original and (normal == original or normal.startswith(original + "/")):
            if destination is not None:
                suffix = normal[len(original):].lstrip("/")
                return Path(destination) / suffix
    return Path(filename)


def load_depth_candidate():
    sys.path.insert(0, str(HERE / "generatore"))
    from depth_candidate import DepthCandidate
    return DepthCandidate


def workload_dimensions(n_targets: int, n_genes: int, control_cells: int, n_arms: int, n_seeds: int) -> dict:
    """Bounds and operation dimensions, not a walltime or peak-RAM promise."""
    predicted_cells = 400 * n_targets
    return {"predicted_cells_per_arm_seed": predicted_cells,
            "generated_cells_total": predicted_cells * n_arms * n_seeds,
            "target_blocks_total": n_targets * n_arms * n_seeds,
            "poisson_gene_rates_total": predicted_cells * n_genes * n_arms * n_seeds,
            "raw_dense_float32_prediction_bytes": predicted_cells * n_genes * 4,
            "csr_prediction_upper_bytes": predicted_cells * n_genes * 8 + (predicted_cells + 1) * 4,
            "csr_prediction_bytes_at_4000_nnz_per_cell": predicted_cells * min(4000, n_genes) * 8 + (predicted_cells + 1) * 4,
            "control_rank_complex128_upper_bytes": control_cells * n_genes * 16,
            "single_target_float64_rate_buffer_bytes": 400 * n_genes * 8,
            "scorer_calls": n_arms * n_seeds,
            "note": "CSR assembly and Bench.score create additional copies; scorer temporaries, truth and reference ranks add memory. Only one arm is retained. No walltime is inferred."}


def target_rng(seed: int, target: str) -> np.random.Generator:
    """Same target/seed stream in every arm, independent of traversal order."""
    hashed = hashlib.sha256(target.encode("utf-8")).digest()
    words = [int.from_bytes(hashed[i:i + 4], "little") for i in (0, 4)]
    return np.random.default_rng(np.random.SeedSequence([int(seed), *words]))


def select_targets(panel, genes, counts, seed: int, n_dev: int, n_confirm: int):
    eligible = sorted(set(panel) & set(genes) & {t for t, n in counts.items() if n >= 2})
    order = np.random.default_rng(seed).permutation(eligible).tolist()
    return eligible, order[:n_dev], order[n_dev:n_dev + n_confirm]


def source_mask(bulk: Path, targets: list[str], effect_genes: np.ndarray) -> tuple[np.ndarray, dict]:
    """Recover stage-98 evidence support, including its control-expression gate.

    The stored t19like values remain frozen. Re-estimating only the mask on a target
    subset does not change gamma's original centring over the 300-target panel.
    """
    stage_path = REPO / "scripts/98_multisource_effects.py"
    spec = importlib.util.spec_from_file_location("stage98_generator_audit", stage_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    table = module.k562_table(bulk, targets, effect_genes)
    index = table.index()
    missing = [t for t in targets if t not in index]
    if missing:
        raise ValueError(f"K562 source cannot reconstruct support for {missing}")
    mask = np.vstack([np.isfinite(table.shrunk[index[t]]) & (table.n_cells[index[t]] > 0)
                      for t in targets])
    return mask, {"method": "stage98.k562_table; finite shrunk values and positive n_cells",
                  "control_fraction_gate": 1e-6,
                  "observed_genes_min_max": [int(mask.sum(1).min()), int(mask.sum(1).max())],
                  "source_stage_sha256": sha256(stage_path)}


def map_effects(effect_genes, lfc, observed, genes):
    pos = pd.Index(np.asarray(effect_genes).astype(str)).get_indexer(np.asarray(genes).astype(str))
    have = pos >= 0
    values = np.zeros((lfc.shape[0], len(genes)), dtype=np.float32)
    mask = np.zeros(values.shape, dtype=bool)
    values[:, have] = lfc[:, pos[have]]
    mask[:, have] = observed[:, pos[have]]
    if not np.isfinite(values).all():
        raise ValueError("Non-finite frozen effect encountered")
    return values, mask


def read_selected_rows(path: Path, rows: np.ndarray, columns: np.ndarray, block_rows: int = 256):
    """Read only selected H5AD rows, with bounded dense buffers; dense or CSR X."""
    rows = np.asarray(rows, dtype=np.int64)
    if rows.ndim != 1 or np.any(np.diff(rows) <= 0):
        raise ValueError("Selected row indices must be strictly increasing and unique")
    blocks = []
    with h5py.File(path, "r") as handle:
        x = handle["X"]
        if isinstance(x, h5py.Dataset):
            for lo in range(0, len(rows), block_rows):
                dense = np.asarray(x[rows[lo:lo + block_rows]], dtype=np.float32)[:, columns]
                blocks.append(sp.csr_matrix(dense))
        else:
            encoding = x.attrs.get("encoding-type", "csr_matrix")
            if isinstance(encoding, bytes):
                encoding = encoding.decode()
            if encoding != "csr_matrix":
                raise ValueError(f"Unsupported sparse layout {encoding}")
            ptr = x["indptr"][:]
            for lo in range(0, len(rows), block_rows):
                subset = rows[lo:lo + block_rows]
                lengths = np.diff(ptr)[subset]
                offsets = np.r_[0, np.cumsum(lengths)]
                data = np.empty(int(offsets[-1]), dtype=np.float32)
                indices = np.empty(data.size, dtype=np.int32)
                for i, row in enumerate(subset):
                    left, right = int(ptr[row]), int(ptr[row + 1])
                    data[offsets[i]:offsets[i + 1]] = x["data"][left:right]
                    indices[offsets[i]:offsets[i + 1]] = x["indices"][left:right]
                shape = (len(subset), int(x.attrs["shape"][1]))
                blocks.append(sp.csr_matrix((data, indices, offsets), shape=shape)[:, columns])
    if not blocks:
        return sp.csr_matrix((0, len(columns)), dtype=np.float32)
    result = sp.vstack(blocks, format="csr")
    if np.any(result.data < 0) or not np.isfinite(result.data).all():
        raise ValueError("Truth contains negative or non-finite counts")
    if not np.equal(result.data, np.floor(result.data)).all():
        raise ValueError("Truth must contain raw integral counts")
    return result


class FullTruthBench(Bench):
    """Bench scoring with all held-out truth; no overlapping replicate anchors."""

    def __init__(self, x, target_rows, ctrl_rows, genes, out, *, seed=2026):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.genes = np.asarray(genes).astype(str)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        cfg = scorer_config()
        self.cfg = replace(cfg, device="cpu", de=replace(cfg.de, backend="scanpy"))
        self.targets = sorted(target_rows)
        self.x, self.ctrl = x, x[ctrl_rows]
        self.half_a = {t: np.asarray(target_rows[t]) for t in self.targets}
        self.half_b = {}
        selected = np.concatenate([target_rows[t] for t in self.targets])
        labels = np.concatenate([np.full(len(target_rows[t]), t) for t in self.targets])
        self.real_ad = to_anndata(sp.vstack([x[selected], self.ctrl], format="csr"),
                                  np.r_[labels, np.full(self.ctrl.shape[0], CONTROL)], self.genes)
        self.pool = ReferencePool(self.ctrl, self.genes)
        self.de_real = fast_scorer_de(x[selected], labels, self.pool)
        self.results = {}
        log(f"full truth: {len(self.targets)} targets; {len(selected)} perturbed cells; "
            f"{len(ctrl_rows)} controls; {len(genes)} genes")

    def anchors(self):
        raise RuntimeError("No independent replicate of full truth: local anchors are unavailable")


def generate_block(basal, lfc_ln, observed, lib_pool, n, amplitude, phi_scale, phi, seed, target):
    """Stage-45 per-target operations, with deterministic target-specific streams."""
    rng = target_rng(seed, target)
    delta = amplitude * lfc_ln / np.log(2.0)
    profile, detail = predicted_profile(basal, delta, observed)
    libraries = resample_library_sizes(lib_pool, n, rng)
    challenge = config.challenge()
    counts = sample_counts(profile, libraries, rng,
                           max_stored_per_cell=challenge.max_stored_per_cell,
                           max_counts_per_cell=challenge.max_counts_per_cell,
                           overdispersion=None if phi_scale == 0 else phi * phi_scale)
    realised = np.asarray(counts.sum(axis=0), dtype=np.float64).ravel()
    p, b = profile / profile.sum(), basal / basal.sum()
    v = np.log1p(50000 * p) - np.log1p(50000 * b)
    detail |= {"target": target, "nnz": int(counts.nnz),
               "mean_library": float(np.asarray(counts.sum(axis=1)).mean()),
               "expected_energy_all_genes": float(v @ v),
               "realised_bulk_l1_from_expected": float(np.abs(realised / realised.sum() - p).sum())}
    return counts, detail


def prepare(args):
    if args.out.exists():
        raise FileExistsError(f"Preparation refuses existing output directory: {args.out}")
    with h5py.File(args.hepg2, "r") as handle:
        obs, var = read_frame(handle["obs"]), read_frame(handle["var"])
        x = handle["X"]
        layout = {"type": type(x).__name__, "shape": list(x.shape) if hasattr(x, "shape") else list(x.attrs["shape"])}
    names = var.index.astype(str).to_numpy()
    _, first = np.unique(names, return_index=True)
    columns = np.sort(first)
    genes = names[columns]
    labels = obs["gene"].astype(str).to_numpy()
    panel = [t.strip() for t in args.targets_file.read_text(encoding="utf-8").splitlines() if t.strip()]
    with np.load(args.effects, allow_pickle=False) as archive:
        effect_targets, effect_genes = archive["targets"].astype(str), archive["genes"].astype(str)
        all_lfc = archive["lfc"]
        original_observed = archive["observed"] if "observed" in archive else None
    if len(set(panel)) != len(panel) or len(set(effect_genes)) != len(effect_genes):
        raise ValueError("Duplicate panel targets or effect-axis genes")
    if set(panel) != set(effect_targets):
        raise ValueError("Frozen targets.txt and effect rows do not describe the same panel")
    counts = pd.Series(labels).value_counts().to_dict()
    eligible, development, confirmation = select_targets(panel, genes, counts, args.selection_seed,
                                                          args.n_development, args.n_confirmation)
    selected = development + confirmation
    if not development or not confirmation:
        raise ValueError("Not enough eligible targets for both registered splits")
    observed, mask_meta = source_mask(args.k562_bulk, selected, effect_genes) if original_observed is None else (
        original_observed[pd.Index(effect_targets).get_indexer(selected)], {"method": "explicit NPZ observed"})
    positions = pd.Index(effect_targets).get_indexer(selected)
    lfc, observed = map_effects(effect_genes, all_lfc[positions], observed, genes)
    ntc = np.flatnonzero(labels == CONTROL)
    controls = np.sort(np.random.default_rng(args.control_seed).choice(ntc, min(args.control_cells, len(ntc)), replace=False))
    target_rows = {t: np.flatnonzero(labels == t).tolist() for t in selected}
    files = [args.hepg2, args.k562_bulk, args.effects, args.targets_file,
             REPO / "reports/gara/anchors_2026-09-17/anchors.json", Path(__file__),
             HERE / "PROTOCOLLO_GENERATORE.md", HERE / "EMENDAMENTO_GENERATORE_02.md",
             HERE / "generatore/PROTOCOLLO_BANCO_BINS.md", HERE / "generatore/depth_candidate.py",
             HERE / "generatore/depth_bins.py"]
    amendment = HERE / "EMENDAMENTO_GENERATORE_01.md"
    if args.truth == "full":
        if not amendment.exists():
            raise FileNotFoundError("Full truth requires the preregistered amendment")
        files.append(amendment)
    files += [REPO / "src/vcc2026" / name for name in ["bench.py", "de_tools.py", "inference.py", "sampling.py", "multisource.py", "predictor_sc.py"]]
    log("fingerprinting frozen inputs (streaming hashes)")
    fingerprints = {str(path.resolve()): {"sha256": sha256(path), "bytes": path.stat().st_size,
                                         "mtime_ns": path.stat().st_mtime_ns} for path in files}
    args.out.mkdir(parents=True)
    effects_path = args.out / "prepared_effects.npz"
    np.savez_compressed(effects_path, targets=np.asarray(selected, dtype=str),
                        genes=np.asarray(genes, dtype=str), lfc=lfc, observed=observed)
    versions = {}
    for package in ["numpy", "scipy", "pandas", "h5py", "cell-eval2", "vcc-cli"]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    manifest = {"prepared_utc": utc(), "status": "prepared_no_scores", "truth": args.truth,
                "design": "joint_14_arms_amendment_02", "registered_arms": REGISTERED_ARMS,
                "path_roots": {"repo": str(REPO.resolve()), "data": str((args.data_root or DATA).resolve())},
                "input_layout": layout, "hepg2": str(args.hepg2.resolve()),
                "development": development, "confirmation": confirmation, "eligible": eligible,
                "counts_requested_actual": {"development": [args.n_development, len(development)],
                                             "confirmation": [args.n_confirmation, len(confirmation)]},
                "target_rows": target_rows, "control_rows": controls.tolist(), "columns": columns.tolist(),
                "selection_seed": args.selection_seed, "control_seed": args.control_seed, "split_seed": 2026,
                "cells_per_prediction": 400, "source_mask": mask_meta, "versions": versions,
                "fingerprints": fingerprints, "prepared_effects_sha256": sha256(effects_path),
                "observed_zero_count": int(((lfc == 0) & observed).sum()),
                "rng_rule": "SHA256(target) first two little-endian uint32 + generator_seed; no arm dependence",
                "difference_from_legacy_g0": "source evidence mask; observed-only composition shift; log2 clip +/-6; 400 prediction cells; target-specific streams",
                "workload_development": workload_dimensions(len(development), len(genes), len(controls), 14, 1),
                "workload_confirmation_maximum": workload_dimensions(len(confirmation), len(genes), len(controls), 3, 3),
                "resources": snapshot(args.out).as_dict()}
    write_json(args.out / "target_manifest.json", manifest)
    log(f"Prepared {len(development)} development + {len(confirmation)} confirmation targets; no scoring")


def per_target(path: Path, targets, members):
    frame = pd.read_csv(path)
    if frame.duplicated(["perturbation", "metric"]).any():
        raise ValueError(f"Duplicate per-target metric in {path}")
    return frame.pivot(index="perturbation", columns="metric", values="value").reindex(index=targets, columns=members)


def projected_contrast(candidate_tables, reference_tables, slopes, bootstrap_indices):
    """Paired bootstrap over targets, same draw for every seed and metric."""
    differences, per_seed = [], []
    finite_reference = None
    for candidate, reference in zip(candidate_tables, reference_tables, strict=True):
        a, b = candidate.to_numpy(float), reference.to_numpy(float)
        if not np.array_equal(np.isfinite(a), np.isfinite(b)):
            raise ValueError("Metric eligibility changed between candidate and reference")
        if finite_reference is None:
            finite_reference = np.isfinite(b)
        elif not np.array_equal(finite_reference, np.isfinite(b)):
            raise ValueError("Metric eligibility changed between seeds")
        d = (a - b) * np.asarray(slopes)[None, :] / 6
        if np.any(np.sum(np.isfinite(d), axis=0) == 0):
            raise ValueError("A projected member has no eligible target")
        differences.append(d)
        per_seed.append(float(np.nanmean(d, axis=0).sum()))
    # The per-metric denominator is its own fixed real-side eligible population.
    stacked = np.stack(differences)
    count = np.isfinite(stacked).sum(axis=0)
    average = np.divide(np.nansum(stacked, axis=0), count,
                        out=np.full(stacked.shape[1:], np.nan), where=count > 0)
    sampled = average[bootstrap_indices]
    sample_count = np.isfinite(sampled).sum(axis=1)
    boot = np.divide(np.nansum(sampled, axis=1), sample_count,
                     out=np.full(sample_count.shape, np.nan), where=sample_count > 0).sum(axis=1)
    if not np.isfinite(boot).all():
        raise ValueError("Bootstrap sampled no eligible target for a member; cannot promote")
    return {"delta_projection": float(np.nanmean(average, axis=0).sum()),
            "per_seed_delta": per_seed,
            "seed_sd": float(np.std(per_seed, ddof=1)) if len(per_seed) > 1 else None,
            "member_contributions": dict(zip(FIVE, np.nanmean(average, axis=0).tolist())),
            "eligible_targets_per_member": dict(zip(FIVE, finite_reference.sum(0).tolist()))}, boot


def summarise(run_dir, manifest, run_manifest, bench):
    anchors = json.loads((REPO / "reports/gara/anchors_2026-09-17/anchors.json").read_text(encoding="utf-8"))["anchors"]
    slopes = [1 / (anchors[m]["replicate"] - anchors[m]["baseline"]) for m in FIVE]
    targets, seeds, arms = bench.targets, run_manifest["seeds"], run_manifest["arms"]
    reference = [per_target(run_dir / f"per_pert_{arm_name(1, 0, seed)}.csv", targets, FIVE) for seed in seeds]
    boot_idx = np.random.default_rng(20260929).integers(0, len(targets), (2000, len(targets)))
    comparisons = []
    n_finalists = len(arms) - 1
    level = 0.975 if run_manifest["split"] == "confirmation" and n_finalists == 2 else 0.95
    for amplitude, phi_scale, generator in arms:
        if (amplitude, phi_scale, generator) == REFERENCE:
            continue
        frames = [per_target(run_dir / f"per_pert_{arm_name(amplitude, phi_scale, seed, generator)}.csv", targets, FIVE) for seed in seeds]
        summary, draws = projected_contrast(frames, reference, slopes, boot_idx)
        ci = np.quantile(draws, [(1 - level) / 2, (1 + level) / 2]).tolist()
        summary |= {"amplitude": amplitude, "phi_scale": phi_scale, "generator": generator,
                    "confidence_level": level,
                    "paired_target_bootstrap_interval": ci,
                    "passes_confirmation": bool(run_manifest["split"] == "confirmation" and
                                                summary["delta_projection"] >= 0.005 and
                                                all(v > 0 for v in summary["per_seed_delta"]) and ci[0] > 0)}
        # Validate arithmetic against the scorer's aggregations, for every member.
        for seed, table in zip(seeds, frames, strict=True):
            reported = bench.results[arm_name(amplitude, phi_scale, seed, generator)]["raw"]
            for member in FIVE:
                if abs(table[member].mean() - reported[member]) > 1e-8:
                    raise ValueError(f"Per-target aggregate mismatch: {member}")
        comparisons.append(summary)
    shortlist = joint_shortlist(comparisons) if run_manifest["split"] == "development" else []
    matched = []
    arm_set = {tuple(arm) for arm in arms}
    diagnostic_pairs = []
    for amplitude, phi_scale, generator in arms:
        if generator == "bins" or phi_scale > 0:
            diagnostic_pairs.append(((amplitude, phi_scale, generator), (amplitude, 0.0, "pooled"),
                                     "generator_at_fixed_amplitude"))
        if amplitude != 1 and generator == "pooled":
            diagnostic_pairs.append(((amplitude, phi_scale, generator), (1.0, phi_scale, "pooled"),
                                     "amplitude_at_fixed_dispersion"))
    for candidate, control, meaning in diagnostic_pairs:
        if control not in arm_set:
            continue
        ca, cp, cg = candidate
        ba, bp, bg = control
        candidate_frames = [per_target(run_dir / f"per_pert_{arm_name(ca, cp, seed, cg)}.csv", targets, FIVE) for seed in seeds]
        control_frames = [per_target(run_dir / f"per_pert_{arm_name(ba, bp, seed, bg)}.csv", targets, FIVE) for seed in seeds]
        detail, draws = projected_contrast(candidate_frames, control_frames, slopes, boot_idx)
        matched.append(detail | {"candidate": candidate, "control": control, "meaning": meaning,
                                 "descriptive_ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
                                 "used_for_promotion": False})
    summary = {"claim_type": "local projection using five official-anchor slopes / six, MSE contribution fixed at zero; not a VCC score",
               "comparisons": comparisons, "shortlist": shortlist,
               "shortlist_cli": [arm_cli(arm) for arm in shortlist], "matched_diagnostics": matched,
               "bootstrap_note": "paired targets; shared draws across seeds and members; seed SD separate; target families not independently resampled",
               "truth": manifest["truth"], "n_targets": len(targets), "finished_utc": utc()}
    write_json(run_dir / "selection.json", summary)
    return summary


def run(args):
    manifest_path = args.out / "target_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("design") != "joint_14_arms_amendment_02":
        raise ValueError("This script requires a new preparation for the prospective 14-arm design")
    for filename, old in manifest["fingerprints"].items():
        path = relocated_path(filename, manifest, args.data_root)
        if not path.exists():
            raise FileNotFoundError(f"Frozen input not found at {path}; use --data-root for relocated data")
        if path.stat().st_size != old["bytes"] or path.stat().st_mtime_ns != old["mtime_ns"]:
            if sha256(path) != old["sha256"]:
                raise ValueError(f"Frozen input changed since preparation: {path}")
    effects_path = args.out / "prepared_effects.npz"
    if sha256(effects_path) != manifest["prepared_effects_sha256"]:
        raise ValueError("Prepared effects changed")
    targets = sorted(manifest[args.split])
    arms = [parse_arm(v) for v in args.arms] if args.arms else list(REGISTERED_ARMS)
    if len(set(arms)) != len(arms) or REFERENCE not in arms:
        raise ValueError("Arms must be unique and include the reference 1:0")
    if args.split == "confirmation" and (args.arms is None or len(arms) not in (2, 3)):
        raise ValueError("Confirmation requires reference and one or two preselected finalists")
    if args.split == "development" and set(arms) != set(REGISTERED_ARMS):
        raise ValueError("Development must use the complete registered 14-arm joint design")
    if args.split == "confirmation":
        previous = json.loads((args.out / "development/selection.json").read_text(encoding="utf-8"))
        finalists = {tuple(v) for v in previous["shortlist"]}
        if set(arms) - {REFERENCE} != finalists:
            raise ValueError("Confirmation arms must exactly match the development shortlist")
    seeds = [1] if args.split == "development" else [1, 2, 3]
    run_dir = args.out / args.split
    if run_dir.exists():
        raise FileExistsError(f"Refusing existing run directory: {run_dir}")
    run_dir.mkdir()
    run_manifest = {"started_utc": utc(), "split": args.split, "truth": manifest["truth"], "targets": targets,
                    "arms": arms, "seeds": seeds, "target_manifest_sha256": sha256(manifest_path),
                    "generator_script_sha256": sha256(Path(__file__)), "resources": snapshot(args.out).as_dict()}
    write_json(run_dir / "run_manifest.json", run_manifest)
    with np.load(effects_path, allow_pickle=False) as archive:
        pos = pd.Index(archive["targets"].astype(str)).get_indexer(targets)
        genes, lfc, observed = archive["genes"].astype(str), archive["lfc"][pos], archive["observed"][pos]
    original_rows = {t: np.asarray(manifest["target_rows"][t], dtype=np.int64) for t in targets}
    controls = np.asarray(manifest["control_rows"], dtype=np.int64)
    all_rows = np.sort(np.concatenate([controls, *original_rows.values()]))
    log(f"reading only {len(all_rows)} selected truth/control rows")
    truth_path = relocated_path(manifest["hepg2"], manifest, args.data_root)
    x = read_selected_rows(truth_path, all_rows, np.asarray(manifest["columns"]))
    rows = {t: np.searchsorted(all_rows, r) for t, r in original_rows.items()}
    ctrl_rows = np.searchsorted(all_rows, controls)
    cls = FullTruthBench if manifest["truth"] == "full" else Bench
    bench = cls(x, rows, ctrl_rows, genes, run_dir, seed=manifest["split_seed"])
    if manifest["truth"] == "half":
        bench.anchors()
    basal = np.asarray(bench.ctrl.sum(axis=0), dtype=np.float64).ravel()
    libs = np.asarray(bench.ctrl.sum(axis=1)).ravel()
    zero_fraction = 1 - np.asarray(bench.ctrl.getnnz(axis=0)) / bench.ctrl.shape[0]
    log("fitting per-gene dispersion from the frozen control pool")
    phi = fit_gene_dispersion(basal, libs, zero_fraction, seed=2026)
    np.save(run_dir / "phi.npy", phi)
    depth_model = None
    if any(generator == "bins" for _, _, generator in arms):
        depth_model = load_depth_candidate().fit(bench.ctrl)
        write_json(run_dir / "depth_control_fit.json", depth_model.selection)
    labels = np.repeat(np.asarray(targets), manifest["cells_per_prediction"])
    for amplitude, phi_scale, generator in arms:
        for seed in seeds:
            name = arm_name(amplitude, phi_scale, seed, generator)
            log(f"generating {name}")
            blocks, diagnostics = [], []
            for i, target in enumerate(targets):
                if generator == "bins":
                    challenge = config.challenge()
                    block, detail = depth_model.sample(lfc[i], observed[i], manifest["cells_per_prediction"],
                                                       target_rng(seed, target), amplitude=amplitude,
                                                       generator="bins", max_stored_per_cell=challenge.max_stored_per_cell,
                                                       max_counts_per_cell=challenge.max_counts_per_cell)
                    detail |= {"target": target, "nnz": int(block.nnz)}
                else:
                    block, detail = generate_block(basal, lfc[i], observed[i], libs, manifest["cells_per_prediction"],
                                                   amplitude, phi_scale, phi, seed, target)
                blocks.append(block)
                diagnostics.append(detail)
            predicted = sp.vstack(blocks, format="csr")
            del blocks, block
            gc.collect()
            write_json(run_dir / f"diagnostics_{name}.json", diagnostics)
            bench.score(name, predicted, labels, extra={"amplitude_relative": amplitude, "phi_scale": phi_scale,
                                                      "generator": generator, "generator_seed": seed,
                                                      "peak_rss_bytes": peak_rss_bytes()})
            write_json(run_dir / f"result_{name}.json", bench.results[name])
            del predicted
            gc.collect()
    payload = {"stage": "generator_bench", "run_manifest": run_manifest, "resources_end": snapshot(args.out).as_dict(),
               "peak_rss_bytes": peak_rss_bytes(), "claim_type": "real scorer on public HepG2; not an official VCC score"}
    if manifest["truth"] == "half":
        bench.finish(payload)
    else:
        write_json(run_dir / "bench.json", payload | {"results": bench.results, "real_n_conf": bench.real_n_conf(),
                                                      "local_anchors": None, "reason": "No independent replica of full truth"})
    summary = summarise(run_dir, manifest, run_manifest, bench)
    log(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["prepare", "run"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--truth", choices=["half", "full"], default="half")
    parser.add_argument("--split", choices=["development", "confirmation"], default="development")
    parser.add_argument("--arms", nargs="+", help="confirmation: reference 1:0 and joint finalists AMPLITUDE:PHI_SCALE or bins:AMPLITUDE")
    parser.add_argument("--data-root", type=Path, help="prepare defaults or relocated root for all frozen data on a remote runner")
    parser.add_argument("--hepg2", type=Path)
    parser.add_argument("--k562-bulk", type=Path)
    parser.add_argument("--effects", type=Path)
    parser.add_argument("--targets-file", type=Path)
    parser.add_argument("--selection-seed", type=int, default=20260929)
    parser.add_argument("--control-seed", type=int, default=2026)
    parser.add_argument("--n-development", type=int, default=48)
    parser.add_argument("--n-confirmation", type=int, default=96)
    parser.add_argument("--control-cells", type=int, default=2000)
    args = parser.parse_args()
    data_root = args.data_root or DATA
    args.hepg2 = args.hepg2 or data_root / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad"
    args.k562_bulk = args.k562_bulk or data_root / "external/K562_gwps_raw_bulk_01.h5ad"
    args.effects = args.effects or data_root / "processed/banco_hepg2_v2_2026-09-26/t19like.npz"
    args.targets_file = args.targets_file or data_root / "processed/banco_hepg2_v2_2026-09-26/targets.txt"
    (prepare if args.phase == "prepare" else run)(args)


if __name__ == "__main__":
    main()
