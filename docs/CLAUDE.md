# docs — the map, the working guide, the decisions, the registry, the archive

The rules for documents (never delete, never edit a checkpoint, states and review sheets) are
in the root `CLAUDE.md`, which is always loaded. This page is the index of the folder.

## The documents that run the project

| File | Answers | How it is kept |
|---|---|---|
| `docs/PROGETTO.md` | where the project stands (§0), the problem, what is uncertain | §0 is rewritten after every scored submission |
| `docs/LAVORO.md` | how the live pipeline runs: stages, commands, rules | the only operational document |
| `docs/SOTTOMISSIONE.md` | the submission contract, §1–2 | `da-verificare`: §3 and §6 name archived stages (sheet R-015) |
| `docs/DECISIONI.md` | what was decided, why, and when to reopen it | a table row and a `### D-NNN — …` section per decision |
| `docs/REGISTRO.md` | whether a document, report or dataset can be relied on | a row for every file under `docs/` and `reports/`; search it for a path |
| `docs/ARCHIVIO.md` | what left the tree, and the command that brings it back | a section per cleanup, a row per file |
| `docs/checkpoints/` | what happened, when, on what evidence | immutable; `docs/checkpoints/INDICE.md` lists them, the latest last |

`scripts/31_check_docs.py` enforces the structure of the registry, the decisions and the
index, and every link between them. It says nothing about whether a claim is true.

## The analyses of 11–15 September

Eight documents analyse experiments and choices from before the single-cell pipeline:
- `BENCHMARK_TRE_CONTESTI.md`, `BENCHMARK_MODULARE.md`, `ENCODER_INPUTS.md` and `SVD_E_RANGO.md`;
- `revisione_analisi_2026-09-11.md` and `revisione_grok_2026-09-12.md`;
- `candidate_adversarial_review_2026-09-12.md` and `data_strategy_2026-09-11.md`.

Most of the experiments they discuss are closed, and their code is archived
(`docs/PROGETTO.md` §2). They are not a guide to today's pipeline. Open one when a decision
or a checkpoint cites it, after reading its row in the registry: their states differ.
