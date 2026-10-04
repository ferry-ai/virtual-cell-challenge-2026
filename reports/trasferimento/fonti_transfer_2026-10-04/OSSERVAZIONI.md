# Osservazioni dopo il congelamento, che non cambiano la regola del protocollo

4/10/2026, 04:20 circa, sessione `2b35612c`. Scritte dopo il congelamento di `PROTOCOLLO.md` (commit `810a08d`) e prima
di qualunque uscita delle linee di confronto. Riguardano che cosa un esito positivo significherebbe per A/B/C, non la
regola.

## Copertura dei 300 bersagli del pannello di gara (misurata)

Righe utilizzabili del cubo r2 (`processed/generalizzazione_contesti_2026-10-02/cube_r2`, almeno 10 cellule, non
duplicate), per gruppo, fra le chiavi riconciliate dei 300 bersagli di `raw/controls/pert_counts.csv`:

| Gruppo | Bersagli del pannello |
|---|---:|
| CD4T | 293 |
| K562 | 281 |
| HEK293T | 281 |
| iPSC (KOLF2.1J e HipSci) | 281 |
| HCT116 | 268 |
| H1 | 17 |
| Neuron | 6 |
| HepG2, Jurkat, RPE1 | 0 |

Le somme cellulari di R-LEAD P4 (`kaggle_sums_r2`) confermano la misura: `jurkat_nadig` 0 bersagli del pannello,
`h1_vcc2025_train` 13, `h1_vcc2025_val` 4, `tian2021_crispri` 6.

## Che cosa ne segue (interpretazione)

- Per i bersagli del pannello, la regola `cells` toglierebbe CD4T, HCT116 e HEK293T, che coprono 268–293 bersagli, e
  aggiungerebbe quasi solo iPSC. La regola `all` equivale in pratica alla produzione più iPSC, più H1 e Neuron su una
  ventina di bersagli. Un vantaggio di `cells` misurato sulle righe di Jurkat (geni essenziali, nessun bersaglio del
  pannello) non si trasferirebbe al pannello.
- Il candidato per A/B/C coerente con il §4 del protocollo, se la regola passa per `transfer_all_J`, è dunque «ricetta
  t25 più le sorgenti iPSC». Lo stadio 106 lo costruisce dagli universi già presenti nella radice dati
  (`processed/universe_hipsci_*`, `--source NOME=CARTELLA`), con la parità del t25 sulle quattro sorgenti della ricetta
  come prova del percorso. Se passa solo `transfer_cells_J`, non c'è un candidato per A/B/C che ne erediti il vantaggio
  senza perdere CD4T, HCT116 e HEK293T: l'esito resterebbe un risultato del banco.
- K562 fra le linee di confronto ha righe genome-wide, simili a quelle del pannello; Jurkat no. Per la rilevanza verso
  A/B/C pesa di più K562, ma la regola resta quella congelata, su entrambe le linee.
- `sums_to_pseudobulk.py` di questa cartella converte le somme in righe per lo stadio 98 (`--extra`). Serve per le
  sorgenti senza universo; per il pannello copre una ventina di bersagli.
