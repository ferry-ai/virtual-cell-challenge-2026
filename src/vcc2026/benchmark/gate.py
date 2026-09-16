"""Expression gate arms: shrink a prediction where the destination does not express.

CP-0013 measured that arms which try to LEARN how context modulates a response do
not generalise across the three folds: the context descriptor makes a real
difference, with a sign that changes with the held-out context. The arms here learn
nothing from comparing contexts. They take `shrunk_transfer` -- the only arm below
the null in all three folds -- exactly as it was selected and calibrated on the
split, and multiply its prediction by a weight read from the control cells of the
context being predicted. Between `shrunk_transfer` and a gate arm, the gate is the
only thing that varies.

Three variants:

* G1 -- every output gene's delta times that gene's weight.
* G2 -- the negative part of each delta times the weight; the positive part left
  intact or attenuated by a second parameter. An absent gene cannot go down, it can
  go up.
* G3 -- the whole predicted response times the weight of the TARGET gene.

and two controls for each:

* permuted (C1): presence shuffled among genes with a fixed seed. If it does as well
  as the real gate, the gain is a global compression, not a gene-context link.
* source (C2): the same gate built from the contexts the prediction came FROM. If it
  does as well as the destination gate, the rule is a filter on low-expression
  noise and has to be called that.

Parameters are selected on the internal cross-context pair inside training -- the
pair ShrunkTransfer calibrates its amplitude on -- on the inner validation targets
and the fold's gene universe. Selection reads the control profiles of the training
contexts only. The test context's controls are read once, to apply the chosen gate,
and only by the destination arms: the task allows query-context NTCs, and the
source arms do not need them at all.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vcc2026.genes import official_axis
from vcc2026.models import WeightedTransfer
from vcc2026.presence import (
    GenePresence,
    combine_log10_presence,
    gate_output,
    gate_rows,
    logistic_weight,
    permute_among,
    presence_summary,
)
from vcc2026.signatures import SignatureSet

from .evaluate import PhaseClock, aggregate_targets, score_matrix
from .models import context_equal_weights

__all__ = [
    "GateArm",
    "GateCandidate",
    "apply_gate",
    "candidate_grid",
    "evaluate_decision",
    "gate_arms_from_config",
    "internal_pair",
    "presence_vector",
    "run_gate_arm",
    "select_gate",
    "select_on_internal_pair",
    "split_presence_summary",
    "target_log10",
]

VARIANT_KINDS = {"G1": "output_symmetric", "G2": "output_asymmetric", "G3": "target"}
OUTPUT_VARIANTS = ("G1", "G2")
PRESENCE_ROLES = ("destination", "source")
MIN_VAL_TARGETS = 3


@dataclass(frozen=True)
class GateArm:
    """One gate arm: which variant, whose controls, and whether permuted."""

    name: str
    variant: str
    presence_from: str
    permuted: bool

    def __post_init__(self) -> None:
        if self.variant not in VARIANT_KINDS:
            raise ValueError(f"{self.name}: unknown variant {self.variant!r}")
        if self.presence_from not in PRESENCE_ROLES:
            raise ValueError(f"{self.name}: presence_from must be one of {PRESENCE_ROLES}")

    @property
    def n_gate_parameters(self) -> int:
        return 3 if self.variant == "G2" else 2

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "variant": self.variant,
            "kind": VARIANT_KINDS[self.variant],
            "presence_from": self.presence_from,
            "permuted": self.permuted,
        }


def gate_arms_from_config(gate_cfg: dict) -> list[GateArm]:
    arms = [
        GateArm(
            name=str(a["name"]),
            variant=str(a["variant"]),
            presence_from=str(a["presence_from"]),
            permuted=bool(a.get("permuted", False)),
        )
        for a in gate_cfg.get("arms") or []
    ]
    names = [a.name for a in arms]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate gate arm names: {names}")
    return arms


@dataclass(frozen=True)
class GateCandidate:
    """A point of the grid. No midpoint means the identity: weight 1 everywhere."""

    midpoint_cpm: float | None = None
    slope_per_decade: float | None = None
    positive_attenuation: float = 1.0

    @property
    def identity(self) -> bool:
        return self.midpoint_cpm is None

    def as_dict(self) -> dict:
        return {
            "identity": self.identity,
            "midpoint_cpm": self.midpoint_cpm,
            "slope_per_decade": self.slope_per_decade,
            "positive_attenuation": self.positive_attenuation,
        }


def candidate_grid(variant: str, grid_cfg: dict) -> list[GateCandidate]:
    """Identity first, so that a tie keeps "do nothing"."""
    if variant not in VARIANT_KINDS:
        raise ValueError(f"unknown variant {variant!r}")
    grid: list[GateCandidate] = []
    if grid_cfg.get("include_identity", True):
        grid.append(GateCandidate())
    betas = [float(b) for b in grid_cfg.get("positive_attenuation", [0.0])]
    for midpoint in grid_cfg["midpoint_cpm"]:
        for slope in grid_cfg["slope_per_decade"]:
            if variant == "G2":
                for beta in betas:
                    grid.append(GateCandidate(float(midpoint), float(slope), beta))
            else:
                grid.append(GateCandidate(float(midpoint), float(slope), 1.0))
    return grid


def apply_gate(
    pred: np.ndarray,
    *,
    variant: str,
    candidate: GateCandidate,
    gene_log10: np.ndarray | None,
    target_log10: np.ndarray | None,
) -> np.ndarray:
    """Gate a (targets, genes) prediction. The identity returns it unchanged."""
    if candidate.identity:
        return pred
    kw = dict(midpoint_cpm=candidate.midpoint_cpm, slope_per_decade=candidate.slope_per_decade)
    if variant in OUTPUT_VARIANTS:
        weight = logistic_weight(gene_log10, **kw)
        beta = 1.0 if variant == "G1" else candidate.positive_attenuation
        return gate_output(pred, weight, positive_attenuation=beta)
    return gate_rows(pred, logistic_weight(target_log10, **kw))


def select_gate(
    pred_val: np.ndarray,
    truth_val: np.ndarray,
    *,
    variant: str,
    candidates: list[GateCandidate],
    gene_log10: np.ndarray | None,
    target_log10: np.ndarray | None,
) -> tuple[GateCandidate, list[dict]]:
    """Lowest validation MSE; a later candidate must be strictly better to win."""
    if pred_val.shape != truth_val.shape:
        raise ValueError(f"shape mismatch {pred_val.shape} vs {truth_val.shape}")
    best, best_mse, table = None, None, []
    for cand in candidates:
        gated = apply_gate(pred_val, variant=variant, candidate=cand,
                           gene_log10=gene_log10, target_log10=target_log10)
        mse = float(np.mean(np.square(gated - truth_val)))
        table.append({**cand.as_dict(), "val_mse": mse})
        if best is None or mse < best_mse:
            best, best_mse = cand, mse
    return best, table


def presence_vector(
    profiles: dict, *, role: str, destination: str, sources, pseudocount: float
) -> np.ndarray:
    """log10 presence on the official axis for one role, from loaded profiles.

    Only the contexts the role names are read: a source vector never touches the
    destination's profile, and vice versa.
    """
    if role == "destination":
        return GenePresence.from_control_profile(profiles[destination]).log10_cpm(pseudocount)
    if role == "source":
        sources = list(sources)
        if destination in sources:
            raise ValueError(f"source contexts {sources} include the destination {destination!r}")
        return combine_log10_presence([
            GenePresence.from_control_profile(profiles[c]).log10_cpm(pseudocount)
            for c in sources
        ])
    raise ValueError(f"unknown presence role {role!r}")


def target_log10(
    axis_log10: np.ndarray,
    targets,
    *,
    position: dict[str, int],
    permuted_over=None,
    seed: int | None = None,
) -> np.ndarray:
    """Presence of each target gene. NaN for a target that is not on the axis.

    With `permuted_over`, the values are shuffled among those targets once, with
    `seed`, so the same target gets the same borrowed value at selection and at
    test.
    """
    def raw(t):
        i = position.get(t, -1)
        return float(axis_log10[i]) if i >= 0 else np.nan

    targets = list(targets)
    if permuted_over is None:
        return np.array([raw(t) for t in targets], dtype=np.float64)
    pool = sorted(set(permuted_over))
    missing = [t for t in targets if t not in set(pool)]
    if missing:
        raise ValueError(f"targets outside the permutation pool, e.g. {missing[:5]}")
    values = np.array([raw(t) for t in pool], dtype=np.float64)
    shuffled = permute_among(values, np.arange(len(pool)), int(seed))
    lookup = dict(zip(pool, shuffled))
    return np.array([lookup[t] for t in targets], dtype=np.float64)


def _gate_inputs(arm: GateArm, axis_log10, targets, *, universe, fold_targets, position, seed):
    """(gene_log10 on the universe, None) for G1/G2; (None, per-target) for G3."""
    if arm.variant in OUTPUT_VARIANTS:
        values = axis_log10
        if arm.permuted:
            values = permute_among(axis_log10, np.flatnonzero(universe.observed), seed)
        return universe.slice(values), None
    return None, target_log10(
        axis_log10, targets, position=position,
        permuted_over=fold_targets if arm.permuted else None, seed=seed,
    )


def internal_pair(
    train_sigs: SignatureSet,
    *,
    sources_by_context: dict[str, list[str]],
    internal_dest_context: str,
    inner_val_targets,
    prior_sd: float,
    alpha: float,
    universe,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Donor prediction and destination truth on the inner validation targets.

    The same pair and the same validation targets as
    `select_multi_source_transfer`: donors are the training contexts other than the
    internal destination, combined with equal weight per context, and the donor
    prediction carries the base arm's selected prior_sd and alpha.
    """
    if internal_dest_context not in sources_by_context:
        raise ValueError(f"{internal_dest_context!r} is not a training context")
    donor_contexts = {c: s for c, s in sources_by_context.items() if c != internal_dest_context}
    if not donor_contexts:
        raise ValueError("an internal pair needs at least one donor context")
    donor = WeightedTransfer(context_equal_weights(donor_contexts), alpha=alpha, prior_sd=prior_sd)
    donor.fit(train_sigs)
    dest_sources = set(sources_by_context[internal_dest_context])
    dst = {
        s.target: s
        for s in SignatureSet([s for s in train_sigs if s.source in dest_sources]).collapse_guides()
    }
    donor_sources = {src for srcs in donor_contexts.values() for src in srcs}
    donor_targets = {s.target for s in train_sigs if s.source in donor_sources}
    shared = donor_targets & set(dst)
    rows_p, rows_d, used = [], [], []
    for target in inner_val_targets:
        if target not in shared:
            continue
        pred = donor.predict(target)
        if pred.support == 0:
            continue
        rows_p.append(universe.slice(pred.delta))
        rows_d.append(universe.slice(dst[target].delta))
        used.append(target)
    if not used:
        n = universe.n_kept
        return np.zeros((0, n)), np.zeros((0, n)), []
    return np.vstack(rows_p), np.vstack(rows_d), used


