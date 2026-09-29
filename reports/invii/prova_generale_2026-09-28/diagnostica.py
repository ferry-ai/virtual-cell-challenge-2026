"""Step 7 of the dress rehearsal: coverage, gamma and amplitude diagnostics (no stage; small arrays).

Four sections, each run when its inputs are given, all written to one new JSON (``--out``). None
of them changes an effect or a prediction: the rehearsal generates at t22's 1.576 (RISULTATI.md).

coverage   (``--effects``: stage 100's output on the fake panel) Per context and per stratum of
           ``bersagli.csv``: targets covered by a source (the manifest's ``targets_missing``) against
           the prediction from the draw (a target is expected covered when a t22 source has it); rows
           that are all zero; uncovered targets with a nonzero entry (the cis head alone); P0 targets
           whose own gene is 0. Registered prediction 4: 270/300 covered (P1 and P3), 0/30 in P0,
           own gene 0 in P0. With ``--negative-control``, that run's covered targets (prediction 6:
           about 30).

gamma      (``--cache-new``, ``--cache-today``, ``--universes``) Per source, the vector gamma = 1
           subtracts (`multisource.AxisTable.common`: the mean ``shrunk`` over the table's targets):
           G-a over the fake panel's cache (what stage 100 used), G-b over today's panel (r9, frozen),
           G-c over every universe target (streamed one chunk at a time). Cosine, norm ratio and the
           amplitude times the largest, median and 99th-percentile absolute difference. With
           ``--effects``: the fake run is re-mixed with `multisource.mix` under G-a (checked against
           stage 100's own lfc), G-b and G-c, the cis head added as stage 100 adds it, and the
           (target, gene) pairs on genes >= 5 CPM whose detectable status (|lfc| > 4/sqrt(400 mu),
           `transfer_model.detectable_threshold`) flips are counted per context.

p3         (``--reference-p3``: t25's effects, today's panel on r9) The P3 targets' lfc in the fake
           run against t25, context by context through the draw's mapping, split into the gamma part
           (amplitude x (G-a mix - G-b mix)) and the rest (the cis prior, refitted by stage 100 without
           the other panel's targets, and any difference of the source rows).

amplitude  (``--reference-effects``: t22's effects on today's panel; the CPM files) The rules of
           RISULTATI.md, none used for generation. N_det(c; s, E, K) is the median over targets of the
           genes >= 5 CPM in c with |s E + K| above the threshold, E the transferred part at
           amplitude 1 and K the cis head, recomputed here as stage 100 adds it and kept outside
           the scale, as in `match_detectable`.
           - R-B: one s for the new contexts with mean_c N_det(c; s, E_t22, K_t22) equal to the mean
             over A/B/C of N_det at the reference amplitude (1.576). Prediction 5: 1.576 +- 0.001 on
             the copies.
           - R-C: as R-B with the fake run's own E and K.
           - R-D: one s per context, each reaching the same reference mean (also for A/B/C).
           - R-E: R-B with each context's median control library size in place of 20,000 UMI, on
             both sides (needs the ``cpm_contesti.py`` JSONs).
           The solver is match_detectable's geometric bisection (1e-3..1e4, 60 steps), which gives
           the lower edge ``s_cross`` where the count reaches the target; it also finds the upper
           edge. N_det is a step function, so when a whole interval meets the target exactly, the
           rule's value ``s`` is the point of that interval closest to the reference amplitude (the
           fixed point is then exact); otherwise ``s`` is ``s_cross``. Both edges are reported.

    scripts/py.cmd reports/invii/prova_generale_2026-09-28/diagnostica.py ^
        --effects <data_root>/processed/effects_prova_t22_2026-09-28 ^
        --cache-new <data_root>/processed/multisource_prova_2026-09-28_me1 ^
        --cache-today <data_root>/processed/multisource_2026-09-27_r9 --universes me1 ^
        --reference-p3 <data_root>/processed/effects_t25_2026-09-27 ^
        --reference-effects <data_root>/processed/effects_t22_2026-09-26 ^
        --cpm-new <data_root>/interim/prova_generale_2026-09-28/basal_cpm_DEF.csv ^
        --negative-control <data_root>/processed/effects_prova_controllo_negativo_2026-09-28 ^
        --out reports/invii/prova_generale_2026-09-28/diagnostica.json

Memory: the four panel tables (``shrunk`` only, about 22 MB each), one universe chunk at a time, the
mixes in blocks of 50 targets and a few (targets x genes) arrays: 370 MiB peak measured on 28/09 on a
smoke run (t22's effects re-mixed from the u26 parity cache, G-c streamed for K562 only), 35 s.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from comune import (  # noqa: E402
    HERE, REPO, SOURCES_ME1, SOURCES_U26, chunk_path, data_root, read_index, sha256_file, write_new_json,
)
from vcc2026.multisource import AxisTable, mix  # noqa: E402
from vcc2026.resources import peak_rss_bytes  # noqa: E402
from vcc2026.transfer_model import detectable_threshold  # noqa: E402

GATE_CPM = 5.0


# --- inputs -------------------------------------------------------------------------------------

def load_effects(folder: Path, ctx: str) -> dict:
    with np.load(folder / f"effects_{ctx}.npz", allow_pickle=False) as z:
        return {"targets": z["targets"].astype(str).tolist(), "genes": z["genes"].astype(str),
                "lfc": z["lfc"], "observed": z["observed"]}


def load_manifest(folder: Path) -> dict:
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


def light_table(cache: Path, name: str) -> AxisTable:
    """A stage-98 table with only ``shrunk`` loaded (raw and se point at it: `mix` and `common` read
    ``shrunk`` and ``n_cells`` alone)."""
    with np.load(cache / f"{name}.npz", allow_pickle=False) as z:
        shrunk = z["shrunk"]
        return AxisTable(name, z["targets"].astype(str).tolist(), shrunk, shrunk, shrunk, z["n_cells"],
                         json.loads(str(z["meta"])))


def universe_common(universe: Path, name: str) -> tuple[np.ndarray, dict]:
    """`AxisTable.common` over every target of a universe table, one chunk at a time."""
    ix = read_index(universe)
    files = sorted({chunk_path(universe, name, c) for c in ix["chunk"]})
    total, count, targets, absent = None, None, 0, []
    for path in files:
        if not path.exists():
            absent.append(path.name)
            continue
        with np.load(path, allow_pickle=False) as z:
            sh = z["shrunk"]
        if total is None:
            total = np.zeros(sh.shape[1], dtype=np.float64)
            count = np.zeros(sh.shape[1], dtype=np.int64)
        total += np.nansum(sh, axis=0, dtype=np.float64)
        count += np.isfinite(sh).sum(axis=0)
        targets += sh.shape[0]
        del sh
    if total is None:
        raise SystemExit(f"{universe}: no chunk of table {name}")
    vec = np.divide(total, count, out=np.zeros(total.size), where=count > 0)
    return vec, {"universe": str(universe), "chunks": len(files), "chunks_absent": absent, "targets": targets}


class Cis:
    """The cis head stage 100 adds after the amplitude, kept sparse: (row, column, float64 value)."""

    def __init__(self, dense: np.ndarray):
        self.shape = dense.shape
        self.rows, self.cols = np.nonzero(dense)
        self.vals = dense[self.rows, self.cols]

    def add_to(self, arr: np.ndarray, sign: float = 1.0) -> np.ndarray:
        """In place, as `priors.add_cis` adds it (each pair once, in float64 when ``arr`` is)."""
        arr[self.rows, self.cols] += sign * self.vals
        return arr

    def dense(self, gate: np.ndarray | None = None) -> np.ndarray:
        out = np.zeros(self.shape, dtype=np.float32)
        out[self.rows, self.cols] = self.vals
        return out if gate is None else out[:, gate]


def cis_head(panel: list[str], axis: np.ndarray, cis_spec: dict | None, coords: Path) -> tuple[Cis, dict]:
    """Stage 100's cis head for ``panel``: the prior refitted without the panel's targets (`priors`)."""
    K = np.zeros((len(panel), axis.size), dtype=np.float64)
    if not cis_spec:
        return Cis(K), {"cis": None}
    from vcc2026 import config
    from vcc2026.predictor_sc import load_coordinates
    from vcc2026.priors import add_cis, cis_prior

    model = cis_prior(pd.read_csv(config.repo_file(cis_spec["pairs"])), panel)
    counts = add_cis(K, np.zeros(K.shape, dtype=bool), panel, axis, model, load_coordinates(coords),
                     int(cis_spec["max_distance_bp"]), float(cis_spec.get("scale", 1.0)))
    return Cis(K), {"prior_ln_by_bin": [float(v) for v in model.by_bin], **counts}


class Cpm:
    """CPM columns by context: the new contexts' file first, then the reference file."""

    def __init__(self, axis: np.ndarray, new: Path | None, ref: Path | None, simulate: dict | None = None):
        self.cols, self.src = {}, {}
        for path, tag in ((ref, "reference"), (new, "new")):
            if path is not None and path.exists():
                frame = pd.read_csv(path).set_index("gene_name").reindex(axis)
                for c in frame.columns:
                    self.cols[c], self.src[c] = frame[c].to_numpy(dtype=np.float64), f"{tag}: {path}"
        for new_ctx, old in (simulate or {}).items():
            if old in self.cols and new_ctx not in self.cols:
                self.cols[new_ctx] = self.cols[old]
                self.src[new_ctx] = f"simulated copy of {old} (--simulate-copies)"

    def gate_threshold(self, ctx: str, umi: float = 20000.0) -> tuple[np.ndarray, np.ndarray]:
        if ctx not in self.cols:
            raise SystemExit(f"no CPM for context {ctx}: give --cpm-new or --cpm-ref with that column")
        cpm = np.nan_to_num(self.cols[ctx], nan=0.0)
        return cpm >= GATE_CPM, detectable_threshold(cpm, umi_per_cell=umi)


