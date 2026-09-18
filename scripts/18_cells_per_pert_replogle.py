"""
18_cells_per_pert_replogle.py

How does the reliability of a per-perturbation response estimate depend on the
number of cells behind it?  Empirical part, measured on Replogle 2022 pseudobulk
(K562 genome-wide, K562 essential, RPE1 essential), where obs['num_cells_filtered']
gives n for every row.

Outputs a JSON blob consumed by 20_cells_needed_report.py
"""
import json, os
import numpy as np
import pandas as pd
import anndata as ad

EXT = "C:/Users/ferra/vcc2026-data/external/"
OUT = "C:/Users/ferra/OneDrive/Desktop/vcc2026/reports/transfer_ceiling/"
TARGETS_CSV = "C:/Users/ferra/OneDrive/Desktop/vcc2026/reports/data_audit/target_inventory.csv"
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(0)


def target_symbol(idx):
    """obs_names look like '0_A1BG_P1_ENSG00000121410' -> 'A1BG'."""
    out = []
    for s in idx:
        parts = s.split("_")
        out.append(parts[1] if len(parts) > 2 else s)
    return pd.Index(out)


def nbin_summary(df, ncol, edges, valcols):
    """Summarise value columns inside bins of n."""
    rows = []
    lab = pd.cut(df[ncol], bins=edges, right=False)
    for interval, sub in df.groupby(lab, observed=True):
        if len(sub) < 10:
            continue
        r = {
            "n_lo": float(interval.left),
            "n_hi": float(interval.right),
            "n_rows": int(len(sub)),
            "n_median": float(sub[ncol].median()),
        }
        for c in valcols:
            v = sub[c].astype(float)
            if c == "energy_test_p_value":
                r["frac_energy_p_lt_0.05"] = float((v < 0.05).mean())
                r["frac_energy_p_lt_0.001"] = float((v < 0.001).mean())
                r["energy_p_median"] = float(v.median())
            else:
                r[c + "_median"] = float(v.median())
                r[c + "_mean"] = float(v.mean())
                r[c + "_frac_gt_0"] = float((v > 0).mean())
                r[c + "_frac_ge_10"] = float((v >= 10).mean())
        rows.append(r)
    return rows


EDGES = np.array([0, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 1000, 1e9])

report = {}

# ---------------------------------------------------------------- load obs ---
files = {
    "k562_gwps": "K562_gwps_raw_bulk_01.h5ad",
    "k562_essential": "K562_essential_raw_bulk_01.h5ad",
    "rpe1_essential": "rpe1_raw_bulk_01.h5ad",
}
obs = {}
for k, f in files.items():
    a = ad.read_h5ad(EXT + f, backed="r")
    o = a.obs.copy()
    o["symbol"] = target_symbol(o.index)
    obs[k] = o
    a.file.close()

targets = pd.read_csv(TARGETS_CSV)["target_gene"].tolist()
tset = set(targets)
report["panel_size"] = len(tset)

# -------------------------------------------- 1. raw n -> detectability -----
report["n_vs_detection"] = {}
for k, o in obs.items():
    pert = o[~o["core_control"].astype(bool)]
    ctrl = o[o["core_control"].astype(bool)]
    report["n_vs_detection"][k] = {
        "n_perturbation_rows": int(len(pert)),
        "n_control_rows": int(len(ctrl)),
        "n_cells_quantiles": {q: float(pert["num_cells_filtered"].quantile(q / 100))
                              for q in (5, 25, 50, 75, 95)},
        "all_perturbations": nbin_summary(
            pert, "num_cells_filtered", EDGES,
            ["anderson_darling_counts", "mann_whitney_counts", "energy_test_p_value"]),
        "core_controls_null": nbin_summary(
            ctrl, "num_cells_filtered", EDGES,
            ["anderson_darling_counts", "mann_whitney_counts", "energy_test_p_value"]),
    }
    if k == "k562_gwps":
        panel = pert[pert["symbol"].isin(tset)]
        report["n_vs_detection"][k]["vcc_panel_rows"] = int(len(panel))
        report["n_vs_detection"][k]["vcc_panel_only"] = nbin_summary(
            panel, "num_cells_filtered", EDGES,
            ["anderson_darling_counts", "mann_whitney_counts", "energy_test_p_value"])

# ------------------------------- 2. is n confounded with true effect size? ---
g = obs["k562_gwps"]
gp = g[~g["core_control"].astype(bool)].copy()
gp["logn"] = np.log10(gp["num_cells_filtered"].clip(lower=1))
conf = {}
for c in ["pct_expr", "fold_expr", "mean_leverage_score", "z_gemgroup_UMI",
          "UMI_count_unfiltered", "mitopercent"]:
    v = gp[c].astype(float)
    ok = np.isfinite(v) & np.isfinite(gp["logn"])
    conf[c] = float(np.corrcoef(gp["logn"][ok], v[ok])[0, 1])
