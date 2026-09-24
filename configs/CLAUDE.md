# configs — what the stages read

| File | What it holds | Read by |
|---|---|---|
| `configs/config.yaml` | the data root and the challenge's constants: contexts, cells, caps | `src/vcc2026/config.py`, so every stage |
| `configs/trials.yaml` | the stage-45 trial, `trial-ext-profile`, and its defaults, seed 20260912 included | `src/vcc2026/trials.py`, for stage 45 |
| `configs/recipes/t<NN>.json` | the recipe of submission tNN: sources, weights and amplitude, per context | stage 100 |

- **A recipe is written before its generation**, with the prediction it is judged by
  (`docs/LAVORO.md` §2). Once stage 100 has run on it, it is never edited: its content and
  hash are in that run's manifest. A new idea is a new file.
- **The format of a recipe** is in the docstring of `scripts/100_build_context_effects.py`;
  the latest recipe is the best example.
- **The default seed is pinned by a test** (`tests/test_trial_inference.py`): changing it
  changes every regenerated matrix.
