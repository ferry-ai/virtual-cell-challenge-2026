# scripts — the live stages

What each stage does and where it runs is the table in `docs/LAVORO.md` §4; the commands of a
submission are in §1, the final set in §7. The same stages by role:

```
submission path   97 CD4 · 102 Orion ─▶ 98 sources ─▶ 100 effects ─▶ 45 cells (or 76) ─▶ 48 package ─▶ vcc submit
experimental      104 learned magnitude channel on the effects, before the cells (not adopted, bench r5)
contexts          85 markers · 99 genetic fingerprints
checks            83 calls on a prediction · 72 generator null · 79 fast-DE parity · 101 and 103 transfer diagnostics
benches (Colab)   73 K562 · 75 HepG2
official scale    82 anchors from official statuses · 84 expected official score of a bench arm
inputs            71 K562 single cell · 74 gene coordinates · 77 cis pairs
documentation     30 new checkpoint · 31 check the documents
```

`tests/test_live_tree.py` fails if the §4 table, or this map, and the folder disagree, or if
the next free number in §4 is wrong: add the row and the number in the same commit as the
script.

## What makes a stage

The root `CLAUDE.md` already says: numbered, single-purpose, never overwriting, run through
the wrappers. In this folder, also:
- **The first line of the docstring says what the stage does**, and the docstring carries a
  usage example.
- **The script puts `src/` on `sys.path`**, so it runs without a wrapper too; a new stage keeps
  that line.
- **Data paths come from `config.paths()` or from arguments**, never from a literal:
  `tests/test_live_tree.py` rejects `C:/Users` in a stage's code.
- **Helpers are shared through `src/vcc2026`, never copied**, like `bench.log` and
  `bench.load_effects` (see `src/vcc2026/CLAUDE.md`).
- **It carries a test** when it could be wrong in silence.

## The stages that decide what gets uploaded

These are 100 (effects), 45 or 76 (cells) and 48 (package). Change them only with a
before/after comparison of their output on a pilot, as in the 24 September section of
`docs/ARCHIVIO.md`.

`env.ps1` activates the project venv in a PowerShell session, where local scripts are allowed.
