# Ambiente isolato r2 verificato

**Misurato, 29 settembre 2026.** I piccoli esiti primari su
`G:/Il mio Drive/vcc2026/runs/lead_candidate_environment_2026-09-29_r2/`
confermano il completamento del bootstrap r2: `returncode.txt` contiene `0`;
`verify.log` registra versioni scientifiche uguali, import e piccolo roundtrip HDF5
riusciti, `vcc-cli==0.2.0` dentro la venv isolata. Non è una verifica dello score.

`ready.json` registra la verifica alle 19:00:05 UTC, base invariata e Python comune
per entrambi gli stadi:
`/content/lead_candidate_environment_r2/venv/bin/python`.
SHA256 di `ready.json`:
`acc857408620803355049d52d59bf5ccc7a3a4ff54197ca40286aec93dfed91a`.
Il codice coincide con l'archivio r3
`f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860`.

Questa evidenza completa la preparazione descritta in `AMBIENTE_ISOLATO.md` e
l'emendamento `EMENDAMENTO_BOOTSTRAP_02.md`; il tentativo r1 fallito durante
ensurepip resta conservato. Il bootstrap r2 stesso non ha avviato generazione.
La sessione principale ha successivamente riferito l'accodamento separato del
job 070 per t28; la sua esecuzione e il suo esito sono gestiti dalla lead.
