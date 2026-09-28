# Revisione di grok della correzione del pseudoconteggio

Rapporto integrale di grok (base di lancio, run `20260927-135652-v2-review-pseudo-grok`, grok-4.7, sola lettura, brief `v2-agy-review-pseudocount.md`), copiato il 27 settembre senza modifiche.

I'll review the pseudobulk fold-change fix in read-only mode and check each of the six points against the code, tests, and the 27 September write-up.The pseudobulk fix holds: a zero–zero gene is `ln(L_c/L_t)`, the drop rule ignores the perturbed count, and a gene with no donor left is NaN through the average. What remains is a null bias of about `ln(1 + 0.5/E_t)` just above the cutoff, and two prose figures that do not match the JSON.

Read only (no shell, no `result.md`). Evidence is the current source and the 27 September JSON.

## 1. Artefact and the drop rule

**Yes. Yes.**

With `p_t = p_c = 0.5`, `effects_from_pseudobulk` computes `ln((S_t+0.5)/L_t) - ln((S_c+0.5)/L_c)` (`src/vcc2026/multisource.py:178`). If `S_t = S_c = 0` this is `ln(L_c/L_t)` (`:107–109`). **Measured** from the formula. A zero in the perturbed group with expected count `E_t = S_c·L_t/L_c ≪ 0.5` is about `ln(0.5/E_t)`, large and positive. The test case `S_c=20`, `L_t=30_000`, `L_c=20_000_000` (`E_t=0.03`) is `ln(16.26)≈2.79` (`tests/test_multisource.py:112–116`). **Inferred** from that arithmetic; the report’s “+2.8” matches (`reports/pseudoconteggio_2026-09-27/RISULTATI.md:42–43`).

The keep test is `E_t = cs * (st.sum()/cs.sum()) >= min_expected` (`multisource.py:184`). `st.sum()` is the perturbed library total, not that gene’s count. A perturbed count of 2 with `E_t≈0.10` is still dropped (`test_multisource.py:87–92`). **Measured.** One gene can move `L_t` only by its share of the library, so it cannot recreate the r8 rule (keep a donor because a count of 1–2 appeared). **Inferred.**

The “about +0.5 at 0.5 expected counts” line (`multisource.py:124–125`, `RISULTATI.md:85–86`) is the null plug-in, not the zero-count reading. A zero at `E_t=0.5` is about 0. The null (`S_t=E_t`, deep controls) is `ln(1+0.5/E_t)=ln(2)≈0.69` at 0.5 and `≈0.41` at 1. At a 10× library ratio it is about 0.60 and 0.36. “Circa +0.5” is the right direction. **Inferred.**

## 2. Mean, SE, and a finite effect with a bad SE

**Yes for the mean and the SE. No zero SE. A finite 0 with a NaN SE exists only inside `SourceEffects`, and `from_source` drops it.**

Donors left for a gene are those with `E_t >= min_expected`. The mean is `Σ n_t e / Σ n_t` and the SE is `sqrt(Σ n_t² v) / Σ n_t` on that subset (`multisource.py:185–198`). Same weights as the full-sample branch (`:180–181`, `:192–194`): target cells in that donor. One donor left still has SE `sqrt(v) > 0` under `pseudo=0.5`, not a sample SD that would be undefined. No donor left: both effect and SE are NaN (`:196–198`). **Measured** from the code. **Inferred** that `v > 0`, so the SE is not 0.

`n_cells` is `int(wsum)` over every donor that passed `min_cells`, including donors dropped for that gene (`:188`, `:203`). `mix` then uses that one number for every gene (`:292`). The mean and SE are not wrong; the later reliability weight is. **Measured.**

After that, `usable` (control fraction `< 1e-6`) writes raw and shrunk as 0 and leaves SE untouched (`:199–202`). A gene below that floor whose every donor was dropped is stored as effect 0 and SE NaN. `AxisTable.from_source` copies only genes at or above the same floor (`:236–240`), so the saved table stays NaN, NaN, NaN. **Measured.** Smallest fix, and it does not change stage-98 arrays: where `~usable`, store NaN in raw, shrunk, and SE instead of 0.

## 3. Does NaN stay unmeasured?

**Yes through the average. No mean is poisoned. Stage 100 then stores 0 with `observed` false.**