def select_on_internal_pair(
    arm: GateArm,
    *,
    gate_cfg: dict,
    train_sigs: SignatureSet,
    train_profiles: dict,
    base_calib: dict,
    sources_by_context: dict[str, list[str]],
    internal_dest_context: str,
    inner_val_targets,
    universe,
    fold_targets,
    position: dict[str, int],
) -> dict:
    """Choose the gate on training data. Reads training-context profiles only.

    `train_profiles` should hold the training contexts and nothing else; passing
    the test context's profile here would not be used, and the caller builds it
    without.
    """
    pseudo = float(gate_cfg["presence"]["log10_pseudocount_cpm"])
    seed = int(gate_cfg["permutation"]["seed"])
    candidates = candidate_grid(arm.variant, gate_cfg["grid"])
    out = {
        "pair": "internal_cross_context_within_training",
        "internal_dest_context": internal_dest_context,
        "donor_contexts": sorted(c for c in sources_by_context if c != internal_dest_context),
        "not_on_test": True,
        "n_candidates": len(candidates),
        "chosen": GateCandidate(),
        "grid": [],
        "why_identity": None,
        "val_targets": [],
    }
    if base_calib.get("label") != "cross_context_within_training":
        out["why_identity"] = (
            "base amplitude was not calibrated on an internal cross-context pair ("
            + str(base_calib.get("why_predetermined") or base_calib.get("label")) + ")"
        )
        return out
    P, D, used = internal_pair(
        train_sigs,
        sources_by_context=sources_by_context,
        internal_dest_context=internal_dest_context,
        inner_val_targets=inner_val_targets,
        prior_sd=float(base_calib["prior_sd"]),
        alpha=float(base_calib["alpha"]),
        universe=universe,
    )
    out["val_targets"] = used
    if len(used) < MIN_VAL_TARGETS:
        out["why_identity"] = f"{len(used)} validation targets on the internal pair"
        return out
    axis_log10 = presence_vector(
        train_profiles, role=arm.presence_from, destination=internal_dest_context,
        sources=out["donor_contexts"], pseudocount=pseudo,
    )
    gene_x, target_x = _gate_inputs(
        arm, axis_log10, used, universe=universe, fold_targets=fold_targets,
        position=position, seed=seed,
    )
    chosen, table = select_gate(
        P, D, variant=arm.variant, candidates=candidates,
        gene_log10=gene_x, target_log10=target_x,
    )
    out["chosen"] = chosen
    out["grid"] = table
    return out


