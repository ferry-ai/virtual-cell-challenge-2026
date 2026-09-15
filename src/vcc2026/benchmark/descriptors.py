"""Context and target descriptors with an explicit provenance record.

Allowed here: NTC / control profiles of any context, including the query
context (the VCC task ships unperturbed cells of A/B/C). Forbidden for the
unseen-target protocol: any feature derived from that target's perturbative
responses, including public-dataset responses of the same target.

With a single training context the context vector does not vary in training,
so a with-context vs without-context comparison cannot identify a context
effect. The builder records that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vcc2026.genes import official_axis
from vcc2026.pseudobulk import PseudobulkFile
from vcc2026.signatures import SignatureSet

from .factorization import FactorizationSpec, factorize
from .protocol import FeatureSpec
from .universe import GeneUniverse

__all__ = [
    "ControlProfile",
    "DescriptorBank",
    "GoSlimTable",
    "extract_control_profile",
    "high_expr_indices",
    "load_go_slim_table",
]


@dataclass
class ControlProfile:
    """Basal profile of one context, from its own NTCs, on the official axis."""

    context: str
    source_id: str
    log1p_cpm: np.ndarray
    observed: np.ndarray
    n_cells: float
    library: float
    provenance: str

    def as_dict(self) -> dict:
        return {
            "context": self.context,
            "source_id": self.source_id,
            "n_cells": self.n_cells,
            "library": self.library,
            "n_genes_observed": int(self.observed.sum()),
            "provenance": self.provenance,
        }


def extract_control_profile(
    pf: PseudobulkFile, *, control: str = "non-targeting"
) -> ControlProfile:
    """Cell-weighted control profile, log1p CPM, aligned to the official axis."""
    from vcc2026.genes import align_to_axis
    from vcc2026.pseudobulk import NTC_SYMBOL, _read_categorical, parse_gene_transcript
    import h5py

    axis = official_axis()
    with h5py.File(pf.path, "r") as f:
        labels = _read_categorical(f["obs"], "gene_transcript")
        symbol, _, _ = parse_gene_transcript(labels)
        ncf = f["obs/num_cells_filtered"][:].astype(np.float64)
        core = f["obs/core_control"][:]
        gene_names = np.asarray(_read_categorical(f["var"], "gene_name"), dtype=str)
        is_ntc = symbol == NTC_SYMBOL
        has_cells = np.isfinite(ncf) & (ncf > 0)
        ctrl_rows = np.flatnonzero(
            (is_ntc & core & has_cells) if control == "core_control"
            else (is_ntc & has_cells)
        )
        if ctrl_rows.size == 0:
            raise ValueError(f"{pf.path}: no usable NTC rows")
        counts = np.zeros(len(gene_names), dtype=np.float64)
        cells = 0.0
        block = 256
        for lo in range(0, ctrl_rows.size, block):
            idx = ctrl_rows[lo : lo + block]
            chunk = f["X"][int(idx.min()) : int(idx.max()) + 1, :].astype(np.float64)
            chunk = chunk[idx - idx.min(), :]
            counts += (chunk * ncf[idx][:, None]).sum(axis=0)
            cells += float(ncf[idx].sum())
    lib = float(counts.sum())
    aligned = align_to_axis(
        counts[None, :], gene_names, ["control"], duplicate_policy="sum", axis=axis
    )
    cpm = np.zeros(len(axis), dtype=np.float64)
    cpm[aligned.observed] = 1e6 * aligned.values[0, aligned.observed] / lib
    return ControlProfile(
        context=pf.context,
        source_id=pf.source_id,
        log1p_cpm=np.log1p(cpm),
        observed=aligned.observed.copy(),
        n_cells=cells,
        library=lib,
        provenance=(
            f"NTC rows of {pf.source_id} ({control}), cell-weighted mean, "
            "log1p CPM on the official axis. Query-context NTCs are allowed "
            "inputs under the VCC task and are given to every arm."
        ),
    )


def high_expr_indices(profile: ControlProfile, universe: GeneUniverse, n: int) -> np.ndarray:
    """Indices *within the universe* of the n most abundant basal genes.

    Selected from a training-context NTC, never from a response, never from
    the test context's ranking (the same indices are reused at test time).
    """
    return high_expr_indices_from_values(profile.log1p_cpm, universe, n)


def high_expr_indices_from_values(
    log1p_cpm: np.ndarray, universe: GeneUniverse, n: int
) -> np.ndarray:
    """Same selection, from an already-combined basal vector.

    With more than one training context the ranking comes from their mean, so
    no single training context decides which genes the descriptor watches. With
    one context the mean is that context and the result is unchanged.
    """
    values = np.asarray(log1p_cpm, dtype=np.float64)[universe.observed]
    n = min(int(n), values.size)
    # Stable: np.argpartition then sort those by value descending, then index.
    part = np.argpartition(-values, n - 1)[:n]
    order = part[np.argsort(-values[part], kind="mergesort")]
    return np.asarray(order, dtype=np.int64)


@dataclass
class DescriptorBank:
    """Fitted on training NTCs and training responses; applied to query NTCs."""

    universe: GeneUniverse
    context_profiles: dict[str, ControlProfile]
    train_contexts: tuple[str, ...]
    high_expr: np.ndarray
    target_index: dict[str, int]
    codes_by_target: dict[str, np.ndarray]
    code_dim: int
    include_context: bool
    include_response_codes: bool
    specs: tuple[FeatureSpec, ...] = field(default_factory=tuple)
    names: tuple[str, ...] = field(default_factory=tuple)
    go_slim: "GoSlimTable | None" = None
    include_go_slim: bool = False

    @property
    def go_dim(self) -> int:
        """140 bits + one missing indicator, or nothing at all."""
        if not (self.include_go_slim and self.go_slim is not None):
            return 0
        return self.go_slim.n_terms + 1

    def _go_vector(self, target: str) -> np.ndarray:
        return self.go_slim.vector(target)

    def n_unique_context_vectors(self) -> int:
        keys = [c for c in self.train_contexts if c in self.context_profiles]
        if len(keys) <= 1:
            return len(keys)
        mats = np.vstack([self._context_vector(c) for c in keys])
        # Distinct rows at a coarse tolerance: one training context → one vector.
        uniq = np.unique(np.round(mats, 6), axis=0)
        return int(uniq.shape[0])

    def _context_vector(self, context: str) -> np.ndarray:
        prof = self.context_profiles[context]
        uni = prof.log1p_cpm[self.universe.observed]
        stats = np.array(
            [
                float(np.mean(uni)),
                float(np.std(uni)),
                float(np.log1p(prof.library)),
                float(np.log1p(prof.n_cells)),
                float(np.mean(uni > np.log1p(1.0))),
            ],
            dtype=np.float64,
        )
        high = uni[self.high_expr]
        return np.concatenate([stats, high])

    def _basal_of_target(self, target: str, context: str) -> np.ndarray:
        axis_pos = official_axis().position()
        idx = axis_pos.get(target, -1)
        prof = self.context_profiles[context]
        if idx < 0 or not prof.observed[idx]:
            return np.array([0.0, 0.0], dtype=np.float64)
        return np.array([prof.log1p_cpm[idx], 1.0], dtype=np.float64)

    def build_specs(self) -> None:
        specs: list[FeatureSpec] = []
        if self.include_context:
            for name in ("ctx_mean", "ctx_std", "ctx_log_library",
                         "ctx_log_n_cells", "ctx_frac_detected"):
                specs.append(FeatureSpec(
                    name, "query_or_train_NTC_stats", False, True, True
                ))
            for i in range(len(self.high_expr)):
                specs.append(FeatureSpec(
                    f"ctx_high_expr_{i}",
                    "train_NTC_high_expression_genes_applied_to_query_NTC",
                    False, True, True,
                ))
        for ctx in self.train_contexts:
            specs.append(FeatureSpec(
                f"target_basal_{ctx}",
                f"NTC basal of the target gene in {ctx}",
                False, ctx not in self.train_contexts, True,
            ))
            specs.append(FeatureSpec(
                f"target_basal_{ctx}_measured",
                "indicator that the target gene is measured in that NTC",
                False, False, True,
            ))
        specs.append(FeatureSpec(
            "target_basal_query",
            "NTC basal of the target gene in the query context",
            False, True, True,
        ))
        specs.append(FeatureSpec(
            "target_basal_query_measured",
            "indicator that the target gene is measured in the query NTC",
            False, True, True,
        ))
        if self.include_go_slim and self.go_slim is not None:
            provenance = self.go_slim.provenance
            for term in self.go_slim.terms:
                specs.append(FeatureSpec(
                    f"go_slim_{term.replace(':', '')}", provenance,
                    # Curated annotation, not a response: legal for a target
                    # excluded from every training response.
                    False, False, True,
                ))
            specs.append(FeatureSpec(
                "go_slim_missing",
                "1 when the ancestral closure never meets the slim, or the symbol "
                "does not resolve to a single HGNC gene",
                False, False, True,
            ))
        if self.include_response_codes:
            for i in range(self.code_dim):
                specs.append(FeatureSpec(
                    f"train_response_code_{i}",
                    "SVD codes of this target's training-context response",
                    True, False, False,
                ))
        self.specs = tuple(specs)
        self.names = tuple(s.name for s in specs)

    def transform(
        self,
        targets,
        query_context: str,
        *,
        allow_response_codes: bool,
    ) -> np.ndarray:
        rows = []
        for target in targets:
            parts = []
            if self.include_context:
                parts.append(self._context_vector(query_context))
            for ctx in self.train_contexts:
                parts.append(self._basal_of_target(target, ctx))
            parts.append(self._basal_of_target(target, query_context))
            if self.go_dim:
                parts.append(self._go_vector(target))
            if self.include_response_codes:
                if allow_response_codes and target in self.codes_by_target:
                    parts.append(self.codes_by_target[target])
                else:
                    parts.append(np.zeros(self.code_dim, dtype=np.float64))
            rows.append(np.concatenate(parts))
        return np.vstack(rows) if rows else np.zeros((0, len(self.names)))

    def transform_rows(self, pairs, *, allow_response_codes: bool) -> np.ndarray:
        """One row per (target, context) pair, for training on several contexts.

        `transform` gives every row the same context, which is right when the
        training side is one context and wrong when it is two: the context block
        would be a constant column and the model could not tell the contexts
        apart even in principle. Here each row carries its own context.
        """
        rows = []
        for target, context in pairs:
            parts = []
            if self.include_context:
                parts.append(self._context_vector(context))
            for ctx in self.train_contexts:
                parts.append(self._basal_of_target(target, ctx))
            parts.append(self._basal_of_target(target, context))
            if self.go_dim:
                parts.append(self._go_vector(target))
            if self.include_response_codes:
                if allow_response_codes and target in self.codes_by_target:
                    parts.append(self.codes_by_target[target])
                else:
                    parts.append(np.zeros(self.code_dim, dtype=np.float64))
            rows.append(np.concatenate(parts))
        return np.vstack(rows) if rows else np.zeros((0, len(self.names)))

    def as_dict(self) -> dict:
        return {
            "train_contexts": list(self.train_contexts),
            "include_context": self.include_context,
            "include_response_codes": self.include_response_codes,
            "code_dim": self.code_dim,
            "n_unique_context_vectors_in_training": self.n_unique_context_vectors(),
            "context_dependence_identifiable": self.n_unique_context_vectors() >= 2,
            "n_features": len(self.names),
            "feature_names": list(self.names),
            "feature_provenance": [
                {
                    "name": s.name,
                    "provenance": s.provenance,
                    "derived_from_perturbative_response": s.derived_from_perturbative_response,
                    "uses_query_ntc": s.uses_query_ntc,
                    "allowed_in_unseen_target": s.allowed_in_unseen_target,
                }
                for s in self.specs
            ],
            "go_slim": (self.go_slim.as_dict() if (self.include_go_slim and self.go_slim)
                        else None),
            "ntc_of_query_context": "allowed_declared_shared_across_arms",
            "high_expr_n": int(len(self.high_expr)),
            "profiles": {k: v.as_dict() for k, v in self.context_profiles.items()},
        }


def fit_descriptor_bank(
    *,
    universe: GeneUniverse,
    profiles: dict[str, ControlProfile],
    train_sigs: SignatureSet,
    codes_by_target: dict[str, np.ndarray] | None,
    include_context: bool,
    include_response_codes: bool,
    n_high_expr: int,
    train_context: str | None = None,
    train_contexts: tuple[str, ...] | None = None,
    go_slim: "GoSlimTable | None" = None,
    include_go_slim: bool = False,
) -> DescriptorBank:
    """Fit the bank on one or more training contexts.

    `train_contexts` is what makes the context descriptor a variable rather than
    a constant: with one training context every row carries the same context
    vector, so nothing can be learned from it and `n_unique_context_vectors()`
    returns 1. The single-context call is kept exactly as it was, so an earlier
    run reproduces.
    """
    if train_contexts is None:
        if train_context is None:
            raise ValueError("give train_context or train_contexts")
        train_contexts = (train_context,)
    train_contexts = tuple(dict.fromkeys(train_contexts))
    missing = [c for c in train_contexts if c not in profiles]
    if missing:
        raise ValueError(f"no NTC profile for training context(s) {missing}")
    basal = np.mean(
        np.vstack([profiles[c].log1p_cpm for c in train_contexts]), axis=0
    )
    high = high_expr_indices_from_values(basal, universe, n_high_expr)
    axis_pos = official_axis().position()
    code_dim = 0
    codes = codes_by_target or {}
    if codes:
        code_dim = len(next(iter(codes.values())))
    elif include_response_codes:
        raise ValueError("include_response_codes=True but no codes were provided")
    bank = DescriptorBank(
        universe=universe,
        context_profiles=profiles,
        train_contexts=train_contexts,
        high_expr=high,
        target_index=axis_pos,
        codes_by_target={k: np.asarray(v, dtype=np.float64) for k, v in codes.items()},
        code_dim=code_dim if include_response_codes else 0,
        include_context=include_context,
        include_response_codes=include_response_codes and code_dim > 0,
        go_slim=go_slim,
        include_go_slim=bool(include_go_slim and go_slim is not None),
    )
    bank.build_specs()
    return bank


def svd_codes(
    Y: np.ndarray,
    universe: GeneUniverse,
    rank: int,
    spec: FactorizationSpec | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Y is already restricted to the universe. Returns (codes, basis, singular_values).

    Centring stays here, not inside ``factorize``: the codes of an uncentred
    matrix would be a different descriptor.
    """
    from .universe import assert_no_zero_fill

    assert_no_zero_fill(universe, Y)
    if Y.shape[0] < 2:
        raise ValueError("need at least two training rows for an SVD")
    k = max(1, min(int(rank), min(Y.shape) - 1))
    # Center genes so the first component is not the mean response.
    mean = Y.mean(axis=0, keepdims=True)
    Yc = Y - mean
    fac = factorize(Yc, k, spec or FactorizationSpec())
    codes = Yc @ fac.Vt.T
    return codes, fac.Vt, fac.S


