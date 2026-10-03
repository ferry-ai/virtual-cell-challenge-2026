"""How much of the gap to the top-100 median can the generator alone close?

Reads only official numbers already in the repo (comparison.json, invii.csv, CP-0052) and the
top-100/top-10 medians of reports/invii/lezioni_invii_2026-09-28/RISULTATI.md. No new run.

MSE model (AUDIT_SCIENTIFICO 2.5): raw normalized MSE at amplitude a is
    u(a) = u0 + P a^2 - 2 C a,   cos = C / sqrt(P),   min_a u = u0 - cos^2,
in units where the true delta has squared norm 1. u0 is the generator's zero-effect point.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parents[2] / "invii"
c30 = json.loads((R / "prediction_t30_2026-10-03/comparison.json").read_text(encoding="utf-8"))
c31 = json.loads((R / "prediction_t31_2026-10-03/comparison.json").read_text(encoding="utf-8"))

U0_T30 = c30["raw_published_t30"]["expr_mse_unbiased_capped_norm"]  # t22 generator, effects ~20x shrunk
MSE_T25, MSE_T28 = 3.017171491, 5.800207145  # CP-0052; t28 = t25 effects x1.5 (+ per-gene dispersion)
MSE_BASELINE, MSE_REPLICATE = 0.99, 0.035  # approximate anchors, lezioni_invii RISULTATI


def fit(u0, u1, u15):
    """Two points at a = 1 and a = 1.5 with u0 fixed: returns P, C, cos, min u."""
    # u1 - u0 = P - 2C ; u15 - u0 = 2.25 P - 3 C
    d1, d2 = u1 - u0, u15 - u0
    C = (d2 - 2.25 * d1) / (4.5 - 3.0)
    P = d1 + 2 * C
    cos = C / P ** 0.5
    return P, C, cos, u0 - cos ** 2


def scaled_mse(u):
    return max(0.0, (MSE_BASELINE - u) / (MSE_BASELINE - MSE_REPLICATE))


out = {"u0_measured_t30": U0_T30, "fits": {}}
for label, u0 in (("u0_t30", U0_T30), ("u0_1.00", 1.00)):
    P, C, cos, umin = fit(u0, MSE_T25, MSE_T28)
    out["fits"][label] = {"P": P, "C": C, "cos": cos, "min_raw_mse": umin,
                          "scaled_mse_at_optimum": scaled_mse(umin)}
# cosine needed for the MSE member to reach 0 and the top-100 median raw (0.77)
out["cos_needed_for_scaled_0"] = max(0.0, U0_T30 - MSE_BASELINE) ** 0.5
out["cos_needed_for_top100_raw_0.77"] = (U0_T30 - 0.77) ** 0.5

# per-member gap, t28 against the top-100 and top-10 medians (scaled), contribution to the mean
t28 = c30["scaled_published"]["t28"]
t25 = c30["scaled_published"]["t25"]
top100 = {"score_mse": 0.227, "score_pds": 0.759, "score_reach": 0.211, "score_fid": 0.001,
          "score_nmae": 0.139, "score_jac": 0.003}
top10 = {"score_mse": 0.335, "score_pds": 0.805, "score_reach": 0.249, "score_fid": 0.051,
         "score_nmae": 0.234, "score_jac": 0.018}
out["gap_on_mean"] = {k: {"t28": t28[k], "top100": top100[k], "to_top100": (top100[k] - t28[k]) / 6,
                          "to_top10": (top10[k] - t28[k]) / 6} for k in top100}
out["nmae_t25_minus_t28_on_mean"] = (t25["score_nmae"] - t28["score_nmae"]) / 6
out["t31_raw_mse"] = c31["raw_published_t31"]["expr_mse_unbiased_capped_norm"]
print(json.dumps(out, indent=2))