conf["spearman_logn_vs_AD"] = float(
    pd.Series(gp["logn"]).corr(pd.Series(gp["anderson_darling_counts"].astype(float)),
                               method="spearman"))
conf["spearman_logn_vs_pct_expr"] = float(
    pd.Series(gp["logn"]).corr(pd.Series(gp["pct_expr"].astype(float)), method="spearman"))
report["confounding"] = conf

# knockdown efficiency strata: within a stratum the *biological* driver of
# effect size (how hard the gene was knocked down) is held roughly fixed.
kd_strata = [(-1.01, -0.85), (-0.85, -0.6), (-0.6, -0.3), (-0.3, 0.05)]
report["n_vs_detection_within_knockdown_strata"] = []
for lo, hi in kd_strata:
    sub = gp[(gp["pct_expr"] >= lo) & (gp["pct_expr"] < hi)]
    if len(sub) < 200:
        continue
    report["n_vs_detection_within_knockdown_strata"].append({
        "pct_expr_lo": lo, "pct_expr_hi": hi, "rows": int(len(sub)),
        "bins": nbin_summary(sub, "num_cells_filtered", EDGES,
                             ["anderson_darling_counts", "energy_test_p_value"]),
    })

# -------- 3. cross-experiment truth label: K562 gwps vs K562 essential -------
# Same cell line, independent experiments/libraries.  The essential-screen result
# is an n-independent (w.r.t. the gwps screen) label of whether the perturbation
# truly does something; then power is read off as sensitivity vs n_gwps.
e = obs["k562_essential"]
ep = e[~e["core_control"].astype(bool)]
gA = gp.groupby("symbol").agg(n_g=("num_cells_filtered", "max"),
                              ad_g=("anderson_darling_counts", "max"),
                              ep_g=("energy_test_p_value", "min"),
                              kd_g=("pct_expr", "min"))
eA = ep.groupby("symbol").agg(n_e=("num_cells_filtered", "max"),
                              ad_e=("anderson_darling_counts", "max"),
                              ep_e=("energy_test_p_value", "min"),
                              kd_e=("pct_expr", "min"))
J = gA.join(eA, how="inner").dropna(subset=["n_g", "n_e"])
report["cross_experiment"] = {
    "shared_targets_k562_gwps_vs_k562_essential": int(len(J)),
    "corr_log_n_between_experiments": float(
        np.corrcoef(np.log10(J.n_g.clip(lower=1)), np.log10(J.n_e.clip(lower=1)))[0, 1]),
    "spearman_AD_between_experiments": float(J.ad_g.corr(J.ad_e, method="spearman")),
}

# sensitivity / specificity of the gwps read-out as a function of n_gwps,
# using the essential screen (restricted to rows with plenty of cells) as label
lab = J[J.n_e >= 100].copy()
lab["true_strong"] = lab.ad_e >= 100
lab["true_null"] = lab.ad_e == 0
curve = []
for lo, hi in zip(EDGES[:-1], EDGES[1:]):
    sub = lab[(lab.n_g >= lo) & (lab.n_g < hi)]
    if len(sub) < 15:
        continue
    strong = sub[sub.true_strong]
    nul = sub[sub.true_null]
    curve.append({
        "n_lo": float(lo), "n_hi": float(min(hi, 1e6)),
        "n_median": float(sub.n_g.median()), "rows": int(len(sub)),
        "n_true_strong": int(len(strong)),
        "sens_AD_ge_10": float((strong.ad_g >= 10).mean()) if len(strong) >= 5 else None,
        "sens_AD_ge_1": float((strong.ad_g >= 1).mean()) if len(strong) >= 5 else None,
        "sens_energy_p_lt_0.05": float((strong.ep_g < 0.05).mean()) if len(strong) >= 5 else None,
        "median_AD_given_true_strong": float(strong.ad_g.median()) if len(strong) >= 5 else None,
        "n_true_null": int(len(nul)),
        "fpr_AD_ge_10_given_true_null": float((nul.ad_g >= 10).mean()) if len(nul) >= 5 else None,
        "fpr_energy_p_lt_0.05_given_true_null": float((nul.ep_g < 0.05).mean()) if len(nul) >= 5 else None,
    })
report["cross_experiment"]["power_curve_labelled_by_essential_screen"] = curve

