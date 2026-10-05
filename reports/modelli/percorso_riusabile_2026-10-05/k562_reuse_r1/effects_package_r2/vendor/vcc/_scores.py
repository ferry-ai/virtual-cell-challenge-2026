"""Single source of truth for the leaderboard score fields the CLI surfaces.

Both `vcc status` (``cli._echo_scores``) and `vcc submit --wait`
(``submit.run_submit`` building ``result.scores``) render the SAME set, in this
order, so they can't drift — adding a metric here flows to both. Dependency-free
on purpose so ``cli`` and ``submit`` can import it without a cold-start cost.

Keys must match the score fields the server returns, plus the legacy cell-eval
fields, ``score_avg`` and ``rank``. Labels mirror what the web app actually shows
a participant — the leaderboard and its submission banner, which call
``score_avg`` **"Overall"**. An older, unused label for it reads "Composite
Score"; nobody sees that, so don't mirror it.
"""

from __future__ import annotations

# Ordered (key, human label, short name): rank + composite + legacy (cell-eval) +
# 2026 (vcc2026). A given entry only carries one metric set; the null ones are
# filtered out on display.
#
# The SHORT NAME is the leaderboard column header, and it is empty for every row
# that has no column of its own (rank, the composite, the legacy metrics, the
# stamp). It rides beside the label because every other surface names these metrics
# both ways at once — the Evaluation page's scoring table and the score email both
# render "Perturbation discrimination pds" — and the board's columns are labelled
# with the short form alone. Printing the label by itself made the CLI the one
# surface where a participant reads a score under one name and then has to guess
# which column on the leaderboard it corresponds to.
#
# For 2026 the SCALED scores are what is shown. Each reads 0 = context-mean
# baseline and 1 = as good as a split-half replicate of the real experiment, so the
# six can be compared to each other and `score_avg` is their mean.
#
# ⚠️ 1 IS NOT THE CEILING. Only `expr_mse_unbiased_capped_norm` clamps at the top;
# the other five may exceed it, so a perfect submission scores above 1.0 rather
# than at it. THERE IS NO FIXED FLOOR either, as of cell_eval2 0.14.0: `mse` is
# clamped below at 0, `nmae` is floored by its penalty cap at -6, and the other four
# are unclamped and bottom out at their own depths (about -0.1 for `jac`, -1.9 for
# `fid` on the `-r3`/0.15.0 bundles — those four are bundle-derived and move on every
# rebuild). A negative score is information, not an error. Never render these as a
# percentage and never assume 1.0 bounds them.
#
# The raw cell_eval2 values are deliberately NOT listed:
# they sit on six different scales and two of them point the other way, so printing
# them in the same column as the scaled ones invites reading a raw 5.25 as a score.
# They remain available in `vcc status --json`, which passes the entry through.
SCORE_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("rank", "Rank", ""),
    ("score_avg", "Overall", ""),
    # Legacy (cell-eval) detail metrics — null on a 2026 entry. No short form: they
    # predate the convention and their archive-board columns are spelled out.
    ("de_score", "DE score", ""),
    ("pert_score", "Perturbation score", ""),
    ("mae_score", "MAE score", ""),
    # 2026 (cell_eval2 `vcc2026` profile) scaled scores — null on a legacy entry.
    # Short names are the leaderboard's own column headers; keep them in step with
    # the scoring service's metric labels and the web app's leaderboard columns.
    ("score_pds", "Perturbation discrimination", "pds"),
    ("score_mse", "Expression accuracy", "mse"),
    ("score_nmae", "DE log-FC accuracy", "nmae"),
    ("score_fid", "DE direction fidelity", "fid"),
    ("score_reach", "DE direction reach", "reach"),
    ("score_jac", "DE significance overlap", "jac"),
    # Provenance. Scores are not comparable across panels or anchor sets, so the
    # stamp is part of reading the score, not metadata about it.
    ("partition", "Partition", ""),
    ("panel_id", "Panel", ""),
    ("anchor_version", "Anchor set", ""),
)

# Just the keys, for filtering an entry dict down to its score fields.
SCORE_KEYS: tuple[str, ...] = tuple(key for key, _, _ in SCORE_FIELDS)
