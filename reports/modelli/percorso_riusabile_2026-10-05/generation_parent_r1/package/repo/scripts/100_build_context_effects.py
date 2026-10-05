"""Stage 100: per-context panel effects for stage 76, from a written recipe over stage-98 sources.

A recipe is a JSON file fixed BEFORE generation:

    {"name": "t08", "effect": "raw", "gamma": 0.5, "reliability_scale": 100,
     "contexts": {"A": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 2}},
                  "B": {"amplitude": 1.0, "weights": {"k562": 1, "cd4_Stim48hr": 1}},
                  "C": {...}},
     "why": "free text: the evidence the weights come from"}

``effect`` picks what `mix` averages: ``shrunk`` (the stage-98 array, the default), ``raw``,
or ``zshrink``, which recomputes each source's local shrinkage from its raw effect and SE with
the recipe's ``shrink_k``: ``raw * z^2 / (z^2 + shrink_k)`` (`multisource.z_shrink`). For the
pseudobulk sources the stage-98 ``shrunk`` array is not that formula at k = 4 applied to the
pooled effect, so ``zshrink`` with ``shrink_k`` 4 differs from ``shrunk``.

An optional ``cis`` block adds the CRISPRi cis head, a model of the knockdown itself rather than
of its downstream response: dCas9-KRAB bound at a target's TSS also represses genes whose TSS is
close, in any context (CP-0020 section 3.5; reports/trasferimento/modulo_cis_2026-09-26/):

    "cis": {"pairs": "reports/trasferimento/cis_2026-09-17/k562_neighbour_pairs.csv",
            "max_distance_bp": 5000, "scale": 2.0}

The prior is the live `vcc2026.predictor_sc.CisModel.from_pairs` (median ln fold change by TSS
distance bin) fitted on stage 77's K562 genome-wide pairs after removing every panel target, so
no predicted target informs it. For each panel target, the genes of the official axis whose TSS
lies within ``max_distance_bp`` of the target's (``--coords``) get ``scale`` x the prior ADDED
to their transferred value, after the amplitude, which calibrates only the transferred part;
those pairs are marked observed so stage 45 applies them, measured by a source or not.

An optional ``association`` block predicts the targets that no source of the context covers, the
final set's new targets, from their network partners (reports/trasferimento/bersagli_nuovi_2026-09-26/):

    "association": {"universe": "processed/universe_k562_2026-09-26",
                    "links": "interim/encoder_inputs_2026-09-14/string_physical_links",
                    "info": "interim/encoder_inputs_2026-09-14/string_protein_info",
                    "min_score": 700, "weight": 0.1}

Paths are relative to the data root. For an uncovered target, ``weight`` x the mean effect of its
STRING physical partners (combined score >= ``min_score``) in the universe cache, centred on the
mean over all universe targets and never including the target itself, is added before the cis
head; those genes are marked observed. Covered targets are untouched, so a panel every source
covers gives the same effects with or without the block.

An optional ``pooling`` block replaces the equal-weight mean with a hierarchical empirical-Bayes
pooling (reports/trasferimento/trasferimento_gerarchico_2026-09-26/), and needs ``"effect": "raw"``:

    "pooling": {"method": "eb", "se_factor": {"cd4_mix": 2.0}, "bin_weight": 100, "bins": 50,
                "basal": "processed/basal_sources_2026-09-26.csv",
                "match_detectable": "processed/effects_t20_2026-09-26"}

Each selected source's raw effect minus ``gamma`` x its common response is read as a response the
lines share, plus the line's own deviation, plus sampling noise of variance ``se_factor`` x SE^2
(`multisource.eb_components`: variances by moments over the panel from the recipe's own sources,
blended with genes of similar expression in ``basal``); the prediction is the posterior mean of the
shared response (`multisource.eb_pool`). Weights only select sources. The context's ``amplitude``
multiplies it, unless ``match_detectable`` names a stage-100 output: then a scale per context makes
the median count of genes above 4 / sqrt(400 mu) (`transfer_model.detectable_threshold` on the
context's control CPM in ``basal``) equal the reference's for that context, cis head included on both
sides. A mixture saved without SE (``cd4_mix``) gets its parts' pooled SE (`transfer_model.mixture_se`).

An optional ``gene_share`` block weights the transferred part gene by gene
(reports/trasferimento/quota_condivisa_2026-09-27/):

    "gene_share": {"path": "reports/trasferimento/quota_condivisa_2026-09-27/t23/share.csv",
                   "basal": "processed/basal_sources_2026-09-26.csv",
                   "match_detectable": "processed/effects_t22_2026-09-26"}

``path`` (in the repository; a report path written before 28 September 2026 is followed to its
category folder by `config.repo_file`, D-046) gives every gene of the official axis a share in [0, 1]: the part of its
knockdown response that the universes' lines have in common, sigma2 / (sigma2 + tau2), 0 where they
cannot estimate it. The transferred part (amplitude applied) is multiplied by it; if
``match_detectable`` names a stage-100 output, a scale per context then makes the median count of
detectable genes equal the reference's, cis head included on both sides, as in ``pooling``. It acts
before the association and cis blocks, and cannot be combined with ``pooling``.

An optional ``expression_gate`` block sets to 0 every effect on a gene the context barely expresses
(reports/invii/prediction_t26_2026-09-29/):

    "expression_gate": {"basal": "processed/basal_sources_2026-09-26.csv", "min_cpm": 5.0}

``basal`` (relative to the data root) has a ``gene_name`` column and one column of control CPM per context
of the recipe; a gene whose CPM in that context is below ``min_cpm``, or missing, gets lfc 0 for every target,
the cis head included. It acts last, and changes nothing else: the ``observed`` mask is left as it is, so a
gated pair that a source measured is written as an observed 0 (stage 45 keeps the gene at its basal level).
It needs only the context's controls, so it applies unchanged to new contexts.

An optional ``common`` key says what ``gamma`` subtracts from each source (defect D9 of the dress
rehearsal, reports/invii/prova_generale_2026-09-28/):

    "common": "panel"                                  (the default)
    "common": "processed/<frozen common vectors>.npz"  (relative to the data root)

``panel`` is each source's mean response over the targets of its table in the cache
(`multisource.AxisTable.common`), so it moves with the panel the cache was built for: in the
rehearsal, K562's vector over a new panel had cosine 0.59 with the one over today's. A path names an
.npz with one vector per source of the recipe, keyed by source name, on the official axis (an
optional ``genes`` key must equal the axis), finite, which `mix` (or the EB pooling) subtracts
instead. The manifest records which, with the file's sha256.

Before any effect is computed, the panel and the cache are checked against each other (defects D2,
D3, D4, D11):

* ``--targets-csv`` is read by `vcc2026.panel.read_panel`: the ``target_gene`` column by name (a
  bare one-column list under any header, as used until 29 September 2026), first-seen order,
  duplicates dropped, the control label refused.
* ``--contexts D,E,F`` (comma or space separated), when given, refuses a recipe whose context keys
  differ from it.
* A cache folder with a ``manifest.json`` that records ``targets_sha256`` (stages 98 and 106 write
  it since 29 September 2026) must match `vcc2026.panel.panel_sha256` of the panel read: the
  cache's targets are then verified. A cache without one (r5 and r9 have no manifest) is not
  verified, and is refused if fewer than half the panel's targets are in any table the recipe
  reads: the rehearsal's negative control, the D/E/F
  panel on the A/B/C cache r9, had 30 of 300 and gave a near-empty prediction without an error. A
  verified cache is refused only if it covers no target. ``"allow_foreign_cache": true`` in the
  recipe lifts these refusals, and the manifest says so.

For each context this writes ``effects_<CTX>.npz`` with ``targets``, ``genes`` (the official
axis) and ``lfc`` (ln fold change, amplitude applied), the format stage 76 reads through
``--effects CTX=PATH``. A (target, gene) pair no source measured stays exactly 0 and is
counted as such in the manifest; a target no source covers is refused unless
``allow_missing_targets`` is true in the recipe (stage 76 would refuse it anyway).

The manifest records the recipe itself and two hashes of its file: ``recipe_sha256`` of the
bytes, which depends on the checkout's line endings, and ``recipe_sha256_lf`` with CRLF folded
to LF, which does not (D-043). Since 29 September 2026 it also records the argv, the UTC start
and end, the peak memory, the targets file (path, byte sha256, panel sha256, count), the result
of the cache check (verified or not, coverage), the sha256 of every cache npz read, and ``common``.

    python scripts/100_build_context_effects.py --recipe configs/recipes/t08.json \
        --cache <stage-98 cache> --out <dir> [--targets-csv <pert_counts.csv>] [--contexts D,E,F]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config  # noqa: E402
from vcc2026.bench import log  # noqa: E402
from vcc2026.genes import official_axis  # noqa: E402
from vcc2026.manifest import text_sha256  # noqa: E402
from vcc2026.multisource import AxisTable, eb_components, eb_pool, mix, zshrink_mixture, zshrink_table  # noqa: E402
from vcc2026.panel import CACHE_MANIFEST, panel_record, panel_sha256, read_panel  # noqa: E402
from vcc2026.predictor_sc import load_coordinates  # noqa: E402
from vcc2026.priors import add_cis, cis_prior, partner_effects  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402
from vcc2026.transfer_model import detectable_threshold, match_detectable, mixture_se  # noqa: E402

DATA_ROOT = config.paths().data_root  # VCC2026_DATA_ROOT, else configs/config.yaml
EFFECTS = ("shrunk", "raw", "zshrink")
COVERAGE_FLOOR = 0.5      # share of the panel an unverified cache must cover (defect D4)
CACHE_FILES_READ: set[Path] = set()   # every npz `load_table` opens, hashed into the manifest


def load_table(cache: Path, name: str, effect: str = "shrunk", shrink_k: float | None = None) -> AxisTable:
    """A stage-98 source, with the effect `mix` reads: stage-98 ``shrunk``, ``raw``, or
    ``zshrink`` recomputed from raw and SE at ``shrink_k``. Unmeasured pairs stay NaN.

    A mixture saved without SE (``cd4_mix``: meta ``from`` lists its parts) is rebuilt from
    its parts under ``zshrink``, each shrunk with its own SE; any other source lacking a
    finite SE on a measured pair is refused rather than turned into votes for zero."""
    CACHE_FILES_READ.add(cache / f"{name}.npz")
    z = np.load(cache / f"{name}.npz", allow_pickle=False)
    meta = json.loads(str(z["meta"]))
    tab = AxisTable(name, z["targets"].astype(str).tolist(), z["shrunk"], z["raw"], z["se"], z["n_cells"], meta)
    if effect == "raw":
        tab.shrunk = tab.raw
    elif effect == "zshrink":
        if shrink_k is None or not shrink_k > 0:
            raise ValueError(f"effect 'zshrink' needs a positive shrink_k, got {shrink_k!r}")
        measured = np.isfinite(tab.raw)
        if not np.isfinite(tab.se[measured]).any() and meta.get("from"):
            parts = [load_table(cache, part, "raw") for part in meta["from"]]
            return zshrink_mixture(name, parts, tab.targets, float(shrink_k))
        tab = zshrink_table(tab, float(shrink_k))
    return tab


def table_se(cache: Path, tab: AxisTable, targets: list[str]) -> np.ndarray:
    """SE rows of a source on ``targets``, NaN where unknown; a mixture saved without SE (meta
    ``from``) gets its parts' reliability-weighted SE."""
    measured = np.isfinite(tab.raw)
    if tab.meta.get("from") and not np.isfinite(tab.se[measured]).any():
        return mixture_se([load_table(cache, part, "raw") for part in tab.meta["from"]], targets, tab.raw.shape[1])
    ix = tab.index()
    out = np.full((len(targets), tab.raw.shape[1]), np.nan, dtype=np.float32)
    for i, t in enumerate(targets):
        if t in ix:
            out[i] = tab.se[ix[t]]
    return out


