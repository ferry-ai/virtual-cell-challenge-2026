"""
19_power_curve_vcc_ntc.py

The reliability-vs-n question, measured in-domain: on the real VCC 2026 NTC cells
(contexts A/B/C, ~20k UMI/cell, 18,533 genes), under the scorer's own conventions
(CPM per cell, gene gate mean CPM/cell > 5, Wilcoxon + BH p_adj < 0.05).

Pretend a subsample of n NTC cells is a "perturbation".  Its true effect is zero,
so everything it produces is noise; then thin known log2 fold changes into it and
see what survives.  That separates POWER from EFFECT SIZE by construction, because
the effect size is set by us.

Outputs reports/transfer_ceiling/vcc_ntc_power.json
"""
import json, os, time
import numpy as np
import scipy.sparse as sp
from scipy.stats import rankdata, norm
import anndata as ad

RAW = "C:/Users/ferra/vcc2026-data/raw/controls/"
OUT = "C:/Users/ferra/OneDrive/Desktop/vcc2026/reports/transfer_ceiling/"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

N_GRID = [5, 10, 25, 50, 100, 200, 400, 800, 1600, 3200]
N_GRID_DE = [10, 25, 50, 100, 200, 400, 800, 1600]
M_REF_NOISE = 6000          # control arm for the LFC-noise curves
M_REF_DE = 2000             # control arm for the Wilcoxon curves (kept small: cost)
REPS_NOISE = 40
REPS_DE = 8
SPIKE_LFCS = [-0.05, -0.1, -0.2, -0.35, -0.5, -1.0]
SPIKE_PER_LEVEL = 100
EPS = 1e-9                  # scorer's epsilon


def bh(p):
    p = np.asarray(p, float)
    n = p.size
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty(n)
    out[o] = np.clip(q, 0, 1)
    return out


def wilcoxon_p(Xn, Xm, chunk=2500):
    """Two-sided Mann-Whitney with exact tie correction via the rank variance."""
    n, G = Xn.shape
    m = Xm.shape[0]
    N = n + m
    z = np.empty(G)
    for s in range(0, G, chunk):
        e = min(s + chunk, G)
        Z = np.vstack([Xn[:, s:e], Xm[:, s:e]]).astype(np.float64, copy=False)
        R = rankdata(Z, axis=0)
        Rs = R[:n].sum(0)
        mu = n * (N + 1) / 2.0
        S = ((R - (N + 1) / 2.0) ** 2).sum(0)          # handles ties exactly
        var = n * m * S / (N * (N - 1))
        with np.errstate(invalid="ignore", divide="ignore"):
            z[s:e] = (Rs - mu) / np.sqrt(var)
        del Z, R
    z = np.nan_to_num(z, nan=0.0)
    return 2.0 * norm.sf(np.abs(z)), z


def load_context(tag):
    a = ad.read_h5ad(RAW + f"context_{tag}.h5ad")
    X = sp.csr_matrix(a.X)
    genes = np.asarray(a.var_names)
    del a
    return X, genes


report = {
    "settings": {
        "n_grid_noise": N_GRID, "n_grid_de": N_GRID_DE,
        "control_arm_cells_noise": M_REF_NOISE, "control_arm_cells_de": M_REF_DE,
        "reps_noise": REPS_NOISE, "reps_de": REPS_DE,
        "spike_lfcs": SPIKE_LFCS, "spike_genes_per_level": SPIKE_PER_LEVEL,
        "de_gate": "mean CPM per cell > 5 (scorer's filter_gene_min_cpm_cell)",
        "de_test": "Wilcoxon rank-sum, two-sided, BH across gated genes, p_adj<0.05",
        "spike_mechanism": "binomial thinning of raw counts in the perturbed arm "
                           "(down-regulation only; up-regulation of the same |LFC| "
                           "is slightly easier to detect because counts go up)",
    }
}