def _exposure(arm, candidate, base_pred, pred, gene_x, target_x, targets) -> dict:
    """How much the chosen gate touched on the test split."""
    denom = float(np.sum(np.abs(base_pred)))
    out = {
        "fraction_abs_delta_removed": (
            float(np.sum(np.abs(base_pred - pred)) / denom) if denom > 0 else None
        ),
    }
    kw = dict(midpoint_cpm=candidate.midpoint_cpm, slope_per_decade=candidate.slope_per_decade)
    if arm.variant in OUTPUT_VARIANTS:
        w = np.ones(gene_x.size) if candidate.identity else logistic_weight(gene_x, **kw)
        out.update({
            "n_universe_genes": int(w.size),
            "n_genes_weight_below_0_5": int(np.sum(w < 0.5)),
            "n_genes_weight_below_0_9": int(np.sum(w < 0.9)),
            "mean_gene_weight": float(np.mean(w)) if w.size else None,
        })
    else:
        w = np.ones(target_x.size) if candidate.identity else logistic_weight(target_x, **kw)
        low = sorted(
            ({"target": t, "log10_presence": (None if not np.isfinite(x) else float(x)),
              "weight": float(wt)}
             for t, x, wt in zip(targets, target_x, w) if wt < 0.9),
            key=lambda d: d["weight"],
        )
        out.update({
            "n_test_targets": int(w.size),
            "n_targets_weight_below_0_5": int(np.sum(w < 0.5)),
            "n_targets_weight_below_0_9": int(np.sum(w < 0.9)),
            "mean_target_weight": float(np.mean(w)) if w.size else None,
            "targets_weight_below_0_9": low[:25],
        })
    return out