# --- small numerics -----------------------------------------------------------------------------

def compare_vectors(a: np.ndarray, b: np.ndarray, amp: float) -> dict:
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    d = amp * np.abs(a - b)
    return {"cosine": float(a @ b / (na * nb)) if na > 0 and nb > 0 else None,
            "norm_ratio": na / nb if nb > 0 else None, "amp_max_abs_diff": float(d.max()),
            "amp_median_abs_diff": float(np.median(d)), "amp_q99_abs_diff": float(np.quantile(d, 0.99))}


def mix_blocks(tables, targets: list[str], block: int = 50, **kwargs) -> np.ndarray:
    """`multisource.mix` over blocks of targets: each row is computed alone, in the same order over
    sources, so the rows are the ones a single call gives, for about a sixth of its transient memory."""
    out = np.zeros((len(targets), tables[0].shrunk.shape[1]), dtype=np.float64)
    for lo in range(0, len(targets), block):
        eff, _ = mix(tables, targets[lo:lo + block], **kwargs)
        out[lo:lo + block] = eff
        del eff
    return out


def detectable(lfc: np.ndarray, gate: np.ndarray, thr: np.ndarray) -> np.ndarray:
    return np.abs(lfc[:, gate]) > thr[gate][None, :]


def n_det(E: np.ndarray, K: np.ndarray, s: float, thr: np.ndarray) -> float:
    """Median over rows of the count of |s E + K| > thr; E, K and thr already restricted to the gate."""
    return float(np.median((np.abs(s * E + K) > thr[None, :]).sum(axis=1)))


