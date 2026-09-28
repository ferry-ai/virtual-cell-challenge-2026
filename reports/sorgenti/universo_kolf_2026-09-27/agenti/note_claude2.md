# Note di claude2 su kolf_effects.py

Rapporto integrale di claude2 (base di lancio, run `20260927-165427-v2-kolf-effects`, Opus 5.5 con sforzo massimo, brief `v2-claude2-kolf-effects.md`), copiato il 27 settembre senza modifiche. L'autoverifica, eseguita da Claude1 lo stesso giorno, passa 12 controlli su 12.

I've written `reports/universo_kolf_2026-09-27/kolf_effects.py`, but nothing has been run (the task says I can't run commands), so the script and its 12-check self-test are untested.

**Commands** (from the repo root; the real run needs `kolf_sums.py merge` to have written `sums.npz` first):
```
.\scripts\py.cmd reports\universo_kolf_2026-09-27\kolf_effects.py --selftest
.\scripts\py.cmd reports\universo_kolf_2026-09-27\kolf_effects.py --sums <dir>\sums.npz --out <data_root>\processed\universe_kolf_2026-09-27_me1 [--report reports\universo_kolf_2026-09-27\effetti_me1]
```
Other options: `--chunk 600`, `--min-cells 10`, `--min-expected 1.0`, `--panel` (defaults to `raw/controls/pert_counts.csv` when that file exists). If the self-test passes it should print 12 PASS lines and `selftest: 12 of 12 checks passed` (inferred).

**What the script does** (implemented; none of it run):
- **Reading the matrix** (`:108`, `:131-184`): `npy_member` finds `sums.npy` through the zip directory, reads the name and extra-field lengths from the member's own 30-byte local header, then parses the NPY header. The script refuses the file if the member is compressed or its sizes disagree. The matrix is then mapped as a (genes × groups) array, 256 genes per map, one map at a time. For each chunk it reads only that chunk's rows.
- **One extra full pass** (`:186`, beyond what you asked): before writing anything it reads the whole matrix once. It checks values are finite and ≥ 0 on genes in the file and NaN on the absent ones, and sums each group's counts on the axis (this gives the off-axis column). It also computes the sha256 of the whole archive in the same pass. It refuses to run if a group's axis counts exceed its `total_counts` by more than 1 + 1e-6 × total; smaller negatives are set to 0 and counted in the manifest. Cost: one extra read of the ~6.9 GB file.
- **Building X** (`:217`): the genes present in the file plus `__off_axis__` (= `total_counts` minus the axis counts), as float64 sparse rows built one row at a time. Each chunk's rows are checked against the first pass's sums.
- **Estimation** (`run`, `:246`): chunks of 600 targets in `sorted` order, NTC excluded. NTC becomes `non-targeting`, donors are `pool<k>`, condition is `KOLF2.1J`. The call is `effects_from_pseudobulk(..., min_cells=10, min_expected=1.0)`, then `AxisTable.from_source("kolf", ...)`. It writes `kolf_NN.npz`, then `index.csv`, then `manifest.json` last with open mode `"x"`. `--out` and `--report` must not exist beforehand.
- **Memory** (inferred, not measured): the dense block is at most 4,808 × 17,971 × 4 B = 346 MB, freed before the estimator runs. The sparse matrix is about 0.6 GB if 60% of entries are non-zero, 1.04 GB if all are. Estimator outputs add about 0.4 GB. So roughly 1.0 GB typical and 1.6 GB worst case. The manifest records the peak working set.
- **Self-test** (`:480-613`): builds a 55-group, 40-gene synthetic `sums.npz` using kolf_sums' own `_matrix_file`, `_write_columns` and `_publish`, then runs the pipeline with chunk 3 and a 7-gene window. The 12 checks:
  1. The memory map reads the same as `np.load`, for 1-, 7- and 256-gene windows.
  2. The planted knockdown (G05 at a quarter) is recovered within 0.02 of ln 0.25. By hand I expect an error of about 0.007 (inferred).
  3. The knockdown does not leak to other targets.
  4. Absent genes are NaN in raw, se and shrunk; all other file genes are finite.
  5. `min_expected` is in effect: a gene with 0.2–0.6 expected counts is NaN, but finite when `min_expected` is 0.
  6. T_FEW (4, 9 and 7 cells) has no effect row and an empty chunk in `index.csv`.
  7. Pools under 10 cells are skipped (T_MIX counts 48 cells).
  8. Output equals one direct estimator call on the whole matrix within 1e-6.
  9. Library, proportional case: multiplying every row's total by 1.5 (controls included) changes no effect.
  10. Library, one target: multiplying one target's totals by 1.5 shifts its raw effects by exactly −ln 1.5. Check 9 alone would also pass if the off-axis column were dropped; this one fails in that case.
  11. Output files: keys, dtypes, metadata, `index.csv` targets and manifest sha256/bytes all match.
  12. A second run into the same `--out` is refused.

