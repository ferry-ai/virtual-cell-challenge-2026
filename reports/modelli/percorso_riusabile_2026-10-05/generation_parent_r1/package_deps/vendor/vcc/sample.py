"""Generate a random-but-valid dummy prediction for testing the submit pipeline.

`vcc sample` builds a synthetic prediction — random sparse counts over a provided
gene list, one cell group per perturbation plus a non-targeting control — and
packages it into a submittable `.vcc` via the *same* prep pipeline `vcc prep`
uses, so the output is byte-format-identical to a real prepped submission.

It is a **test utility**: the expression values are noise, so submitting one
scores poorly. The point is a file that passes validation and exercises the
upload → scoring path end to end (and, at `--full` size, the resumable upload).

Cold start is preserved by cli.py importing this module lazily (inside the
`sample` command) — NOT by the in-function imports below: the module-top
`from vcc.prep import ...` already pulls anndata/numpy/scipy/pandas via prep. So
keep `vcc.sample` out of cli.py's top-level imports (D6).
"""

from __future__ import annotations

import csv
import os
import secrets
import tempfile
from dataclasses import dataclass, field

from vcc.prep import (
    DEFAULT_CONTEXT_COL,
    DEFAULT_NTC_NAME,
    DEFAULT_PERT_COL,
    EXPECTED_CELLS_PER_PERT,
    EXPECTED_GENE_DIM,
    MAX_CELL_DIM,
    REQUIRED_CONTEXTS,
    PrepError,
    PrepResult,
    assert_output_distinct_from_inputs,
    read_gene_list,
    run_prep,
)


class SampleError(Exception):
    """A user-facing problem generating a sample (bad perts file, bad args)."""


# Cells per perturbation for a `--no-full` sample: small on purpose, since that mode
# exists to exercise the upload path with a file scoring will reject. A `--full`
# sample uses the panel's real count (`EXPECTED_CELLS_PER_PERT`) instead.
SMALL_CELLS_PER_PERT = 5


@dataclass
class SampleResult:
    output: str
    is_vcc: bool
    n_cells: int
    n_genes: int
    n_perts: int
    ntc_cells: int
    # The seed actually used, whether passed or generated. Always concrete so any
    # sample can be reproduced with `--seed`.
    seed: int = 0
    prep: PrepResult | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "output": self.output,
            "is_vcc": self.is_vcc,
            "n_cells": self.n_cells,
            "n_genes": self.n_genes,
            "n_perts": self.n_perts,
            "ntc_cells": self.ntc_cells,
            "seed": self.seed,
            "notes": self.notes,
        }
        if self.prep is not None:
            d["prep"] = self.prep.to_dict()
        return d


