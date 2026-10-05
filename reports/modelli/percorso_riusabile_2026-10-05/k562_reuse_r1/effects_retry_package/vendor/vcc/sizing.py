"""Whether a prediction is dense enough to be unscoreable, decided before the upload.

Dependency-free by design, like `config.py` and `_version.py`, so `vcc prep` can refuse
an oversized submission without importing AnnData or NumPy.

This is a MIRROR of the scoring service's own sizing rules, deliberately, the same way `_require_counts`
mirrors cell_eval2's `validate_input_type`. The constants live in `scoring-limits.json`
at the repo root and the test suites on both sides assert against it, because a cap the
client and the server disagree about is worse than no cap: the participant is told the
file is fine and the server rejects it after a multi-GB upload.

WHAT THIS PREVENTS. A prediction that needs more RAM than the scoring machine has is
OOM-killed by the cgroup — SIGKILL, no exception, no traceback naming the cause. The job
cannot report its own death, so the submission sat in `scoring` with a null error for
over ten hours and burned four Batch attempts. Locally, it is arithmetic on a number
prep has already counted.

⚠️ THE COST PER NONZERO IS NOT CONSTANT. SciPy indexes CSR with int32 while it can and
promotes to int64 above 2**31 nonzeros, so the per-nonzero cost steps from 8 bytes to 12
exactly there. Measured: a 2.08e9-nnz prediction is 15.84 GiB resident, a 4.25e9-nnz one
47.93 GiB — a flat rate fitted to the first underestimates the second by a third.
"""

from __future__ import annotations

GIB = float(2**30)

INT32_INDEX_LIMIT = 2**31
# anon_gib = ANON_MATRIX_COPIES * matrix(nnz) + ANON_OVERHEAD_GIB
#
# Refitted on 254 production runs (21-24 Aug 2026) from the scoring job's own
# `MEMORY [...]` instrumentation: least squares gives anon = 1.117*matrix + 6.47
# (R^2 = 0.917), worst residual +19.41 GiB. What ships is that fit with the worst
# residual folded into the intercept and both terms rounded UP, so it over-predicts all
# 254 measurements and errs toward a bigger machine rather than an OOM.
#
# ⚠️ This models ANON, not the cgroup peak -- `memory.peak` also counts page cache, which
# scales with the container granted rather than with the submission. See
# scoring-limits.json for the full provenance.
#
# NOT to be confused with prep_peak_gib() below: that is the RAM `vcc prep` needs on the
# participant's own machine to PACKAGE a prediction. This one sizes the scoring container.
ANON_MATRIX_COPIES = 1.12
ANON_OVERHEAD_GIB = 26.0
SAFETY_MARGIN = 0.9

# g2-standard-32's container share: the largest machine scoring is willing to use.
LARGEST_CONTAINER_MIB = 126976

HARD_CAP_NNZ = 4_750_000_000


def bytes_per_nnz(nnz: int) -> int:
    """8 while SciPy can index with int32, 12 once it must promote to int64."""
    return 8 if nnz <= INT32_INDEX_LIMIT else 12


def _matrix_gib(nnz: int) -> float:
    return bytes_per_nnz(nnz) * float(nnz) / GIB


def estimated_peak_gib(nnz: int) -> float:
    """Peak ANONYMOUS memory the SCORING job holds for a prediction with `nnz` nonzeros.

    One resident copy of the prediction plus a fixed overhead (CUDA context, gpudge's
    buffers, the streaming windows) and the safety envelope.

    Replaced an earlier `max(read, scoring)` form that modelled the cgroup high-water
    mark. That quantity is dominated by page cache, so it tracked the container already
    granted rather than the submission; measuring anon directly across 254 production
    runs showed one linear form describes it at R^2 = 0.917.

    This is the SERVER's number, mirrored here so the CLI can refuse an oversized
    submission before a multi-GB upload. For the participant's local packaging cost see
    `prep_peak_gib`.
    """
    return ANON_MATRIX_COPIES * _matrix_gib(nnz) + ANON_OVERHEAD_GIB


def exceeds_hard_cap(nnz: int) -> bool:
    return nnz > HARD_CAP_NNZ


# Prep (client-side packaging) peak, distinct from the SCORING container sizing
# above. Post-#476-fix prep holds ~one resident copy of the matrix during read
# (`SAME_DTYPE`), plus a second only when the astype actually copies — i.e. the
# input dtype differs from the output encoding, or the lognorm path mutates X in
# place (`CAST`). The modf/second-array passes are gone.
#
# The copy is now conditional on exactly the dtype match, so the estimate is too,
# rather than quoting the worst case for every prediction: a full float32 panel
# that the fix made a no-copy case measured 1.18x the matrix (#480), so predicting
# 2.0x there sent contestants to rent a bigger box for a job their machine would
# have finished. SAME_DTYPE tracks that 1.18x measurement (with headroom); CAST
# keeps the conservative ~2x for a real second copy.
PREP_MATRIX_COPIES_SAME_DTYPE = 1.3
PREP_MATRIX_COPIES_CAST = 2.2
# Reordering genes to the required order indexes the AnnData into a VIEW, which
# re-materializes on access WHILE the original is still resident — so the peak
# carries a transient extra ~1x the matrix that neither `casts` value models. This
# is inherent to reordering in memory (a `.copy()` would hit the same transient),
# not something a code change removes, so it's modelled here rather than fixed. A
# reordered dry run measured ~2.2x vs ~1.2x in-order — a ~1.0x delta (#480).
PREP_REORDER_COPIES = 1.0
PREP_OVERHEAD_GIB = 2.0


