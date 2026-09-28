# KOLF streaming count sums

**Measured:** Implemented `kolf_sums.py` and seven network-free integration tests in
`tests/test_kolf_sums.py`. No public-file ingestion was run. Only this new report
folder and the new test file were changed.

## Interface and outputs

**Measured (implementation):** With the project's `src/` on `PYTHONPATH`:

```text
python kolf_sums.py obs --url URL --axis /path/to/gene_names.csv --out DIR
python kolf_sums.py block --url URL --groups DIR/groups.npz --block 0 --blocks 16 --out DIR
# Repeat block for 1 through 15, using the same groups.npz.
python kolf_sums.py merge --dir DIR --out DIR/sums.npz
```

`--axis` is optional: without it the script calls `official_axis().symbols`.
The explicit CSV option needs only numpy, h5py and httpx plus the standard library;
the default axis loader additionally needs the project's normal dependencies and
configured control bundle. The CSV must have one header and 18,533 unique symbols.
No data/output paths are hardcoded. Python 3.10-compatible syntax is used.

`groups.npz` stores `group_of_cell` (int32), group `target`, `pool`, `n_cells`,
`total_counts` (float64), `axis_genes`, `file_columns` (-1 if absent),
`missing_genes`, source URL/size, category labels, CSC pointers and physical chunk
maps. All four requested categorical columns are read and validated; batch and
perturbed do not filter cells or alter grouping. Only observed target/pool pairs
are emitted, including NTC. Missing categorical codes and duplicate source gene
symbols fail explicitly. Pools use the supplied channel-code modulo 8 rule.

Each `block_I_of_K.npz` stores `genes`, `axis_positions`, `sums` (float32,
groups by genes), I/K, groups SHA-256, and logical/fetched count-byte totals.
The contiguous axis splits follow `np.array_split` on present genes; I starts at 0.
Empty blocks are valid. The final NPZ stores `sums`, `genes` on the full official
axis, the four group-table arrays, mapping/missing genes, URL and groups SHA-256.
Unmeasured genes are NaN; measured all-zero columns stay zero. Archives are
standard NPZ, readable by `np.load(..., allow_pickle=False)`.

## Memory, storage and resumption

**Measured (implementation), inferred (large-file bound):** A batch contains at most
8,000,000 nonzeros and 32 genes, irrespective of K. Raw float32/int64 output arrays
therefore total at most 96 MB. Four range workers use the reader's default 8 MiB
request target. The supplied real chunk sizes are smaller than that target.
One unusually large column is subdivided into bounded nonzero segments, accumulated
in float64. Ordinary columns use float64 `np.bincount` and are cast once to float32.
The real layout allows at most 93,504 groups (11,688 x 8); a 32-column output window
is at most 11,968,512 bytes. Per-cell IDs, bincount temporaries, chunk maps, futures,
HTTP buffers and metadata remain independent of K. This is conservatively below
the requested ~2 GB for the supplied layout; peak RSS was not measured at real scale.

Both block and merge create a disk-backed Fortran-order NPY, map only small windows,
flush/unmap each window, and stream it into an uncompressed NPZ in 8 MiB buffers.
Merge never loads a whole block matrix. Even K=1 does not map the full output.
For all 93,504 possible groups and 18,533 genes, the matrix is 6,931,638,528 bytes.
Allow roughly twice the matrix size as additional free disk while publishing a
block or final archive; existing input blocks remain on disk during merge.

**Measured:** Completed blocks are checked against groups SHA-256, I/K, expected
gene positions/names and matrix header/length, then skipped without any fetch or
rewrite. A uniquely named temporary directory holds partial work. The final NPZ
name is published by same-filesystem rename only after its archive is closed.
Exceptions publish nothing; process-kill leftovers have temporary names and are
ignored. Resume recomputes the interrupted block, not an internal batch checkpoint.
Merge rejects missing/extra blocks, mixed splits, wrong group identity or gene
coverage/order. Existing obs/final outputs are refused. Assign only one worker per
block/output; concurrent publication of the same path is not coordinated.

## Verification

**Measured:** The requested wrapper works. Interpreter:
`C:\Users\ferra\vcc2026-data\.venv\Scripts\python.exe`; numpy 2.5.3, h5py 3.16.0.
Exact focused command and final output:

```text
.\scripts\py.cmd -m unittest tests.test_kolf_sums
.......
----------------------------------------------------------------------
Ran 7 tests in 8.595s

OK
```

Tests cover the independently computed dense reference (including NTC, modulo
pools, all-gene total_counts, absent and zero genes), K=1/K=3 identical merges,
forced four-nonzero batches splitting individual columns, empty blocks, missing
blocks, fetch-free resumption, failure before publication, mixed K and wrong groups.
All synthetic files live in temporary directories inside the working copy.
Tests explicitly replace both HTTP entry points with exceptions; count bytes use
the real `local_fetcher` and chunk-map/read_rows implementation. X contains different
values, so accidentally using X would fail the dense comparison.

