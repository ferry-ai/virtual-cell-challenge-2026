"""Route C bench (PROTOCOLLO.md in this folder): leave-one-line-out transfer on the Kaggle rlab corpus, real scorer.

Phase 1 reads every shard once. Per key (study|context), CRISPRi cells only, it sums the counts of every target and of
the NTC controls on the official axis, and for the keys of the held-out lines it records where each cell sits.
Phase 2 turns sums into effects with the formulas of `predictor_sc.effects_from_bulk` (pooled fraction against the
key's controls, quasi-Poisson SE with phi = 0.2), `multisource.z_shrink` with k = 4 and the t22 form gamma = 1, and
saves one effects file per line group. Phase 3 builds, for each held-out line, a `vcc2026.bench.Bench` from its own
cells and scores the registered arms; phase 4 reads the registered rule with a paired bootstrap over targets.

    python banco_tipo.py --inputs /kaggle/input --axis gene_names.csv --out out

Nothing here is tuned after a number: groups, panel sizes, amplitude rule, seeds and rule are the protocol's.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

NTC = "__NTC__"
PHI, MIN_CTRL_FRAC, SHRINK_K = 0.2, 1e-6, 4.0
MIN_NTC_KEY = 30
PANEL_MIN_CELLS, PANEL_MAX, CELLS_MAX, CTRL_MAX, PANEL_SEED = 40, 150, 300, 5000, 2026
SHUF_SEED, BOOT_N, BOOT_SEED = 2027, 10_000, 0
TYPES = {"k562": "myeloid", "rpe1": "epithelial", "hepg2": "hepatic", "jurkat": "lymphoid_t", "h1": "pluripotent",
         "hipsci": "pluripotent", "kolf": "pluripotent", "tian_ipsc": "pluripotent", "tian_neuron": "neuronal"}
HELD_OUT = ("h1", "kolf", "hepg2", "jurkat")
SAME_LINE = {"kolf": {"hipsci_targeted_19|kolf_2", "hipsci_targeted_19|kolf_3"}}  # KOLF2.1J derives from kolf_2


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def group_of(study: str, context: str) -> str | None:
    """The registered key -> line-group rule (PROTOCOLLO, table of groups); None leaves the key out, listed."""
    s, c = study.lower(), context.lower()
    if "hipsci" in s:
        return "hipsci" if "targeted" in s else None
    if "tian" in s or "norman" in s:
        if "k562" in c or "norman" in c:
            return None
        if "neuron" in c:                  # "iPSC-induced neuron" is a neuron: checked before "ipsc" (r1 erred here)
            return "tian_neuron"
        if "ipsc" in c or "ips" == c:
            return "tian_ipsc"
        return None
    for name in ("k562", "rpe1", "hepg2", "jurkat", "kolf"):
        if name in s:
            return name
    if s.startswith("h1") or "h1_" in s:
        return "h1"
    return None


# ---------------------------------------------------------------- phase 1: sums

def read_shard(path: Path):
    import anndata as ad

    a = ad.read_h5ad(path)
    obs, var = a.obs, a.var
    oi = var["official_index"].to_numpy().astype(np.int64)
    ok = (oi >= 0) & var["measured"].to_numpy().astype(bool)
    if "mapping" in var.columns:
        ok &= var["mapping"].astype(str).to_numpy() == "unique"
    x = sp.csr_matrix(a.X)
    return obs, oi, ok, x


def to_axis(x: sp.csr_matrix, oi: np.ndarray, ok: np.ndarray, G: int) -> sp.csr_matrix:
    """Cells x official axis; a native feature mapped twice onto one axis gene is summed by the projection."""
    cols = np.flatnonzero(ok)
    proj = sp.csr_matrix((np.ones(cols.size, np.float32), (np.arange(cols.size), oi[cols])), shape=(cols.size, G))
    return (x[:, cols].astype(np.float32) @ proj).tocsr()


class Sums:
    def __init__(self, G: int):
        self.G = G
        self.acc: dict[str, dict[str, np.ndarray]] = defaultdict(dict)
        self.n: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.mask: dict[str, np.ndarray] = {}
        self.where: dict[str, list] = defaultdict(list)   # held-out keys: (shard id, row, label)
        self.shards_of: dict[str, set] = defaultdict(set)

    def add(self, sid: int, obs: pd.DataFrame, oi, ok, x, axis_set: set, keep_rows_for: set) -> dict:
        mod = obs["modality"].astype(str).to_numpy()
        ck = obs["control_kind"].astype(str).to_numpy()
        tgt = obs["target"].astype(str).to_numpy()
        keys = (obs["study"].astype(str) + "|" + obs["context"].astype(str)).to_numpy()
        lab = np.where(ck == "NTC", NTC, np.where(np.isin(tgt, list(axis_set)), tgt, ""))
        use = (mod == "CRISPRi") & (lab != "")
        stats = {"cells": int(len(obs)), "used": int(use.sum())}
        if not use.any():
            return stats
        G = self.G
        xa = to_axis(x[np.flatnonzero(use)], oi, ok, G)
        measured = np.zeros(G, bool)
        measured[oi[ok]] = True
        k_use, l_use = keys[use], lab[use]
        pair = pd.Series(k_use).str.cat(pd.Series(l_use), sep="\t").to_numpy()
        codes, inv = np.unique(pair, return_inverse=True)
        R = sp.csr_matrix((np.ones(inv.size, np.float32), (inv, np.arange(inv.size))), shape=(codes.size, inv.size))
        S = (R @ xa).tocsr()
        S.sum_duplicates()
        counts = np.bincount(inv, minlength=codes.size)
        for i, code in enumerate(codes):
            key, label = code.split("\t")
            row = self.acc[key].get(label)
            if row is None:
                row = self.acc[key][label] = np.zeros(G, np.float64)
            a, b = S.indptr[i], S.indptr[i + 1]
            row[S.indices[a:b]] += S.data[a:b]
            self.n[key][label] += int(counts[i])
        for key in np.unique(k_use):
            self.mask[key] = measured.copy() if key not in self.mask else (self.mask[key] & measured)
            self.shards_of[key].add(sid)
            if key in keep_rows_for or group_of(*key.split("|", 1)) in keep_rows_for:
                rows = np.flatnonzero(use)[k_use == key]
                self.where[key].extend(zip([sid] * rows.size, rows.tolist(), l_use[k_use == key].tolist()))
        return stats


# ---------------------------------------------------------------- phase 2: effects

def key_effects(sums: Sums, key: str):
    """(targets, E float32 T x G with NaN off the usable genes) for one key, or None without enough controls."""
    from vcc2026.multisource import z_shrink

    n_ctrl = sums.n[key].get(NTC, 0)
    if n_ctrl < MIN_NTC_KEY:
        return None
    m = sums.mask[key]
    s0 = sums.acc[key][NTC]
    ctrl_mu = s0 / n_ctrl
    ctrl_frac = np.where(m, ctrl_mu, 0.0)
    ctrl_frac = ctrl_frac / ctrl_frac.sum()
    usable = m & (ctrl_frac >= MIN_CTRL_FRAC)
    n_c = max(float(n_ctrl), 1000.0)
    targets = sorted(t for t in sums.acc[key] if t != NTC)
    E = np.full((len(targets), sums.G), np.nan, np.float32)
    for i, t in enumerate(targets):
        tot = float(sums.n[key][t])
        mu = np.where(m, sums.acc[key][t] / tot, 0.0)
        if mu.sum() <= 0:
            continue
        frac = mu / mu.sum()
        eff = np.log(np.maximum(frac, 1e-7)) - np.log(np.maximum(ctrl_frac, 1e-7))
        se = np.sqrt(1.0 / (tot * np.maximum(mu, 1e-3)) + PHI / tot
                     + 1.0 / (n_c * np.maximum(ctrl_mu, 1e-3)) + PHI / n_c)
        E[i, usable] = z_shrink(eff[usable], se[usable], SHRINK_K)
    E -= np.nanmean(E, axis=0, keepdims=True)                     # gamma = 1: the key's own mean response
    return targets, E


def pooled(units: list[tuple[list, np.ndarray]], target: str, genes: np.ndarray) -> np.ndarray | None:
    """NaN-mean over the units (keys or groups) that measured ``target``, on ``genes``; None if none did."""
    rows = [E[idx[target], genes] for idx, E in units if target in idx]
    if not rows:
        return None
    with np.errstate(all="ignore"):
        return np.nanmean(np.vstack(rows), axis=0) if len(rows) > 1 else rows[0].copy()


class Library:
    """Key effects, indexed; group effects are built on demand from an allowed set of keys."""

    def __init__(self, effects: dict[str, tuple[list, np.ndarray]]):
        self.eff = {k: ({t: i for i, t in enumerate(ts)}, E) for k, (ts, E) in effects.items()}
        self.group = {k: group_of(*k.split("|", 1)) for k in effects}

    def keys_in(self, group: str, allowed: set) -> list[str]:
        return [k for k in self.eff if self.group[k] == group and k in allowed]

    def group_vec(self, group: str, allowed: set, target: str, genes: np.ndarray):
        return pooled([self.eff[k] for k in self.keys_in(group, allowed)], target, genes)

    def covers(self, group: str, allowed: set, target: str) -> bool:
        return any(target in self.eff[k][0] for k in self.keys_in(group, allowed))


def arm_matrix(lib: Library, groups: list[str], allowed: set, targets: list[str], genes: np.ndarray):
    """(M T x g pooled over groups at equal weight, S K x T x g per group, single-key norms) on ``genes``."""
    S = np.full((len(groups), len(targets), genes.size), np.nan, np.float32)
    norms = []
    for gi, g in enumerate(groups):
        for ti, t in enumerate(targets):
            v = lib.group_vec(g, allowed, t, genes)
            if v is not None:
                S[gi, ti] = v
            for k in lib.keys_in(g, allowed):
                idx, E = lib.eff[k]
                if t in idx:
                    norms.append(float(np.linalg.norm(np.nan_to_num(E[idx[t], genes]))))
    with np.errstate(all="ignore"):
        M = np.nanmean(S, axis=0)
    return np.nan_to_num(M), S, np.array(norms)


def amplitude(M: np.ndarray, single_norms: np.ndarray) -> float:
    """The registered rule: median per-target norm of the pooled effect = median norm of the single keys."""
    pn = np.linalg.norm(M, axis=1)
    pn = pn[pn > 0]
    if not pn.size or not single_norms.size:
        return 1.0
    return float(np.median(single_norms[single_norms > 0]) / np.median(pn))


# ---------------------------------------------------------------- phase 3: benches

def anchors_with_baseline_per(bench) -> None:
    """`Bench.anchors`, keeping the baseline's per-target table for the bootstrap (written as per_pert_baseline.csv)."""
    import cell_eval2
    from cell_eval2.baseline import _lock_from_adata, _prediction_from_adata, baseline_config, generic_response_profile
    from vcc2026.bench import CONTROL, aggregate
    from vcc2026.de_tools import fast_scorer_de

    b_rows = np.concatenate([bench.half_b[t] for t in bench.targets])
    b_labels = np.concatenate([np.full(bench.half_b[t].size, t) for t in bench.targets])
    bench.score("replicate", bench.x[b_rows], b_labels)
    cfg = bench.cfg
    prof = generic_response_profile(bench.real_ad, pert_col=cfg.pert_col, control=cfg.control)
    base_pred = _prediction_from_adata(bench.real_ad, prof, pert_col=cfg.pert_col, control=cfg.control,
                                       emit="dispersed", seed=bench.seed)
    base_cfg = baseline_config(_lock_from_adata(bench.real_ad, base_pred, cfg, de_real=bench.de_real))
    lab = base_pred.obs[cfg.pert_col].astype(str).to_numpy()
    nc = lab != CONTROL
    de_base = fast_scorer_de(base_pred.X[nc], lab[nc], bench.pool)
    per = cell_eval2.compute_metrics(base_pred, bench.real_ad, config=base_cfg, de_real=bench.de_real, de_pred=de_base)
    pd.DataFrame({c: per[c].to_numpy() for c in per.columns}).to_csv(bench.out / "per_pert_baseline.csv", index=False)
    sig = de_base.filter(de_base["p_adj"] < 0.05)
    bench.results["baseline"] = {"raw": aggregate(per), "n_sig_per_target": sig.height / max(len(bench.targets), 1)}
    log("baseline: " + " ".join(f"{k[:12]}={v:.4f}" for k, v in bench.results["baseline"]["raw"].items()
                                 if v is not None))