**Arrays read and written:**
- **Read:** `target`, `pool`, `n_cells`, `total_counts`, `genes`, `file_columns`, `missing_genes`, `groups_sha256`, `url` (small arrays, `np.load`); `sums.npy` through the memory map only.
- **Written, per chunk:** `targets`, `shrunk`/`raw`/`se` (float32, targets × 18,533), `n_cells`, `meta` (the estimator's metadata plus source, url, `groups_sha256`, min_cells and licence).
- **`index.csv`:** target, chunk, n_cells, cells_total, pools_with_cells, pools_min_cells, in_panel (only if a panel file is found), on_official_axis.
- **`manifest.json`:** input path, size, sha256, `groups_sha256`, data offset and whether the axis matches the official one; the estimator's full options; the chunks' size and sha256; and a summary with target counts, NTC cells per pool, share of each library on the axis, whether all sums are whole numbers, and peak memory.

**What I'm unsure about in kolf_sums' layout:**
- **`total_counts`:** it sums the authors' `obs/total_counts`. I assumed this equals the sum over all genes of `layers/counts`; that is not checked on the real file. If it was computed on another gene set, the off-axis column silently absorbs the difference. The script only fails when the axis counts exceed the total.
- **Group row order** (target code × 8 + pool): the code doesn't depend on it, but speed does. If the `gene_target` categories are not alphabetical, each chunk's rows are scattered, and each chunk may read about the whole 6.9 GB matrix (inferred).
- **Precision above 2^24:** merge stores float32, so counts above 2^24 (possible in the NTC rows of highly expressed genes, about 10k cells per pool) lose integer exactness. The relative error is ≤ 6e-8; my reasoning says it doesn't matter for the estimates (inferred).
- **Control label:** the `NTC` label comes from `RISULTATI.md:42`; the script refuses a file without it.
- **Pools without NTC cells:** if any pool has none, the estimator skips that pool's rows. This is logged and recorded per pool in the manifest.

**Choices you may want to change:**
- **File numbering:** `kolf_NN` follows the K562 script: one file per block of 600 targets, holding only that block's targets with effects, so usually fewer than 600 rows. orion_universe instead repacks files to exactly 600 targets with effects. `atlas_bench` only reads file names from `index.csv`, so either works there.
- **Estimator batch size:** one call per 600 targets; orion used 150 per call.
- **Extra pass:** keep or drop the full validation and hash pass.
- **`--report`:** optional, and the folder name is yours to choose.

**Not done:**
- I did not run the self-test, `31_check_docs.py` or the unit test suite.
- From reading `REGISTRO.md:98` together with `31_check_docs.py:288-299`, the folder entry `reports/universo_kolf_2026-09-27/` covers the new file.
- The script imports `kolf_sums`, so it needs h5py and httpx, as `run_blocks.py` does.
- There is no existing KOLF panel cache to check parity against.

**Files changed:**
- `reports/universo_kolf_2026-09-27/kolf_effects.py` (new): the script and its self-test.
