# Instructions for Codex

The working agreement for every agent in this repository is `CLAUDE.md`. It applies
to Codex in full: read it before anything else. The project map is
`docs/PROGETTO.md`.

The daily chain (plan → review → implementation) is described in
`docs/CICLO_GIORNALIERO.md`. Codex runs stage 2 through the skill `$revisione-piano`
in `.agents/skills/`, started by `scripts/32_daily_cycle.py`. In that stage Codex
writes only inside the day's folder under `reports/ciclo_giornaliero/`.