- `z_shrink` (`:47–50`): a NaN SE fails `se > 0`, so the ratio stays 0, and `NaN * 0 / k` is NaN. The fix emits NaN effect and NaN SE together, so this stays NaN. A finite effect with a non-positive SE would become 0; that pair is not what the drop rule writes. **Inferred** (IEEE/NumPy; not executed).
- `from_source` (`:238–240`) copies the NaN into a NaN-filled table.
- `common` (`:259–261`) uses a finite count and `nansum`, not `mean`. An all-NaN gene contributes nothing; the fallback 0 is not subtracted from any finite row.
- `mix` (`:290–296`) adds only `isfinite` rows. If every source is NaN, the effect is 0 and the weight is 0. That 0 is not in the average.
- Stage 100 (`scripts/100_build_context_effects.py:267–268`, `:305–322`) saves that 0 as `lfc` and sets `observed = (w > 0)`. `eb_pool` (`multisource.py:350–355`) does the same and is off unless the recipe has `pooling`. t25 does not (`configs/recipes/t25.json:3–6`).
- Stage 45 applies the delta only where `observed` is true (`src/vcc2026/inference.py:259–265`), so the gene stays at basal: a realized fold change of 0. The write-up says so (`RISULTATI.md:98–99`). **Measured.**

Stage 76 adds `lfc` and never reads `observed` (`scripts/76_generate_sc_prediction.py:186–188`, `:222–223`). A stored 0 adds nothing to the base model. t25 is the trial-01 generator (`reports/prediction_t25_2026-09-27/prediction.json:3`), which is stage 45.

## 4. `min_expected=0` versus the old path

**Yes for the arithmetic. The cited check is array equality, not a file hash.**

`wvec` is built only when `min_expected > 0` (`multisource.py:163`, `:180–181`). At 0 the sums are the old ones, and `meta` gains no `min_expected` key (`:211–212`). **Measured.**

`confronto_r5_parita.json:10` and the same field for all nine sources are `"identical": true`. The script (`compare_r5_r6.py:57`) uses `np.array_equal` on `shrunk`, `raw`, `se`, `n_cells`, with `equal_nan=True`. It does not hash the npz. **Measured** that the JSON says identical. **Unverified** that the files are byte-identical; this session did not re-read the caches.

## 5. Prose versus the JSON

**Two figures differ. The rest of the r9 table and the t25 bullets match at the printed precision.**

From `confronto_r5_r9.json` `change` / induced counts:

| Source | Identical entries | Corr | Energy | Newly unmeasured | Induced |
|---|---|---|---|---|---|
| `cd4_Rest` | 0.921 → 92% | 0.856 → 0.86 | 0.868 → 0.87 | 29590 | 16 → 0 |
| `cd4_Stim8hr` | 0.937 → 94% | **0.885, prose 0.89** | 0.917 → 0.92 | 16275 | 14 → 0 |
| `cd4_Stim48hr` | 0.937 → 94% | 0.969 → 0.97 | 0.979 → 0.98 | 18862 | 7 → 0 |
| `cd4_mix` | 0.864 → 86% | 0.881 → 0.88 | 0.950 → 0.95 | 20291 | 17 → 0 |
| `orion_hct116` | 0.941 → 94% | 0.914 → 0.91 | 0.675 → 0.68 | 169277 | 315 → 0 |
| `orion_hek293t` | 0.950 → 95% | 0.918 → 0.92 | 0.863 → 0.86 | 90498 | 2 → 0 |

`cd4_Stim8hr` correlation is `0.8847180987801906` (`confronto_r5_r9.json:139`). Two-decimal rounding is 0.88. The prose says 0.89 (`RISULTATI.md:91`). **Measured.**

“Identical entries” is the share equal among pairs finite in both (`compare_r5_r6.py:82`), not among all pairs. The percentages match that field.

K562 `identical: true` (`confronto_r5_r9.json:10`). **Measured.**

Repressed-by-over-90% is not “as in r5” (`RISULTATI.md:97–98`). r9 spans 0–14, which matches `cd4_mix` r9 = 14 (`confronto_r5_r9.json:321`). r5 for that source is 10 (`:294`). Also r5 → r9: `cd4_Rest` 2 → 5 (`:45`, `:72`), `cd4_Stim8hr` 5 → 6 (`:99`, `:126`), `cd4_halfB` 1 → 2 (`:251`, `:267`). **Measured.**

