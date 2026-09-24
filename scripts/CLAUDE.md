# scripts — the live stages

What each stage does, where it runs and in which order is in `docs/LAVORO.md`:
- §1 is the path of a submission;
- §4 is the table of stages;
- §7 is the final set.

`tests/test_live_tree.py` fails if §4 and this folder disagree, or if the next free number
in §4 is wrong. Add the row in the same commit as the script.

## What makes a stage

- **One number, one purpose.** A new stage takes the next free number in §4. The first line
  of its docstring says what it does, and the docstring carries a usage example.
- **It never overwrites.** It writes to a new `--out` (or `--run-id`) and refuses one that
  already holds results: a manifest or a report is evidence of what was true that day.
- **It runs through the wrappers**, which set UTF-8 and `PYTHONPATH`:
  - `.\scripts\py.cmd scripts\NN_name.py ...`;
  - `.\scripts\vcc.cmd ...` for the competition CLI.

  The scripts also put `src/` on `sys.path`, so they run without a wrapper too; a new stage
  keeps that line.
- **Data paths come from `config.paths()` or from arguments.** Stages 97 to 103 default to a
  hardcoded `C:/Users/ferra/vcc2026-data`: do not copy that into a new stage.
- **Helpers are shared through `src/vcc2026`, never copied**, like `bench.log` and
  `bench.load_effects` (see `src/vcc2026/CLAUDE.md`).
- **It carries a test** when it could be wrong in silence.

## The stages that decide what gets uploaded

These are 100 (effects), 45 or 76 (cells) and 48 (package). Change them only with a
before/after comparison of their output on a pilot, as in the 24 September section of
`docs/ARCHIVIO.md`.

`env.ps1` activates the project venv in a PowerShell session, where local scripts are allowed.
