# t29 — upload in corso

**Misurato** (1/10, ora italiana):
- 15:28: parte `submit_t29.ps1` come processo Windows separato, con nome e descrizione registrati prima
  (`submission_texts.md`). La CLI legge e verifica il `.vcc` (4.206.919.680 byte, sha256 di stadio 48
  `4562a8131eecf4630651c95b458634ce35ac0feb691f1343e8a2046a034ec4c8`), poi apre l'entry **K6Q36uGCaEwQ1wRLmBLp** con
  un upload riprendibile.
- Il Wi-Fi di casa invia a 0,17-0,25 MB/s: 320 MB nei primi 31 minuti. Fine stimata verso le 22, non misurata.
- Il portatile resta sveglio fino alle 00:39 (`keep_awake_t29.ps1` e `keep_awake_t29_r2.ps1`).

**Se l'upload si interrompe:** prima si verifica lo sha256 del `.vcc` contro `t29_packaging.json`, e che il processo
`vcc` non sia più vivo (`~/.config/vcc/locks/submit-default.lock`). Poi
`vcc submit --resume K6Q36uGCaEwQ1wRLmBLp` riprende sullo stesso file (PROCEDURE §2, punto 5).
