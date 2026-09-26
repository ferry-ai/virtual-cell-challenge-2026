# Il membro mse dello scorer: analisi di claude2

Rapporto integrale dell'agente claude2 (hub, esecuzione `20260926-144527-v2-claude2-mse`, sola lettura,
brief `v2-claude2-mse-member.md`), copiato senza modifiche il 26 settembre. **Rapporto di un agente: le
sue affermazioni vanno verificate prima di essere usate come misure.**

---

**Outcome:** our raw 3.88 is almost certainly a signal-energy problem, not a sampling or generator artefact. At amplitude 1.576 our predicted deltas carry about 2.9× the real effect's energy and are nearly orthogonal to it. No honest amplitude choice gets our current direction below the zero point (about 0.986). Reaching 0.6–0.85 takes a pooled, magnitude-weighted cosine with the truth of about 0.4–0.6, unless an entry exploits a scorer loophole the organisers left open on purpose (hypothesis H-E below).

Read-only: I read the scorer source, our pipeline and the existing reports. I ran no code; every number below is either quoted from a file or my own arithmetic on quoted numbers.

## 1. How `expr_mse_unbiased_capped_norm` is computed (measured, from code)

Paths: `SP` = `C:/Users/ferra/vcc2026-data/.venv/Lib/site-packages/cell_eval2/`, `D` = `SP/metrics/delta.py`.

- **Expression space.**
  - Each side's pseudobulk is `mu_p,g = log1p(TS · P_p,g / S_p)`, where P is the group's summed counts and S its total (`D:3-13`).
  - TS = 5e4 (`SP/moments.py:43`, `SP/competition.py:45`).
  - Because it is built from group sums, per-cell library sizes cancel. Only group composition matters (inferred from `D:8`).
- **Genes scored.**
  - All 18,533 genes except the perturbation's own target, in both the numerator and the denominator (`D:1029-1035`, `D:1166-1177`, `D:276-356`).
  - There is no expression gate: the distance runs over every column (`moments.py:524-527`).
  - The corrections are *not* adjusted for the dropped gene (`D:302-314`).
- **Numerator per perturbation p:**
  `(‖mu_pred,p − mu_real,p‖² over G_p − r·min(C_pred,p, k·C_real,p) − C_real,p) / |G_p|` (`D:981-996`, code at `D:878-881`).
  - The C terms are delete-1 jackknives of the group's bulk (`moments.py:137-143`, `465-499`). The estimator is biased up by 0.32% at TS = 5e4 (`moments.py:189-190`).
  - A group with fewer than 2 cells gets C = 0 (`moments.py:221`).
- **Cap #247.** k = 1: a prediction can never subtract more than the reference's own correction (`D:36-43`, applied at `D:696-707`).
- **Budget #348.**
  - `r = min(1, B_pred / claim)`. B_pred is the prediction's own across-perturbation centred sum of squares, with each row weighted by 1/|G_p| and each row's own target column dropped (`D:157-229`, `D:130-154`).
  - claim is the weighted sum of the capped corrections (`D:834-866`). The whole-panel prediction is used when available (`D:232-273`).
  - Two residuals are disclosed as still open: the non-binding regime (`D:738-753`) and truth-aligned overscaling (`D:754-764`).
- **Denominator (real side only).**
  - `(‖mu_real,p − mu_real,ctrl‖² over G_p − C_real,p − C_ctrl) / |G_p|` (`D:1143-1150`, code at `D:1200-1236`).
  - The submission cannot move it (`D:1179-1181`).
- **Aggregation over perturbations.**
  - Σ numerators / Σ denominators, over perturbations where both are finite (`SP/catalog.py:345-348`, `SP/run.py:1806-1866`).
  - Perturbations with large real effects therefore dominate.
  - The label sets must match exactly, so a submission cannot drop perturbations to choose its own denominator (`run.py:1850-1861`).
- **Scaling.**
  - The official score is `from_replicate`: `(u − b)/(r_rep − b)` with a measured baseline b and replicate r_rep (`SP/score.py:377-454`, anchor set at line 431). It is clamped to [0, 1] (`catalog.py:349-350`, `score.py:14-15`).
  - b is the organisers' mean-perturbation-response baseline (`SP/baseline.py:104-138`), emitted as identical cells so its claim is 0 (`baseline.py:771-777`).
  - b ≤ 1.231 is measured (`reports/anchors_2026-09-17/anchors.json:131-137`).
  - A least-squares fit on 10 leaderboard rows gives b ≈ 0.9864, r ≈ 0.0415 (`reports/leaderboard_2026-09-16/snapshot.md:48`). That is an interpretation, aggregated over contexts.
  - So each 0.1 of raw below b is worth about 0.1/(6·0.945) ≈ +0.018 on the average score (interpretation).