# same, using RPE1 essential as the label (different cell line -> upper bound on
# how much of the loss is power vs genuine context difference)
r = obs["rpe1_essential"]
rp = r[~r["core_control"].astype(bool)]
rA = rp.groupby("symbol").agg(n_r=("num_cells_filtered", "max"),
                              ad_r=("anderson_darling_counts", "max"),
                              ep_r=("energy_test_p_value", "min"))
J2 = gA.join(rA, how="inner").dropna(subset=["n_g", "n_r"])
lab2 = J2[J2.n_r >= 100].copy()
curve2 = []
for lo, hi in zip(EDGES[:-1], EDGES[1:]):
    sub = lab2[(lab2.n_g >= lo) & (lab2.n_g < hi)]
    strong = sub[sub.ad_r >= 100]
    if len(strong) < 5:
        continue
    curve2.append({"n_lo": float(lo), "n_median": float(sub.n_g.median()),
                   "n_true_strong": int(len(strong)),
                   "sens_AD_ge_10": float((strong.ad_g >= 10).mean())})
report["cross_experiment"]["power_curve_labelled_by_rpe1_cross_cellline"] = curve2

# ------------- 4. empirical pseudobulk LFC noise floor from NTC rows ---------
# core_control rows are pseudobulks of non-targeting cells with varying n.  Their
# true LFC against the pooled control is ZERO, so the spread of their measured
# LFC is exactly the sampling+batch noise of a pseudobulk built from n cells.
A = ad.read_h5ad(EXT + "K562_gwps_raw_bulk_01.h5ad")
X = np.asarray(A.X, dtype=np.float64)
o = A.obs
is_ctrl = o["core_control"].astype(bool).values
nc = o["num_cells_filtered"].values.astype(float)
gene_name = A.var["gene_name"].values
del A

# pooled control profile, weighted by cells behind each control row
w = nc[is_ctrl]
ref = (X[is_ctrl] * w[:, None]).sum(0) / w.sum()
depth = float(np.median(X.sum(1)))
keep = ref > 0.05                      # keep genes with >=0.05 counts/cell (~4 CPM)
report["noise_floor"] = {
    "pseudobulk_depth_counts_per_cell": depth,
    "genes_total": int(X.shape[1]),
    "genes_kept_ref_gt_0.05_counts_per_cell": int(keep.sum()),
}

eps = 1e-3
lfc_ctrl = np.log2((X[is_ctrl][:, keep] + eps) / (ref[keep] + eps))
ctrl_n = nc[is_ctrl]

# stratify genes by expression so that the 1/(n*lambda) Poisson term is visible
expr_bins = [(0.05, 0.2), (0.2, 0.5), (0.5, 1.5), (1.5, 5.0), (5.0, 1e9)]
noise_rows = []
for lo, hi in zip(EDGES[:-1], EDGES[1:]):
    sel = (ctrl_n >= lo) & (ctrl_n < hi)
    if sel.sum() < 8:
        continue
    row = {"n_lo": float(lo), "n_hi": float(min(hi, 1e6)),
           "n_median": float(np.median(ctrl_n[sel])), "ctrl_rows": int(sel.sum())}
    sub = lfc_ctrl[sel]
    for elo, ehi in expr_bins:
        gsel = (ref[keep] >= elo) & (ref[keep] < ehi)
        if gsel.sum() < 20:
            continue
        # robust SD across control rows, per gene, then median over genes
        sd = sub[:, gsel].std(axis=0, ddof=1)
        row[f"sd_lfc_expr_{elo}_{ehi}"] = float(np.median(sd))
    row["sd_lfc_all_kept_genes"] = float(np.median(sub.std(axis=0, ddof=1)))
    noise_rows.append(row)
report["noise_floor"]["measured_sd_of_control_pseudobulk_lfc"] = noise_rows

# fit  var = a/n + b   on the pooled-gene curve
nn = np.array([r["n_median"] for r in noise_rows])
vv = np.array([r["sd_lfc_all_kept_genes"] ** 2 for r in noise_rows])
Amat = np.vstack([1.0 / nn, np.ones_like(nn)]).T
coef, *_ = np.linalg.lstsq(Amat, vv, rcond=None)
report["noise_floor"]["fit_var_lfc_eq_a_over_n_plus_b"] = {
    "a": float(coef[0]), "b": float(coef[1]),
    "b_as_sd_floor_lfc": float(np.sqrt(max(coef[1], 0))),
    "note": "a/n is sampling noise, b is the irreducible batch/well floor",
}

# ---------- 5. how big are the true LFCs in the VCC-panel regime? ------------
# Observed per-row LFC variance = true biological variance + noise(n).
# Subtract the measured control noise at matched n.
sym = target_symbol(o.index).values
pert_mask = ~is_ctrl
panel_mask = pert_mask & np.isin(sym, list(tset))
report["effect_size_regime"] = {"panel_rows_in_gwps": int(panel_mask.sum())}