def read_cells(sums: Sums, shard_paths: list[Path], picks: list[tuple[int, int]], G: int) -> sp.csr_matrix:
    """The picked (shard id, row) cells on the official axis, in the order given."""
    by_shard = defaultdict(list)
    for pos, (sid, row) in enumerate(picks):
        by_shard[sid].append((row, pos))
    out = [None] * len(picks)
    for sid, items in by_shard.items():
        _, oi, ok, x = read_shard(shard_paths[sid])
        rows = np.array([r for r, _ in items])
        xa = to_axis(x[rows], oi, ok, G)
        for j, (_, pos) in enumerate(items):
            out[pos] = xa[j]
    return sp.vstack(out).tocsr()


def load_extra(pattern: str, L: str):
    """External effects for line L (npz: targets, genes = official-axis indices, lfc), as {target: row}, lfc."""
    with np.load(pattern.format(line=L)) as z:
        targets, genes, lfc = z["targets"].astype(str), z["genes"], z["lfc"].astype(np.float32)
    full = np.zeros((targets.size, int(genes.max()) + 1), np.float32)
    full[:, genes] = lfc
    return {t: i for i, t in enumerate(targets)}, full


def run_line(L: str, sums: Sums, lib: Library, shard_paths, axis: np.ndarray, out: Path, arms_mod,
             exclude_groups=(), extras=None) -> dict:
    """``exclude_groups`` leaves whole line groups out of every arm's sources; ``extras`` {name: path pattern with
    {line}} adds arms that apply external effects as they are (no amplitude rule), on a panel they all cover."""
    from vcc2026.bench import Bench
    from vcc2026.generator import ControlModel
    from vcc2026.predictor_sc import derangement

    G = axis.size
    cand = [k for k in sums.where if group_of(*k.split("|", 1)) == L]
    if not cand:
        return {"line": L, "readable": False, "why": "no key of this line in the corpus"}
    studies = {k.split("|", 1)[0] for k in cand}
    excluded = {k for k in lib.eff if k.split("|", 1)[0] in studies or lib.group[k] == L} | SAME_LINE.get(L, set())
    allowed = {k for k in lib.eff if k not in excluded and lib.group[k] is not None
               and lib.group[k] not in set(exclude_groups)}
    ext = {name: load_extra(pat, L) for name, pat in (extras or {}).items()}
    groups = sorted({lib.group[k] for k in allowed})
    same = [g for g in groups if TYPES[g] == TYPES[L]]
    cross = [g for g in groups if TYPES[g] != TYPES[L]]
    compared = {"k562": ["k562"], "cross": cross, "all": groups} | ({"same": same} if same else {})

    def eligible(key):
        out_t = []
        for t, n in sums.n[key].items():
            if t == NTC or n < PANEL_MIN_CELLS:
                continue
            if all(any(lib.covers(g, allowed, t) for g in gs) for gs in compared.values())                     and all(t in rows for rows, _ in ext.values()):
                out_t.append(t)
        return sorted(out_t)

    key = max(cand, key=lambda k: len(eligible(k)))          # the key with the most admitted targets
    el = eligible(key)
    info = {"line": L, "key": key, "excluded_keys": sorted(excluded), "groups_same": same, "groups_cross": cross,
            "eligible_targets": len(el)}
    log(f"{L}: key {key}, {len(el)} eligible targets; same={same} cross={cross}")
    if len(el) < 20:
        return info | {"readable": False, "why": f"panel of {len(el)} targets < 20"}
    rng = np.random.default_rng(PANEL_SEED)
    panel = sorted(rng.choice(el, size=min(PANEL_MAX, len(el)), replace=False).tolist())
    where = defaultdict(list)
    for sid, row, lab in sums.where[key]:
        where[lab].append((sid, row))
    picks, labels = [], []
    for t in panel + [NTC]:
        cap = CTRL_MAX if t == NTC else CELLS_MAX
        rows = where[t]
        take = rng.choice(len(rows), size=min(cap, len(rows)), replace=False)
        picks.extend(rows[i] for i in sorted(take))
        labels.extend([t] * take.size)
    labels = np.array(labels)
    x_all = read_cells(sums, shard_paths, picks, G)
    gmask = sums.mask[key]
    genes_idx = np.flatnonzero(gmask)
    x = x_all[:, genes_idx]
    genes = axis[genes_idx]
    target_rows = {t: np.flatnonzero(labels == t) for t in panel}
    ctrl_rows = np.flatnonzero(labels == NTC)
    bench = Bench(x, target_rows, ctrl_rows, genes, out / f"bench_{L}", seed=PANEL_SEED)
    anchors_with_baseline_per(bench)
    model = ControlModel(state="kde", seed=PANEL_SEED).fit(bench.ctrl, log=log)
    ctrl_cpm = 1e6 * np.asarray(bench.ctrl.sum(axis=0)).ravel() / max(float(bench.ctrl.sum()), 1.0)
    expressed = ctrl_cpm >= 5.0
    targets = bench.targets
    partner = derangement(targets, SHUF_SEED)
    pos = {t: i for i, t in enumerate(targets)}
    gene_pos = {g: i for i, g in enumerate(genes)}

    built = {}
    for name, gs in compared.items():
        M, S, norms = arm_matrix(lib, gs, allowed, targets, genes_idx)
        built[name] = (M, S, amplitude(M, norms))
    plan = [("null", None)]
    plan += [("k562", ("k562", 1.0, None)), ("cross", ("cross", 1.0, None))]
    if same:
        plan += [("same", ("same", 1.0, None)), ("all", ("all", 1.0, None)), ("same_shuf", ("same", 1.0, "shuf")),
                 ("same_a2", ("same", 2.0, None)), ("cross_a2", ("cross", 2.0, None))]
    else:
        plan += [("cross_shuf", ("cross", 1.0, "shuf")), ("cross_a2", ("cross", 2.0, None))]
    plan += [("alloc", ("all", 1.0, "alloc")), ("normrest", ("all", 1.0, "normrest"))]
    plan += [(name, ("extra", 1.0, name)) for name in ext]
    amp_log, factor_log = {}, {}
    for arm, spec in plan:
        rng_arm = np.random.default_rng(PANEL_SEED + 1)
        blocks, labs = [], []
        if spec is not None:
            base, a, mod = spec
            if base == "extra":
                rows_x, lfc_x = ext[mod]
                M = np.stack([lfc_x[rows_x[t], genes_idx] for t in targets])
                S, s = None, 1.0
            else:
                M, S, s = built[base]
            f = np.ones(len(targets))
            if mod in ("alloc", "normrest"):
                fn = arms_mod.alloc_factors if mod == "alloc" else arms_mod.normrest_factors
                f, finfo = fn(S, M, expressed)
                factor_log[arm] = finfo
            amp_log[arm] = {"base": base, "a": a, "s": s}
        for t in targets:
            n = bench.n_pred(t)
            if spec is None:
                blocks.append(model.sample(n, rng_arm))
            else:
                if mod == "shuf":
                    v = M[pos[partner[t]]].copy()
                    j = gene_pos.get(partner[t])
                    if j is not None:
                        v[j] = 0.0                                 # the partner's own knockdown is not a response
                else:
                    v = M[pos[t]] * f[pos[t]]
                blocks.append(model.sample(n, rng_arm, fold_change=np.exp(np.clip(a * s * v, -3, 3))))
            labs.append(np.full(n, t))
        bench.score(arm, sp.vstack(blocks).tocsr(), np.concatenate(labs))
    bench.finish({"stage": "strada_c_banco", "line": L, "key": key, "panel": targets, "amplitudes": amp_log,
                  "exclude_groups": list(exclude_groups), "extras": {n: str(v) for n, v in (extras or {}).items()},
                  "factors": factor_log, "groups_same": same, "groups_cross": cross,
                  "excluded_keys": sorted(excluded), "shuffle_partner": partner})
    return info | {"readable": True, "panel": len(targets), "arms": [a for a, _ in plan]}