- **"No change" reads about 1.0.**
  - Numerator and denominator carry the same terms when the prediction equals the control (`D:316-319`, `D:1147-1150`).
  - In practice it reads slightly above 1: 1.0249 on #268's panel, and the drift is amplified by 3–6% relative by the target-gene exclusion (`SP/scales.py:339-341`, `358-365`).
  - It reads above 1 if the cap binds (`D:1048-1052`), or if one cell block is reused for every perturbation, which makes r = 0 (`catalog.py:318-322`).
  - Our generator's null read 1.012 on the local HepG2 bench (measured, `reports/bench_2026-09-17/hepg2_h002_bench.json:411`).
  - Because b < 1, predicting no change scores slightly below 0 and is clamped to 0.

## 2. Decomposing 3.88

Write d̂ for our predicted delta, d for the real one, and D for Σ denominators. In expectation:
**u ≈ 1 + ‖d̂‖²/D − 2⟨d̂,d⟩/D + (penalties from the cap or from r < 1).**

- **What the official raws say (inferred).**
  - t11 (a = 0.197) reads 1.129 and t15 (a = 0.394, same vector) reads 1.579 (`reports/analisi_2026-09-24/calcoli.json:50-66`).
  - Fitting u = 1 + a²P − 2aC gives P = 4.14, C = 0.080, cos ≈ 0.04 (`calcoli.json:70-117`). The fit assumes u = 1 at zero effect; with that zero set anywhere in 0.95–1.15, cos ranges from −0.06 to 0.26.
  - Applied to t20 (u = 3.8775, `reports/trial_2026-09-26/status_I8FX2yQabjKjPPDTYnaW.json`): roughly 2.9 units are predicted energy the truth does not match, about 1 unit is real effect we did not capture, and the cross-term is small.
  - This agrees with the public-source proxy: the error-optimal amplitude is 0.02–0.16 and even there the gain over the null is under 0.11% (`reports/banco_varianti_2026-09-25/MSE.md:19-34`).

| Term | Likely size in 3.88 | Local diagnostic |
|---|---|---|
| Amplitude or energy on many genes | Dominant (inferred). In this space a gene above about 20 CPM (the log1p knee at TS·p = 1) counts at full (ln FC)². Lower genes are damped. t20 blocks reach max \|effective log2FC\| of 1.8–5.3, with median 0.03–0.06 (`t20_generation_diagnostics.json:183-526`). | Compute E = Σ_p Σ_{g≠target} (mu_pred − mu_ctrl)² at TS = 5e4 from each submitted effects file and basal (no cells needed). Break it down by expression bin, cis-head genes, top-decile perturbations, per source, and the compositional-shift part. |
| Sampling noise of our cells and the cap | Near 0 (inferred). Poisson iid cells have a jackknife that matches their real noise. Poisson is less dispersed than real cells, so C_pred < C_real,p and the cap does not bind. Our large spread makes B_pred ≫ claim, so r = 1. | On a t20 pilot, compute C_pred per block (`moments.jackknife_correction`, TS = 5e4). Compare it with C of 400/200/100-cell subsamples of real controls, and compute B/claim (`_across_pert_budget`). |
| Library size or composition mismatch | Library size cancels. The compositional shift has median \|0.0074\| and max 0.34 log2 (`t20_manifest_45_generate_prediction.json` / diagnostics `:110-115`); small except on a few perturbations. | Energy of the shift component per perturbation, taken from diagnostic 1. |
| Genes absent from the reference, or zero in the basal | Negligible: both sides use the full 18,533-gene axis. | Count real-control zeros weighted by predicted energy. |
| Clipping at \|log2FC\| 6 | Not active: 0 clipped in the 12 sampled blocks. | Keep the check; the risk is large FCs just below the clip. |
| Context-invariant effects | The A, B and C effects files are byte-identical (same sha256 at `:89,97,104`), so any context-specific truth is missed. | None needed. |

## 3. What can bring the member below b, and at what DE cost

Minimising over amplitude gives u* ≈ 1 − cos², where cos is pooled over all perturbation×gene coordinates and weighted by magnitude. Beating b ≈ 0.986 needs cos > 0.12; 0.85 needs about 0.39; 0.65 needs about 0.59 (inferred).