def lfc_stats(mask, tag):
    out = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        sel = mask & (nc >= lo) & (nc < hi)
        if sel.sum() < 10:
            continue
        L = np.log2((X[sel][:, keep] + eps) / (ref[keep] + eps))
        obs_var = (L ** 2).mean(axis=1)             # per row, across genes
        # matched noise variance from the fit
        nmed = np.median(nc[sel])
        noise_var = coef[0] / nmed + coef[1]
        true_var = np.maximum(obs_var.mean() - noise_var, 0.0)
        out.append({
            "n_lo": float(lo), "n_median": float(nmed), "rows": int(sel.sum()),
            "rms_observed_lfc": float(np.sqrt(obs_var.mean())),
            "rms_noise_lfc_expected": float(np.sqrt(noise_var)),
            "rms_true_lfc_deconvolved": float(np.sqrt(true_var)),
            "median_abs_lfc_observed": float(np.median(np.abs(L))),
            "p99_abs_lfc_observed": float(np.percentile(np.abs(L), 99)),
        })
    return {tag: out}


report["effect_size_regime"].update(lfc_stats(panel_mask, "vcc_panel_targets"))
report["effect_size_regime"].update(lfc_stats(pert_mask, "all_perturbations"))

# top-gene effect size for well-powered panel rows: what does a real hit look like
sel = panel_mask & (nc >= 200)
if sel.sum() >= 5:
    L = np.log2((X[sel][:, keep] + eps) / (ref[keep] + eps))
    ab = np.abs(L)
    srt = np.sort(ab, axis=1)[:, ::-1]
    report["effect_size_regime"]["well_powered_panel_rows_n_ge_200"] = {
        "rows": int(sel.sum()),
        "median_abs_lfc_of_top1_gene": float(np.median(srt[:, 0])),
        "median_abs_lfc_of_top5_gene": float(np.median(srt[:, 4])),
        "median_abs_lfc_of_top10_gene": float(np.median(srt[:, 9])),
        "median_abs_lfc_of_top25_gene": float(np.median(srt[:, 24])),
        "median_abs_lfc_of_top50_gene": float(np.median(srt[:, 49])),
    }
sel2 = pert_mask & (nc >= 200)
if sel2.sum() >= 5:
    L = np.log2((X[sel2][:, keep] + eps) / (ref[keep] + eps))
    srt = np.sort(np.abs(L), axis=1)[:, ::-1]
    report["effect_size_regime"]["well_powered_all_rows_n_ge_200"] = {
        "rows": int(sel2.sum()),
        "median_abs_lfc_of_top1_gene": float(np.median(srt[:, 0])),
        "median_abs_lfc_of_top10_gene": float(np.median(srt[:, 9])),
        "median_abs_lfc_of_top50_gene": float(np.median(srt[:, 49])),
    }

# --------- 6. AGGREGATE value: does pooling low-n rows recover signal? -------
# Pool k low-n rows of *different* perturbations and ask whether the shared
# (perturbation-independent) component is recoverable.  Proxy: correlation
# between the mean LFC of two disjoint random halves of the low-n rows.
agg = {}
for nmax in (10, 20, 30, 50, 100):
    sel = pert_mask & (nc < nmax) & (nc >= max(1, nmax // 2))
    idx = np.where(sel)[0]
    if len(idx) < 60:
        continue
    L = np.log2((X[idx][:, keep] + eps) / (ref[keep] + eps))
    per_k = {}
    for k in (1, 3, 10, 30, 100, 300):
        if 2 * k > len(idx):
            continue
        cors = []
        for _ in range(40):
            pick = rng.choice(len(idx), size=2 * k, replace=False)
            m1 = L[pick[:k]].mean(0)
            m2 = L[pick[k:]].mean(0)
            cors.append(np.corrcoef(m1, m2)[0, 1])
        per_k[str(k)] = float(np.median(cors))
    agg[f"rows_with_{max(1, nmax // 2)}_to_{nmax}_cells"] = {
        "available_rows": int(len(idx)),
        "split_half_corr_of_mean_lfc_by_n_rows_pooled": per_k,
    }
report["aggregate_value"] = agg

with open(OUT + "replogle_n_curves.json", "w") as f:
    json.dump(report, f, indent=2)
print("wrote", OUT + "replogle_n_curves.json")
print(json.dumps({k: report[k] for k in ("confounding", "cross_experiment", "noise_floor")},
                 indent=2)[:6000])