def solve(f, target: float, reference: float, lo: float = 1e-3, hi: float = 1e4, steps: int = 60) -> dict:
    """The amplitude at which ``f`` meets ``target`` (see the module docstring for the convention)."""
    a, b = lo, hi
    for _ in range(steps):
        mid = float(np.sqrt(a * b))
        a, b = (mid, b) if f(mid) < target else (a, mid)
    s_cross = b                          # smallest s found with f(s) >= target
    a, b = lo, hi
    for _ in range(steps):
        mid = float(np.sqrt(a * b))
        a, b = (mid, b) if f(mid) <= target else (a, mid)
    s_upper = a                          # largest s found with f(s) <= target
    exact = f(s_cross) == target and s_cross <= s_upper
    s = float(min(max(reference, s_cross), s_upper)) if exact else s_cross
    return {"s": s, "s_cross": s_cross, "s_upper": s_upper, "exact_level": bool(exact),
            "f_at_s": f(s), "target": target}


# --- sections ------------------------------------------------------------------------------------

def section_coverage(effects: Path, bersagli: pd.DataFrame, negative: Path | None) -> dict:
    man = load_manifest(effects)
    out = {"effects": str(effects), "per_context": {}}
    for ctx, info in man["contexts"].items():
        z = load_effects(effects, ctx)
        targets, lfc, genes = z["targets"], z["lfc"], z["genes"]
        col = {g: i for i, g in enumerate(genes)}
        missing = set(info["targets_missing"])
        rows = []
        for i, t in enumerate(targets):
            r = bersagli.loc[t] if t in bersagli.index else None
            own = col.get(t)
            rows.append({"target": t, "stratum": None if r is None else r["stratum"],
                         "expected_covered": None if r is None else bool(r["n_sources"] > 0),
                         "covered": t not in missing, "all_zero": bool(not np.any(lfc[i])),
                         "own_gene_zero": None if own is None else bool(lfc[i, own] == 0)})
        frame = pd.DataFrame(rows)
        frame["uncovered_nonzero"] = ~frame["covered"] & ~frame["all_zero"]
        by = {}
        for stratum, g in frame.groupby("stratum", dropna=False):
            by[str(stratum)] = {"targets": int(len(g)), "expected_covered": int(g["expected_covered"].sum()),
                                "covered": int(g["covered"].sum()), "all_zero_rows": int(g["all_zero"].sum()),
                                "uncovered_with_cis_only": int(g["uncovered_nonzero"].sum()),
                                "own_gene_zero": int(g["own_gene_zero"].fillna(False).sum()),
                                "own_gene_on_axis": int(g["own_gene_zero"].notna().sum())}
        p0 = frame[frame["stratum"] == "P0"]
        out["per_context"][ctx] = {
            "targets": len(targets), "covered": int(frame["covered"].sum()),
            "covered_as_expected": bool((frame["covered"] == frame["expected_covered"]).all()),
            "all_zero_rows": int(frame["all_zero"].sum()), "by_stratum": by,
            "manifest_targets_covered": info["targets_covered"], "manifest_cis": info.get("cis"),
            "prediction_4": {"covered_270": int(frame["covered"].sum()) == 270,
                             "p0_covered_0": int(p0["covered"].sum()) == 0,
                             "p0_own_gene_zero_all": bool(p0["own_gene_zero"].fillna(False).all()) and len(p0) > 0}}
    if negative is not None:
        neg = load_manifest(negative)
        out["negative_control"] = {"effects": str(negative), "cache": neg.get("cache"),
                                   "targets_covered": {c: v["targets_covered"] for c, v in neg["contexts"].items()},
                                   "targets_missing": {c: len(v["targets_missing"]) for c, v in neg["contexts"].items()}}
    return out