def load_control_profile_npz(path) -> ControlProfile:
    """Read a basal profile written by scripts/55_control_profile.py.

    Same object as `extract_control_profile` returns, for a source whose file is
    not a Replogle-style pseudobulk. The benchmark then needs no second reader.
    """
    from pathlib import Path as _Path

    with np.load(_Path(path), allow_pickle=False) as handle:
        return ControlProfile(
            context=str(handle["context"]),
            source_id=str(handle["source_id"]),
            log1p_cpm=np.asarray(handle["log1p_cpm"], dtype=np.float64),
            observed=np.asarray(handle["observed"], dtype=bool),
            n_cells=float(handle["n_cells"]),
            library=float(handle["library"]),
            provenance=str(handle["provenance"]),
        )


@dataclass
class GoSlimTable:
    """Frozen `symbol -> 140 GO slim bits + missing` lookup (scripts/58).

    Curated annotation, read without ever touching a perturbation response, so
    it is legal for a target excluded from every training response. Two things
    it is not: it is not a learned embedding, and it is not evidence that the
    annotation helps -- that is what the permuted control arm is for.

    `permutation_seed` builds the control: the bit vectors are shuffled among
    the symbols, once, with that seed. The same permutation therefore applies at
    fit and at inference, which is the only way the arm answers «does the
    gene-to-annotation link matter» instead of «do 140 extra columns matter».
    """

    symbols: tuple[str, ...]
    bits: np.ndarray                 # (n_symbols, n_terms) bool
    missing: np.ndarray              # (n_symbols,) bool
    terms: tuple[str, ...]
    source: str = ""
    permutation_seed: int | None = None
    _index: dict = field(default_factory=dict, repr=False)
    _order: np.ndarray | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._index = {s: i for i, s in enumerate(self.symbols)}
        if self.permutation_seed is not None:
            rng = np.random.default_rng(int(self.permutation_seed))
            self._order = rng.permutation(len(self.symbols))
        else:
            self._order = None

    @property
    def n_terms(self) -> int:
        return len(self.terms)

    @property
    def permuted(self) -> bool:
        return self._order is not None

    def vector(self, symbol: str) -> np.ndarray:
        """(n_terms + 1,) float: the bits, then the missing indicator.

        A symbol absent from the table is `missing = 1` with zero bits -- the
        same encoding as a symbol whose closure never meets the slim, because
        downstream the two mean the same thing: no annotation to use.
        """
        i = self._index.get(symbol)
        if i is None:
            out = np.zeros(self.n_terms + 1, dtype=np.float64)
            out[self.n_terms] = 1.0
            return out
        j = int(self._order[i]) if self._order is not None else i
        out = np.empty(self.n_terms + 1, dtype=np.float64)
        out[: self.n_terms] = self.bits[j]
        out[self.n_terms] = float(self.missing[j])
        return out

    def as_dict(self) -> dict:
        return {
            "n_symbols": len(self.symbols),
            "n_terms": self.n_terms,
            "n_missing": int(self.missing.sum()),
            "source": self.source,
            "permuted": self.permuted,
            "permutation_seed": self.permutation_seed,
            "provenance": self.provenance,
        }

    @property
    def provenance(self) -> str:
        base = ("GO slim bit, GAF -> ancestral closure (is_a/part_of) -> "
                "goslim_generic; curated annotation, no perturbation response")
        return base + (" [PERMUTED CONTROL: bits shuffled among symbols]"
                       if self.permuted else "")


def load_go_slim_table(path, *, permutation_seed: int | None = None) -> GoSlimTable:
    """Read the frozen table written by scripts/58_build_go_slim_table.py."""
    from pathlib import Path as _Path

    path = _Path(path)
    with np.load(path, allow_pickle=True) as handle:
        return GoSlimTable(
            symbols=tuple(str(s) for s in handle["symbols"]),
            bits=np.asarray(handle["bits"], dtype=bool),
            missing=np.asarray(handle["missing"], dtype=bool),
            terms=tuple(str(t) for t in handle["slim_terms"]),
            source=str(path),
            permutation_seed=permutation_seed,
        )
