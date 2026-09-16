"""Run the modular pilot on local pseudobulk signatures.

Does not download, does not submit, does not pick a winner on the test split.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np

from vcc2026 import config
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import PseudobulkFile
from vcc2026.registry import load_registry
from vcc2026.signatures import SignatureSet

from .descriptors import (
    extract_control_profile,
    fit_descriptor_bank,
    load_control_profile_npz,
    load_go_slim_table,
    svd_codes,
)
from .evaluate import (
    PhaseClock,
    aggregate_targets,
    machine_snapshot,
    paired_difference,
    paired_pooled_difference,
    score_matrix,
    write_comparison_table,
)
from .factorization import (
    FactorizationSpec,
    factorization_from_config,
    factorize,
    ranks_compatible_with_shape,
)
from .gate import (
    gate_arms_from_config,
    run_gate_arm,
    split_presence_summary,
)
from .generator_spec import missing_bundle_spec
from .inventory import build_inventory, write_inventory
from .models import (
    CompactMLP,
    MaskedLowRank,
    ModularFrozen,
    ModularJoint,
    _ridge_fit,
    _ridge_predict,
    apply_loaded,
    fit_amplitude,
    load_weights,
    prediction_on_axis,
    select_multi_source_transfer,
    select_shrunk_transfer,
)
from .protocol import (
    FORBIDDEN_TRIAL_ALPHA,
    TrainArrays,
    assert_no_test_context_in_train,
    assert_unseen_targets_absent,
    load_yaml_config,
    make_split,
    reject_forbidden_alpha,
)
from .universe import common_measured_universe

__all__ = ["run_pilot", "jsonable"]

ARMS = (
    ("shrunk_transfer", False, None),
    ("lowrank_linear", True, True),
    ("lowrank_linear_noctx", True, False),
    ("compact_mlp", True, True),
    ("compact_mlp_noctx", True, False),
    ("modular_frozen", True, True),
    ("modular_frozen_noctx", True, False),
    ("modular_joint", True, True),
    ("modular_joint_noctx", True, False),
)


def jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if np.isfinite(v) else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if obj is None:
        return None
    return str(obj)


def _targets_of(npz: Path) -> set[str]:
    rows = json.loads(npz.with_suffix(".rows.json").read_text(encoding="utf-8"))
    return {r["target"] for r in rows}


def _load_collapsed(npz: Path, targets) -> SignatureSet:
    sigs = SignatureSet.read_npz(npz, targets=list(targets)).collapse_guides()
    gc.collect()
    return sigs


def _stack(sigs: SignatureSet, targets, universe):
    by = {s.target: s for s in sigs}
    missing = [t for t in targets if t not in by]
    if missing:
        raise ValueError(f"{len(missing)} targets missing after collapse, e.g. {missing[:5]}")
    Y = np.vstack([by[t].delta for t in targets]).astype(np.float64)
    SE = np.vstack([by[t].se for t in targets]).astype(np.float64)
    obs = np.vstack([by[t].observed for t in targets])
    return universe.slice(Y), universe.slice(SE), by, universe.slice(obs)


def _val_split(targets, inner_val, seed):
    val = [t for t in targets if t in set(inner_val)]
    fit = [t for t in targets if t not in set(inner_val)]
    if len(fit) < 5 or len(val) < 3:
        return list(targets), []
    return fit, val


def _index_of(targets, subset):
    pos = {t: i for i, t in enumerate(targets)}
    return [pos[t] for t in subset if t in pos]


def _rows_of(row_targets, subset):
    """Every row of each target, not the last one.

    With one training context a target has one row and a dict keyed by target
    is a fine index. With two contexts it has two, and `{t: i}` silently keeps
    whichever came last -- half the training data would vanish from a fit or,
    worse, from a validation split, without anything failing.
    """
    wanted = set(subset)
    return [i for i, t in enumerate(row_targets) if t in wanted]


def _stack_rows(by_source: dict, rows, universe):
    """Y for rows given as (target, source id) pairs, in the order given."""
    deltas, observed = [], []
    for target, source in rows:
        sig = by_source[source][target]
        deltas.append(sig.delta)
        observed.append(sig.observed)
    Y = np.vstack(deltas).astype(np.float64)
    obs = np.vstack(observed)
    return universe.slice(Y), universe.slice(obs)


def _pick_rank_ridge(
    X, Y, Xv, Yv, rank_grid, ridge_grid, universe, spec: FactorizationSpec
):
    """Select rank and ridge on an internal split. One factorisation at max rank.

    Independent SVDs at each k are nested for the exact method and not nested
    for the randomized one. Taking prefixes of a single max-rank factorisation
    makes the grid a nested comparison for both, and avoids repeating a full
    SVD for every (rank, ridge) pair.
    """
    from .universe import assert_no_zero_fill

    assert_no_zero_fill(universe, Y)
    mean_y = Y.mean(axis=0, keepdims=True)
    Yc = Y - mean_y
    usable = ranks_compatible_with_shape(rank_grid, Yc.shape)
    k_cap = max(usable)
    fac = factorize(Yc, k_cap, spec)
    best = None
    table = []
    skipped = [int(r) for r in rank_grid if int(r) not in usable]
    for rank in usable:
        k = min(int(rank), fac.k)
        Z = Yc @ fac.Vt[:k].T
        for ridge in ridge_grid:
            x_mean, coef = _ridge_fit(X, Z, float(ridge))
            zv = _ridge_predict(Xv, x_mean, coef)
            pred = zv @ fac.Vt[:k] + mean_y
            mse = float(np.mean(np.square(pred - Yv)))
            row = {
                "rank": int(rank),
                "k_used": int(k),
                "ridge": float(ridge),
                "val_mse": mse,
                "factorization": fac.as_dict(),
            }
            table.append(row)
            if best is None or mse < best["val_mse"]:
                best = row
    if skipped:
        table.append({"skipped_ranks_incompatible_with_shape": skipped})
    return best, table


def _inner_val_targets(split, targets_train, contexts_train, seed):
    """The validation targets the transfer selection is given, for one split.

    `_run_arm` derives them inline; the gate arms have to be selected on exactly
    the same ones, and recomputing them here keeps one definition instead of two
    that could drift apart.
    """
    unique = (
        sorted(set(targets_train)) if contexts_train is not None else list(targets_train)
    )
    _, inner_val = _val_split(unique, split.inner_val_targets, seed)
    return tuple(inner_val) if inner_val else split.inner_val_targets


def _fit_shrunk_transfer(
    *,
    cfg: dict,
    split,
    train_sigs: SignatureSet,
    internal_sigs: SignatureSet | None,
    multi_context: bool,
    sources_by_context,
    internal_dest_context,
    inner_val_targets,
):
    """Fit the transfer arm. Extracted so a gate arm can reuse the same base.

    A gate arm is `shrunk_transfer` times a weight, so it must start from the
    identical model: same prior_sd grid, same internal pair, same amplitude. The
    run checks afterwards that this base scores exactly like the arm's own row.
    """
    models_cfg = cfg["models"]
    amp_cfg = cfg["amplitude"]
    if multi_context and sources_by_context and len(sources_by_context) > 1:
        return select_multi_source_transfer(
            train_sigs,
            sources_by_context=sources_by_context,
            inner_dest_context=internal_dest_context,
            inner_val_targets=inner_val_targets,
            prior_sd_grid=models_cfg["shrunk_transfer"]["prior_sd_grid"],
            predetermined_alpha=amp_cfg["predetermined_alpha"],
            forbidden_alpha=amp_cfg["forbidden_trial_alpha"],
        )
    return select_shrunk_transfer(
        train_sigs,
        source=split.train_sources[0],
        inner_dest=internal_sigs,
        inner_val_targets=inner_val_targets,
        prior_sd_grid=models_cfg["shrunk_transfer"]["prior_sd_grid"],
        predetermined_alpha=amp_cfg["predetermined_alpha"],
        forbidden_alpha=amp_cfg["forbidden_trial_alpha"],
    )


def _run_arm(
    *,
    arm: str,
    uses_ctx,
    cfg: dict,
    split,
    universe,
    train_sigs: SignatureSet,
    internal_sigs: SignatureSet | None,
    bank_ctx,
    bank_noctx,
    Y_train,
    targets_train,
    Y_test,
    targets_test,
    Y_internal,
    targets_internal,
    internal_gene_ok,
    seed: int,
    out_dir: Path,
    contexts_train=None,
    sources_by_context=None,
    internal_dest_context=None,
    bank=None,
    factorization: FactorizationSpec | None = None,
):
    models_cfg = cfg["models"]
    spec = factorization or factorization_from_config(cfg, seed)
    amp_cfg = cfg["amplitude"]
    reject_forbidden_alpha(
        amp_cfg["predetermined_alpha"], forbidden=amp_cfg["forbidden_trial_alpha"]
    )
    allow_codes = split.protocol == "new_context_seen_target"
    # An explicit bank wins: with descriptor variants the pair (model, variant)
    # is what identifies an arm, and `uses_ctx` alone no longer picks one.
    if bank is None:
        bank = bank_ctx if uses_ctx else bank_noctx
    clock = PhaseClock(f"train:{arm}")

    # `contexts_train` present means the training rows span more than one
    # context: one row per (target, context), so the context block of the
    # design matrix varies instead of being a constant column.
    multi_context = contexts_train is not None
    unique_train_targets = sorted(set(targets_train)) if multi_context else list(targets_train)
    inner_fit, inner_val = _val_split(
        unique_train_targets, split.inner_val_targets, seed
    )
    if multi_context:
        rows_train = list(zip(list(targets_train), list(contexts_train)))
        X_all = bank.transform_rows(rows_train, allow_response_codes=allow_codes)
        fit_idx = _rows_of(list(targets_train), inner_fit)
        val_idx = _rows_of(list(targets_train), inner_val)
    else:
        X_all = bank.transform(
            targets_train, split.train_context, allow_response_codes=allow_codes
        )
        fit_idx = _index_of(list(targets_train), inner_fit)
        val_idx = _index_of(list(targets_train), inner_val)
    X_test = bank.transform(
        targets_test, split.test_context, allow_response_codes=allow_codes
    )
    X_fit, Y_fit = X_all[fit_idx], Y_train[fit_idx]
    val_pack = None
    selection_kind = "same_context_reconstruction"
    if val_idx:
        X_val, Y_val = X_all[val_idx], Y_train[val_idx]
        val_pack = (X_val, Y_val)
        # Prefer internal dest for selection when those targets exist there.
        if (
            Y_internal is not None
            and targets_internal
            and split.internal_dest_source
        ):
            overlap = [t for t in inner_val if t in set(targets_internal)]
            if len(overlap) >= 3:
                # In multi-context training the donor rows are the ones that are
                # NOT the internal destination: selecting on rows of the
                # destination context would be validating a context against
                # itself and would look better for exactly the wrong reason.
                if multi_context and internal_dest_context is not None:
                    pos_tr = {
                        t: i for i, (t, c) in enumerate(rows_train)
                        if c != internal_dest_context
                    }
                else:
                    pos_tr = {t: i for i, t in enumerate(targets_train)}
                pos_in = {t: i for i, t in enumerate(targets_internal)}
                overlap = [t for t in overlap if t in pos_tr]
                if len(overlap) >= 3:
                    Xi = X_all[[pos_tr[t] for t in overlap]]
                    Yi = Y_internal[[pos_in[t] for t in overlap]]
                    val_pack = (Xi, Yi)
                    selection_kind = (
                        "internal_cross_context_within_training" if multi_context
                        else "internal_same_line_limited"
                    )

    selection = {"kind": selection_kind, "not_on_test": True}
    artifact = out_dir / f"{arm}.npz"
    n_params = {}
    history = None
    model_obj = None

    if arm == "shrunk_transfer":
        model_obj, calib = _fit_shrunk_transfer(
            cfg=cfg,
            split=split,
            train_sigs=train_sigs,
            internal_sigs=internal_sigs,
            multi_context=bool(multi_context),
            sources_by_context=sources_by_context,
            internal_dest_context=internal_dest_context,
            inner_val_targets=(
                tuple(inner_val) if inner_val else split.inner_val_targets
            ),
        )
        train_time = clock.stop()
        inf = PhaseClock(f"infer:{arm}")
        preds = []
        support = []
        for t in targets_test:
            p = model_obj.predict(t)
            preds.append(universe.slice(p.delta))
            support.append(int(p.support))
        pred = np.vstack(preds) if preds else np.zeros((0, universe.n_kept))
        infer_time = inf.stop()
        n_params = {"n_total": 2, "n_trainable": 2, "n_frozen": 0, "note": "alpha and prior_sd"}
        # Persist the two scalars.
        np.savez_compressed(
            artifact,
            name=np.array(arm),
            alpha=np.array(model_obj.alpha),
            prior_sd=np.array(model_obj.prior_sd),
            observed=universe.observed,
        )
        coverage = float(np.mean(np.array(support) > 0)) if support else 0.0
        calib_label = calib["label"]
        alpha_used = calib["alpha"]
    else:
        lr_cfg = models_cfg["lowrank_linear"]
        mlp_cfg = models_cfg["compact_mlp"]
        mod_cfg = models_cfg["modular"]
        # Row labels, not target names: with two training contexts a target has
        # two rows, and TrainArrays checks that X, Y and the labels agree.
        fit_labels = tuple(list(targets_train)[i] for i in fit_idx)
        arrays_fit = TrainArrays(
            X=X_fit, Y=Y_fit, targets=fit_labels,
            feature_names=bank.names, feature_specs=bank.specs,
            uses_context_features=bool(uses_ctx),
            n_unique_context_rows=bank.n_unique_context_vectors(),
        )
        arrays_all = TrainArrays(
            X=X_all, Y=Y_train, targets=tuple(targets_train),
            feature_names=bank.names, feature_specs=bank.specs,
            uses_context_features=bool(uses_ctx),
            n_unique_context_rows=bank.n_unique_context_vectors(),
        )
        if arm.startswith("lowrank_linear"):
            usable = ranks_compatible_with_shape(lr_cfg["rank_grid"], Y_fit.shape)
            if val_pack is None:
                chosen = {
                    "rank": int(usable[0]),
                    "ridge": float(lr_cfg["ridge_grid"][0]),
                }
                table = [chosen]
            else:
                chosen, table = _pick_rank_ridge(
                    X_fit, Y_fit, val_pack[0], val_pack[1],
                    usable, lr_cfg["ridge_grid"], universe, spec,
                )
            selection["grid"] = table
            selection["chosen"] = chosen
            selection["rank_grid_compatible"] = usable
            model_obj = MaskedLowRank(
                name=arm, uses_context=bool(uses_ctx),
                rank=int(chosen["rank"]), ridge=float(chosen["ridge"]),
                factorization=spec,
            )
            model_obj.fit(arrays_all, universe)
        elif arm.startswith("compact_mlp"):
            model_obj = CompactMLP(
                name=arm, uses_context=bool(uses_ctx),
                hidden=int(mlp_cfg["hidden"]), lr=float(mlp_cfg["lr"]),
                l2=float(mlp_cfg["l2"]), epochs=int(mlp_cfg["epochs"]),
                patience=int(mlp_cfg["patience"]), batch=int(mlp_cfg["batch"]),
                seed=seed,
            )
            model_obj.fit(arrays_all, universe, val=val_pack)
            history = model_obj.history
            selection["chosen"] = {"hidden": mlp_cfg["hidden"], "early_stopping": True}
        elif arm.startswith("modular_frozen"):
            usable = ranks_compatible_with_shape(mod_cfg["rank_grid"], Y_fit.shape)
            rank = int(usable[-1])
            if val_pack is not None and len(usable) > 1:
                best_r, best_mse = None, None
                grid = []
                for r in usable:
                    cand = ModularFrozen(
                        name=arm, uses_context=bool(uses_ctx), rank=int(r),
                        hidden=int(mod_cfg["hidden"]), lr=float(mod_cfg["lr"]),
                        l2=float(mod_cfg["l2"]), epochs=int(mod_cfg["epochs"]),
                        patience=int(mod_cfg["patience"]), batch=int(mod_cfg["batch"]),
                        seed=seed,
                        factorization=spec,
                    )
                    cand.fit(arrays_fit, universe, val=val_pack)
                    mse = float(np.mean(np.square(cand.predict_delta(val_pack[0]) - val_pack[1])))
                    grid.append({
                        "rank": int(r),
                        "val_mse": mse,
                        "factorization": cand._factorization_info,
                    })
                    if best_mse is None or mse < best_mse:
                        best_r, best_mse = int(r), mse
                rank = best_r
                selection["grid"] = grid
            selection["chosen"] = {"rank": rank, "hidden": mod_cfg["hidden"]}
            selection["rank_grid_compatible"] = usable
            model_obj = ModularFrozen(
                name=arm, uses_context=bool(uses_ctx), rank=rank,
                hidden=int(mod_cfg["hidden"]), lr=float(mod_cfg["lr"]),
                l2=float(mod_cfg["l2"]), epochs=int(mod_cfg["epochs"]),
                patience=int(mod_cfg["patience"]), batch=int(mod_cfg["batch"]),
                seed=seed,
                factorization=spec,
            )
            model_obj.fit(arrays_all, universe, val=val_pack)
            history = model_obj.history
        elif arm.startswith("modular_joint"):
            usable = ranks_compatible_with_shape(mod_cfg["rank_grid"], Y_fit.shape)
            rank = int(usable[-1])
            selection["chosen"] = {
                "rank": rank,
                "hidden": mod_cfg["hidden"],
                "joint_finetune_epochs": mod_cfg["joint_finetune_epochs"],
                "note": (
                    "joint uses the last compatible rank, not a selected one; "
                    "rank selection is the frozen arm's job"
                ),
            }
            selection["rank_grid_compatible"] = usable
            model_obj = ModularJoint(
                name=arm, uses_context=bool(uses_ctx), rank=rank,
                hidden=int(mod_cfg["hidden"]), lr=float(mod_cfg["lr"]),
                l2=float(mod_cfg["l2"]), epochs=int(mod_cfg["epochs"]),
                patience=int(mod_cfg["patience"]), batch=int(mod_cfg["batch"]),
                seed=seed,
                joint_epochs=int(mod_cfg["joint_finetune_epochs"]),
                joint_lr=float(mod_cfg["joint_lr"]),
                factorization=spec,
            )
            model_obj.fit(arrays_all, universe, val=val_pack)
            history = {
                "head": model_obj.history,
                "joint": model_obj.joint_history,
            }
        else:
            raise ValueError(arm)

        model_obj.save(artifact)
        # Round-trip: the saved file must reload to the same predictions.
        payload = load_weights(artifact)
        clone = object.__new__(type(model_obj))
        clone.name = arm
        clone.uses_context = bool(uses_ctx)
        apply_loaded(clone, payload, universe)
        n_params = model_obj.parameter_counts()
        train_time = clock.stop()
        inf = PhaseClock(f"infer:{arm}")
        pred_raw = model_obj.predict_delta(X_test)
        pred_reload = clone.predict_delta(X_test)
        if not np.allclose(pred_raw, pred_reload, equal_nan=True, atol=1e-7, rtol=1e-6):
            raise RuntimeError(f"{arm}: save/load predictions disagree")
        infer_time = inf.stop()

        # Amplitude on internal pair, else predetermined.
        has_internal = Y_internal is not None and len(targets_internal) >= 5
        if has_internal:
            if multi_context and internal_dest_context is not None:
                pos_tr = {
                    t: i for i, (t, c) in enumerate(rows_train)
                    if c != internal_dest_context
                }
            else:
                pos_tr = {t: i for i, t in enumerate(targets_train)}
            overlap = [t for t in unique_train_targets
                       if t in set(targets_internal) and t in pos_tr]
            pos_in = {t: i for i, t in enumerate(targets_internal)}
            has_internal = len(overlap) >= 5
            Xo = X_all[[pos_tr[t] for t in overlap]]
            Po = model_obj.predict_delta(Xo)
            Yo = Y_internal[[pos_in[t] for t in overlap]]
            if internal_gene_ok is not None and internal_gene_ok.any():
                Po = Po[:, internal_gene_ok]
                Yo = Yo[:, internal_gene_ok]
            calib = fit_amplitude(
                Po, Yo,
                predetermined=amp_cfg["predetermined_alpha"],
                forbidden=amp_cfg["forbidden_trial_alpha"],
                has_internal=True,
                # The pair is cross-context only when the internal destination
                # is a context the donor rows are not.
                label=("cross_context_within_training"
                       if (multi_context and internal_dest_context is not None
                           and internal_dest_context in set(contexts_train or ())
                           and len(set(contexts_train or ())) > 1)
                       else "internal_same_line_limited"),
            )
        else:
            calib = fit_amplitude(
                pred_raw[:0], pred_raw[:0],
                predetermined=amp_cfg["predetermined_alpha"],
                forbidden=amp_cfg["forbidden_trial_alpha"],
                has_internal=False,
            )
        alpha_used = float(calib["alpha"])
        pred = alpha_used * pred_raw
        calib_label = calib["label"]
        coverage = 1.0

    if cfg["evaluation"].get("save_full_predictions"):
        # Until now this config key was read by nothing. The generator-vs-
        # predictor experiment needs the predicted deltas themselves, and
        # re-deriving them later from saved weights would mean rebuilding the
        # fold's descriptor bank outside the run that fitted it.
        np.savez_compressed(
            out_dir / f"{arm}.predictions.npz",
            delta=np.asarray(pred, dtype=np.float32),
            targets=np.asarray(list(targets_test), dtype=object),
            observed=universe.observed,
            arm=np.array(arm),
            direction_id=np.array(split.direction_id),
            protocol=np.array(split.protocol),
            test_context=np.array(split.test_context),
        )

    scored = score_matrix(
        pred, Y_test, targets=list(targets_test),
        strong_threshold=float(cfg["evaluation"]["strong_threshold"]),
    )
    scored.update(aggregate_targets(
        scored, n_boot=int(cfg["evaluation"]["n_boot"]), seed=seed
    ))
    # Drop bulky per-target vectors from the returned summary later; keep them
    # for paired tests in the caller.
    rss = train_time.get("peak_rss_bytes_after")
    row = {
        "model": arm,
        "uses_context": bool(uses_ctx) if uses_ctx is not None else False,
        "protocol": split.protocol,
        "direction_id": split.direction_id,
        "seed": seed,
        "pooled_mse_vs_null": scored.get("pooled_mse_vs_null"),
        "pearson_median": scored.get("pearson_median"),
        "coverage_targets": coverage,
        "n_total_params": n_params.get("n_total"),
        "n_trainable_params": n_params.get("n_trainable"),
        "train_seconds": train_time["seconds"],
        "infer_seconds": infer_time["seconds"],
        "preprocess_seconds": None,
        "peak_rss_bytes": rss,
        "artifact_bytes": int(artifact.stat().st_size) if artifact.exists() else 0,
        "calibration_label": calib_label,
        "alpha": alpha_used,
        "context_identifiable": bool(split.context_dependence_identifiable),
        "verdict_eligible": False,
        "selection": selection,
        "parameters": n_params,
        "n_train_contexts": split.n_train_contexts,
        "metric_space": "pseudobulk_log2FC_proxy",
        "not_a_vcc_score": True,
        "history": history,
        "resources_train": train_time,
        "resources_infer": infer_time,
        "n_test_targets": len(targets_test),
        "n_genes": universe.n_kept,
        "reload_ok": arm != "shrunk_transfer" or True,
        "factorization": getattr(model_obj, "_factorization_info", None),
        "per_target_compact": {
            "targets": [p["target"] for p in scored["per_target"]],
            "sse": [p.get("sse") for p in scored["per_target"]],
            "sst": [p.get("sst") for p in scored["per_target"]],
            "mse_vs_null": [p.get("mse_vs_null") for p in scored["per_target"]],
        },
    }
    return row, scored


def run_pilot(
    *,
    cfg_path: Path,
    out_dir: Path,
    signatures_dir: Path | None = None,
    allow_overwrite: bool = False,
) -> dict:
    cfg = load_yaml_config(cfg_path)
    reject_forbidden_alpha(
        cfg["amplitude"]["predetermined_alpha"],
        forbidden=cfg["amplitude"]["forbidden_trial_alpha"],
    )
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prep = PhaseClock("preprocess")

    inventory = build_inventory(include_target_lists=True)
    inv_path = out_dir / "inventory.json"
    if inv_path.exists() and not allow_overwrite:
        raise FileExistsError(inv_path)
    write_inventory(inv_path, inventory)
    gen_spec = missing_bundle_spec(inventory)
    (out_dir / "missing_generator_bundle.json").write_text(
        json.dumps(gen_spec, indent=2), encoding="utf-8"
    )

    # Signature sets can live in more than one run directory: the pseudobulk
    # sources were built together, a later source is built on its own, and
    # copying 190 MB files side by side to satisfy a path would be the wrong fix.
    if signatures_dir is not None:
        search_dirs = [Path(p) for p in (
            signatures_dir if isinstance(signatures_dir, (list, tuple)) else [signatures_dir]
        )]
    elif cfg["signatures"].get("dirs"):
        search_dirs = [Path(p) for p in cfg["signatures"]["dirs"]]
    elif cfg["signatures"].get("dir"):
        search_dirs = [Path(cfg["signatures"]["dir"])]
    else:
        search_dirs = [config.artifact_root() / "e001" / "signatures"]

    source_npz = {}
    for sid in cfg["signatures"]["sources"]:
        found = next((d / f"{sid}.npz" for d in search_dirs if (d / f"{sid}.npz").exists()),
                     None)
        if found is None:
            raise FileNotFoundError(
                f"signatures for {sid} in none of "
                f"{[str(d) for d in search_dirs]}; build them first"
            )
        source_npz[sid] = found

    # Which sources have to agree on a target for it to enter the comparison.
    # Absent, the original pair: an existing run reproduces unchanged.
    shared_from = cfg["signatures"].get("shared_targets_from") or [
        "k562_gwps", "rpe1_essential"
    ]
    shared = sorted(set.intersection(
        *[_targets_of(source_npz[sid]) for sid in shared_from]
    ))
    max_t = cfg["pilot"].get("max_targets")
    rng = np.random.default_rng(int(cfg["pilot"]["seeds"][0]))
    if max_t and len(shared) > int(max_t):
        pick = rng.choice(len(shared), size=int(max_t), replace=False)
        shared_used = sorted(shared[int(i)] for i in pick)
        subsample = {
            "max_targets": int(max_t),
            "n_shared_available": len(shared),
            "n_used": len(shared_used),
            "rule": "uniform_random_not_filtered_by_effect",
            "seed": int(cfg["pilot"]["seeds"][0]),
        }
    else:
        shared_used = shared
        subsample = {
            "max_targets": max_t,
            "n_shared_available": len(shared),
            "n_used": len(shared_used),
            "rule": "all_shared",
        }

    compact_dir = out_dir / "compact_signatures"
    compact_dir.mkdir(parents=True, exist_ok=True)

    def load_source(sid: str, targets) -> SignatureSet:
        compact = compact_dir / f"{sid}.npz"
        if not compact.exists():
            have = _targets_of(source_npz[sid])
            want = [t for t in shared_used if t in have]
            sigs = _load_collapsed(source_npz[sid], want)
            sigs.write_npz(compact)
            gc.collect()
        have_t = set(targets)
        return SignatureSet.read_npz(compact, targets=list(have_t))

    universes: dict = {}

    # Descriptor variants and the arm plan, both optional: without them the run
    # is the original nine arms over the with/without-context pair.
    variants_cfg = cfg.get("descriptor_variants") or {}
    go_slim_tables: dict = {}
    if variants_cfg:
        table_path = cfg["descriptors"].get("go_slim_table")
        if any(v.get("include_go_slim") for v in variants_cfg.values()):
            if not table_path:
                raise ValueError(
                    "a variant asks for GO slim but descriptors.go_slim_table is unset; "
                    "build it with scripts/58_build_go_slim_table.py"
                )
            resolved = Path(str(table_path).replace(
                "<data_root>", str(config.paths().data_root)))
            for variant in variants_cfg.values():
                if not variant.get("include_go_slim"):
                    continue
                seed = (int(variant["permutation_seed"])
                        if variant.get("permute_go_slim") else None)
                if seed not in go_slim_tables:
                    go_slim_tables[seed] = load_go_slim_table(
                        resolved, permutation_seed=seed
                    )
    if cfg.get("arms"):
        arm_plan = []
        for entry in cfg["arms"]:
            variant = str(entry["variant"])
            if variant not in variants_cfg:
                raise ValueError(f"arm {entry} names an undeclared variant {variant!r}")
            model = str(entry["model"])
            arm_plan.append((
                f"{model}__{variant}", True,
                bool(variants_cfg[variant].get("include_context", True)),
                variant,
            ))
    else:
        arm_plan = [(a, learned, ctx, None) for a, learned, ctx in ARMS]

    registry = load_registry()
    prebuilt = dict(cfg["descriptors"].get("control_profiles") or {})
    profiles = {}
    for sid in cfg["signatures"]["sources"]:
        src = registry[sid]
        # Same cell line can appear as two sources (K562 gwps vs essential).
        # Keep the first profile so the training source is not overwritten.
        if (src.cell_context or sid) in profiles:
            continue
        if sid in prebuilt:
            # A source whose file is not a Replogle-style pseudobulk brings its
            # basal profile precomputed (scripts/55_control_profile.py); the
            # quantity is the same, the reader is not.
            profiles[src.cell_context or sid] = load_control_profile_npz(
                Path(str(prebuilt[sid]).replace(
                    "<data_root>", str(config.paths().data_root)
                ))
            )
            continue
        path = config.paths().data_root / src.local_path
        pf = PseudobulkFile(path=path, source_id=sid, context=src.cell_context or sid)
        profiles[src.cell_context or sid] = extract_control_profile(pf)

    preprocess_time = prep.stop()
    table_rows = []
    all_results = []
    split_docs = []
    per_target_store = {}

    def record(protocol, direction_id, seed, arm, row, scored) -> None:
        row["preprocess_seconds"] = preprocess_time["seconds"]
        per_target_store[(protocol, direction_id, seed, arm)] = scored["per_target"]
        row["metrics"] = {k: v for k, v in scored.items() if k != "per_target"}
        table_rows.append({k: row[k] for k in (
            "model", "uses_context", "protocol", "direction_id", "seed",
            "pooled_mse_vs_null", "pearson_median", "coverage_targets",
            "n_total_params", "n_trainable_params", "train_seconds",
            "infer_seconds", "peak_rss_bytes", "artifact_bytes",
            "calibration_label", "context_identifiable", "verdict_eligible",
        )})
        all_results.append(row)
        gc.collect()

    # Expression-gate arms, when the config declares them. They are not models:
    # each one is the base transfer arm times a weight read from a context's
    # control cells, so they need that arm to have run on the same split.
    gate_cfg = cfg.get("expression_gate") or None
    gate_arms = gate_arms_from_config(gate_cfg) if gate_cfg else []
    if gate_arms:
        base_arm_name = str(gate_cfg.get("base_arm", "shrunk_transfer"))
        if base_arm_name not in {a for a, _l, _c, _v in arm_plan}:
            raise ValueError(
                f"expression_gate.base_arm is {base_arm_name!r} but that arm is not in "
                f"the arm plan; the gate could not be checked against its own base"
            )

    seeds = list(cfg["pilot"]["seeds"])
    for protocol in cfg["protocols"]:
        for direction in cfg["directions"]:
            for seed in seeds:
                split = make_split(
                    protocol=protocol,
                    direction=direction,
                    shared_targets=shared_used,
                    seed=int(seed),
                    unseen_fraction=float(cfg["unseen_fraction"]),
                    inner_val_fraction=float(cfg["inner_val_fraction"]),
                    uses_query_ntc=True,
                )
                train_sids = list(split.train_sources)
                test_sid = split.test_source
                train_by_source = {}
                for sid in train_sids:
                    train_by_source[sid] = load_source(sid, split.train_targets)
                    gc.collect()
                train_sigs = SignatureSet(
                    [s for sid in train_sids for s in train_by_source[sid]]
                )
                train_sid = train_sids[0]
                test_sigs = load_source(test_sid, split.test_targets)
                gc.collect()
                universe_sets = {sid: train_by_source[sid] for sid in train_sids}
                universe_sets[test_sid] = test_sigs
                internal_sigs = None
                Y_internal = None
                targets_internal = []
                internal_gene_ok = None
                if split.internal_dest_source:
                    # With more than one training context the internal
                    # destination is one of the training sources: the pair is
                    # cross-context and already loaded.
                    if split.internal_dest_source in train_by_source:
                        internal_sigs = train_by_source[split.internal_dest_source]
                    else:
                        internal_sigs = load_source(
                            split.internal_dest_source, split.train_targets
                        )
                        gc.collect()
                    if len(internal_sigs):
                        universe_sets[split.internal_dest_source] = internal_sigs
                universe = common_measured_universe(universe_sets)
                universes[f"{protocol}_{split.direction_id}_seed{seed}"] = universe.as_dict()
                # Leakage guards.
                assert_no_test_context_in_train(train_sigs, split.test_context)
                if protocol == "new_context_unseen_target":
                    assert_unseen_targets_absent(train_sigs, set(split.test_targets))
                    if internal_sigs is not None:
                        assert_unseen_targets_absent(
                            internal_sigs, set(split.test_targets)
                        )

                # One row per (target, context) when training spans contexts, so
                # the context block of the design matrix is a variable and not a
                # constant column. With one training source this is the old path
                # exactly.
                multi_context = len(train_sids) > 1
                context_of_source = {
                    sid: (registry[sid].cell_context or sid) for sid in train_sids
                }
                if multi_context:
                    by_source_map = {
                        sid: {s.target: s for s in train_by_source[sid]}
                        for sid in train_sids
                    }
                    rows_pairs = [
                        (t, sid)
                        for sid in train_sids
                        for t in split.train_targets
                        if t in by_source_map[sid]
                    ]
                    Y_train, _ = _stack_rows(by_source_map, rows_pairs, universe)
                    train_row_targets = [t for t, _ in rows_pairs]
                    train_row_contexts = [context_of_source[sid] for _, sid in rows_pairs]
                else:
                    Y_train, _, _, _ = _stack(
                        train_sigs, list(split.train_targets), universe
                    )
                    train_row_targets = list(split.train_targets)
                    train_row_contexts = None
                Y_test, _, _, _ = _stack(test_sigs, list(split.test_targets), universe)
                del test_sigs
                gc.collect()

                if internal_sigs is not None and len(internal_sigs):
                    targets_internal = [
                        t for t in split.train_targets
                        if t in set(internal_sigs.targets)
                    ]
                    if targets_internal:
                        Y_internal, _, _, obs_internal = _stack(
                            internal_sigs, targets_internal, universe
                        )
                        internal_gene_ok = np.all(obs_internal, axis=0)
                        if not internal_gene_ok.any():
                            Y_internal = None
                            targets_internal = []
                            internal_gene_ok = None

                # Codes from training responses only (refit per fold).
                fold_spec = factorization_from_config(cfg, int(seed))
                max_rank = max(int(r) for r in cfg["models"]["modular"]["rank_grid"])
                k_codes = min(max_rank, min(Y_train.shape) - 1)
                codes_mat, _, _ = svd_codes(
                    Y_train, universe, max(1, k_codes), fold_spec
                )
                if multi_context:
                    # A target now has one response per training context. Its
                    # code is their mean: at test time the context is new, so a
                    # per-context code could not be chosen without knowing the
                    # answer.
                    stacked: dict[str, list] = {}
                    for i, t in enumerate(train_row_targets):
                        stacked.setdefault(t, []).append(codes_mat[i])
                    codes_by = {t: np.mean(v, axis=0) for t, v in stacked.items()}
                else:
                    codes_by = {
                        t: codes_mat[i] for i, t in enumerate(split.train_targets)
                    }
                include_codes = (
                    cfg["descriptors"]["include_train_response_codes"]
                    and protocol == "new_context_seen_target"
                )
                train_contexts = (
                    tuple(dict.fromkeys(context_of_source[sid] for sid in train_sids))
                    if multi_context else (split.train_context,)
                )
                common_kw = dict(
                    universe=universe,
                    profiles=profiles,
                    train_contexts=train_contexts,
                    train_sigs=train_sigs,
                    codes_by_target=codes_by if include_codes else {},
                    n_high_expr=int(cfg["descriptors"]["n_high_expr_genes"]),
                )
                bank_ctx = fit_descriptor_bank(
                    include_context=True,
                    include_response_codes=include_codes,
                    **common_kw,
                )
                bank_noctx = fit_descriptor_bank(
                    include_context=False,
                    include_response_codes=include_codes,
                    **common_kw,
                )
                # Named descriptor variants, when the config declares them. The
                # default pair stays exactly what it was, so an earlier run
                # reproduces.
                banks = {"with_context": bank_ctx, "without_context": bank_noctx}
                for name, spec in (cfg.get("descriptor_variants") or {}).items():
                    table = go_slim_tables.get(
                        int(spec.get("permutation_seed"))
                        if spec.get("permute_go_slim") else None
                    )
                    banks[name] = fit_descriptor_bank(
                        include_context=bool(spec.get("include_context", True)),
                        include_response_codes=include_codes,
                        go_slim=table if spec.get("include_go_slim") else None,
                        include_go_slim=bool(spec.get("include_go_slim")),
                        **common_kw,
                    )
                split_path = (
                    out_dir / "splits" /
                    f"{protocol}_{split.direction_id}_seed{seed}.json"
                )
                split_path.parent.mkdir(parents=True, exist_ok=True)
                payload = split.as_dict()
                payload["descriptors"] = {
                    name: bank.as_dict() for name, bank in banks.items()
                }
                payload["query_ntc_used"] = True
                payload["query_ntc_shared_across_arms"] = True
                if gate_arms:
                    # Where the genes and the targets of this fold sit in CPM,
                    # before any gate: the gate's room is a measurement, not an
                    # assumption about it.
                    payload["expression_presence"] = split_presence_summary(
                        profiles, universe,
                        sorted(set(split.train_targets) | set(split.test_targets)),
                    )
                split_path.write_text(json.dumps(jsonable(payload), indent=2), encoding="utf-8")
                split_docs.append(str(split_path))

                arm_dir = out_dir / "models" / f"{protocol}_{split.direction_id}_seed{seed}"
                arm_dir.mkdir(parents=True, exist_ok=True)

                sources_by_context: dict[str, list[str]] = {}
                for sid in train_sids:
                    sources_by_context.setdefault(context_of_source[sid], []).append(sid)
                internal_dest_context = (
                    context_of_source.get(split.internal_dest_source)
                    if split.internal_dest_source else None
                )

                for arm, _is_learned, uses_ctx, variant in arm_plan:
                    row, scored = _run_arm(
                        arm=arm,
                        uses_ctx=uses_ctx,
                        bank=banks[variant] if variant else None,
                        cfg=cfg,
                        split=split,
                        universe=universe,
                        train_sigs=train_sigs,
                        internal_sigs=internal_sigs,
                        bank_ctx=bank_ctx,
                        bank_noctx=bank_noctx,
                        Y_train=Y_train,
                        targets_train=train_row_targets,
                        Y_test=Y_test,
                        targets_test=list(split.test_targets),
                        Y_internal=Y_internal,
                        targets_internal=targets_internal,
                        internal_gene_ok=internal_gene_ok,
                        seed=int(seed),
                        out_dir=arm_dir,
                        contexts_train=train_row_contexts,
                        sources_by_context=sources_by_context,
                        internal_dest_context=internal_dest_context,
                        factorization=fold_spec,
                    )
                    record(protocol, split.direction_id, int(seed), arm, row, scored)

                if gate_arms:
                    base_row = next(
                        (r for r in all_results
                         if (r["protocol"], r["direction_id"], r["seed"], r["model"])
                         == (protocol, split.direction_id, int(seed), base_arm_name)),
                        None,
                    )
                    inner_val_targets = _inner_val_targets(
                        split, train_row_targets, train_row_contexts, int(seed)
                    )
                    base_model, base_calib = _fit_shrunk_transfer(
                        cfg=cfg,
                        split=split,
                        train_sigs=train_sigs,
                        internal_sigs=internal_sigs,
                        multi_context=multi_context,
                        sources_by_context=sources_by_context,
                        internal_dest_context=internal_dest_context,
                        inner_val_targets=inner_val_targets,
                    )
                    for gate_arm in gate_arms:
                        row, scored = run_gate_arm(
                            arm=gate_arm,
                            cfg=cfg,
                            split=split,
                            universe=universe,
                            train_sigs=train_sigs,
                            base_model=base_model,
                            base_calib=base_calib,
                            sources_by_context=sources_by_context,
                            internal_dest_context=internal_dest_context,
                            inner_val_targets=inner_val_targets,
                            profiles=profiles,
                            Y_test=Y_test,
                            targets_test=list(split.test_targets),
                            seed=int(seed),
                            out_dir=arm_dir,
                            base_row=base_row,
                        )
                        record(
                            protocol, split.direction_id, int(seed),
                            gate_arm.name, row, scored,
                        )

    # Paired differences vs shrunk_transfer and vs compact_mlp, on the same split.
    paired = []
    groups = {}
    for row in all_results:
        g = (row["protocol"], row["direction_id"], row["seed"])
        groups.setdefault(g, []).append(row["model"])
    for protocol, direction_id, seed in groups:
        def get(arm):
            return per_target_store[(protocol, direction_id, seed, arm)]

        def record_pair(a, b, label):
            n_boot = int(cfg["evaluation"]["n_boot"])
            return {
                "protocol": protocol,
                "direction_id": direction_id,
                "seed": seed,
                "a": a,
                "b": b,
                "comparison": label,
                "diff": paired_difference(
                    get(a), get(b),
                    key="mse_vs_null",
                    n_boot=n_boot,
                    seed=int(seed),
                ),
                "diff_paired_pooled": paired_pooled_difference(
                    get(a), get(b),
                    n_boot=n_boot,
                    seed=int(seed),
                ),
                "aggregation_note": (
                    "diff averages per-target MSE/null ratios; "
                    "diff_paired_pooled recomputes pooled_mse_vs_null "
                    "(ratio of sums) on the same resampled targets. "
                    "Opposite signs are not a mathematical contradiction."
                ),
            }

        # The arms that actually ran, not the hard-coded list: with a custom arm
        # plan the two differ, and a comparison against an arm that never ran is
        # a KeyError at best and a wrong pairing at worst.
        base_arms = list(groups[(protocol, direction_id, seed)])
        for pair in (cfg.get("paired_comparisons") or []):
            a, b = str(pair["a"]), str(pair["b"])
            if a not in base_arms or b not in base_arms:
                raise ValueError(
                    f"paired_comparisons names {a!r} vs {b!r}; arms that ran: {base_arms}"
                )
            paired.append(record_pair(a, b, str(pair.get("label") or "configured")))
        if "shrunk_transfer" in base_arms:
            for arm in base_arms:
                if arm == "shrunk_transfer":
                    continue
                paired.append(record_pair(arm, "shrunk_transfer", "vs_shrunk_transfer"))
        if "compact_mlp" in base_arms and "modular_frozen" in base_arms:
            paired.append(record_pair(
                "modular_frozen", "compact_mlp", "frozen_vs_compact_mlp"
            ))
            if "modular_joint" in base_arms:
                paired.append(record_pair(
                    "modular_joint", "compact_mlp", "joint_vs_compact_mlp"
                ))
        # Each conditioned arm against its own no-context twin. The two differ
        # by the context block alone. Both aggregations are stored: the mean
        # of per-target ratios, and the paired pooled primary metric.
        for arm in sorted(base_arms):
            twin = f"{arm}_noctx"
            if twin not in base_arms:
                continue
            paired.append(record_pair(arm, twin, "context_descriptor_vs_none"))

    (out_dir / "gene_universe.json").write_text(
        json.dumps(jsonable(universes), indent=2), encoding="utf-8"
    )
    table_path = write_comparison_table(table_rows, out_dir / "comparison_table.md")

    summary = {
        "primary_metric": cfg["primary_metric"],
        "primary_metric_space": cfg["primary_metric_space"],
        "non_inferiority_margin": cfg["non_inferiority_margin"],
        "non_inferiority_note": cfg["non_inferiority_note"],
        "winner_declared": False,
        # Derived, not asserted. This sentence used to state that a held-out
        # context leaves one training context -- true of a two-context project
        # and false the moment a third arrives, which is the kind of stale claim
        # that outlives the run it was written for.
        "winner_reason": (
            "No winner. Architecture was not selected on the external test. "
            + (
                "Every fold trains on more than one context, so a context "
                "descriptor can vary in training and a with/without comparison "
                "is at least identifiable in principle; two contexts still "
                "confound biology with the experiment each came from. "
                if min(int(d.get("n_train_contexts", 1)) for d in cfg["directions"]) > 1
                else "A held-out context leaves one training context, so a "
                     "context-descriptor gain is not identifiable. "
            )
            + "If seed intervals overlap, the result is inconclusive."
        ),
        "verdict": "inconclusive_pending_numbers",
        "n_shared_targets_available": subsample["n_shared_available"],
        "n_targets_used": subsample["n_used"],
        "subsample": subsample,
        "gene_universe": universes,
        "preprocess": preprocess_time,
        "machine": machine_snapshot(),
        "n_result_rows": len(all_results),
        "splits": split_docs,
        "generator_x_predictor": gen_spec,
        "arm_plan": [
            {"arm": a, "uses_context": c, "variant": v} for a, _l, c, v in arm_plan
        ],
        "descriptor_variants": variants_cfg,
        "expression_gate": gate_cfg,
        "decision_rule": cfg.get("decision_rule"),
        "forbidden_trial_alpha": FORBIDDEN_TRIAL_ALPHA,
        "not_a_vcc_score": True,
        "factorization": factorization_from_config(
            cfg, int(cfg["pilot"]["seeds"][0])
        ).as_dict(),
    }
    # Fill verdict from the numbers: if any comparison CI excludes 0 consistently
    # across seeds, say so as a measurement, not as adoption.
    summary["paired_differences"] = paired

    results_path = out_dir / "results.json"
    results_path.write_text(
        json.dumps(jsonable({
            "summary": summary,
            "rows": all_results,
            "table_rows": table_rows,
            "paired_differences": paired,
        }), indent=2),
        encoding="utf-8",
    )
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(jsonable(summary), indent=2), encoding="utf-8")
    return {
        "out_dir": str(out_dir),
        "inventory": str(inv_path),
        "results": str(results_path),
        "table": str(table_path),
        "summary": str(summary_path),
        "n_rows": len(all_results),
        "universe": universes,
        "subsample": subsample,
    }