**Measured:** `.\scripts\py.cmd scripts\31_check_docs.py` initially reported:

```text
1 problem(s):
  - REGISTRO.md: reports/universo_kolf_2026-09-27/kolf_sums.py exists but no registry entry covers it
```

The new report needs a registry entry and a reports index entry during integration.
Those existing documents were deliberately left untouched under the task's scope.
**Measured:** Final checker output after adding this report:

```text
2 problem(s):
  - REGISTRO.md: reports/universo_kolf_2026-09-27/kolf_sums.py exists but no registry entry covers it
  - REGISTRO.md: reports/universo_kolf_2026-09-27/result.md exists but no registry entry covers it
```

**Measured:** After the final code change (constant-space split selection), the
combined local regression command and output were:

```text
.\scripts\py.cmd -m unittest tests.test_kolf_sums tests.test_remote_csr tests.test_remote_ranges
................
----------------------------------------------------------------------
Ran 16 tests in 4.405s

OK
```

**Measured:** `.\scripts\py.cmd reports\universo_kolf_2026-09-27\kolf_sums.py --help`
exited 0 and displayed the three subcommands. `git status --short` showed only the
new report folder and `tests/test_kolf_sums.py`; no existing tracked files changed.
**Measured:** Broader suite command (TEMP/TMP redirected inside the worktree so
existing tests also keep their synthetic files here):

```powershell
$env:TEMP=(Get-Location).Path; $env:TMP=(Get-Location).Path; .\scripts\py.cmd -m unittest discover -s tests
```

Its final summary was:

```text
Ran 190 tests in 410.275s

FAILED (failures=1, errors=1)
```

The failure was `test_doc_workflow.CheckerTests.test_this_repository_is_consistent`,
which reported the unregistered script (the suite started before result.md was
created). The error was
`test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`:
`ModuleNotFoundError: No module named 'cell_eval2.config'`, originating at
`src/vcc2026/de_tools.py:39` via `bench.py:155`. Those files were not modified.
**Inferred:** This latter failure is an environment/dependency issue outside the
KOLF implementation. It was not repaired under this task's restricted edit scope.

## Bytes to plan K

**Inferred from the user-provided layout, not independently measured remotely:**
Source: `https://ndownloader.figshare.com/files/64650261`, the HDF5 layout supplied
in the task from its 2026-09-27 inspection.
For selected file columns C, exact useful count payload is
`12 * sum(indptr[c+1] - indptr[c] for c in C)` (4 bytes data + 8 bytes indices).
All 37,567 genes contain `7,872,183,461 * 12 = 94,466,201,532` bytes,
or 94.47 decimal GB / 87.98 GiB. X is never requested.

If all 18,533 official symbols were present AND their average nnz equalled the
file-wide mean, their payload would be 46.60 GB. On that heuristic only:
K=8 gives 5.83 GB/block, K=16 gives 2.91 GB/block, K=32 gives 1.46 GB/block.
Actual axis coverage and per-gene sparsity are unknown; equal gene counts do not
imply equal bytes. Increasing K is for scheduling/retry granularity, not RAM control.

After obs, calculate exact useful bytes per candidate split offline:

```python
import numpy as np
with np.load("DIR/groups.npz", allow_pickle=False) as g:
    columns = g["file_columns"]
    columns = columns[columns >= 0]
    ptr = g["indptr"]
    K = 16
    print([12 * int(np.sum(ptr[c + 1] - ptr[c]))
           for c in np.array_split(columns, K)])
```

Actual transfer additionally includes request coalescing gaps (up to 64 KiB
between merged pieces), HTTP retries and the one-time HDF5/obs metadata reads.
Partial chunks are read exactly, without rounding each column to a full chunk.
The block's `fetched_count_bytes` measures successful fetched ranges including
coalescing gaps, excluding retry traffic and obs metadata. Obs has a 512 MiB
cumulative metadata-read budget and a 32 x 128 KiB range cache; adequacy of that
budget for this file has not been verified.

## Limits and integration questions

**Unverified:** The remote source, real axis coverage, production peak RSS,
Colab/Kaggle execution and throughput. No network was used. Maps assume the source
is immutable: URL and HTTP total size are checked, but equal-size content mutation
cannot be detected. Resume validates metadata/header/length, not a full payload
checksum scan; merge reads the full ZIP members and checks their CRCs.

**Open for Claude1:** Add the new folder to the registry/index when integrating;
choose the official axis path, scratch disk location and K after inspecting cached
indptr; resolve the environment's missing `cell_eval2.config` before expecting the
full suite to pass. No source adoption or model-quality claim follows from these
synthetic tests.
