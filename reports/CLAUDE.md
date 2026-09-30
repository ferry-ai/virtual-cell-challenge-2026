# reports — the evidence, filed by category

A folder here is evidence of what was seen on its date, and it is never edited: a new run
writes to a new folder. Since 28 September 2026 (D-046) every folder sits in a category:
`reports/<categoria>/<tema>_<data>/`. **The map is [README.md](README.md)**: what to read
first, the eight categories, and the code other folders import. Each category has a
`README.md` with one row per folder: date, core, whether it still holds, how much it weighs.

Choose current work through `docs/PIANI.md`, not through next steps in a dated report.
After a run, link its evidence from the relevant plan card; keep the report immutable.

## Rules for a new report

- **Pick the category** by the question the folder answers:

  | Category | Question |
  |---|---|
  | `gara/` | what the scorer, the anchors, the leaderboard or the A/B/C controls say |
  | `invii/` | what we submitted and how it scored (`prediction_t<NN>_<data>/`, `trial_<data>/`) |
  | `sorgenti/` | what a source contains and how its effects are estimated |
  | `trasferimento/` | whether a variant of the production recipe helps, on held-out sources |
  | `modelli/` | whether a model learned over many contexts generalises |
  | `generatore_e_banchi/` | how effects become cells and calls; six-metric benches with the real scorer |
  | `analisi/` | reviews, state analyses, hypotheses |
  | `storico/` | nothing new goes here: it holds the closed lines of 11–19 September |

- **Name it `<tema>_<data>`, never reusing a folder name** already present in any category:
  checkpoints and older reports name folders as `reports/<cartella>/`, and that path is
  resolved one level down by name (`scripts/31_check_docs.py`, `config.repo_file`).
  `tests/test_live_tree.py` fails on a duplicate name or a folder outside a category.
- **Add a row to the category's `README.md`** (newest first) and a row to `docs/REGISTRO.md`,
  in the same commit. One registry row can cover a folder of homogeneous files.
- **Write down the claim type**: measured, interpretation, hypothesis, proposal. A proxy is not a
  VCC score: say which members it sees.
- **Code in a report is a record.** If you need a changed copy of a file other reports import
  (see the table in README.md), put it in your new folder and import it from there.
- **A folder with many files or several sub-studies gets a `README.md`** that indexes it by area,
  with what to read first (D-048).
- **Bulky machine outputs** (over about 1 MB) go to the data root, with a committed manifest of
  paths, sizes and hashes, unless they are the only evidence of a verdict (D-048).
- **Reports of other agents** launched through the agent hub go, whole, in an `agenti/` subfolder
  of the study's folder, as `<tema>_<agente>.md`, stating at the top the agent, the run, the
  model, the mode and the brief. The owner asked for this on 25/09: the hub's `runs/` can be
  cleaned (`docs/AGENTI.md` §1). A report of an agent is a claim until you verify it.
- **One declared exception to "never edited":** the incident ledger in
  `reports/analisi/lead_scientist_2026-09-29/learning/incidents/`, where new revision files are
  added and none is changed (`docs/ERRORI.md`, D-049).
- **A path you cite** goes as `reports/<categoria>/<cartella>/…` from now on.

## What a submission leaves here

Registered before generating, because the threshold does not move after the score
(CP-0030):
- `reports/invii/prediction_t<NN>_<data>/prediction.json`: the expected band, and the rule to
  read the result by;
- `reports/invii/trial_<data>/submission_texts.md`: the name and description of the upload.

Written while generating and submitting, in `reports/invii/trial_<data>/`:
- `t<NN>_manifest_45_generate_prediction.json` and `t<NN>_generation_diagnostics.json`;
- `t<NN>_manifest_48_package_prediction.json` and `t<NN>_packaging.json`;
- the output of `vcc`, saved as it is: `submit_t<NN>_started.txt`, `submit_t<NN>_raw.json`,
  `submit_<entry>.json`, `status_<entry>.json`.

What follows the score is one checklist, `docs/LAVORO.md` §2, point 7. Two complete examples:
t25, all local (`reports/invii/prediction_t25_2026-09-27/`, `reports/invii/trial_2026-09-27/`), and
t28, generated on Colab and uploaded from a local copy (`reports/invii/prediction_t28_2026-09-29/`,
`reports/invii/trial_2026-09-29/`).

The owner's authorisations are transcribed in `reports/invii/trial_2026-09-22/autorizzazioni.md`.
Read them, but a new agent confirms in chat before using one.
