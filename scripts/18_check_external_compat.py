"""Ask the same questions of every candidate external dataset, once, cheaply.

Every dataset we consider adopting has to answer an identical list: does it live
on our gene axis, does it perturb any of our 300 targets, is X raw single-cell
counts, are there non-targeting controls and under what label, and are there
enough cells per perturbation to estimate a fold change. Answering that by hand
per dataset is slow and, worse, inconsistent between datasets.

So the acceptance contract is derived once from the data we actually hold
(raw/controls: the 18,533-symbol gene axis, the 300 targets, and the three NTC
control matrices), cached under reports/external_compat/contract.json, and then
every candidate is scored against it.

Contract derivation also measures the NTC-guide structure. The challenge gives
46 NTC guide IDs per context. Whether those 46 behave as exchangeable replicates
or carry a systematic per-guide shift decides how much batch structure an
external dataset must carry to be comparable, so it is measured rather than
assumed: per-guide pseudobulk profiles are compared against a label-permutation
null that preserves group sizes exactly.

Read-only on all sources. Never asserts that a field exists without having read
it; a field it cannot find is reported as absent, not guessed.

    scripts/py.cmd scripts/18_check_external_compat.py                    # contract only
    scripts/py.cmd scripts/18_check_external_compat.py PATH.h5ad [...]    # check files
    scripts/py.cmd scripts/18_check_external_compat.py --refresh-contract
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from anndata.io import read_elem
from scipy import sparse

QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)

#: obs columns that plausibly name the perturbed gene. Candidacy is only a
#: shortlist; the column is chosen by measured overlap with our gene axis, never
#: by its name alone.
PERT_COL_CANDIDATES = (
    "target_gene", "gene_target", "target", "targets", "gene", "gene_symbol",
    "gene_name", "perturbation", "perturbation_name", "pert", "pert_name",
    "pert_target", "knockdown", "kd_gene", "guide_target", "sgrna_target",
    "grna_target", "condition", "treatment", "label", "gene_id", "guide_identity",
    "perturbed_gene", "crispr_target", "feature_call", "gene_call",
)

#: Labels that mark a non-targeting / control arm. Matched case-insensitively
#: against the levels of the chosen perturbation column.
NTC_PATTERNS = (
    r"non[-_ ]?targeting", r"nontargeting", r"^ntc", r"_ntc", r"^nt$", r"^nt[-_]",
    r"control", r"^ctrl", r"scramble", r"scrambled", r"safe[-_ ]?harbor",
    r"^neg([-_ ]|$)", r"negative", r"no[-_ ]?guide", r"unperturbed", r"untreated",
    r"^none$", r"^random", r"^olfr", r"^luciferase", r"^gal4", r"^lacz",
)

#: obs columns whose presence is evidence the rows are aggregates, not cells.
PSEUDOBULK_OBS_HINTS = (
    "num_cells_filtered", "num_cells_unfiltered", "n_cells", "ncells",
    "num_cells", "cell_count", "n_cells_filtered",
)

ENSG_RE = re.compile(r"^ENSG\d{6,}")
SYMBOL_COLS = ("gene_name", "gene_symbol", "symbol", "gene_symbols", "gene_names",
               "feature_name", "gene_short_name", "names", "symbols", "hgnc_symbol")
ENSG_COLS = ("gene_id", "gene_ids", "ensembl_id", "ensembl_gene_id", "ensembl",
             "ensembl_ids", "feature_id", "gene_ensembl_id", "ensg")


# --------------------------------------------------------------------------- #
# matrix access
# --------------------------------------------------------------------------- #
class MatrixView:
    """Row-chunked read access to an .h5ad matrix node, sparse or dense.

    anndata's backed mode is avoided on purpose: this has to open files written
    by anndata versions we have never seen, where a failure to open must be
    reported rather than raised.
    """

    #: CSC has to be materialised before rows can be taken; refuse above this.
    CSC_NNZ_CAP = 60_000_000

    def __init__(self, node: h5py.Group | h5py.Dataset, name: str):
        self.name = name
        enc = str(node.attrs.get("encoding-type", ""))
        self._csr = None
        if isinstance(node, h5py.Dataset):
            if node.ndim != 2:
                raise ValueError(f"{name}: dense node is {node.ndim}-dimensional")
            self.kind, self.shape, self._node = "dense", tuple(node.shape), node
            self.nnz = None
        elif enc in ("csr_matrix", "csc_matrix"):
            self.kind = enc.split("_")[0]
            self.shape = tuple(int(v) for v in node.attrs["shape"])
            self._node = node
            self.nnz = int(node["data"].shape[0])
            if self.kind == "csr":
                self._indptr = node["indptr"][:]
            else:
                if self.nnz > self.CSC_NNZ_CAP:
                    raise ValueError(f"{name}: CSC with {self.nnz} nonzeros exceeds cap")
                self._csr = sparse.csc_matrix(
                    (node["data"][:], node["indices"][:], node["indptr"][:]),
                    shape=self.shape).tocsr()
        else:
            raise ValueError(f"{name}: unsupported encoding {enc!r}")

    @property
    def n_obs(self) -> int:
        return int(self.shape[0])

    @property
    def n_vars(self) -> int:
        return int(self.shape[1])

    def chunk(self, start: int, stop: int) -> sparse.csr_matrix:
        stop = min(stop, self.n_obs)
        if self.kind == "dense":
            return sparse.csr_matrix(np.asarray(self._node[start:stop], dtype=np.float64))
        if self.kind == "csc":
            return sparse.csr_matrix(self._csr[start:stop], dtype=np.float64)
        p0, p1 = int(self._indptr[start]), int(self._indptr[stop])
        return sparse.csr_matrix(
            (np.asarray(self._node["data"][p0:p1], dtype=np.float64),
             self._node["indices"][p0:p1],
             self._indptr[start:stop + 1] - p0),
            shape=(stop - start, self.n_vars))


def row_blocks(n_obs: int, max_rows: int | None, block: int = 4096) -> list[tuple[int, int]]:
    """Contiguous row blocks covering the file, thinned evenly if capped.

    Thinning keeps whole blocks so reads stay contiguous, and spreads them across
    the file so a dataset sorted by batch is not sampled from one batch only.
    """
    blocks = [(s, min(s + block, n_obs)) for s in range(0, n_obs, block)]
    if max_rows is None or n_obs <= max_rows:
        return blocks
    keep = max(1, int(np.ceil(max_rows / block)))
    idx = np.unique(np.linspace(0, len(blocks) - 1, keep).round().astype(int))
    return [blocks[i] for i in idx]


def dist(values) -> dict | None:
    """Quantile summary, or None when there is nothing to summarise."""
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    out = {"n": int(v.size), "mean": float(v.mean())}
    for q, x in zip(QUANTILES, np.quantile(v, QUANTILES)):
        out[f"p{q * 100:g}"] = float(x)
    return out


def scan_matrix(mv: MatrixView, blocks: list[tuple[int, int]]) -> dict:
    """Streaming per-cell and per-gene statistics over the given row blocks.

    mean_cpm is the mean of per-cell CPM, in that order, because that is the
    order the scorer's DE expression gate uses.
    """
    libs, ndet, minv, maxv = [], [], np.inf, -np.inf
    n_vals = n_noninteger = n_negative = 0
    cpm_sum = np.zeros(mv.n_vars, dtype=np.float64)
    gene_det = np.zeros(mv.n_vars, dtype=np.int64)
    n_rows = 0
    for start, stop in blocks:
        x = mv.chunk(start, stop)
        x.eliminate_zeros()
        d = x.data
        if d.size:
            minv, maxv = min(minv, float(d.min())), max(maxv, float(d.max()))
            n_noninteger += int(np.count_nonzero(np.abs(d - np.rint(d)) > 1e-6))
            n_negative += int(np.count_nonzero(d < 0))
            n_vals += int(d.size)
        lib = np.asarray(x.sum(axis=1)).ravel()
        libs.append(lib)
        ndet.append(x.getnnz(axis=1))
        cpm_sum += np.asarray(x.multiply((1e6 / np.maximum(lib, 1e-12))[:, None])
                              .sum(axis=0)).ravel()
        gene_det += x.getnnz(axis=0)
        n_rows += stop - start
    libs = np.concatenate(libs) if libs else np.zeros(0)
    ndet = np.concatenate(ndet) if ndet else np.zeros(0)
    return {
        "rows_scanned": n_rows,
        "library_size": dist(libs),
        "genes_detected_per_cell": dist(ndet),
        "n_rows_with_zero_total": int(np.count_nonzero(libs <= 0)),
        "value_min": None if not np.isfinite(minv) else minv,
        "value_max": None if not np.isfinite(maxv) else maxv,
        "nonzero_values_checked": n_vals,
        "fraction_noninteger": None if n_vals == 0 else n_noninteger / n_vals,
        "fraction_negative": None if n_vals == 0 else n_negative / n_vals,
        "_mean_cpm": cpm_sum / max(n_rows, 1),
        "_gene_det": gene_det,
    }


# --------------------------------------------------------------------------- #
# contract: the gene axis, the targets, the control matrices, the NTC guides
# --------------------------------------------------------------------------- #
def ntc_guide_structure(mv: MatrixView, codes: np.ndarray, n_groups: int,
                        gate: np.ndarray, n_perm: int, seed: int) -> dict:
    """Are the NTC guides exchangeable replicates?

    Per-guide profiles are mean-of-per-cell-CPM, the same order of operations the
    scorer's DE gate uses. The null is the identical statistic computed on
    permuted guide labels, which preserves group sizes exactly, so any excess is
    guide identity and not group-size or sampling noise.
    """
    rng = np.random.default_rng(seed)
    perms = np.stack([rng.permutation(codes) for _ in range(n_perm)]) if n_perm else \
        np.zeros((0, codes.size), dtype=codes.dtype)
    acc = np.zeros((1 + n_perm, n_groups, mv.n_vars), dtype=np.float64)
    counts = np.zeros((1 + n_perm, n_groups), dtype=np.int64)
    lib_sum = np.zeros(n_groups, dtype=np.float64)
    for start, stop in row_blocks(mv.n_obs, None):
        x = mv.chunk(start, stop)
        lib = np.asarray(x.sum(axis=1)).ravel()
        cpm = sparse.csr_matrix(x.multiply((1e6 / np.maximum(lib, 1))[:, None]))
        n = stop - start
        for k in range(1 + n_perm):
            c = codes[start:stop] if k == 0 else perms[k - 1][start:stop]
            g = sparse.csr_matrix((np.ones(n), (c, np.arange(n))), shape=(n_groups, n))
            acc[k] += np.asarray((g @ cpm).todense())
            counts[k] += np.bincount(c, minlength=n_groups)
        np.add.at(lib_sum, codes[start:stop], lib)

    mean_cpm = acc / np.maximum(counts, 1)[:, :, None]          # (1+P, groups, genes)
    overall = np.log1p(acc[0].sum(axis=0) / max(counts[0].sum(), 1))
    lg = np.log1p(mean_cpm[:, :, gate])
    ref = overall[gate]
    rms = np.sqrt(((lg - ref) ** 2).mean(axis=2))                # (1+P, groups)
    real, null = rms[0], rms[1:].ravel()

    # per-gene: does guide identity move a gene beyond the permutation envelope?
    var_between = lg.var(axis=1)                                 # (1+P, gate genes)
    if n_perm:
        exceed = int(np.count_nonzero(var_between[0] > var_between[1:].max(axis=0)))
        expected = float(gate.sum()) / (n_perm + 1)
    else:
        exceed, expected = None, None

    cells = counts[0]
    return {
        "n_guides": int(n_groups),
        "cells_per_guide": dist(cells),
        "cells_per_guide_min": int(cells.min()), "cells_per_guide_max": int(cells.max()),
        "median_library_per_guide": dist(lib_sum / np.maximum(cells, 1)),
        "gate_genes_used": int(gate.sum()),
        "n_permutations": int(n_perm),
        "guide_rms_log1p_shift": {
            "observed_mean": float(real.mean()), "observed_max": float(real.max()),
            "permuted_mean": float(null.mean()) if null.size else None,
            "permuted_max": float(null.max()) if null.size else None,
            "inflation_observed_over_permuted": float(real.mean() / null.mean()) if null.size else None,
            "n_guides_above_permuted_max": int((real > null.max()).sum()) if null.size else None,
        },
        "genes_exceeding_permutation_envelope": exceed,
        "genes_expected_by_chance": expected,
        "_per_guide_rms": real,
        "_cells": cells,
        "_mean_lib": lib_sum / np.maximum(cells, 1),
    }


def derive_contract(data_root: Path, out: Path, n_perm: int, seed: int) -> dict:
    bundle = data_root / "raw/controls"
    genes = pd.read_csv(bundle / "gene_names.csv")["gene_name"].astype(str)
    targets = pd.read_csv(bundle / "pert_counts.csv")["target_gene"].astype(str)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    contract = {
        "source": str(bundle),
        "gene_axis": {
            "n_genes": int(genes.size),
            "n_unique": int(genes.nunique()),
            "n_duplicated": int(genes.duplicated().sum()),
            "order": "Ensembl gene ID (verified previously); the file carries symbols only",
            "carries_ensembl_ids": False,
            "first": genes.iloc[:3].tolist(), "last": genes.iloc[-3:].tolist(),
        },
        "targets": {"n": int(targets.nunique()),
                    "n_on_gene_axis": int(targets.isin(set(genes)).sum())},
        "manifest": manifest,
        "contexts": {},
        "ntc_guides": {},
    }
    gene_set = set(genes)
    guide_rows = []
    for ctx in ("A", "B", "C"):
        path = bundle / f"context_{ctx}.h5ad"
        with h5py.File(path, "r") as f:
            var = read_elem(f["var"])
            obs = read_elem(f["obs"])
            if not np.array_equal(np.asarray(var.index, dtype=str), genes.to_numpy()):
                raise ValueError(f"context_{ctx}: var index does not match gene_names.csv")
            mv = MatrixView(f["X"], f"context_{ctx}:X")
            stats = scan_matrix(mv, row_blocks(mv.n_obs, None))
            gate = stats["_mean_cpm"] > 5

            ctx_entry = {
                "path": str(path), "n_cells": mv.n_obs, "n_genes": mv.n_vars,
                "matrix_encoding": mv.kind, "nnz": mv.nnz,
                "library_size": stats["library_size"],
                "genes_detected_per_cell": stats["genes_detected_per_cell"],
                "value_min": stats["value_min"], "value_max": stats["value_max"],
                "fraction_noninteger": stats["fraction_noninteger"],
                "de_gate_genes_cpm_gt_5": int(gate.sum()),
                "obs_columns": list(obs.columns),
                "target_gene_levels": sorted(set(obs["target_gene"].astype(str)))
                                      if "target_gene" in obs else None,
            }
            contract["contexts"][ctx] = ctx_entry

            if "ntc_id" not in obs.columns:
                contract["ntc_guides"][ctx] = {"error": "obs['ntc_id'] absent"}
                continue
            cat = pd.Categorical(obs["ntc_id"].astype(str))
            g = ntc_guide_structure(mv, cat.codes.astype(np.int64), len(cat.categories),
                                    gate, n_perm, seed)
            levels = list(cat.categories)
            for i, name in enumerate(levels):
                guide_rows.append({"context": ctx, "ntc_id": name,
                                   "n_cells": int(g["_cells"][i]),
                                   "mean_library_size": float(g["_mean_lib"][i]),
                                   "rms_log1p_shift": float(g["_per_guide_rms"][i])})
            g["levels_preview"] = levels[:5]
            contract["ntc_guides"][ctx] = {k: v for k, v in g.items() if not k.startswith("_")}
            contract["contexts"][ctx]["ntc_levels"] = levels

    sets = [set(contract["contexts"][c].get("ntc_levels") or []) for c in "ABC"]
    contract["ntc_guides"]["levels_shared_across_contexts"] = (
        len(set.intersection(*sets)) if all(sets) else None)
    contract["ntc_guides"]["levels_union_across_contexts"] = (
        len(set.union(*sets)) if all(sets) else None)

    ref_lib = [contract["contexts"][c]["library_size"]["p50"] for c in "ABC"]
    # The axes themselves stay in their CSVs rather than being copied into the
    # report; the contract records where to read them so it cannot drift.
    contract["acceptance"] = {
        "gene_names_csv": str(bundle / "gene_names.csv"),
        "pert_counts_csv": str(bundle / "pert_counts.csv"),
        "reference_median_library_size": float(np.median(ref_lib)),
        "reference_median_genes_detected": float(np.median(
            [contract["contexts"][c]["genes_detected_per_cell"]["p50"] for c in "ABC"])),
        "cells_per_perturbation_required": manifest.get("cells_per_pert"),
    }
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(guide_rows).to_csv(out / "ntc_guide_structure.csv", index=False)
    (out / "contract.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")
    return contract


# --------------------------------------------------------------------------- #
# external file check
# --------------------------------------------------------------------------- #
def frame_or_none(f: h5py.File, key: str) -> tuple[pd.DataFrame | None, str | None]:
    if key not in f:
        return None, f"{key}/ absent"
    try:
        df = read_elem(f[key])
    except Exception as exc:  # a file written by a version we do not know
        return None, f"{key}/ unreadable: {type(exc).__name__}: {exc}"
    if not isinstance(df, pd.DataFrame):
        return None, f"{key}/ is {type(df).__name__}, not a DataFrame"
    return df, None


def strip_version(v: np.ndarray) -> np.ndarray:
    return np.array([s.split(".")[0] for s in v], dtype=object)


def gene_axis(var: pd.DataFrame | None, gene_set: set[str]) -> dict:
    """Locate symbols and Ensembl IDs on the var axis without assuming either."""
    out: dict = {"n_vars": None if var is None else int(var.shape[0]),
                 "var_columns": [] if var is None else list(var.columns),
                 "symbol_source": None, "ensembl_source": None,
                 "overlap_by_symbol": None, "overlap_by_symbol_uppercased": None,
                 "n_ensembl_ids": None, "notes": []}
    if var is None:
        out["notes"].append("var absent; gene space cannot be compared")
        return out

    def as_str(s) -> np.ndarray:
        return np.asarray(pd.Series(s).astype(str).to_numpy(), dtype=object)

    idx = as_str(var.index)
    cols = {c.lower(): c for c in var.columns}
    ensg_frac_idx = float(np.mean([bool(ENSG_RE.match(s)) for s in idx])) if idx.size else 0.0

    symbols = ens = None
    if ensg_frac_idx < 0.5:
        symbols, out["symbol_source"] = idx, "var index"
    else:
        ens, out["ensembl_source"] = idx, "var index"
    for name in SYMBOL_COLS:
        if symbols is None and name in cols:
            symbols, out["symbol_source"] = as_str(var[cols[name]]), f"var['{cols[name]}']"
    for name in ENSG_COLS:
        if ens is None and name in cols:
            cand = as_str(var[cols[name]])
            if cand.size and np.mean([bool(ENSG_RE.match(s)) for s in cand]) > 0.5:
                ens, out["ensembl_source"] = cand, f"var['{cols[name]}']"

    if symbols is not None:
        s = set(symbols.tolist())
        out["overlap_by_symbol"] = int(len(s & gene_set))
        out["overlap_by_symbol_uppercased"] = int(
            len({x.upper() for x in s} & {x.upper() for x in gene_set}))
        out["fraction_of_our_axis_covered"] = round(len(s & gene_set) / len(gene_set), 4)
        out["n_duplicate_symbols"] = int(symbols.size - len(s))
    else:
        out["notes"].append("no symbol axis found among var index or "
                            + ", ".join(SYMBOL_COLS))
    if ens is not None:
        out["n_ensembl_ids"] = int(len(set(strip_version(ens).tolist())))
        out["notes"].append(
            "Ensembl IDs present, but gene_names.csv carries symbols only, so "
            "ID-level matching against our axis is not possible here; overlap is "
            "reported by symbol.")
    else:
        out["notes"].append("no Ensembl ID axis found; comparison is by symbol only")
    return out


def perturbation_field(obs: pd.DataFrame | None, index_values: np.ndarray | None,
                       gene_set: set[str], targets: set[str]) -> dict:
    """Pick the perturbation column by measured overlap, and report the runners-up.

    Every candidate's score is reported so a wrong pick is visible rather than
    silent; if nothing scores, the answer is "not found", not a guess.
    """
    out: dict = {"chosen": None, "chosen_source": None, "candidates": [],
                 "notes": []}
    if obs is None and index_values is None:
        out["notes"].append("obs absent; no perturbation labels available")
        return out

    fields: list[tuple[str, np.ndarray]] = []
    if obs is not None:
        for c in obs.columns:
            s = obs[c]
            if not (isinstance(s.dtype, pd.CategoricalDtype)
                    or s.dtype == object or str(s.dtype).startswith("str")):
                continue
            v = np.asarray(s.astype(str).to_numpy(), dtype=object)
            if len(set(v.tolist())) > 50_000:
                out["notes"].append(f"obs['{c}'] skipped: more than 50,000 distinct "
                                    "values, so it is an identifier, not a label")
                continue
            fields.append((f"obs['{c}']", v))
    if index_values is not None and index_values.size:
        fields.append(("obs index", index_values))
        # Replogle-style "0_GENE_P1P2_ENSG..." identifiers: try the tokens too.
        tok = np.array(["|".join(t for t in str(s).split("_") if t in gene_set) or str(s)
                        for s in index_values], dtype=object)
        if np.mean([t in gene_set for t in tok]) > 0.2:
            fields.append(("obs index (underscore token in our gene axis)", tok))

    for name, v in fields:
        levels = sorted(set(v.tolist()))
        hits = sum(1 for lv in levels if lv in targets)
        sym = sum(1 for lv in levels if lv in gene_set)
        ntc = [lv for lv in levels if any(re.search(p, lv, re.I) for p in NTC_PATTERNS)]
        score = (hits, sym / max(len(levels), 1))
        out["candidates"].append({
            "field": name, "n_levels": len(levels),
            "levels_that_are_our_targets": hits,
            "levels_on_our_gene_axis": sym,
            "fraction_of_levels_on_our_gene_axis": round(sym / max(len(levels), 1), 4),
            "control_like_levels": ntc[:12],
            "n_control_like_levels": len(ntc),
            "_score": score,
        })
    ranked = sorted(out["candidates"], key=lambda d: d["_score"], reverse=True)
    for d in ranked:
        del d["_score"]
    out["candidates"] = ranked
    best = ranked[0] if ranked else None
    if best is None or (best["levels_that_are_our_targets"] == 0
                        and best["fraction_of_levels_on_our_gene_axis"] < 0.2):
        out["notes"].append(
            "no obs field's levels look like perturbed gene symbols; this file "
            "may not be a perturbation screen, or it may use an identifier "
            "vocabulary we do not share")
        return out
    out["chosen"] = best["field"]
    out["chosen_source"] = "highest count of our 300 targets, then fraction of levels on our gene axis"
    values = dict(fields)[best["field"]]
    out["_values"] = values
    return out


def load_axes(contract: dict) -> tuple[set[str], set[str]]:
    """The gene axis and the 300 targets, read from the CSVs the contract names."""
    a = contract["acceptance"]
    genes = pd.read_csv(a["gene_names_csv"])["gene_name"].astype(str)
    targets = pd.read_csv(a["pert_counts_csv"])["target_gene"].astype(str)
    return set(genes), set(targets)


def check_external(path: Path, contract: dict, max_cells: int,
                   gene_set: set[str], targets: set[str]) -> dict:
    rep: dict = {"path": str(path), "file_size_bytes": path.stat().st_size,
                 "errors": [], "warnings": []}
    with h5py.File(path, "r") as f:
        obs, obs_err = frame_or_none(f, "obs")
        var, var_err = frame_or_none(f, "var")
        for e in (obs_err, var_err):
            if e:
                rep["errors"].append(e)
        rep["obs_columns"] = [] if obs is None else list(obs.columns)
        rep["has_raw_slot"] = "raw" in f
        rep["layers"] = list(f["layers"].keys()) if "layers" in f else []
        rep["obsm"] = list(f["obsm"].keys()) if "obsm" in f else []

        rep["gene_space"] = gene_axis(var, gene_set)

        idx_vals = None if obs is None else np.asarray(obs.index.astype(str).to_numpy(), dtype=object)
        pert = perturbation_field(obs, idx_vals, gene_set, targets)
        pert_values = pert.pop("_values", None)
        rep["perturbation_field"] = pert

        # --- X -------------------------------------------------------------
        mv = None
        if "X" not in f:
            rep["errors"].append("X absent")
        else:
            try:
                mv = MatrixView(f["X"], "X")
            except Exception as exc:
                rep["errors"].append(f"X unreadable: {type(exc).__name__}: {exc}")
        if mv is not None:
            blocks = row_blocks(mv.n_obs, max_cells)
            s = scan_matrix(mv, blocks)
            rep["matrix"] = {
                "shape": [mv.n_obs, mv.n_vars], "encoding": mv.kind, "nnz": mv.nnz,
                **{k: v for k, v in s.items() if not k.startswith("_")},
            }
            ref = contract["acceptance"]
            lib = s["library_size"]
            rep["matrix"]["median_library_vs_ours"] = (
                None if lib is None else round(lib["p50"] / ref["reference_median_library_size"], 4))
            det = s["genes_detected_per_cell"]
            rep["matrix"]["median_detection_vs_ours"] = (
                None if det is None else round(det["p50"] / ref["reference_median_genes_detected"], 4))
            rep["matrix"]["ours_median_library_size"] = ref["reference_median_library_size"]
            rep["matrix"]["ours_median_genes_detected"] = ref["reference_median_genes_detected"]

        # --- raw counts? ---------------------------------------------------
        reasons = []
        m = rep.get("matrix")
        if m is None:
            is_counts = None
            reasons.append("X could not be read")
        else:
            frac = m["fraction_noninteger"]
            neg = m["fraction_negative"]
            is_counts = bool(frac is not None and frac <= 1e-6 and neg == 0)
            if frac is None:
                reasons.append("matrix has no nonzero values")
            elif frac > 1e-6:
                reasons.append(f"{frac:.1%} of nonzero values are not integers")
            if neg:
                reasons.append(f"{neg:.1%} of nonzero values are negative")
            if is_counts:
                reasons.append("all sampled nonzero values are non-negative integers")
        rep["raw_integer_counts"] = {"verdict": is_counts, "evidence": reasons}
        for name in rep["layers"]:
            if re.search(r"count|raw|umi", name, re.I):
                rep["warnings"].append(
                    f"layers['{name}'] may hold counts even if X does not; not scanned")

        # --- pseudobulk? ---------------------------------------------------
        pb = []
        if obs is not None:
            hit = [c for c in obs.columns if c.lower() in PSEUDOBULK_OBS_HINTS]
            if hit:
                pb.append(f"obs carries aggregate-count columns {hit}")
        if m is not None and m["encoding"] == "dense" and m["shape"][0] < 100_000:
            pb.append("X is dense with few rows")
        if m is not None and m["fraction_noninteger"] not in (None, 0.0) and m["fraction_noninteger"] > 0.01:
            pb.append("values are not integer counts")

        # --- cells per perturbation, and NTC ------------------------------
        if pert_values is None:
            rep["cells_per_perturbation"] = None
            rep["controls"] = {"present": None,
                               "note": "no perturbation field identified; controls cannot be located"}
        else:
            vc = pd.Series(pert_values).value_counts()
            ntc_levels = [lv for lv in vc.index
                          if any(re.search(p, str(lv), re.I) for p in NTC_PATTERNS)]
            pert_only = vc.drop(index=ntc_levels, errors="ignore")
            if int(vc.max()) == 1:
                pb.append("every perturbation label occurs exactly once (one row per perturbation)")
            rep["cells_per_perturbation"] = {
                "field": pert["chosen"],
                "n_levels": int(vc.size),
                "n_levels_that_are_our_targets": int(sum(1 for lv in vc.index if lv in targets)),
                "rows_per_level": dist(vc.to_numpy()),
                "rows_per_level_excluding_controls": dist(pert_only.to_numpy()) if pert_only.size else None,
                "n_levels_with_ge_100_rows": int((pert_only >= 100).sum()),
                "n_levels_with_ge_400_rows": int((pert_only >= 400).sum()),
                "our_targets_with_ge_100_rows": int(
                    sum(1 for lv, n in pert_only.items() if lv in targets and n >= 100)),
            }
            rep["controls"] = {
                "present": bool(ntc_levels),
                "labels": [str(lv) for lv in ntc_levels[:20]],
                "n_labels": len(ntc_levels),
                "n_control_rows": int(vc.reindex(ntc_levels).sum()) if ntc_levels else 0,
                "matched_by": "case-insensitive regex over the chosen field's levels",
            }
            if not ntc_levels:
                rep["controls"]["note"] = (
                    "no level matched a non-targeting pattern; controls may exist "
                    "under a label this list does not cover, or in another column")
        # a boolean control flag elsewhere in obs is worth surfacing either way
        if obs is not None:
            flags = [c for c in obs.columns
                     if re.search(r"control|ntc|non[-_]?target", c, re.I)]
            if flags:
                rep.setdefault("controls", {})["other_control_like_obs_columns"] = flags

        rep["pseudobulk_evidence"] = pb
        rep["single_cell_raw_counts"] = bool(is_counts) and not pb

    # --- guide / batch structure, which the NTC finding says we need -------
    if obs is not None:
        batchy = [c for c in obs.columns
                  if re.search(r"batch|gem|lane|donor|replicate|rep\b|library|sample|"
                               r"guide|sgrna|grna|barcode|10x|channel|well", c, re.I)]
        rep["batch_like_obs_columns"] = batchy
    else:
        rep["batch_like_obs_columns"] = None

    rep["verdict"] = verdict_line(rep, len(gene_set))
    return rep


def verdict_line(rep: dict, n_reference_genes: int) -> str:
    gs = rep["gene_space"]
    frac = gs.get("fraction_of_our_axis_covered")
    cpp = rep.get("cells_per_perturbation") or {}
    hits = cpp.get("n_levels_that_are_our_targets", 0)
    ctrl = (rep.get("controls") or {}).get("present")
    sc = rep["single_cell_raw_counts"]
    med = (cpp.get("rows_per_level_excluding_controls") or {}).get("p50")

    if rep["errors"]:
        return f"REJECT - unreadable: {rep['errors'][0]}"
    if frac is None:
        return ("REJECT - no gene symbol axis found, so the file cannot be placed "
                f"on our {n_reference_genes:,}-gene space")
    if frac < 0.5:
        return (f"REJECT - only {frac:.1%} of our {n_reference_genes:,} genes are present; "
                "too little shared gene space to transfer anything")
    if not sc:
        why = "; ".join(rep["pseudobulk_evidence"]) or "X is not raw integer counts"
        return (f"REFERENCE-ONLY - not single-cell raw counts ({why}). "
                f"Gene overlap {frac:.1%}, {hits} of our 300 targets. Usable as a "
                "fold-change prior, not as training cells and not as a scoring harness.")
    if not ctrl:
        return (f"PARTIAL - single-cell raw counts, gene overlap {frac:.1%}, "
                f"{hits} of our 300 targets, but no non-targeting control label was "
                "found; without controls neither training contrasts nor cell-eval2 scoring work")
    if hits >= 25 and med is not None and med >= 50:
        return (f"USABLE-DIRECT - single-cell raw counts with controls, gene overlap "
                f"{frac:.1%}, {hits} of our 300 targets, median {med:.0f} cells per "
                "perturbation. Supports both training and a local scoring harness.")
    return (f"USABLE-HARNESS - single-cell raw counts with controls, gene overlap "
            f"{frac:.1%}, but only {hits} of our 300 targets"
            + (f" and median {med:.0f} cells per perturbation" if med is not None else "")
            + ". Good for building a local cell-eval2 harness; weak for direct transfer.")


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("h5ad", nargs="*", type=Path, help="candidate .h5ad files to check")
    ap.add_argument("--data-root", type=Path, default=Path("C:/Users/ferra/vcc2026-data"))
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[1] / "reports/external_compat")
    ap.add_argument("--refresh-contract", action="store_true",
                    help="recompute the contract from raw/controls instead of using the cache")
    ap.add_argument("--n-permutations", type=int, default=8,
                    help="label permutations for the NTC-guide exchangeability null")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-cells", type=int, default=60000,
                    help="row cap when scanning a candidate file; blocks are spread evenly")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    cache = args.out / "contract.json"
    if cache.exists() and not args.refresh_contract:
        contract = json.loads(cache.read_text(encoding="utf-8"))
    else:
        contract = derive_contract(args.data_root, args.out, args.n_permutations, args.seed)

    if not args.h5ad:
        print(json.dumps(contract, indent=2))
        print(f"\ncontract -> {cache}")
        print(f"guides   -> {args.out / 'ntc_guide_structure.csv'}")
        return

    gene_set, targets = load_axes(contract)
    for path in args.h5ad:
        if not path.exists():
            print(f"MISSING  {path}")
            continue
        try:
            rep = check_external(path, contract, args.max_cells, gene_set, targets)
        except Exception as exc:
            print(f"REJECT - {path.name}: {type(exc).__name__}: {exc}")
            continue
        dest = args.out / f"{path.stem}.json"
        dest.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
        print(json.dumps(rep, indent=2, default=str))
        print(f"\n{path.name}: {rep['verdict']}")
        print(f"report -> {dest}\n")


if __name__ == "__main__":
    main()