t25 versus `prediction.json` `t25_effects_against_t22`:

- Y share of weighted energy: A 0.0534 → 5.3% and 0.000803 → 0.08%; C 0.0552 → 5.5% and 0.000844 → 0.08% (`prediction.json:93–95`, `:127–129`).
- Energy ratios 0.9858, 1.0192, 0.9649 → 0.99, 1.02, 0.96 (`:90`, `:107`, `:124`).
- Correlations 0.9016, 0.9227, 0.8779 → 0.90, 0.92, 0.88 (`:91`, `:108`, `:125`).
- Genes moved: t22 `13958.0` matches 13,958. t25 is **`13728.5`**, prose **13,728** (`:98–99` and the same for B and C; `RISULTATI.md:111`). **Measured.**

Those t25 figures were not recomputed from `processed/effects_t25_2026-09-27/`. **Unverified** against the npz files.

## 6. Bias the write-up does not treat as still there

**Yes. Just above one expected count the kept estimator is still biased high, by about 0.3–0.4 nat.**

Under a true null, deep controls, constant pseudocount: `ln(1 + 0.5/E_t)`. At the keep boundary `E_t=1` that is `ln(1.5)≈0.41` (about 0.36 if controls are only 10× the perturbed library). At 2 counts, `≈0.22`. At 10, `≈0.05`. `min_expected=1` drops the unbounded part and keeps this. **Inferred.**

`pseudo_scale="library"` is 0 at that same plug-in null (`multisource.py:113–116`). The r7 section says library mode moves genes by `ln(E_t/(E_t+0.5))` (about −0.4 at 1 count and −0.05 at 10) and that constant mode was almost undistorted there (`RISULTATI.md:64–66`). The −0.4 is the constant-mode null bias with the sign flipped. HCT116 really does move a lot under library scale: correlation 0.718 and 57% of co-finite entries changed by more than 0.01 (`confronto_r5_r7.json:376–378`). **Measured** that those are the JSON values. **Inferred** that much of that shift is this bias, not a new one. Library scale also shrinks real effects at low counts, so the two estimators should not be identical even after the null is fixed.

Two smaller gaps, neither in the r9 write-up:

- Donors are kept only when `S_c` is high enough. Near the cut that truncates the control count upward and pulls the fold change down by roughly `0.8/sqrt(λ_c)`. For a CD4-like library (`λ_c≈10` at `E_t=1`) that is about −0.25; for Orion (`λ_c` in the hundreds) a few hundredths. It fades once the typical count is well above the cut. **Inferred**, normal approximation, not measured on the caches.
- Reliability does not follow the donors left (point 2). t25 averages `shrunk` (`t25.json:3`), and `z_shrink` already uses the wider SE, so a one-donor gene is shrunk before it is over-weighted. The overweight is real for the mix weight and would be larger on `raw`.

Smallest change if that residual bias is unacceptable: use the library scale already in the function, or raise `min_expected` until `ln(1+0.5/E_t)` is a size you accept (10 counts → about 0.05), knowing either choice marks many more pairs unmeasured. A one-line patch inside the current rule cannot remove a bias that sits above the cutoff.

## The three findings

1. The derivation and the kept rule are right, and NaN does not enter the donor mean, `common`, or `mix`. Stage 100’s 0 is paired with `observed` false; stage 45 leaves that gene at basal.
2. The kept estimator is still high by about `ln(1+0.5/E_t)` (about +0.4 at one expected count). The r7 text calls constant mode almost unbiased there and treats that same shift as library-mode damage. That is backwards for the null plug-in.
3. `cd4_Stim8hr` correlation is 0.885 in `confronto_r5_r9.json:139`, not 0.89, and t25’s median genes moved is 13728.5 in `prediction.json:99`, not 13728. Repressed-by-90% also rose (for example `cd4_mix` 10 → 14), and `mix` still weights a gene by all of the target’s cells after some donors were dropped.

Not done: no tests, no cache hashes, no recomputation of the JSON, no `result.md` (this session is read-only). Open for Claude1: whether r7 was rejected because library scale also shrinks real low-count effects, or because constant mode was believed to be unbiased at one expected count.
