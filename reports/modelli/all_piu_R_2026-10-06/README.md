# t36: il transfer `all` più la correzione appresa R di Davide

6 ottobre 2026, sera. Claude Code per Alfredo, che ha chiesto in chat di portare avanti oggi, con i due slot, il
lavoro suo e di Davide.

**Previsione e regola:** [prediction_t36_2026-10-06/prediction.json](../../invii/prediction_t36_2026-10-06/prediction.json).
Sono state registrate prima dei file della correzione, della generazione del candidato e di qualsiasi punteggio.

## Perché questa combinazione

Nel banco v2 di Davide (scorer vero, emissione del t28, cinque linee tenute fuori; su `main`,
`reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04`):
- **la base `all`** (tutte le tabelle del cubo) batte `prod` (≈ t28) su 5 linee su 5, da +0,04 a +0,11 di media
  scalata locale, col PDS mai peggiore;
- **la correzione R della rete CellNet**, sopra `all`, aggiunge da +0,003 a +0,019, positiva su 5/5.

Il t30 aveva messo R sopra `prod` e sul sito ha perso −0,005. Nel banco, R funziona solo sulla base con cui è stata
appresa (ESITO_BANCO_V2, «Interpretazione»).

## Come si costruisce

1. **La base:** `vcc2026-data/processed/effects_all_2026-10-05`, prodotta da
   [esporta_all.py](../guadagno_appreso_2026-10-05/esporta_all.py): 10 gruppi, ampiezza 1,576, 300/300 bersagli.
2. **R e w:** sono quelli che Davide ha già calcolato per il t30 con `export_abc.py`, sui controlli ufficiali di A/B/C
   (`export_abc_r2`: `correction_<ctx>.npz` e `targets_<ctx>.csv`). R non dipende dalla base: dipende dalla rete del
   fold HepG2, dagli ancoraggi `all` e dai controlli.
3. **La combinazione:** [combina_R.py](combina_R.py) fa base + w·R sulle coppie osservate della base, altrove lascia
   tutto invariato. Con w = 0 deve restituire la base identica (controllo di parità).
4. **La generazione:** stadio 45 con l'emissione del t28 (`--effects-scale 1.5 --gene-dispersion`, seme 20260912),
   poi stadio 48.

## Stato

- **Base senza R** (servirà per il t37 se il secondo slot è libero): generazione `allt28gen_r2` avviata alle 21:45.
  Il primo tentativo (`allt28gen`) si è interrotto col riavvio della sessione, a 1,58 GB, ed è conservato com'è.
- **Correzione R:** in attesa dei file di Davide.
