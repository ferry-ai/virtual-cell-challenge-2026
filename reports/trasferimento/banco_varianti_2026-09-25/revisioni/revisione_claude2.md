The bench's shrinkage gain is real in its fair form, but the headline sizes for three of the four held-out sources are inflated by a defect: in the recomputed shrinkage variants the CD4 source seems to vote zero instead of being skipped, and the variants are scored on different target sets.

## Findings (read-only; I ran no commands)

**1. Different target sets between variants — confirmed in code and outputs.** `shrink_sweep.py:95-97` keeps only the targets whose pooled row is non-zero, and it recomputes this for each variant. `r2/variants.csv` shows the effect:

| Held out | Targets, raw | Targets, zk* |
|---|---|---|
| K562 | 271 | 257 |
| HCT116 | 265 | 242 |
| HEK293T | 278 | 254 |
| CD4 | 292 | 292 |

So table 2 of `RISULTATI.md` ranks the shrunk variants on fewer targets and fewer candidates than raw (**measured**).

**2. CD4 votes zero in the recomputed shrinkage variants — suspected, strongly.** In `shrink_sweep.py:37-38`, `zz` is set to 0 wherever `se>0` is false, and that includes NaN SE, so the effect becomes exactly 0 (**confirmed in code**). `mix` then counts that 0 as a measured value with full reliability weight (`multisource.py:201-204`). That breaks the rule that unmeasured pairs never vote zero.

The evidence that CD4's SE is unusable here (**inferred**):
- Targets drop only when CD4 is a predictor.
- CD4's `n_conf` is 0.0 everywhere (`r1/variants.csv:23`). That fits NaN SE, though very large SE would also give it. I did not open the npz.
- The recomputed zk4 disagrees with the cache's `shrunk` exactly when CD4 predicts. With CD4 held out they match (0.6812 vs 0.6812). Otherwise they differ:

| Held out | Cache shrunk (r1) | Recomputed zk4 (r2) |
|---|---|---|
| K562 | 0.7769 | 0.7632 |
| HCT116 | 0.7005 | 0.7343 |
| HEK293T | 0.6735 | 0.7479 |

The fair comparison is r1 `shrunk_g1`: it uses the same targets as raw and keeps CD4's own shrinkage. Its gain is only +0.013 / +0.021 / +0.013 / +0.016 (CD4 / K562 / HCT116 / HEK293T). The +0.083 to +0.123 on the two Orion sources in table 2 therefore mixes shrinkage with a hidden down-weighting of CD4, gene by gene (**inferred**). The report half-notices this at `RISULTATI.md:98-99`.

**3. The noise simulation inherits problem 2.** `noise_sim.py:77-81` uses the same `table()`, so CD4 still votes zero in its zk16/zk64 arms. The target sets are equal here, because `has` comes from raw (`noise_sim.py:82`). For CD4's missing targets, the zk arms predict noise only, which penalises zk slightly. The +0.058 and +0.080 for HCT116 and HEK293T carry the same confound (**inferred**).

**4. The q99 amplitude rule — suspected.** Matching q99 needs amplitudes of 7 to 39 on zk64 (`r4/measurements.json`: 19.4 for HCT116, 38.7 at 2×q99). Below the 99th percentile everything is near zero. Above it, `a·e` for the top genes can reach the ±20 clip (`noise_sim.py:101`), a fold change of up to e^20 that no real generator would produce. The maximum |a·e| is never reported. The simulation's truth has no noise, and its noise model is Poisson only. That noise model does not itself favour small effects: its SD is the same in every arm (`noise_sim.py:93,100`). But amplifying a few genes 20 to 40 times lifts them far above that noise. Whether the real generator and the Wilcoxon members tolerate this is untested.

**5. Checks that cleared:**
- **Leakage:** cleared. Predictors exclude the held-out source's family (`analyze.py:143`, `shrink_sweep.py:83`, `noise_sim.py:72`). `common()` uses only the predictor's own targets, and q99 comes from predictions, not truth.
- **Sparsity reward:** cleared. The cosine divides by the norm of the prediction row, which is constant across the candidate truths, so a sparse prediction gains nothing from sparsity itself. NaN truth becomes 0 and the gene weights are the same for every variant (`analyze.py:80-83`).
- **Ties:** cleared. All-zero rows are filtered out, and noise_sim adds noise.
- **Tuning on the test sources:** suspected, mild. k=64 is simply the best value seen, the curve is still rising, and there is no nested selection.

## Arithmetic spot-checks (all match, **measured**)

- **Table 1** against the r1 json: CD4 0.6677, 0.6812, 0.662, 0.6662, 0.5005 → 0.668, 0.681, 0.662, 0.666, 0.501. K562 0.7769 → 0.777; HEK293T shuffled 0.4962 → 0.496.
- **Table 2** against `pds_minus_raw` in r2: CD4 0.0072, 0.0135, 0.0231, 0.0302, −0.0014; K562 −0.0106, 0.0275; HEK293T 0.1230.
- **Table 4** against r4: all 24 cells match. That includes K562 zk16 0.7396 → 0.740 and HCT116 raw 0.6365 → 0.637.
- **Text below table 4:**
  - zk64 minus t15 raw = 0.0264, 0.0416, 0.0581, 0.0797 ✓.
  - Calibration: 0.0195 to 0.0487 ✓.
  - t16 prediction: 0.0054 to 0.0257 ✓.

## Recommended control

Rerun `shrink_sweep` and `noise_sim` to a new `--out` with one change. Shrink a source only where its SE is finite and positive; otherwise keep the pair NaN, or use CD4's cache `shrunk`. Score every variant on a single fixed target set. Also add a "raw, no CD4" arm, so that source choice is separated from shrinkage. Report paired per-target differences with a bootstrap interval.

**What would kill the claim:** on the fixed target set with CD4 handled correctly, zk64 minus raw falls to about the r1 cache gain (+0.013 to +0.021) or below. Or "raw, no CD4" matches zk64 on the Orion sources. Either way, the large gain would come from dropping CD4, not from shrinkage. If the interval also includes 0 on two or more held-out sources, the proxy supports no submission at all.

## Not done / open questions

- I did not open the npz cache, so the NaN/0 SE for `cd4_mix` is inferred. Please confirm with `np.isfinite(se).mean()` on it.
- I did not read `gating.py` and `controls.py`, or check the r3 numbers.
- I did not measure the maximum |a·e| in the zk64 arms.
- Open question for Claude1: how would stage 100 treat pseudobulk sources that have no SE?
