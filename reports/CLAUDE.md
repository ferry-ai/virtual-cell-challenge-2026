# reports — the evidence, one folder per experiment

- **Nothing here is overwritten or deleted**, not even a failed attempt: it records what was
  seen that day. A new run writes to a new folder, `reports/<tema>_<data>/`.
- **Every new file or folder needs a row in `docs/REGISTRO.md`**, or
  `scripts/31_check_docs.py` fails. One row can cover a folder of homogeneous files: a path
  that ends with `/`.
- **Do not browse to find evidence.** Many folders are about experiments that are closed and
  archived. Start from the checkpoint or decision that cites a report, or search
  `docs/REGISTRO.md` for its path: the row says whether it can still be relied on.

## What a submission leaves here

Registered before generating, because the threshold does not move after the score
(CP-0030):
- `reports/prediction_t<NN>_<data>/prediction.json`: the expected band, and the rule to read
  the result by;
- `reports/trial_<data>/submission_texts.md`: the name and description of the upload.

Written while generating and submitting, in `reports/trial_<data>/`:
- `t<NN>_manifest_45_generate_prediction.json` and `t<NN>_generation_diagnostics.json`;
- `t<NN>_manifest_48_package_prediction.json` and `t<NN>_packaging.json`;
- the output of `vcc`, saved as it is: `submit_t<NN>_started.txt`, `submit_t<NN>_raw.json`,
  `submit_<entry>.json`, `status_<entry>.json`.

After the score come `reports/prediction_t<NN>_<data>/comparison.json`, a checkpoint and §0
of `docs/PROGETTO.md`. The latest complete example is t15: `reports/prediction_t15_2026-09-23/`
and `reports/trial_2026-09-24/`.

The owner's authorisations are transcribed in `reports/trial_2026-09-22/autorizzazioni.md`.
Read them, but a new agent confirms in chat before using one.