def run_gate_arm(
    *,
    arm: GateArm,
    cfg: dict,
    split,
    universe,
    train_sigs: SignatureSet,
    base_model,
    base_calib: dict,
    sources_by_context: dict[str, list[str]],
    internal_dest_context: str | None,
    inner_val_targets,
    profiles: dict,
    Y_test: np.ndarray,
    targets_test,
    seed: int,
    out_dir,
    base_row: dict | None,
) -> tuple[dict, dict]:
    """Select on the internal pair, apply to the test context, score like any arm."""
    gate_cfg = cfg["expression_gate"]
    if internal_dest_context is None or len(sources_by_context) < 2:
        raise ValueError(
            "the expression gate needs two training contexts: its selection pair must "
            "be cross-context, and with one context the source and destination gates "
            "would read the same controls"
        )
    if split.test_context in sources_by_context:
        raise ValueError(f"test context {split.test_context!r} is a training context")
    pseudo = float(gate_cfg["presence"]["log10_pseudocount_cpm"])
    perm_seed = int(gate_cfg["permutation"]["seed"])
    position = official_axis().position()
    fold_targets = sorted(set(split.train_targets) | set(split.test_targets))
    targets_test = list(targets_test)

    clock = PhaseClock(f"select:{arm.name}")
    train_profiles = {c: profiles[c] for c in sources_by_context}
    selection = select_on_internal_pair(
        arm,
        gate_cfg=gate_cfg,
        train_sigs=train_sigs,
        train_profiles=train_profiles,
        base_calib=base_calib,
        sources_by_context=sources_by_context,
        internal_dest_context=internal_dest_context,
        inner_val_targets=inner_val_targets,
        universe=universe,
        fold_targets=fold_targets,
        position=position,
    )
    train_time = clock.stop()

    infer = PhaseClock(f"infer:{arm.name}")
    preds, support = [], []
    for t in targets_test:
        p = base_model.predict(t)
        preds.append(universe.slice(p.delta))
        support.append(int(p.support))
    base_pred = np.vstack(preds) if preds else np.zeros((0, universe.n_kept))
    base_check = {"base_arm": gate_cfg.get("base_arm", "shrunk_transfer")}
    null = float(np.mean(np.square(Y_test)))
    base_pooled = float(np.mean(np.square(base_pred - Y_test)) / null) if null > 0 else None
    base_check["refit_base_pooled_mse_vs_null"] = base_pooled
    if base_row is not None:
        reference = base_row.get("pooled_mse_vs_null")
        base_check["base_row_pooled_mse_vs_null"] = reference
        if reference is None or base_pooled is None or abs(reference - base_pooled) > 1e-12:
            raise RuntimeError(
                f"{arm.name}: the refitted base scores {base_pooled} and the "
                f"{base_check['base_arm']} row scores {reference}; the gate would not "
                f"be comparing one factor"
            )
        base_check["identical"] = True
    axis_log10 = presence_vector(
        profiles, role=arm.presence_from, destination=split.test_context,
        sources=list(sources_by_context), pseudocount=pseudo,
    )
    gene_x, target_x = _gate_inputs(
        arm, axis_log10, targets_test, universe=universe, fold_targets=fold_targets,
        position=position, seed=perm_seed,
    )
    chosen = selection["chosen"]
    pred = apply_gate(base_pred, variant=arm.variant, candidate=chosen,
                      gene_log10=gene_x, target_log10=target_x)
    infer_time = infer.stop()

    exposure = _exposure(arm, chosen, base_pred, pred, gene_x, target_x, targets_test)
    artifact = out_dir / f"{arm.name}.npz"
    np.savez_compressed(
        artifact,
        name=np.array(arm.name),
        variant=np.array(arm.variant),
        presence_from=np.array(arm.presence_from),
        permuted=np.array(arm.permuted),
        permutation_seed=np.array(perm_seed),
        identity=np.array(chosen.identity),
        midpoint_cpm=np.array(np.nan if chosen.midpoint_cpm is None else chosen.midpoint_cpm),
        slope_per_decade=np.array(
            np.nan if chosen.slope_per_decade is None else chosen.slope_per_decade),
        positive_attenuation=np.array(chosen.positive_attenuation),
        alpha=np.array(float(base_calib["alpha"])),
        prior_sd=np.array(float(base_calib["prior_sd"])),
        observed=universe.observed,
    )
    if cfg["evaluation"].get("save_full_predictions"):
        np.savez_compressed(
            out_dir / f"{arm.name}.predictions.npz",
            delta=np.asarray(pred, dtype=np.float32),
            targets=np.asarray(targets_test, dtype=object),
            observed=universe.observed,
            arm=np.array(arm.name),
            direction_id=np.array(split.direction_id),
            protocol=np.array(split.protocol),
            test_context=np.array(split.test_context),
        )

    scored = score_matrix(
        pred, Y_test, targets=targets_test,
        strong_threshold=float(cfg["evaluation"]["strong_threshold"]),
    )
    scored.update(aggregate_targets(scored, n_boot=int(cfg["evaluation"]["n_boot"]), seed=seed))
    k = arm.n_gate_parameters
    n_params = {
        "n_total": 2 + k,
        "n_trainable": 2 + k,
        "n_frozen": 0,
        "note": (
            f"alpha and prior_sd inherited from {base_check['base_arm']}; "
            f"{k} gate hyperparameters selected on the internal pair"
        ),
    }
    coverage = float(np.mean(np.array(support) > 0)) if support else 0.0
    selection_doc = dict(selection)
    selection_doc["chosen"] = chosen.as_dict()
    row = {
        "model": arm.name,
        "uses_context": arm.presence_from == "destination",
        "reads_query_context_controls": arm.presence_from == "destination",
        "protocol": split.protocol,
        "direction_id": split.direction_id,
        "seed": seed,
        "pooled_mse_vs_null": scored.get("pooled_mse_vs_null"),
        "pearson_median": scored.get("pearson_median"),
        "coverage_targets": coverage,
        "n_total_params": n_params["n_total"],
        "n_trainable_params": n_params["n_trainable"],
        "train_seconds": train_time["seconds"],
        "infer_seconds": infer_time["seconds"],
        "preprocess_seconds": None,
        "peak_rss_bytes": train_time.get("peak_rss_bytes_after"),
        "artifact_bytes": int(artifact.stat().st_size) if artifact.exists() else 0,
        "calibration_label": base_calib.get("label"),
        "alpha": float(base_calib["alpha"]),
        "context_identifiable": bool(split.context_dependence_identifiable),
        "verdict_eligible": False,
        "selection": selection_doc,
        "parameters": n_params,
        "n_train_contexts": split.n_train_contexts,
        "metric_space": "pseudobulk_log2FC_proxy",
        "not_a_vcc_score": True,
        "history": None,
        "resources_train": train_time,
        "resources_infer": infer_time,
        "n_test_targets": len(targets_test),
        "n_genes": universe.n_kept,
        "gate": {
            **arm.as_dict(),
            "chosen": chosen.as_dict(),
            "identity_chosen": chosen.identity,
            "why_identity": selection["why_identity"],
            "exposure_on_test": exposure,
            "base_check": base_check,
            "permutation_seed": perm_seed if arm.permuted else None,
        },
        "per_target_compact": {
            "targets": [p["target"] for p in scored["per_target"]],
            "sse": [p.get("sse") for p in scored["per_target"]],
            "sst": [p.get("sst") for p in scored["per_target"]],
            "mse_vs_null": [p.get("mse_vs_null") for p in scored["per_target"]],
        },
    }
    return row, scored


