# src/vcc2026 — the library of the live stages

Every module here is imported by at least one live stage. The table says which: that is what
changes when you change a module. `tests/test_live_tree.py` fails if the table and the imports
disagree, so update the row in the same commit as the import.

| Module | What it does (from its docstring) | Stages that import it | Modules that import it |
|---|---|---|---|
| `bench.py` | Six-metric bench shared by the single-cell benches; also `log` and `load_effects`, used by many stages | 71, 72, 73, 75, 76, 83, 97, 98, 99, 100, 101, 102, 103, 104 | — |
| `config.py` | Challenge constants and filesystem paths, loaded from `configs/config.yaml` | 45, 48, 71, 72, 74, 76, 77, 79, 83, 85, 97, 98, 99, 100, 101, 102, 103, 104 | `genes`, `trials` |
| `de_tools.py` | The scorer's own differential-expression call, usable outside a full scoring run | 72, 79, 83 | `bench` |
| `generator.py` | A learned generative model of one context's control cells (`ControlModel`) | 72, 73, 75, 76 | — |
| `genes.py` | The official 18,533-gene output axis | 45, 74, 76, 98, 100, 101, 103, 104 | — |
| `inference.py` | From a predicted log2 fold change to the raw counts a submission contains | 45, 72, 76, 83 | — |
| `manifest.py` | Run manifests: what went in, what came out, and what it was run with | 45, 48, 77, 100 | — |
| `multisource.py` | Same-target effects from several perturbation sources, on the official gene axis | 98, 100, 101, 103, 104 | `transfer_model` |
| `packaging.py` | Validate and package a prediction into a `.vcc` in bounded memory | 48 | — |
| `predictor_sc.py` | A per-target log fold change, assembled from single-cell evidence | 73, 75, 76, 77, 98, 100, 104 | `multisource`, `priors` |
| `priors.py` | Target priors that need no measurement of the target: the CRISPRi cis head and network partners | 100, 104 | — |
| `remote_csr.py` | Selected rows of a remote CSR matrix, read as exact byte ranges in parallel | 97, 102 | — |
| `remote_ranges.py` | Budgeted HTTP random access to public files | 97 | — |
| `resources.py` | Measured machine limits, and the peak memory a run actually used | 45, 48 | `packaging` |
| `sampling.py` | Turn predicted mean expression profiles into raw count matrices | 45, 72, 73, 75 | — |
| `sc_effects.py` | Per-target effects estimated from single cells, with their own uncertainty | 73 | `predictor_sc` |
| `sc_stream.py` | Read a dense, contiguous single-cell h5ad in one sequential pass | 71, 75, 76, 77, 79, 83, 98 | `predictor_sc` |
| `submission.py` | Stream a prediction to .h5ad without ever holding the full matrix in RAM | 45, 76 | — |
| `trials.py` | Trial definitions, read from `configs/trials.yaml` | 45 | — |
| `transfer_model.py` | A learned magnitude channel for transferred knockdown effects (stage 104) | 104 | — |

## Rules for this folder

- **No definition without a live caller.** A function that only its own test calls is dead
  code, and `tests/test_live_tree.py` fails on it. The three helpers kept for the tests are
  listed there, each with its reason.
- **The scorer and `anndata` are imported inside the functions that use them**, so a stage
  that only wants `bench.log` does not load them. `submission.py` needs `anndata` at import
  and is the one exception.
- **No data paths in code.** Paths come from `config.paths()`, which `VCC2026_DATA_ROOT`
  overrides; `tests/test_pipeline_contracts.py` rejects `C:/Users` in this folder.
- **A change under stages 45, 48, 76 or 100 is proven on their output, not by reading.** Run
  a pilot before and after and compare the files byte for byte. The 24 September section of
  `docs/ARCHIVIO.md` shows how it was done for stage 45.
- A new module gets a row in the table above, in the same commit.