def eb_effects(cache: Path, tables: list[AxisTable], panel: list[str], gamma: float, spec: dict,
               basal: pd.DataFrame, common: dict | None = None) -> tuple[np.ndarray, np.ndarray, dict]:
    """(posterior mean of the shared response, sources measuring each pair, summary) for one context.
    ``common`` maps a source to the frozen vector ``gamma`` multiplies (`load_common`); by default each
    table's own mean over its targets."""
    factors = spec.get("se_factor", {})
    ys, ses, ks = [], [], []
    for tab in tables:
        m = tab.common() if common is None else common[tab.name]
        ys.append(tab.rows(panel).astype(np.float64) - gamma * m[None, :])
        ses.append(table_se(cache, tab, panel).astype(np.float64))
        ks.append(float(factors.get(tab.name, 1.0)))
    with np.errstate(all="ignore"):
        expr = np.log1p(np.nanmean(np.vstack([basal[t.name].to_numpy(dtype=float) for t in tables]), axis=0))
    sigma2, tau2 = eb_components(ys, ses, ks, expr, bin_weight=float(spec.get("bin_weight", 100.0)),
                                 n_bins=int(spec.get("bins", 50)))
    theta = eb_pool(ys, ses, ks, sigma2, tau2)
    n = np.sum([np.isfinite(y) & np.isfinite(se) for y, se in zip(ys, ses)], axis=0).astype(np.float64)
    ok = np.isfinite(expr)
    info = {"se_factor": {t.name: k for t, k in zip(tables, ks)}, "sigma2_median": float(np.median(sigma2[ok])),
            "tau2_median": float(np.median(tau2[ok])), "share_sigma2_above_tau2": float(np.mean(sigma2[ok] > tau2[ok]))}
    return theta, n, info