def split_presence_summary(profiles: dict, universe, fold_targets) -> dict:
    """Where the loaded contexts' genes and targets sit in CPM, before any gate."""
    position = official_axis().position()
    pos = np.array([position.get(t, -1) for t in fold_targets], dtype=np.int64)
    out = {}
    for context, profile in profiles.items():
        cpm = GenePresence.from_control_profile(profile).cpm
        target_cpm = np.where(pos >= 0, cpm[np.clip(pos, 0, None)], np.nan)
        out[context] = {
            "genes_in_universe": presence_summary(universe.slice(cpm)),
            "fold_targets": presence_summary(target_cpm),
        }
    return out


_REQUIREMENTS = {
    "negative_ci_excludes_zero": lambda mean, excl: mean < 0.0 and excl,
    "positive_ci_excludes_zero": lambda mean, excl: mean > 0.0 and excl,
    "not_negative_ci_excludes_zero": lambda mean, excl: not (mean < 0.0 and excl),
}


def evaluate_decision(paired: list[dict], rule: dict, *, directions, seeds) -> dict:
    """Apply a decision rule written before the run to the paired differences.

    A comparison that is missing, or was skipped for too few targets, fails every
    clause it is needed by: no evidence cannot promote anything.
    """
    protocol = rule["protocol"]
    statistic = rule.get("statistic", "diff")
    index = {
        (p["protocol"], p["direction_id"], int(p["seed"]), p["a"], p["b"]): p
        for p in paired
    }

    def check(clause: dict, variant: str | None) -> dict:
        a = clause["a"].replace("{V}", variant or "")
        b = clause["b"].replace("{V}", variant or "")
        require = clause["require"]
        if require not in _REQUIREMENTS:
            raise ValueError(f"unknown requirement {require!r}")
        rows = []
        for direction in directions:
            for seed in seeds:
                entry = index.get((protocol, direction, int(seed), a, b))
                block = (entry or {}).get(statistic) or {}
                if "mean_a_minus_b" not in block:
                    rows.append({"direction_id": direction, "seed": int(seed),
                                 "holds": False, "status": "missing_or_skipped"})
                    continue
                mean = float(block["mean_a_minus_b"])
                excl = bool(block["ci95_excludes_zero"])
                rows.append({
                    "direction_id": direction, "seed": int(seed),
                    "mean_a_minus_b": mean, "ci95": block.get("ci95"),
                    "ci95_excludes_zero": excl,
                    "holds": bool(_REQUIREMENTS[require](mean, excl)),
                    "status": "evaluated",
                })
        return {
            "id": clause["id"], "a": a, "b": b, "require": require,
            "statistic": statistic, "holds": all(r["holds"] for r in rows),
            "n_splits": len(rows), "n_holding": sum(r["holds"] for r in rows),
            "splits": rows,
        }

    variants = {}
    for variant in rule["variants"]:
        clauses = [check(c, variant) for c in rule["clauses"]]
        variants[variant] = {
            "promoted_to_candidate": all(c["holds"] for c in clauses),
            "clauses": clauses,
        }
    reading = []
    for clause in rule.get("reading_clauses") or []:
        templated = "{V}" in clause["a"] or "{V}" in clause["b"]
        for variant in (rule["variants"] if templated else [None]):
            result = check(clause, variant)
            result["variant"] = variant
            reading.append(result)
    return {
        "rule_fixed_before_the_run": bool(rule.get("fixed_before_the_run")),
        "owner_confirmed": bool(rule.get("owner_confirmed")),
        "protocol": protocol,
        "statistic": statistic,
        "variants": variants,
        "any_promoted_to_candidate": any(v["promoted_to_candidate"] for v in variants.values()),
        "reading_clauses": reading,
        "winner_declared": False,
        "promoted_means": rule.get("promoted_means"),
    }
