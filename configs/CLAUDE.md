# configs — what the stages read

| File | What it holds | Read by |
|---|---|---|
| `configs/config.yaml` | the data root and the challenge's constants: contexts, cells, caps | `src/vcc2026/config.py`, so every stage |
| `configs/trials.yaml` | the stage-45 trial, `trial-ext-profile`, and its defaults, seed 20260912 included | `src/vcc2026/trials.py`, for stage 45 |
| `configs/recipes/t<NN>.json` | the recipe of submission tNN: sources, weights and amplitude, per context. The files here are Davide's (`td NN`); a new recipe is named `td<NN>.json` or `ta<NN>.json` after its author (D-058, `docs/PROCEDURE.md` §2) | stage 100 |

- **A recipe is written before its generation**, with the prediction it is judged by
  (`docs/PROCEDURE.md` §2). Once stage 100 has run on it, it is never edited: its content and
  hash are in that run's manifest. A new idea is a new file.
- **Repository paths inside a recipe** (the cis pairs, the gene share) are read through
  `config.repo_file`: recipes written before 28 September name `reports/<folder>/…`, which since
  D-046 lives in `reports/<categoria>/<folder>/…`. A new recipe names the current path.
  `tests/test_pipeline_contracts.py` fails if a file a recipe names cannot be found.
- **The format of a recipe** is in the docstring of `scripts/100_build_context_effects.py`;
  use the declared reference recipe and its generation manifests as the example; the newest
  recipe is not necessarily adopted, and does not specify every stage-45 option.
- **The default seed is pinned by a test** (`tests/test_trial_inference.py`): changing it
  changes every regenerated matrix.