def prep_peak_gib(nnz: int, casts: bool = True, reordered: bool = False) -> float:
    """Rough peak RAM ``vcc prep`` needs to PACKAGE a prediction with ``nnz`` nonzeros.

    Distinct from ``estimated_peak_gib`` (which sizes the scoring container): this
    is the participant's local packaging cost — the thing that SIGKILLs a laptop
    with no message (#476).

    ``casts`` is whether packaging will make a second full-matrix copy — True when
    the input dtype differs from the output encoding or the matrix is mutated in
    place (the lognorm path), False when the astype aliases (the common float32
    counts case the fix made free). Defaults to True so an unknown caller gets the
    conservative bound.

    ``reordered`` is whether the input's genes needed reordering to the required
    order — that path materializes an AnnData view alongside the original, adding a
    transient ~1x the matrix that ``casts`` alone doesn't capture. Without it the
    warning would under-predict for a reordered submission — the OOM direction, the
    one #476 exists to prevent.
    """
    copies = PREP_MATRIX_COPIES_CAST if casts else PREP_MATRIX_COPIES_SAME_DTYPE
    if reordered:
        copies += PREP_REORDER_COPIES
    return copies * _matrix_gib(nnz) + PREP_OVERHEAD_GIB


def _sysconf_gib(pages_name: str) -> "float | None":
    """`os.sysconf(pages_name) * page_size` in GiB, or None if unavailable.

    Dependency-free (no psutil). Returns None when the name isn't defined
    (macOS lacks SC_AVPHYS_PAGES), when os.sysconf doesn't exist (Windows), or
    when a count comes back non-positive — SC_AVPHYS_PAGES can return -1 WITHOUT
    raising on some platforms, which must not become a negative RAM figure.
    """
    try:
        import os

        pages = os.sysconf(pages_name)
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (ValueError, OSError, AttributeError):
        return None
    if pages is None or pages <= 0 or page_size <= 0:
        return None
    return pages * page_size / GIB


def total_ram_gib() -> "float | None":
    """Best-effort *total* system RAM in GiB (Linux + macOS, via SC_PHYS_PAGES), else None.

    We size against TOTAL, not *available* (SC_AVPHYS_PAGES): on Linux the OS uses
    free RAM for page cache, so "available" is often reported very low even with
    plenty of instantly-reclaimable memory — which would fire false-positive
    warnings on machines that actually have ample RAM. Total is a stable hardware
    figure, so `need > total` is a reliable "won't fit" signal. SC_PHYS_PAGES also
    works on macOS, unlike SC_AVPHYS_PAGES (Windows has no os.sysconf at all → None).
    """
    return _sysconf_gib("SC_PHYS_PAGES")


def prep_memory_warning(
    nnz: int, n_cells: int | None = None, casts: bool = True, reordered: bool = False
) -> "str | None":
    """A heads-up if packaging is likely to exceed the machine's total RAM, else None.

    Sized against TOTAL RAM (see total_ram_gib) so it fires cross-platform without
    the Linux page-cache false positives that an "available RAM" check produces.
    Deliberately NON-fatal — warns, never refuses, since the machine may have swap
    and a wrong refusal would block a valid submission. Returns None when RAM can't
    be determined (e.g. Windows) or the estimate fits.

    ``casts`` and ``reordered`` are forwarded to :func:`prep_peak_gib` — pass False
    for ``casts`` when the astype won't copy (input dtype already matches the
    encoding) so a no-copy job isn't warned as if it needed ~2x the matrix, and True
    for ``reordered`` when the genes needed reordering, whose view materialization
    adds a transient the size estimate must include.
    """
    need = prep_peak_gib(nnz, casts=casts, reordered=reordered)
    total = total_ram_gib()
    if total is None or need <= total:
        return None
    density = f" ({nnz / n_cells:,.0f} per cell)" if n_cells else ""
    return (
        f"This prediction has {nnz:,} stored entries{density}; packaging it may need about "
        f"{need:.0f} GiB of RAM, more than the ~{total:.0f} GiB total on this machine.\n"
        "`vcc prep` may be killed by the OS with no error message. Run prep on a machine with "
        "more RAM, or reduce the prediction's density (fewer expressed genes per cell).\n"
        "This is an estimate — with swap, or if more RAM frees up, it may still complete."
    )


def too_dense_message(nnz: int, n_cells: int | None = None) -> str:
    """The refusal, phrased so a modeller knows what to change."""
    # "stored entries", not "nonzero values": `nnz` is scipy's count of STORED values, which
    # includes any zero saved explicitly, and a dense array stores every slot. Calling them
    # nonzeros invites a modeller to conclude their sparse-looking matrix cannot be the
    # problem. Kept in step with the scoring service's own too-large message and the
    # wiki's troubleshooting table, which quotes this string.
    # ⚠️ Do NOT reinstate the "against a N GiB ceiling" clause -- see the twin of this
    # message in the scoring service's own sizing module. The cap was solved against the
    # RETIRED memory model; under the anon refit the largest tier fits far more than the
    # cap allows, so quoting both numbers had the refusal say, in one sentence, that the
    # submission fits.
    density = f" ({nnz / n_cells:,.0f} per cell)" if n_cells else ""
    return (
        f"Prediction has {nnz:,} stored entries{density}, above the {HARD_CAP_NNZ:,} "
        f"limit scoring accepts — about {estimated_peak_gib(nnz):.0f} GiB of memory "
        "once loaded.\n"
        "This is a DENSITY limit, not a file-size one: predictions compress well, so a "
        "small .vcc can still be far too dense — scoring holds the matrix uncompressed.\n"
        "Predict fewer expressed genes per cell. Dropping genes below ~1 CPM costs "
        "almost no expression mass, and the DE metrics already discard anything under "
        "5 CPM.\n"
        "Pass --max-nnz -1 to disable this check (the server enforces it regardless)."
    )