def load_gene_share(path: Path, axis: np.ndarray) -> np.ndarray:
    """A share in [0, 1] for every gene of ``axis``, from a CSV with columns ``gene`` and ``share``."""
    table = pd.read_csv(path)
    if table["gene"].duplicated().any():
        raise ValueError(f"{path}: a gene appears twice")
    share = table.set_index("gene")["share"].reindex(axis)
    if share.isna().any() or ((share < 0) | (share > 1)).any():
        raise ValueError(f"{path}: needs a share in [0, 1] for every gene of the official axis")
    return share.to_numpy(dtype=np.float64)


def apply_gene_share(eff: np.ndarray, share: np.ndarray, reference: np.ndarray | None = None,
                     offset: np.ndarray | None = None, cpm: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """``eff`` times the share of each gene; with a ``reference`` (a stage-100 lfc of the same context),
    scaled so that the median count of detectable genes, ``offset`` (the cis head) added on both sides,
    equals the reference's (`transfer_model.match_detectable`). Returns (effects, scale)."""
    out = np.asarray(eff, dtype=np.float64) * share[None, :]
    if reference is None:
        return out, 1.0
    _, scale = match_detectable(out, reference, detectable_threshold(cpm), cpm >= 5.0, offset=offset)
    return out * scale, scale


def apply_expression_gate(eff: np.ndarray, cpm: np.ndarray, min_cpm: float) -> tuple[np.ndarray, dict]:
    """``eff`` with every gene whose context CPM is below ``min_cpm`` (or NaN) set to 0 for all targets.
    Returns (effects, counts); the input is not modified."""
    cpm = np.asarray(cpm, dtype=np.float64)
    if cpm.shape != (eff.shape[1],):
        raise ValueError(f"expression gate: {cpm.shape[0]} CPM values for {eff.shape[1]} genes")
    low = ~(cpm >= float(min_cpm))
    out = np.array(eff, copy=True)
    energy = float(np.sum(np.asarray(eff, dtype=np.float64) ** 2))
    gated = float(np.sum(np.asarray(eff, dtype=np.float64)[:, low] ** 2))
    out[:, low] = 0
    return out, {"min_cpm": float(min_cpm), "genes_gated": int(low.sum()),
                 "genes_without_cpm": int(np.isnan(cpm).sum()),
                 "energy_share_gated": gated / energy if energy > 0 else 0.0}


def parse_contexts(values: list[str] | None) -> list[str] | None:
    """``--contexts`` as given, comma or space separated: ``D,E,F`` and ``D E F`` give the same list."""
    if values is None:
        return None
    out = [c for v in values for c in v.replace(",", " ").split()]
    if not out or len(set(out)) != len(out):
        raise SystemExit(f"--contexts needs distinct context labels, got {values!r}")
    return out


def check_contexts(recipe_contexts, expected: list[str] | None) -> None:
    """Refuse a recipe whose context keys are not exactly ``expected`` (when given), in any order."""
    if expected is not None and sorted(recipe_contexts) != sorted(expected):
        raise SystemExit(f"recipe contexts {sorted(recipe_contexts)} differ from --contexts {sorted(expected)}")


def check_cache_targets(cache: Path, panel: list[str], tables: list[AxisTable], allow_foreign: bool) -> dict:
    """Whether ``cache`` was built for ``panel``; refuses a cache that looks built for another (defect D4).

    Verified: the cache's ``manifest.json`` records ``targets_sha256`` and it equals
    `panel_sha256(panel)`; a different value is refused. Not verified (no manifest, or a manifest
    without that key): refused when fewer than `COVERAGE_FLOOR` of the panel's targets are in any of ``tables``. A
    verified cache is refused only when it covers no target. ``allow_foreign`` lifts every refusal."""
    info = {"cache_manifest": False, "targets_sha256_in_cache": None, "targets_verified": False,
            "allow_foreign_cache": allow_foreign}
    path = cache / CACHE_MANIFEST       # written by stages 98 and 106 (`vcc2026.panel.write_cache_manifest`)
    if path.is_file():
        info["cache_manifest"] = True
        info["cache_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        info["targets_sha256_in_cache"] = json.loads(path.read_text(encoding="utf-8")).get("targets_sha256")
    present = set().union(*(t.targets for t in tables))
    covered = sum(t in present for t in panel)
    info.update({"targets": len(panel), "targets_covered": covered, "coverage": covered / len(panel),
                 "targets_covered_by_table": {t.name: len(set(panel) & set(t.targets)) for t in tables}})
    problems = []
    if info["targets_sha256_in_cache"] is None:
        info["why_not_verified"] = ("the cache has no manifest.json" if not info["cache_manifest"]
                                    else "the cache's manifest.json has no targets_sha256")
        if info["coverage"] < COVERAGE_FLOOR:
            problems.append(f"its targets are not verified ({info['why_not_verified']}) and only {covered} of the "
                            f"{len(panel)} panel targets ({info['coverage']:.0%}) are in any table the recipe reads, "
                            f"under the floor of {COVERAGE_FLOOR:.0%}")
    elif info["targets_sha256_in_cache"] == panel_sha256(panel):
        info["targets_verified"] = True
        if covered == 0:
            problems.append("no panel target is in any table the recipe reads")
    else:
        info["why_not_verified"] = "targets_sha256 in the cache's manifest.json differs from the panel read"
        problems.append(f"it was built for other targets: its manifest.json records targets_sha256 "
                        f"{info['targets_sha256_in_cache']}, the panel read gives {panel_sha256(panel)}")
    if problems and not allow_foreign:
        raise SystemExit(f"cache {cache} looks built for another panel: {'; '.join(problems)}. Build a cache for "
                         "this --targets-csv, or set \"allow_foreign_cache\": true in the recipe.")
    info["refusals_lifted"] = problems
    return info


def load_common(spec, names: list[str], axis: np.ndarray) -> tuple[dict | None, dict]:
    """The response ``gamma`` subtracts from each source, from the recipe's ``common`` key (defect D9).

    ``None`` or ``"panel"``: each table's own mean over its targets in the cache, returned as None so
    `mix` and `eb_effects` compute it as before. A path (relative to the data root): an .npz with one
    finite vector on the official axis per source in ``names``, keyed by source name, and optionally
    ``genes``, which must equal the axis. Returns (vectors by source, or None; manifest entry)."""
    if spec is None or spec == "panel":
        return None, {"mode": "panel"}
    if not isinstance(spec, str):
        raise SystemExit(f"recipe common must be 'panel' or a path relative to the data root, got {spec!r}")
    path = DATA_ROOT / spec
    vectors = {}
    with np.load(path, allow_pickle=False) as z:
        if "genes" in z.files and z["genes"].astype(str).tolist() != axis.tolist():
            raise SystemExit(f"common {spec}: its genes are not the official axis")
        missing = [n for n in names if n not in z.files]
        if missing:
            raise SystemExit(f"common {spec}: no vector for sources {missing}")
        for n in names:
            v = np.asarray(z[n], dtype=np.float64)
            if v.shape != (axis.size,) or not np.isfinite(v).all():
                raise SystemExit(f"common {spec}: {n} needs {axis.size} finite values on the official axis, "
                                 f"got shape {v.shape}")
            vectors[n] = v
        unused = sorted(set(z.files) - set(names) - {"genes"})
    return vectors, {"mode": "frozen", "path": spec, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "norm": {n: float(np.linalg.norm(v)) for n, v in vectors.items()}, "unused_keys": unused}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--recipe", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--targets-csv", type=Path, default=DATA_ROOT / "raw/controls/pert_counts.csv")
    p.add_argument("--coords", type=Path, default=DATA_ROOT / "external/annotation/gene_coordinates_gencode_v50.tsv",
                   help="gene TSS coordinates (stage 74), read only when the recipe has a cis block")
    p.add_argument("--contexts", nargs="+", default=None,
                   help="the bundle's contexts, comma or space separated; the recipe's keys must be exactly these")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    CACHE_FILES_READ.clear()
    if (args.out / "manifest.json").exists():
        raise FileExistsError(f"{args.out} already holds effects; choose a new --out")
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    contexts_checked = parse_contexts(args.contexts)
    check_contexts(recipe["contexts"], contexts_checked)
    allow_foreign = recipe.get("allow_foreign_cache", False)
    if not isinstance(allow_foreign, bool):
        raise SystemExit(f"recipe allow_foreign_cache must be true or false, got {allow_foreign!r}")
    axis = np.asarray(official_axis().symbols)
    panel = read_panel(args.targets_csv)
    targets_info = panel_record(args.targets_csv, panel)
    gamma = float(recipe.get("gamma", 0.0))
    scale = float(recipe.get("reliability_scale", 100.0))
    names = sorted({s for c in recipe["contexts"].values() for s in c["weights"]})
    effect = recipe.get("effect", "shrunk")
    if effect not in EFFECTS:
        raise SystemExit(f"recipe effect must be one of {EFFECTS}, got {effect!r}")
    shrink_k = recipe.get("shrink_k")
    if effect == "zshrink" and not (isinstance(shrink_k, (int, float)) and shrink_k > 0):
        raise SystemExit(f"recipe effect 'zshrink' needs a positive number shrink_k, got {shrink_k!r}")
    pool_spec = recipe.get("pooling")
    if pool_spec is not None:
        if pool_spec.get("method") != "eb":
            raise SystemExit(f"recipe pooling method must be 'eb', got {pool_spec.get('method')!r}")
        if effect != "raw":
            raise SystemExit("recipe pooling 'eb' shrinks by itself and needs effect 'raw'")
        pool_basal = pd.read_csv(DATA_ROOT / pool_spec["basal"]).set_index("gene_name").reindex(axis)
    share_spec, share_vec, share_info = recipe.get("gene_share"), None, None
    if share_spec is not None:
        if pool_spec is not None:
            raise SystemExit("recipe gene_share and pooling cannot be combined")
        share_path = config.repo_file(share_spec["path"])
        share_vec = load_gene_share(share_path, axis)
        share_basal = (pd.read_csv(DATA_ROOT / share_spec["basal"]).set_index("gene_name").reindex(axis)
                       if share_spec.get("match_detectable") else None)
        share_info = {"spec": share_spec, "sha256": hashlib.sha256(share_path.read_bytes()).hexdigest(),
                      "genes_zero": int((share_vec == 0).sum()), "genes_one": int((share_vec == 1).sum()),
                      "median": float(np.median(share_vec))}
        log(f"gene share: {share_info['genes_zero']} genes at 0, median {share_info['median']:.3f}")
    gate_spec, gate_basal, gate_info = recipe.get("expression_gate"), None, None
    if gate_spec is not None:
        gate_path = DATA_ROOT / gate_spec["basal"]
        gate_basal = pd.read_csv(gate_path).set_index("gene_name").reindex(axis)
        absent = [c for c in recipe["contexts"] if c not in gate_basal.columns]
        if absent:
            raise SystemExit(f"expression_gate basal {gate_spec['basal']} has no CPM column for {absent}")
        gate_info = {"spec": gate_spec, "sha256": hashlib.sha256(gate_path.read_bytes()).hexdigest()}
    common, common_info = load_common(recipe.get("common"), names, axis)
    if common is not None:
        log(f"common: frozen vectors from {common_info['path']}, not the cache tables' own means")
    tables = [load_table(args.cache, n, effect, shrink_k) for n in names]
    cache_info = check_cache_targets(args.cache, panel, tables, allow_foreign)
    log(f"cache targets {'verified' if cache_info['targets_verified'] else 'NOT verified'}: "
        f"{cache_info['targets_covered']}/{len(panel)} panel targets in the recipe's tables"
        + (f"; allowed by the recipe despite: {cache_info['refusals_lifted']}" if cache_info["refusals_lifted"] else ""))
    args.out.mkdir(parents=True, exist_ok=True)
    cis_spec, cis_info = recipe.get("cis"), None
    if cis_spec is not None:
        pairs_path = config.repo_file(cis_spec["pairs"])
        cis_model = cis_prior(pd.read_csv(pairs_path), panel)
        coords = load_coordinates(args.coords)
        cis_info = {"spec": cis_spec, "pairs_sha256": hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
                    "coords": str(args.coords), "coords_sha256": hashlib.sha256(args.coords.read_bytes()).hexdigest(),
                    "edges_bp": list(cis_model.edges), "prior_ln_by_bin": cis_model.by_bin.tolist(),
                    "pairs_by_bin": cis_model.n_by_bin.tolist()}
        log("cis prior (ln, median by bin, panel targets excluded): "
            + " ".join(f"{e}:{v:+.3f}" for e, v in zip(cis_model.edges, cis_model.by_bin)))
    assoc_spec, assoc_info, assoc = recipe.get("association"), None, {}
    if assoc_spec is not None:
        paths = {k: DATA_ROOT / assoc_spec[k] for k in ("universe", "links", "info")}
        assoc, counts = partner_effects(panel, paths["universe"], paths["links"], paths["info"],
                                        int(assoc_spec.get("min_score", 700)), axis)
        assoc_info = {"spec": assoc_spec, **counts,
                      "sha256": {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in paths.items() if v.is_file()}}
        log(f"association: {counts['targets_with_partners']} panel targets have partners in the universe")
    summary = {}
    for ctx, spec in recipe["contexts"].items():
        weights = {k: float(v) for k, v in spec["weights"].items()}
        pool_info = None
        if pool_spec is None:
            eff, w = mix([t for t in tables if weights.get(t.name, 0) > 0], panel, weights=weights,
                         gamma=gamma, reliability_scale=scale, common=common)
            eff *= float(spec.get("amplitude", 1.0))
        else:
            eff, w, pool_info = eb_effects(args.cache, [t for t in tables if weights.get(t.name, 0) > 0], panel,
                                           gamma, pool_spec, pool_basal, common)
            factor = float(spec.get("amplitude", 1.0))
            if pool_spec.get("match_detectable"):
                ref = np.load(DATA_ROOT / pool_spec["match_detectable"] / f"effects_{ctx}.npz")
                if list(ref["targets"].astype(str)) != panel or list(ref["genes"].astype(str)) != list(axis):
                    raise SystemExit(f"{pool_spec['match_detectable']}: targets or genes differ for context {ctx}")
                offset = np.zeros(eff.shape, dtype=np.float32)
                if cis_spec is not None:
                    add_cis(offset, np.zeros(eff.shape, dtype=bool), panel, axis, cis_model, coords,
                            int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
                cpm = pool_basal[ctx].to_numpy(dtype=float)
                _, factor = match_detectable(eff, ref["lfc"], detectable_threshold(cpm), cpm >= 5.0, offset=offset)
            eff = eff.astype(np.float64) * factor
            pool_info["scale"] = factor
        share_scale = None
        if share_vec is not None:
            ref_lfc, offset, cpm = None, None, None
            if share_spec.get("match_detectable"):
                ref = np.load(DATA_ROOT / share_spec["match_detectable"] / f"effects_{ctx}.npz")
                if list(ref["targets"].astype(str)) != panel or list(ref["genes"].astype(str)) != list(axis):
                    raise SystemExit(f"{share_spec['match_detectable']}: targets or genes differ for context {ctx}")
                ref_lfc = ref["lfc"]
                offset = np.zeros(eff.shape, dtype=np.float32)
                if cis_spec is not None:
                    add_cis(offset, np.zeros(eff.shape, dtype=bool), panel, axis, cis_model, coords,
                            int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
                cpm = share_basal[ctx].to_numpy(dtype=float)
            eff, share_scale = apply_gene_share(eff, share_vec, ref_lfc, offset, cpm)
            log(f"{ctx}: gene share applied, scale {share_scale:.4f}")
        covered = (w > 0).any(axis=1)
        missing = [t for t, c in zip(panel, covered) if not c]
        if missing and not recipe.get("allow_missing_targets", False):
            raise SystemExit(f"context {ctx}: no source covers {len(missing)} targets, e.g. {missing[:5]}")
        observed = w > 0
        assoc_used = []
        if assoc_spec is not None:
            weight = float(assoc_spec.get("weight", 0.1))
            for i, t in enumerate(panel):
                if not covered[i] and t in assoc:
                    eff[i] += weight * assoc[t]
                    observed[i] |= assoc[t] != 0
                    assoc_used.append(t)
            log(f"{ctx}: association on {len(assoc_used)} uncovered targets")
        cis_counts = None
        if cis_spec is not None:
            cis_counts = add_cis(eff, observed, panel, axis, cis_model, coords,
                                 int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
            log(f"{ctx}: cis head on {cis_counts['pairs']} pairs of {cis_counts['targets_with_a_neighbour']} targets")
        gate_counts = None
        if gate_spec is not None:
            eff, gate_counts = apply_expression_gate(eff, gate_basal[ctx].to_numpy(dtype=float),
                                                     float(gate_spec["min_cpm"]))
            log(f"{ctx}: expression gate at {gate_counts['min_cpm']:g} CPM, {gate_counts['genes_gated']} genes set to 0, "
                f"{gate_counts['energy_share_gated']:.1%} of the squared effect")
        path = args.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(panel), genes=axis, lfc=eff.astype(np.float32),
                            observed=observed)
        nz = (eff != 0).sum(axis=1)
        summary[ctx] = {"weights": weights, "amplitude": spec.get("amplitude", 1.0),
                        "targets_covered": int(covered.sum()), "targets_missing": missing,
                        "genes_nonzero_median": float(np.median(nz)),
                        "abs_lfc_q99_median": float(np.median(np.quantile(np.abs(eff), 0.99, axis=1))),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if cis_counts is not None:
            summary[ctx]["cis"] = cis_counts
        if pool_info is not None:
            summary[ctx]["pooling"] = pool_info
        if share_scale is not None:
            summary[ctx]["gene_share_scale"] = share_scale
        if assoc_spec is not None:
            summary[ctx]["association_targets"] = assoc_used
        if gate_counts is not None:
            summary[ctx]["expression_gate"] = gate_counts
        log(f"{ctx}: {covered.sum()}/{len(panel)} targets, median {np.median(nz):.0f} genes moved, "
            f"median q99 |ln fc| {summary[ctx]['abs_lfc_q99_median']:.3f}")
    manifest = {"stage": "100_build_context_effects", "written_utc": datetime.now(timezone.utc).isoformat(),
                "recipe": recipe, "recipe_sha256": hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
                "recipe_sha256_lf": text_sha256(args.recipe),
                "cache": str(args.cache), "gamma": gamma, "reliability_scale": scale, "contexts": summary,
                "units": "ln fold change on the official axis; unmeasured pairs are exactly 0",
                "argv": sys.argv, "started_utc": started, "targets": targets_info, "contexts_checked": contexts_checked,
                "cache_check": cache_info, "common": common_info,
                "cache_npz_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(CACHE_FILES_READ)}}
    if cis_info is not None:
        manifest["cis"] = cis_info
    if assoc_info is not None:
        manifest["association"] = assoc_info
    if share_info is not None:
        manifest["gene_share"] = share_info
    if gate_info is not None:
        manifest["expression_gate"] = gate_info
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["peak_rss_bytes"] = peak_rss_bytes()
    with open(args.out / "manifest.json", "x", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"wrote {args.out}")


if __name__ == "__main__":
    main()