| Option | Effect on the MSE member | Cost on the four DE members | Kind |
|---|---|---|---|
| Global shrinkage | At cos ≈ 0.04 the best raw is about 0.998, still above b: scaled gain 0. | Large. Amplitude is what bought fid, reach, nmae and jac: t15 → t16 was +0.171 scaled on the DE members (PROGETTO §0). t11 → t15 raised pds 0.739 → 0.774 on the same vector. Pure loss. | prediction |
| Gene-selective shrinkage (drop low-confidence, high-energy genes) | Lowers ‖d̂‖² while keeping ⟨d̂,d⟩ only if the removed genes are the misaligned ones. The t19-style restriction did not visibly fix it (t20 is 3.88). | Small, if the removed genes were not producing correct calls. | better prediction |
| Per-perturbation magnitude | Ratio of sums: predicted energy on perturbations with small real effects is pure cost. | A perturbation shrunk to zero drops toward pds 0.5 and loses its calls (`scales.py:53-57`). | better prediction, if magnitude is predictable |
| Shared shift (common component) | The oracle mean-response baseline only reaches about 0.986, so this is worth ≤ 0.014 raw on A/B/C (interpretation). On HepG2 it was worth 0.25 (baseline 0.746, `hepg2_h002_bench.json:390`). We currently remove each source's mean response. | Could help fidelity if the shared direction is real; hurts pds slightly. | biology, if the component transfers across contexts |
| Number and dispersion of cells | No change in expectation while the cap does not bind and r = 1. Fewer or more dispersed cells make the cap bind and read worse (`D:1048-1062`). A reused block makes r = 0 and reads worse. More cells cut variance only. | More cells give more Wilcoxon power, so more calls. | scorer mechanics |
| Pinned aggregates (cell scatter that cancels in the group sum) | Closed when binding by #348 (`D:708-736`, `D:1006-1027`), but **open in the non-binding regime** (`D:738-753`). | None directly. | scorer loophole, adversarial |

The scorer also explicitly closes three other levers: the on-target gene gift (#172), scattering the target column into the budget (`D:192-201`), and choosing the denominator by omitting perturbations (`run.py:1852`).

## 4. How other entries could reach 0.6–0.85 with raw PDS 0.82–0.87

- **H-A: energy is concentrated in a few strong perturbations** (hypothesis).
  - Getting the direction and magnitude right on those buys cos² while barely moving pds, which is a per-perturbation average.
  - Test: in K562 genome-wide and HepG2, compute each perturbation's share of Σ(jackknife-corrected distance) at TS = 5e4. Also check whether our predicted energy ranks the panel's targets like the measured energy does.
- **H-B: a low-rank response axis with per-perturbation loadings** (proliferation or stress) that the mean baseline misses (hypothesis).
  - Test: energy captured by the top-k principal components of source response matrices, and whether loadings transfer K562 → HepG2 or across the Mixscale lines.
- **H-C: same-line or near-line perturbation data** (hypothesis). This is already an open strategic question in the R-V2 plan; it cannot be tested locally without that data.
- **H-D: a calibrated per-perturbation or per-gene amplitude channel** (hypothesis).
  - Test: the HepG2 bench v2 (job 046, real scorer) with arms for selective shrinkage and predicted magnitude, reading all six members.
- **H-E: exploiting the non-binding residual** (hypothesis; scorer mechanics).
  - An entry with real spread (r = 1) that pins its group sums collects up to g = Σ min(C_pred, C_real,p)/D. The organisers measured this at 0.72–0.90 of the range for a pinned control paste before the #348 fix (`D:711-714`).
  - Because the budget and the charge move together (`D:51-57`), the pinned deduction offsets the a²P cost up to g. That gives u ≈ 1 − 2·cos·√g: about 0.73 at cos 0.15, g ≈ 0.8. That is exactly the observed range with modest skill.
  - Test: only in the local bench, e.g. antithetic cell pairs on a t20-like arm, and only if the owner wants the mechanism understood.
  - It is an exploit the organisers describe as one; the scorer warns only when the ratio falls below 0.7 (`D:867-877`). I do not recommend submitting it without the owner's explicit decision and a check of the rules.

## Local experiments, ranked
1. **Calibrate D from the official raws.** Compute E for trial-01, t08, t10, t11, t15, t17 and t20 from their effects files and the A/B/C basals, then fit u − 1 against E. If the points fall on one line, cross ≈ 0 and we get a local predictor of the raw member for any candidate. It is pure arithmetic and takes minutes.
2. **Energy decomposition of t20:** expression bin, cis head, top perturbations, per source, shift component. This locates the 2.9 units.
3. **Regime check on our cells:** C_pred against the control-subsample C at n = 400/200/100, plus B/claim. This confirms sampling contributes nothing to 3.88.
4. **H-A and H-B on sources:** concentration of the denominator and low-rank energy share, then transfer of loadings.
5. **HepG2 bench v2 arms** for selective, per-perturbation and common-component shrinkage, priced on all six members.
6. (Owner decision) the H-E mechanics test.

## Not verified / open questions for Claude1
- How the three per-context raws combine into the published 3.88 (mean of the ratios?) is not verified. b and r may also differ by context; the leaderboard fit is aggregated.
- The number of real cells per perturbation in val, and therefore how large C_real is compared with D, is not verified. The "g up to about 1" figure rests on the organisers' note that the jackknife consumes 46–55% of the raw distance (`D:1041-1042`).
- The t11/t15 fit assumes u = 1 at zero effect. The t16 raw is unknown because its scaled value was clamped.
- Do the rules allow the H-E emission? The owner should decide before anyone tests it.
- I did not open the public leaderboard, so any claim about what specific other entries do remains hypothesis.
