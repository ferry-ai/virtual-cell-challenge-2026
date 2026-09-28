# docs — the map, the working guide, the decisions, the registry, the archive

The rules for documents (never delete, never edit a checkpoint, states and review sheets) are
in the root `CLAUDE.md`, which is always loaded. This page is the index of the folder.

## The documents that run the project

| File | Answers | How it is kept |
|---|---|---|
| `docs/PROGETTO.md` | where the project stands (§0), the problem, what is uncertain | §0 is rewritten after every scored submission |
| `docs/PIANI.md` | what to do next; promising open work and closed lines | index of priorities and dependencies; assignments live in the cards |
| `docs/piani/` | the next action, owner, dependencies and closure evidence for one plan | editable cards; read `docs/piani/CLAUDE.md` and shared-workspace rules before editing |
| `docs/LAVORO.md` | how the live pipeline runs: stages, commands, rules | the procedural guide; work selection is in PIANI |
| `docs/GENERALIZZAZIONE.md` | how research selects data and evaluates new targets and contexts | research scope and evaluation requirements under D-044; does not replace submission commands |
| `docs/SOTTOMISSIONE.md` | the submission contract, §1–2 | `da-verificare`: §3 and §6 name archived stages (sheet R-015) |
| `docs/DECISIONI.md` | what was decided, why, and when to reopen it | a table row and a `### D-NNN — …` section per decision |
| `docs/REGISTRO.md` | whether a document, report or dataset can be relied on | a row for every file under `docs/` and `reports/`; search it for a path |
| `docs/ARCHIVIO.md` | what left the tree, and the command that brings it back | a section per cleanup, a row per file |
| `docs/checkpoints/` | what happened, when, on what evidence | immutable; `docs/checkpoints/INDICE.md` lists them, the latest last |
| `docs/storico/` | analyses and texts that no longer guide the work, kept as they were | its `README.md` gives the core and the status of each; moved there on 28 September (D-046) |

`scripts/31_check_docs.py` enforces the structure of the registry, the decisions and the
index, and every link between them. It says nothing about whether a claim is true.

## The analyses of 11–15 September, and other superseded texts

They are in `docs/storico/`, with an index: the eight analyses of 11–15 September (benchmarks,
encoder inputs, SVD, the first reviews and data strategy), the history sections of the root
README and the old §3–§4 of PROGETTO. Most of the experiments they discuss are closed and their
code is archived. They are not a guide to today's pipeline. Open one when a decision or a
checkpoint cites it — a checkpoint names it as `docs/<file>`, and it is found in `docs/storico/`
— after reading its row in the registry: their states differ.