def section_gamma(args, recipe: dict, cpm: Cpm, p3: list[str]) -> tuple[dict, dict]:
    names = sorted({s for c in recipe["contexts"].values() for s in c["weights"]})
    gamma, scale = float(recipe.get("gamma", 0.0)), float(recipe.get("reliability_scale", 100.0))
    amp0 = float(next(iter(recipe["contexts"].values())).get("amplitude", 1.0))
    tables = {n: light_table(args.cache_new, n) for n in names}
    commons = {"G-a": {n: t.common() for n, t in tables.items()}}
    if args.cache_today is not None:
        commons["G-b"] = {}
        for n in names:
            commons["G-b"][n] = light_table(args.cache_today, n).common()
    universes = {}
    if args.universes != "none":
        preset = SOURCES_ME1 if args.universes == "me1" else SOURCES_U26
        universes = {n: data_root() / "processed" / preset[n] for n in names if n in preset}
    for spec in args.universe:
        n, _, path = spec.partition("=")
        universes[n] = Path(path)
    if args.sources:     # a smoke run streams fewer universes; the other sources keep G-a inside G-c
        universes = {n: u for n, u in universes.items() if n in args.sources}
    universes_read = {}
    if universes:
        commons["G-c"] = {}
        for n, u in universes.items():
            if n in names:
                commons["G-c"][n], universes_read[n] = universe_common(u, n)
                info = universes_read[n]
                print(f"G-c {n}: {info['targets']} universe targets, {info['chunks']} chunks, "
                      f"{len(info['chunks_absent'])} absent", flush=True)
    out = {"gamma": gamma, "amplitude": amp0, "cache_new": str(args.cache_new),
           "cache_today": None if args.cache_today is None else str(args.cache_today),
           "universes": universes_read, "per_source": {}}
    for n in names:
        rec = {"targets_in_new_table": len(tables[n].targets)}
        for x, y in (("G-a", "G-b"), ("G-a", "G-c"), ("G-b", "G-c")):
            if x in commons and y in commons and n in commons[x] and n in commons[y]:
                rec[f"{x} vs {y}"] = compare_vectors(commons[x][n], commons[y][n], amp0)
        out["per_source"][n] = rec
    p3_rows = {}
    if args.effects is not None:
        man = load_manifest(args.effects)
        first = next(iter(man["contexts"]))
        z = load_effects(args.effects, first)
        panel, axis = z["targets"], z["genes"]
        del z
        K, cis_info = cis_head(panel, axis, recipe.get("cis"), args.coords)
        out["cis"] = cis_info
        pos = [panel.index(t) for t in p3 if t in panel]
        out["flips"] = {}
        groups: dict[tuple, list[str]] = {}     # contexts sharing weights share the mixes
        for ctx, spec in recipe["contexts"].items():
            if ctx in man["contexts"]:
                groups.setdefault(tuple(sorted((k, float(v)) for k, v in spec["weights"].items())), []).append(ctx)
        for key, ctxs in groups.items():
            weights = dict(key)
            used = [tables[n] for n in names if weights.get(n, 0) > 0]
            amps = {c: float(recipe["contexts"][c].get("amplitude", 1.0)) for c in ctxs}
            eff = mix_blocks(used, panel, weights=weights, gamma=gamma, reliability_scale=scale, common=commons["G-a"])
            p3_a = eff[pos].copy()                     # float64 rows for the P3 split
            lfc_a, det_a = {}, {}
            for c in ctxs:
                x = eff * amps[c]                      # as stage 100: amplitude, then the cis head
                lfc_a[c] = K.add_to(x).astype(np.float32)
                del x
                stage = load_effects(args.effects, c)["lfc"]
                gate, thr = cpm.gate_threshold(c)
                det_a[c] = detectable(lfc_a[c], gate, thr)
                out["flips"][c] = {"reproduces_stage100_max_abs_diff": float(np.max(np.abs(lfc_a[c] - stage))),
                                   "reproduces_stage100_exactly": bool(np.array_equal(lfc_a[c], stage)),
                                   "genes_at_5_cpm": int(gate.sum()),
                                   "n_det_median": {"G-a": float(np.median(det_a[c].sum(axis=1)))}}
                del stage
            del eff, lfc_a
            for variant, common in commons.items():
                if variant == "G-a":
                    continue
                eff = mix_blocks(used, panel, weights=weights, gamma=gamma, reliability_scale=scale, common=common)
                if variant == "G-b" and pos:
                    for c in ctxs:
                        p3_rows[c] = {"targets": [panel[i] for i in pos], "gamma_part": amps[c] * (p3_a - eff[pos])}
                for c in ctxs:
                    x = eff * amps[c]
                    lfc_v = K.add_to(x).astype(np.float32)
                    del x
                    gate, thr = cpm.gate_threshold(c)
                    det_v = detectable(lfc_v, gate, thr)
                    rec = out["flips"][c]
                    rec[f"flips_G-a_to_{variant}"] = int((det_a[c] != det_v).sum())
                    rec[f"flips_G-a_to_{variant}_per_target_median"] = float(np.median((det_a[c] != det_v).sum(axis=1)))
                    rec["n_det_median"][variant] = float(np.median(det_v.sum(axis=1)))
                    del lfc_v, det_v
                del eff
            del det_a, used
        del K
    return out, p3_rows