# =============================================================== noise curves ==
report["lfc_noise_by_n"] = {}
report["overdispersion"] = {}
for tag in ("A", "B", "C"):
    t0 = time.time()
    X, genes = load_context(tag)
    tot = np.asarray(X.sum(1)).ravel()                    # per-cell total UMI
    ncell = X.shape[0]

    # CPM per cell, sparse
    inv = sp.diags(1e6 / np.maximum(tot, 1))
    C = (inv @ X).tocsr().astype(np.float32)
    mean_cpm = np.asarray(C.mean(0)).ravel()
    gate = mean_cpm > 5.0                                 # scorer's gene gate
    gi = np.where(gate)[0]
    Cg = C[:, gi]
    mg = mean_cpm[gi]

    # method-of-moments overdispersion on CPM per cell:
    #   Var(y) = m^2/ (lambda) ... expressed as CV^2 = 1/lambda + phi
    # lambda = expected raw counts per cell for that gene = mean_cpm * depth / 1e6
    sq = np.asarray(Cg.multiply(Cg).mean(0)).ravel()
    var_cpm = sq - mg ** 2
    depth = float(np.median(tot))
    lam = mg * depth / 1e6
    cv2 = var_cpm / np.maximum(mg ** 2, 1e-12)
    phi = cv2 - 1.0 / np.maximum(lam, 1e-9)               # biological CV^2
    report["overdispersion"][tag] = {
        "median_umi_per_cell": depth,
        "n_gated_genes": int(gate.sum()),
        "median_cv2_total": float(np.median(cv2)),
        "median_phi_biological_cv2": float(np.median(phi)),
        "phi_quartiles": [float(np.percentile(phi, q)) for q in (25, 50, 75)],
        "phi_by_cpm_stratum": {},
    }
    strata = [(5, 10), (10, 25), (25, 50), (50, 100), (100, 250), (250, 1e9)]
    for lo, hi in strata:
        s = (mg >= lo) & (mg < hi)
        if s.sum() < 20:
            continue
        report["overdispersion"][tag]["phi_by_cpm_stratum"][f"{lo}-{hi}"] = {
            "genes": int(s.sum()),
            "median_phi": float(np.median(phi[s])),
            "median_lambda_counts_per_cell": float(np.median(lam[s])),
        }

    # ---- empirical SE of the pseudobulk log2 fold change vs n
    perm = rng.permutation(ncell)
    ref_idx = perm[:M_REF_NOISE]
    pool = perm[M_REF_NOISE:]
    ref_prof = np.asarray(Cg[ref_idx].mean(0)).ravel()

    rows = []
    for n in N_GRID:
        if n > len(pool):
            continue
        L = np.empty((REPS_NOISE, len(gi)), dtype=np.float64)
        for r in range(REPS_NOISE):
            pick = rng.choice(pool, size=n, replace=False)
            prof = np.asarray(Cg[pick].mean(0)).ravel()
            L[r] = np.log2((prof + EPS) / (ref_prof + EPS))
        sd = L.std(0, ddof=1)
        row = {"n": n, "sd_lfc_median_over_gated_genes": float(np.median(sd)),
               "sd_lfc_mean": float(np.mean(sd)),
               "rms_lfc_across_genes_and_reps": float(np.sqrt((L ** 2).mean()))}
        for lo, hi in strata:
            s = (mg >= lo) & (mg < hi)
            if s.sum() < 20:
                continue
            row[f"sd_lfc_cpm_{lo}_{hi}"] = float(np.median(sd[s]))
        rows.append(row)
    report["lfc_noise_by_n"][tag] = rows

    # fit var = a/n  (+ b) per stratum and overall
    fits = {}
    nn = np.array([r["n"] for r in rows], float)
    for key in ["sd_lfc_median_over_gated_genes"] + \
               [f"sd_lfc_cpm_{lo}_{hi}" for lo, hi in strata]:
        if key not in rows[0]:
            continue
        vv = np.array([r[key] ** 2 for r in rows], float)
        A = np.vstack([1.0 / nn, np.ones_like(nn)]).T
        coef, *_ = np.linalg.lstsq(A, vv, rcond=None)
        fits[key] = {"a": float(coef[0]), "b": float(coef[1]),
                     "sd_floor_at_infinite_n": float(np.sqrt(max(coef[1], 0)))}
    report["lfc_noise_by_n"][tag + "_fit_var_a_over_n_plus_b"] = fits
    print(tag, "noise curves done", round(time.time() - t0, 1), "s", flush=True)

    if tag != "A":
        del X, C, Cg
        continue

    # ============================================ Wilcoxon power, context A ====
    t0 = time.time()
    raw_g = X[:, gi].tocsr()                      # raw counts, gated genes
    tot_all = tot                                 # per-cell total over ALL genes

    perm = rng.permutation(ncell)
    ref_idx = perm[:M_REF_DE]
    pool = perm[M_REF_DE:]
    ref_dense = np.asarray(raw_g[ref_idx].todense(), dtype=np.float32)
    ref_cpm = ref_dense / np.maximum(tot_all[ref_idx][:, None], 1) * 1e6
    del ref_dense

    G = len(gi)
    # assign disjoint spike sets, balanced across the expression range
    order = np.argsort(mg)
    spike_sets = {}
    taken = np.zeros(G, bool)
    for j, lfc in enumerate(SPIKE_LFCS):
        cand = order[j::len(SPIKE_LFCS)]
        cand = cand[~taken[cand]][:SPIKE_PER_LEVEL]
        taken[cand] = True
        spike_sets[str(lfc)] = cand
    null_genes = np.where(~taken)[0]

    de_rows = []
    for n in N_GRID_DE:
        acc = {str(l): [] for l in SPIKE_LFCS}
        acc_raw = {str(l): [] for l in SPIKE_LFCS}
        fp, fp_raw, total_sig, lfc_err = [], [], [], {str(l): [] for l in SPIKE_LFCS}
        null_sig_counts = []
        for r in range(REPS_DE):
            pick = rng.choice(pool, size=n, replace=False)
            D = np.asarray(raw_g[pick].todense(), dtype=np.float64)
            t = tot_all[pick].astype(np.float64).copy()
            # --- pure null run (no spike) for calibration, first rep block only
            if r < max(2, REPS_DE // 2):
                cpm0 = D / np.maximum(t, 1)[:, None] * 1e6
                p0, _ = wilcoxon_p(cpm0.astype(np.float32), ref_cpm)
                q0 = bh(p0)
                null_sig_counts.append(int((q0 < 0.05).sum()))
                del cpm0
            # --- spiked run
            Dm = D.copy()
            for lfc in SPIKE_LFCS:
                cols = spike_sets[str(lfc)]
                keepfrac = 2.0 ** lfc
                sub = Dm[:, cols]
                thinned = rng.binomial(sub.astype(np.int64), keepfrac).astype(np.float64)
                t -= (sub - thinned).sum(1)
                Dm[:, cols] = thinned
            cpm = Dm / np.maximum(t, 1)[:, None] * 1e6
            p, _ = wilcoxon_p(cpm.astype(np.float32), ref_cpm)
            q = bh(p)
            sig = q < 0.05
            sig_raw = p < 0.05
            total_sig.append(int(sig.sum()))
            fp.append(int(sig[null_genes].sum()))
            fp_raw.append(float(sig_raw[null_genes].mean()))
            prof = cpm.mean(0)
            lf = np.log2((prof + EPS) / (ref_cpm.mean(0) + EPS))
            for lfc in SPIKE_LFCS:
                cols = spike_sets[str(lfc)]
                acc[str(lfc)].append(float(sig[cols].mean()))
                acc_raw[str(lfc)].append(float(sig_raw[cols].mean()))
                lfc_err[str(lfc)].append(float(np.mean(np.abs(lf[cols] - lfc))))
            del D, Dm, cpm
        de_rows.append({
            "n": n,
            "null_only_run_median_sig_genes_bh05": float(np.median(null_sig_counts)),
            "null_only_run_max_sig_genes_bh05": float(np.max(null_sig_counts)),
            "spiked_run_median_total_sig_genes_bh05": float(np.median(total_sig)),
            "false_positives_among_unspiked_genes_bh05_median": float(np.median(fp)),
            "unspiked_frac_raw_p_lt_0.05_median": float(np.median(fp_raw)),
            "power_bh05_by_lfc": {k: float(np.median(v)) for k, v in acc.items()},
            "power_rawp05_by_lfc": {k: float(np.median(v)) for k, v in acc_raw.items()},
            "mean_abs_lfc_estimation_error_by_lfc":
                {k: float(np.median(v)) for k, v in lfc_err.items()},
        })
        print("  DE n=", n, de_rows[-1]["power_bh05_by_lfc"],
              "fp", de_rows[-1]["false_positives_among_unspiked_genes_bh05_median"],
              round(time.time() - t0, 1), "s", flush=True)
    report["wilcoxon_power_context_A"] = {
        "gated_genes": int(G),
        "spike_set_median_cpm": {k: float(np.median(mg[v])) for k, v in spike_sets.items()},
        "curve": de_rows,
    }
    del X, C, Cg, raw_g

with open(OUT + "vcc_ntc_power.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote", OUT + "vcc_ntc_power.json")