def _read_perts(
    path: str, pert_col: str, ntc_name: str, context_col: str = DEFAULT_CONTEXT_COL
) -> list[tuple[str | None, str, int | None]]:
    """Read (context|None, perturbation, n_cells|None) rows from a perts CSV.

    Accepts the `pert_counts.csv` layout. The 2026 file is a bare list — just a
    `target_gene` column — and both `n_cells` and `context` are optional, so a
    pre-2026 three-column file reads the same way it always did. The NTC label,
    blanks, and duplicates are dropped;
    de-duplication is per (context, perturbation), since the same gene is
    perturbed in every context.

    `context` is None for a pre-2026 file with no such column; the caller then
    replicates the perturbations across every required context.
    """
    perts: list[tuple[str | None, str, int | None]] = []
    seen: set[tuple[str | None, str]] = set()
    # The -p option is a plain click.Path (no exists=True), so a missing path,
    # a directory, or a non-UTF-8 file would otherwise escape as a bare
    # traceback. Wrap I/O so it surfaces as a clean SampleError, matching the
    # actionable "Gene list not found" that -g gives via read_gene_list.
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:  # utf-8-sig tolerates an Excel BOM
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or pert_col not in reader.fieldnames:
                raise SampleError(
                    f"Perturbation file '{path}' must have a '{pert_col}' column. "
                    f"Found columns: {reader.fieldnames}"
                )
            has_counts = "n_cells" in reader.fieldnames
            has_context = context_col in reader.fieldnames
            for row in reader:
                name = (row.get(pert_col) or "").strip()
                context = (row.get(context_col) or "").strip() if has_context else ""
                key = (context or None, name)
                if not name or name == ntc_name or key in seen:
                    continue
                # A file that declares contexts must give every perturbation one.
                # A blank cell used to become a None context, and None then mixed
                # with real labels downstream: `sorted({None, 'A'})` raised a bare
                # TypeError, and when the blank row happened not to leave a context
                # uncovered it slipped through to prep, where pandas had turned the
                # None into NaN ("expected str instance, float found"). Both were
                # tracebacks for what is simply a malformed row, so reject it here
                # — this is what keeps every context in `perts` non-None.
                if has_context and not context:
                    raise SampleError(
                        f"Row {reader.line_num} of '{path}' has a '{context_col}' column but "
                        f"leaves it blank for '{name}'. Every perturbation needs a context "
                        f"({', '.join(str(c) for c in REQUIRED_CONTEXTS)}); use the "
                        "pert_counts.csv from the controls bundle unedited."
                    )
                seen.add(key)
                n: int | None = None
                if has_counts:
                    raw = (row.get("n_cells") or "").strip()
                    try:
                        n = int(float(raw)) if raw else None
                    except (ValueError, OverflowError):
                        # OverflowError: int(float("1e309")) is int(inf). Non-finite
                        # n_cells otherwise escaped as a raw traceback (#421); treat
                        # it as "no usable count", same as an unparseable value.
                        n = None
                perts.append((context or None, name, n))
    except FileNotFoundError:
        raise SampleError(f"Perturbations file not found: {path}") from None
    except IsADirectoryError:
        raise SampleError(f"Perturbations path is a directory, not a file: {path}") from None
    except UnicodeDecodeError as exc:
        raise SampleError(f"Perturbations file '{path}' is not valid UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise SampleError(f"Could not read perturbations file '{path}': {exc}") from exc
    if not perts:
        raise SampleError(f"No usable perturbations found in '{path}'.")
    return perts


def run_sample(
    *,
    genes_path: str,
    output_path: str,
    perts_path: str,
    cells_per_pert: int | None = None,
    full: bool = True,
    ntc_cells: int | None = None,
    genes_per_cell: int = 300,
    umi_lambda: float = 5.0,
    seed: int | None = None,
    pert_col: str = DEFAULT_PERT_COL,
    ntc_name: str = DEFAULT_NTC_NAME,
    context_col: str = DEFAULT_CONTEXT_COL,
    contexts: tuple[str, ...] = REQUIRED_CONTEXTS,
    encoding: int = 32,
    max_cell_dim: int | None = MAX_CELL_DIM,
    as_h5ad: bool = False,
    force: bool = False,
) -> SampleResult:
    """Generate a random valid prediction and write it as `.vcc` (or `.h5ad`).

    Raises `SampleError` / `prep.PrepError` on bad input.
    """
    import anndata as ad
    import numpy as np
    import pandas as pd
    from scipy.sparse import csr_matrix

    # Cells per perturbation, when the perts file does not state one. The 2026
    # `pert_counts.csv` is a bare perturbation list, so under --full that is the
    # normal case and the panel's real count applies; --no-full stays deliberately
    # small. An explicit value wins in either mode (and an `n_cells` column still
    # wins over both — see `sized` below).
    if cells_per_pert is None:
        cells_per_pert = EXPECTED_CELLS_PER_PERT if full else SMALL_CELLS_PER_PERT
    if cells_per_pert < 1:
        raise SampleError("--cells-per-pert must be >= 1.")
    if genes_per_cell < 1:
        raise SampleError("--genes-per-cell must be >= 1.")
    if max_cell_dim is not None and max_cell_dim < 1:
        # The CLI maps --max-cell-dim -1 to None (disabled); any remaining
        # non-positive value is nonsense (0, -2, …) and would otherwise reject
        # every sample with a confusing "maximum of -2" message.
        raise SampleError("--max-cell-dim must be >= 1, or -1 to disable the cap.")
    if seed is not None and seed < 0:
        # np.random.default_rng rejects a negative seed with a numpy ValueError
        # ("expected non-negative integer"), which — unlike every other numeric
        # flag here — was unguarded and escaped as a raw traceback (#405). -1 is a
        # common "unset/random" sentinel, so this is easy to hit; omit --seed for a
        # random run.
        raise SampleError("--seed must be >= 0 (omit --seed for a random seed).")
    # Never write the sample over one of its own inputs (#404). The .vcc path also
    # runs through run_prep (which guards this), but the --h5ad path writes
    # directly, so check up front. Reuse prep's guard — single source of truth, and
    # it tolerates a realpath OSError; it raises PrepError, re-raised as SampleError.
    try:
        assert_output_distinct_from_inputs(
            output_path, [("gene list", genes_path), ("perturbation list", perts_path)]
        )
    except PrepError as exc:
        raise SampleError(str(exc)) from exc
    if not force and os.path.exists(output_path):
        raise SampleError(
            f"Output already exists: {output_path}. Re-run with --force to overwrite, "
            "or choose a different -o/--output path."
        )

    genes = read_gene_list(genes_path)  # real gene order; PrepError if unreadable
    n_genes = len(genes)
    if n_genes == 0:
        raise SampleError(f"Gene list '{genes_path}' is empty.")

    # Random noise, not a real model — surface that in the output/JSON so a
    # generated sample is never mistaken for a genuine submission.
    notes: list[str] = [
        "Random test data for exercising the submit pipeline — not a real "
        "prediction, so scores will be poor."
    ]
    if n_genes != EXPECTED_GENE_DIM:
        notes.append(
            f"Gene list has {n_genes} genes, not the challenge's {EXPECTED_GENE_DIM} — "
            "this sample won't score against the real data (fine for pipeline testing)."
        )

    # Resolve the perturbation set + per-perturbation cell counts, per context.
    # `perts` is a list of (context, name, n_cells): a submission must cover every
    # context, so the sample generates all of them or it would not even pass prep.
    # `perts_path` is REQUIRED. It used to be optional, and omitting it produced a
    # file built from the first --n-perts *gene symbols* as stand-in perturbation
    # labels. That file passed prep (sample turned prep's own checks off for it,
    # since there was nothing to check against) and passed `vcc submit` (a .vcc is
    # only validated as a container), then died in scoring with "N perturbations
    # have 0 cells" — after a full upload. A sample whose whole purpose is to
    # exercise the submit path must not be rejected at the last step, so the
    # placeholder mode is gone rather than merely warned about.
    ctx_list = list(contexts) or [None]
    pert_rows = _read_perts(perts_path, pert_col, ntc_name, context_col)
    # A count-less perts file used to be a hard error here — with no n_cells there was
    # no way to reproduce the panel's real cell counts, so a --full sample would have
    # been rejected by scoring. The 2026 file is a bare perturbation list and the count
    # comes from EXPECTED_CELLS_PER_PERT (or --cells-per-pert), so it is reproducible
    # again and the error is gone.
    #
    # Honor the file's n_cells under --full whenever it's a positive integer; blank /
    # missing / non-positive values fall back to cells_per_pert (a 0- or negative-cell
    # perturbation group is meaningless in a prediction).
    sized = [
        (ctx, name, n if (full and isinstance(n, int) and n >= 1) else cells_per_pert)
        for ctx, name, n in pert_rows
    ]
    # A pre-2026 file carries no context column; replicate its perturbations
    # across every required context so the sample is still submittable.
    if all(ctx is None for ctx, _, _ in sized):
        perts = [(c, name, n) for c in ctx_list for _, name, n in sized]
    else:
        perts = [(ctx, name, n) for ctx, name, n in sized]
        # No None in here: _read_perts rejects a blank context when the file has
        # the column, so contexts are either all-None (handled above) or all real.
        # That invariant is what makes this sort safe.
        covered = {ctx for ctx, _, _ in perts}
        missing = [c for c in ctx_list if c is not None and c not in covered]
        if missing:
            raise SampleError(
                f"--perts file covers contexts {sorted(covered)} but a submission must "
                f"cover {ctx_list}; missing {missing}."
            )
    if not full:
        notes.append(
            f"--no-full: every perturbation got {cells_per_pert} cells instead of the official "
            f"{EXPECTED_CELLS_PER_PERT}, so SCORING WILL REJECT THIS FILE ('wrong number of "
            "cells'). Use it to exercise upload only; drop --no-full for a file that scores."
        )

    # Controls are NOT part of a 2026 submission -- the scorer uses the held-out
    # data's own control cells -- so the sample generates none by default and
    # prep would reject them anyway. --ntc-cells stays for the legacy
    # (contexts-disabled) shape, where the control label IS required.
    ntc = ntc_cells if ntc_cells is not None else (0 if contexts else cells_per_pert)
    if ntc < 0:
        raise SampleError("--ntc-cells must be >= 0.")
    if ntc and contexts:
        raise SampleError(
            "--ntc-cells > 0 would make an invalid submission: control cells must not be "
            "submitted (scoring uses the held-out controls). Drop --ntc-cells, or pass "
            "--contexts '' for the legacy single-context shape."
        )

    # Distinct perturbations, not (context, perturbation) rows: the same gene is
    # perturbed in every context, so counting rows would report 3x the panel size.
    n_distinct_perts = len({name for _, name, _ in perts})

    # Enforce the cell cap BEFORE allocating the label lists / matrix. A huge
    # --cells-per-pert (reachable via --no-full, where every perturbation uses it,
    # since it has no upper bound) would otherwise build a multi-billion-element
    # list and MemoryError before any check ran (#429). The projected total equals
    # the eventual len(labels): per-perturbation counts plus ntc cells per context.
    n_cells = sum(count for _, _, count in perts) + ntc * len(ctx_list)
    if max_cell_dim is not None and n_cells > max_cell_dim:
        raise SampleError(
            f"Generated cell count {n_cells} exceeds the maximum of {max_cell_dim}. "
            "Reduce the perturbations / --cells-per-pert, or raise the cap with "
            "--max-cell-dim (or --max-cell-dim -1 to disable it)."
        )

    # obs.target_gene + obs.context: every perturbation's cells. No control cells
    # under the 2026 shape (`ntc` is 0 there) — see the check above.
    labels: list[str] = []
    ctx_labels: list[str] = []
    for context, name, count in perts:
        labels.extend([name] * count)
        ctx_labels.extend([context] * count)
    for context in ctx_list:
        labels.extend([ntc_name] * ntc)
        ctx_labels.extend([context] * ntc)

    # Random sparse counts (float, matching prep's expected integer-counts input),
    # every cell with a nonzero total so median-normalization is clean. Built
    # fully vectorized (no dense allocation): each cell gets `k` random gene hits
    # (with replacement; duplicates are summed), counts are Poisson + 1 (>= 1).
    # Resolve the seed to a concrete value BEFORE building the matrix, so the
    # result can report it and the run is reproducible with `--seed`.
    #
    # The default used to be a literal 0, which meant every `vcc sample` on every
    # machine produced a byte-identical prediction -- so every tester's submission
    # scored exactly the same, which reads as a scoring bug rather than as the
    # samples being identical. Defaulting to fresh entropy makes two testers'
    # samples differ; passing --seed still pins one.
    resolved_seed = secrets.randbits(32) if seed is None else seed
    rng = np.random.default_rng(resolved_seed)
    k = min(genes_per_cell, n_genes)
    indptr = np.arange(0, (n_cells + 1) * k, k, dtype=np.int64)
    indices = rng.integers(0, n_genes, size=n_cells * k, dtype=np.int32)
    data = (rng.poisson(umi_lambda, size=n_cells * k) + 1).astype(np.float32)
    X = csr_matrix((data, indices, indptr), shape=(n_cells, n_genes))
    X.sum_duplicates()  # canonicalize the rare same-gene-twice-in-a-cell collisions

    obs = pd.DataFrame({pert_col: labels}, index=[str(i) for i in range(n_cells)])
    if contexts:
        obs[context_col] = ctx_labels
    var = pd.DataFrame(index=list(genes))
    adata = ad.AnnData(X=X, obs=obs, var=var)

    if as_h5ad:
        try:
            adata.write_h5ad(output_path)
        except OSError as exc:
            raise SampleError(
                f"Could not write '{output_path}'. Check the destination is writable ({exc})."
            ) from exc
        return SampleResult(
            output=output_path,
            is_vcc=False,
            n_cells=n_cells,
            n_genes=n_genes,
            n_perts=n_distinct_perts,
            ntc_cells=ntc,
            seed=resolved_seed,
            notes=notes,
        )

    # Package via the real prep pipeline so the .vcc matches a prepped submission
    # exactly. Hand run_prep a temp .h5ad. The gene dimension equals the provided
    # list by construction, so disable prep's fixed-18080 check (a smaller test /
    # custom gene list is legitimate here).
    tmp = tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False)
    tmp.close()
    try:
        try:
            adata.write_h5ad(tmp.name)
        except OSError as exc:
            raise SampleError(
                f"Could not write a temporary .h5ad for packaging ({exc})."
            ) from exc
        prep_res = run_prep(
            input_path=tmp.name,
            genes_path=genes_path,
            output_path=output_path,
            # A sample is built FROM pert_counts.csv, so it is verified against
            # that same file — always. This is the check that would have caught
            # the placeholder-perturbation file before it was ever uploaded.
            perts_path=perts_path,
            verify_targets=True,
            # Only a --full sample reproduces the official cell count; --no-full is
            # deliberately undersized (and says so), so don't hold it to that.
            check_cell_counts=full,
            # Same count the cells were generated with, so prep checks the sample
            # against what built it even when --cells-per-pert overrode the constant.
            cells_per_pert=cells_per_pert,
            pert_col=pert_col,
            ntc_name=ntc_name,
            context_col=context_col,
            output_context_col=context_col,
            required_contexts=tuple(contexts),
            # Legacy shape (no contexts) still carries a control group and must
            # not be rejected for it.
            reject_controls=bool(contexts),
            encoding=encoding,
            expected_gene_dim=None,  # sample surfaces the gene-dim mismatch itself (note above)
            max_cell_dim=max_cell_dim,
            force=force,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    return SampleResult(
        output=output_path,
        is_vcc=True,
        n_cells=n_cells,
        n_genes=n_genes,
        n_perts=n_distinct_perts,
        ntc_cells=ntc,
        seed=resolved_seed,
        prep=prep_res,
        notes=notes,
    )