def section_p3(args, recipe_manifest: dict, p3_rows: dict, mapping: dict, p3: list[str]) -> dict:
    ref_man = load_manifest(args.reference_p3)
    out = {"reference": str(args.reference_p3), "cis_prior_ln_by_bin": {
        "fake_run": (recipe_manifest.get("cis") or {}).get("prior_ln_by_bin"),
        "reference": (ref_man.get("cis") or {}).get("prior_ln_by_bin")}, "per_context": {}}
    for ctx in recipe_manifest["contexts"]:
        ref_ctx = mapping.get(ctx, ctx)
        fake = load_effects(args.effects, ctx)
        ref = load_effects(args.reference_p3, ref_ctx)
        fi = {t: i for i, t in enumerate(fake["targets"])}
        ri = {t: i for i, t in enumerate(ref["targets"])}
        both = [t for t in p3 if t in fi and t in ri]
        a = fake["lfc"][[fi[t] for t in both]].astype(np.float64)
        b = ref["lfc"][[ri[t] for t in both]].astype(np.float64)
        delta = a - b
        rec = {"reference_context": ref_ctx, "targets": len(both), "max_abs_delta": float(np.abs(delta).max()),
               "pairs_above_1e-6": int((np.abs(delta) > 1e-6).sum()),
               "observed_mismatches": int((fake["observed"][[fi[t] for t in both]]
                                           != ref["observed"][[ri[t] for t in both]]).sum())}
        if ctx in p3_rows:
            order = [p3_rows[ctx]["targets"].index(t) for t in both]
            g = p3_rows[ctx]["gamma_part"][order]
            rest = delta - g
            rec.update({"max_abs_gamma_part": float(np.abs(g).max()), "max_abs_rest": float(np.abs(rest).max()),
                        "pairs_rest_above_1e-6": int((np.abs(rest) > 1e-6).sum())})
        out["per_context"][ctx] = rec
    return out