# ---------------------------------------------------------------- phase 4: the rule

# Per-target columns: five members aggregated by the mean, then the two legs of the MSE member, which cell_eval2
# aggregates as a ratio of sums (catalog: expr_mse_unbiased_capped_norm, agg="ratio_of_sums").
COLUMNS = ["pds_cosine", "de_wilcoxon_lfc_nmae", "de_wilcoxon_direction_fidelity_yield_raw",
           "de_wilcoxon_direction_reach_raw", "de_wilcoxon_sig_jaccard",
           "expr_mse_unbiased_capped", "expr_distance_unbiased"]


def per_target(path: Path, targets: list[str]) -> np.ndarray:
    """(T x 6) per-target members from cell_eval2's tidy table (perturbation, metric, value); NaN where omitted."""
    df = pd.read_csv(path)
    wide = df.pivot_table(index="perturbation", columns="metric", values="value", aggfunc="first")
    wide.index = wide.index.astype(str)
    return wide.reindex(index=targets, columns=COLUMNS).to_numpy(dtype=float)


def members(tab: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """(B x 6) aggregated members for every resample in ``idx``: NaN-skipping means, and the MSE ratio of sums."""
    with np.errstate(all="ignore"):
        five = np.nanmean(tab[idx, :5], axis=1)
        num, den = tab[idx, 5], tab[idx, 6]
        ok = np.isfinite(num) & np.isfinite(den)
        mse = np.where(ok, num, 0.0).sum(axis=1) / np.where(ok, den, 0.0).sum(axis=1)
    return np.column_stack([five[:, :1], mse, five[:, 1:]])


def scaled_mean(arm: np.ndarray, base: np.ndarray, rep: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Mean of the six locally scaled members for every resample in ``idx`` (B x T), anchors resampled too."""
    u, b, r = members(arm, idx), members(base, idx), members(rep, idx)
    with np.errstate(all="ignore"):
        s = (u - b) / (r - b)
    s[:, 1] = np.clip(s[:, 1], 0.0, 1.0)
    return s.mean(axis=1)


def compare(bdir: Path, targets: list[str], arm: str, ref: str) -> dict | None:
    asked = ref
    if ref == "all" and not (bdir / "per_pert_all.csv").exists():
        ref = "cross"                    # a line with no same-type group: `all` is `cross` (PROTOCOLLO, bracci)
    if not (bdir / f"per_pert_{arm}.csv").exists() or not (bdir / f"per_pert_{ref}.csv").exists():
        return None
    base, rep = per_target(bdir / "per_pert_baseline.csv", targets), per_target(bdir / "per_pert_replicate.csv", targets)
    A, R = per_target(bdir / f"per_pert_{arm}.csv", targets), per_target(bdir / f"per_pert_{ref}.csv", targets)
    T = len(targets)
    full = np.arange(T)[None, :]
    point = float(scaled_mean(A, base, rep, full)[0] - scaled_mean(R, base, rep, full)[0])
    idx = np.random.default_rng(BOOT_SEED).integers(0, T, size=(BOOT_N, T))
    d = scaled_mean(A, base, rep, idx) - scaled_mean(R, base, rep, idx)
    d = d[np.isfinite(d)]
    lo, hi = np.quantile(d, [0.025, 0.975])
    return {"arm": arm, "ref": asked, "ref_used": ref, "mean": point, "ci95": [float(lo), float(hi)], "n_targets": T,
            "resamples_finite": int(d.size)}


def gate(bdir: Path) -> dict:
    s = pd.read_csv(bdir / "scaled_local.csv", index_col=0, keep_default_na=False)  # the arm "null" is not NaN
    raw = json.loads((bdir / "bench.json").read_text())["results"]
    better = 0
    from vcc2026.bench import SCORED as DIRS
    for m, d in DIRS.items():
        r, b = raw["replicate"]["raw"][m], raw["baseline"]["raw"][m]
        better += int((r > b) if d == "higher" else (r < b))
    return {"replicate_beats_baseline_members": better, "passes": better >= 4,
            "scaled_local": s.round(4).to_dict(orient="index")}


def read_rule(out: Path, lines: dict, extras=()) -> dict:
    res = {"lines": {}, "rule": {}}
    for L, info in lines.items():
        if not info.get("readable"):
            res["lines"][L] = info
            continue
        bdir = out / f"bench_{L}"
        targets = json.loads((bdir / "bench.json").read_text())["panel"]
        g = gate(bdir)
        pairs = [("same", "cross"), ("same", "same_shuf"), ("all", "cross"), ("cross", "k562"),
                 ("alloc", "all"), ("normrest", "all"), ("cross", "cross_shuf"), ("same_a2", "same"),
                 ("cross_a2", "cross"), ("null", "cross")]
        pairs += [(x, ref) for x in extras for ref in ("all", "cross", "k562", "same")]
        if "net" in extras and "net0" in extras:
            pairs.append(("net", "net0"))
        res["lines"][L] = info | {"gate": g, "comparisons": [c for a, b in pairs if (c := compare(bdir, targets, a, b))]}
        res["lines"][L]["readable"] = g["passes"]

    def get(L, arm, ref):
        line = res["lines"].get(L, {})
        if not line.get("readable"):
            return None
        return next((c for c in line["comparisons"] if c["arm"] == arm and c["ref"] == ref), None)

    sc, ss, sk = get("h1", "same", "cross"), get("h1", "same", "same_shuf"), get("kolf", "same", "cross")
    res["rule"]["strada_c"] = {
        "readable": sc is not None and ss is not None,
        "passes": bool(sc and ss and sk and sc["ci95"][0] > 0 and ss["ci95"][0] > 0 and sk["mean"] >= 0),
        "h1_same_vs_cross": sc, "h1_same_vs_shuf": ss, "kolf_same_vs_cross": sk,
        "note": None if sk is not None else "KOLF not readable: route C cannot pass today"}
    b_arms = {}
    for arm in ("alloc", "normrest"):
        h, j = get("hepg2", arm, "all"), get("jurkat", arm, "all")
        b_arms[arm] = {"hepg2": h, "jurkat": j, "passes": bool(h and j and h["ci95"][0] > 0 and j["mean"] >= 0)}
    passing = [a for a in b_arms if b_arms[a]["passes"]]
    res["rule"]["strada_b_arms"] = b_arms | {"winner": max(passing, key=lambda a: b_arms[a]["hepg2"]["mean"])
                                             if passing else None}
    if "net" in extras:      # reports/modelli/rete_sorgenti_2026-10-03/PROTOCOLLO_R1.md
        nh, ng = get("h1", "net", "all"), get("hepg2", "net", "all")
        res["rule"]["rete_sorgenti"] = {"h1_net_vs_all": nh, "hepg2_net_vs_all": ng,
                                        "passes": bool(nh and ng and nh["ci95"][0] > 0 and ng["mean"] >= 0)}
    return res


# ---------------------------------------------------------------- main

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inputs", type=Path, required=True, help="folder searched recursively for *.h5ad shards")
    p.add_argument("--axis", type=Path, required=True, help="gene_names.csv, the official 18,533-gene axis")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--code", type=Path, default=None, help="folder holding the vcc2026 package (src/)")
    p.add_argument("--lines", nargs="+", default=list(HELD_OUT))
    p.add_argument("--exclude-groups", nargs="*", default=[], help="line groups never used as sources")
    p.add_argument("--extra", action="append", default=[], metavar="NAME=PATTERN",
                   help="external effects arm; PATTERN is an npz path with {line}")
    a = p.parse_args()
    if a.code:
        sys.path.insert(0, str(a.code))
    import arms as arms_mod  # route B's registered arms, copied next to this file

    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out / "lettura.json").exists():
        raise SystemExit(f"{a.out} already holds a reading; choose a new --out")
    axis = pd.read_csv(a.axis, header=None).iloc[:, 0].astype(str).to_numpy()
    if axis[0].lower() in ("gene", "gene_name", "genes", "symbol"):
        axis = axis[1:]
    G = axis.size
    axis_set = set(axis)
    shard_paths = sorted(a.inputs.rglob("*.h5ad"))
    log(f"axis {G} genes; {len(shard_paths)} shards below {a.inputs}")

    sums = Sums(G)
    t0, report = time.time(), []
    for sid, path in enumerate(shard_paths):
        try:
            obs, oi, ok, x = read_shard(path)
        except Exception as exc:  # a shard that does not read is listed, never silently dropped
            report.append({"shard": str(path), "error": f"{type(exc).__name__}: {exc}"})
            log(f"SKIP {path.name}: {exc}")
            continue
        st = sums.add(sid, obs, oi, ok, x, axis_set, set(a.lines))
        report.append({"shard": str(path), **st})
        if sid % 25 == 0:
            log(f"phase 1: {sid + 1}/{len(shard_paths)} shards, {time.time() - t0:.0f}s")

    effects, keys_info = {}, {}
    for key in sorted(sums.acc):
        g = group_of(*key.split("|", 1))
        n_ntc = sums.n[key].get(NTC, 0)
        keys_info[key] = {"group": g, "type": TYPES.get(g), "ntc": int(n_ntc),
                          "targets": int(sum(1 for t in sums.n[key] if t != NTC)),
                          "genes_measured": int(sums.mask[key].sum()), "shards": len(sums.shards_of[key])}
        if g is None or n_ntc < MIN_NTC_KEY:
            keys_info[key]["used"] = False
            continue
        r = key_effects(sums, key)
        if r is not None:
            effects[key] = r
            keys_info[key]["used"] = True
    (a.out / "sorgenti.json").write_text(json.dumps({"keys": keys_info, "shards": report}, indent=1))
    log(f"phase 2: {len(effects)} keys with effects: " + ", ".join(sorted(effects)))
    lib = Library(effects)
    for g in sorted({lib.group[k] for k in effects}):
        ks = lib.keys_in(g, set(effects))
        ts = sorted(set().union(*[set(lib.eff[k][0]) for k in ks]))
        E = np.vstack([lib.group_vec(g, set(effects), t, np.arange(G)) for t in ts]).astype(np.float16)
        np.savez_compressed(a.out / f"effetti_{g}.npz", targets=np.array(ts), lfc=E, keys=np.array(ks))
        log(f"effetti_{g}.npz: {len(ts)} targets from {len(ks)} keys")

    lines = {}
    for L in a.lines:
        try:
            lines[L] = run_line(L, sums, lib, shard_paths, axis, a.out, arms_mod, exclude_groups=a.exclude_groups,
                                extras=dict(e.split("=", 1) for e in a.extra))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            lines[L] = {"line": L, "readable": False, "why": f"{type(exc).__name__}: {exc}"}
        (a.out / "linee.json").write_text(json.dumps(lines, indent=1, default=str))
    lettura = read_rule(a.out, lines, extras=[e.split("=", 1)[0] for e in a.extra])
    (a.out / "lettura.json").write_text(json.dumps(lettura, indent=1, default=str))
    log(json.dumps(lettura["rule"], indent=1, default=str))
    log("done")


if __name__ == "__main__":
    main()
