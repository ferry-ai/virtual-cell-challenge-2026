# Ripresa del caricamento di ta 42

15 ottobre 2026. Il primo caricamento, partito alle 16:54 UTC con [submit_ta42.ps1](submit_ta42.ps1), è stato
interrotto dal riavvio del PC verso le 17:20 UTC.
- Nessuna ricevuta di fine: `submit_ta42_raw.json` e `submit_ta42_stderr.txt` sono vuoti.
- Il server teneva l'entry `wAUBxckeaH0Ab8bMXYaM` in stato `uploading`.
- Lo stato locale della CLI, `~/.config/vcc/state.json`, la elencava fra i `pending_uploads`.

**Prima di riprendere:**
- lo sha256 del `.vcc` (`cf5aa84e…`) coincide con `archive_sha256` di `ta42_packaging.json`;
- il processo che teneva il lock della CLI (pid 24804) non esisteva più.

**Ripresa,** con [resume_ta42.ps1](resume_ta42.ps1) e `vcc submit --resume wAUBxckeaH0Ab8bMXYaM`:
1. Primo tentativo (`resume_ta42_try1_*`): rifiutato dalla CLI per il lock rimasto del processo morto.
2. Il lock è stato tolto, come indica il messaggio della CLI.
3. Secondo tentativo (`resume_ta42_*`): concluso alle 17:36 UTC, md5 verificato, **stessa entry**.

Nessuna seconda entry creata, nessuna quota in più.