def split_effects(folder: Path, ctx: str, K: Cis, amp: float) -> np.ndarray:
    """E, the transferred part at amplitude 1: (lfc - cis head) / amplitude."""
    lfc = K.add_to(load_effects(folder, ctx)["lfc"].astype(np.float64), -1.0)
    lfc /= amp
    return lfc.astype(np.float32)


def section_amplitude(args, recipe: dict, cpm: Cpm, mapping: dict, libraries: dict) -> dict:
    ref_recipe = json.loads(args.reference_recipe.read_text(encoding="utf-8"))
    ref_man = load_manifest(args.reference_effects)
    ref_ctx = list(ref_man["contexts"])
    z = load_effects(args.reference_effects, ref_ctx[0])
    panel, axis = z["targets"], z["genes"]
    del z
    K_ref, cis_ref = cis_head(panel, axis, ref_recipe.get("cis"), args.coords)
    amp_ref = {c: float(ref_recipe["contexts"][c].get("amplitude", 1.0)) for c in ref_ctx}
    E_ref, same = {}, True
    for c in ref_ctx:
        E = split_effects(args.reference_effects, c, K_ref, amp_ref[c])
        first = E_ref.get(ref_ctx[0])
        if first is not None and np.array_equal(first, E):
            E = first            # t22's contexts are byte-identical: keep one copy
        elif first is not None:
            same = False
        E_ref[c] = E
    reference_amp = float(np.median(list(amp_ref.values())))
    new_ctx = list(recipe["contexts"])

    def e_for(c):   # the t22 effects a new context is scored with: its source context, else the first
        return E_ref.get(mapping.get(c, c), E_ref[ref_ctx[0]])

    def gated(E, K, c, umi=20000.0):
        gate, thr = cpm.gate_threshold(c, umi)
        return E[:, gate], K.dense(gate), thr[gate]

    out = {"reference_effects": str(args.reference_effects), "reference_contexts": ref_ctx,
           "reference_amplitudes": amp_ref, "reference_effects_identical_across_contexts": same,
           "cis_reference": cis_ref, "cpm_sources": {c: cpm.src.get(c) for c in [*ref_ctx, *new_ctx]}}

    ref_parts = {c: gated(E_ref[c], K_ref, c) for c in ref_ctx}
    per_ref = {c: n_det(*ref_parts[c][:2], amp_ref[c], ref_parts[c][2]) for c in ref_ctx}
    target = float(np.mean(list(per_ref.values())))
    out["reference_n_det"] = {"per_context": per_ref, "mean": target}
    del ref_parts

    new_parts = {c: gated(e_for(c), K_ref, c) for c in new_ctx}
    f_b = lambda s: float(np.mean([n_det(E, K, s, thr) for E, K, thr in new_parts.values()]))  # noqa: E731
    out["R-B"] = solve(f_b, target, reference_amp)
    out["R-D"] = {"per_context": {}}
    for c, (E, K, thr) in new_parts.items():
        out["R-D"]["per_context"][c] = solve(lambda s, E=E, K=K, thr=thr: n_det(E, K, s, thr), target, reference_amp)
    for c in ref_ctx:
        if c in new_parts:
            continue
        E, K, thr = gated(E_ref[c], K_ref, c)
        out["R-D"]["per_context"][c] = solve(lambda s, E=E, K=K, thr=thr: n_det(E, K, s, thr), target, reference_amp)
        del E, K, thr
    del new_parts
    out["prediction_5"] = {"s": out["R-B"]["s"], "within_0.001": abs(out["R-B"]["s"] - 1.576) <= 1e-3,
                           "s_cross_within_0.001": abs(out["R-B"]["s_cross"] - 1.576) <= 1e-3}

    if libraries and all(c in libraries for c in [*ref_ctx, *new_ctx]):
        ref_parts = {c: gated(E_ref[c], K_ref, c, libraries[c]) for c in ref_ctx}
        target_e = float(np.mean([n_det(E, K, amp_ref[c], thr) for c, (E, K, thr) in ref_parts.items()]))
        del ref_parts
        parts = {c: gated(e_for(c), K_ref, c, libraries[c]) for c in new_ctx}
        f_e = lambda s: float(np.mean([n_det(E, K, s, thr) for E, K, thr in parts.values()]))  # noqa: E731
        out["R-E"] = {"median_library_sizes": {c: libraries[c] for c in [*ref_ctx, *new_ctx]},
                      "reference_mean": target_e, **solve(f_e, target_e, reference_amp)}
        del parts
    else:
        out["R-E"] = {"skipped": "needs the median library size of every context (--libraries: cpm_contesti.py JSONs)"}

    if args.effects is not None:
        man = load_manifest(args.effects)
        z = load_effects(args.effects, next(iter(man["contexts"])))
        panel_new = z["targets"]
        del z
        K_new, cis_new = cis_head(panel_new, axis, recipe.get("cis"), args.coords)
        parts = {}
        for c in new_ctx:
            if c in man["contexts"]:
                E_new = split_effects(args.effects, c, K_new, float(recipe["contexts"][c].get("amplitude", 1.0)))
                parts[c] = gated(E_new, K_new, c)
                del E_new
        f_c = lambda s: float(np.mean([n_det(E, K, s, thr) for E, K, thr in parts.values()]))  # noqa: E731
        out["R-C"] = {"cis_new": cis_new, **solve(f_c, target, reference_amp)}
        del parts, K_new
    else:
        out["R-C"] = {"skipped": "needs --effects (the fake run)"}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    root = data_root()
    ap.add_argument("--out", type=Path, required=True, help="a new JSON")
    ap.add_argument("--recipe", type=Path, default=HERE / "ricetta_t22_DEF.json")
    ap.add_argument("--reference-recipe", type=Path, default=REPO / "configs" / "recipes" / "t22.json")
    ap.add_argument("--bersagli", type=Path, default=HERE / "bersagli.csv")
    ap.add_argument("--estrazione", type=Path, default=HERE / "estrazione.json")
    ap.add_argument("--effects", type=Path, default=None, help="stage 100's output on the fake panel")
    ap.add_argument("--negative-control", type=Path, default=None)
    ap.add_argument("--cache-new", type=Path, default=None, help="the cache the fake run used (G-a)")
    ap.add_argument("--cache-today", type=Path, default=None, help="today's panel cache, r9 (G-b)")
    ap.add_argument("--universes", choices=["me1", "u26", "none"], default="none", help="G-c preset")
    ap.add_argument("--universe", action="append", default=[], metavar="NAME=DIR", help="G-c, overrides a preset")
    ap.add_argument("--sources", nargs="*", default=None,
                    help="stream G-c only for these tables (a smoke run); the others keep G-a in the G-c mix")
    ap.add_argument("--reference-p3", type=Path, default=None, help="t25's effects (today's panel, r9)")
    ap.add_argument("--reference-effects", type=Path, default=None, help="t22's effects (today's panel)")
    ap.add_argument("--cpm-ref", type=Path, default=root / "interim" / "basal_cpm_by_context.csv")
    ap.add_argument("--cpm-new", type=Path, default=None, help="cpm_contesti.py's CSV for the new contexts")
    ap.add_argument("--libraries", nargs="*", type=Path, default=[],
                    help="cpm_contesti.py JSONs: median library sizes for R-E")
    ap.add_argument("--simulate-copies", action="store_true",
                    help="without --cpm-new, give each new context its source's reference CPM (a smoke run)")
    ap.add_argument("--coords", type=Path, default=root / "external/annotation/gene_coordinates_gencode_v50.tsv")
    args = ap.parse_args()
    t0 = time.time()
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; choose a new --out")
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    mapping = json.loads(args.estrazione.read_text(encoding="utf-8")).get("mapping_new_to_old", {}) \
        if args.estrazione.exists() else {}
    bersagli = pd.read_csv(args.bersagli).set_index("target_gene")
    p3 = sorted(bersagli.index[bersagli["stratum"] == "P3"])

    axis_source = args.effects or args.reference_effects
    if axis_source is None:
        raise SystemExit("give --effects or --reference-effects")
    z = load_effects(axis_source, next(iter(load_manifest(axis_source)["contexts"])))
    axis = z["genes"]
    del z
    cpm = Cpm(axis, args.cpm_new, args.cpm_ref, mapping if args.simulate_copies else None)
    libraries = {}
    for path in args.libraries:
        for c, facts in json.loads(path.read_text(encoding="utf-8"))["per_context"].items():
            libraries[c] = float(facts["median_library_size"])

    report = {"script": "reports/invii/prova_generale_2026-09-28/diagnostica.py", "argv": sys.argv[1:],
              "recipe": str(args.recipe), "recipe_sha256": sha256_file(args.recipe), "mapping_new_to_old": mapping,
              "note": "diagnostics only: nothing here changes an effect or a prediction",
              "peak_rss_bytes_after": {"inputs": peak_rss_bytes()}}
    if args.effects is not None:
        report["coverage"] = section_coverage(args.effects, bersagli, args.negative_control)
        report["peak_rss_bytes_after"]["coverage"] = peak_rss_bytes()
        print(json.dumps({c: {k: v[k] for k in ("covered", "all_zero_rows", "prediction_4")}
                          for c, v in report["coverage"]["per_context"].items()}), flush=True)
    p3_rows = {}
    if args.cache_new is not None:
        report["gamma"], p3_rows = section_gamma(args, recipe, cpm, p3)
        report["peak_rss_bytes_after"]["gamma"] = peak_rss_bytes()
        print(json.dumps({n: {k: (v.get("cosine") if isinstance(v, dict) else v) for k, v in r.items()}
                          for n, r in report["gamma"]["per_source"].items()}), flush=True)
    if args.reference_p3 is not None and args.effects is not None:
        report["p3"] = section_p3(args, load_manifest(args.effects), p3_rows, mapping, p3)
        report["peak_rss_bytes_after"]["p3"] = peak_rss_bytes()
    if args.reference_effects is not None:
        report["amplitude"] = section_amplitude(args, recipe, cpm, mapping, libraries)
        report["peak_rss_bytes_after"]["amplitude"] = peak_rss_bytes()
        a = report["amplitude"]
        print(f"reference N_det mean {a['reference_n_det']['mean']:.2f}; R-B s {a['R-B']['s']:.4f} "
              f"(cross {a['R-B']['s_cross']:.4f}, upper {a['R-B']['s_upper']:.4f}); R-D "
              + ", ".join(f"{c} {v['s']:.3f}" for c, v in a["R-D"]["per_context"].items()), flush=True)
    report.update({"written_utc": datetime.now(timezone.utc).isoformat(), "seconds": round(time.time() - t0, 1),
                   "peak_rss_bytes": peak_rss_bytes()})
    write_new_json(args.out, report)
    print(f"-> {args.out} ({report['seconds']}s, peak RSS {(report['peak_rss_bytes'] or 0) / 2**20:.0f} MiB)")


if __name__ == "__main__":
    main()
