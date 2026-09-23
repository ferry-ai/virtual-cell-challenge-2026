# Regola del t14 (ControlModel, ampiezza scelta per le chiamate), scritta prima dei piloti — 23 settembre 2026

Scritta intorno alle 03:45 locali del 23 settembre, dopo che il t13 si era fermato per la sua
regola (`RISULTATO_NULLO.md`) e prima di qualunque pilota `ControlModel` di questa serie.
Gira su Colab, job 045 in coda dietro al t09 (job 044).

## Regola

1. **Generatore:** `ControlModel`, stadio 76, parametri predefiniti (stato `kde`, `knn` 30,
   `n_draw` 4000, seme 2026) e `--keep-effects-target`. Nessun termine cis o di trasferimento
   oltre al file degli effetti.
2. **Effetti:** il file del migliore fra t08 e t11 per punteggio ufficiale, t08 a parità
   entro 0,005. Il job parte con quello del t08; se il t11 lo batte prima che il job giri, il
   percorso si cambia nel job prima dell'avvio.
3. **Controllo nullo:** `--a-effects 0`, 20 bersagli per contesto, stadio 83 con 9.200
   controlli. Se la mediana di n_pred supera 10 in un contesto, il job si ferma senza
   generare.
4. **Ampiezza:** `--a-effects` in {1, 2,5, 5, 10}, stessi 20 bersagli e stesso seme. Si
   sceglie il più piccolo che dà n_pred mediano ≥ 60 in A, B e C; se nessuno ci arriva, 10.
5. Poi generazione completa a quel valore, impacchettamento con lo stadio 48 e copia su
   Drive. La scelta e i conteggi si scrivono in `choice.json` accanto al `.vcc`.

## Differenza dal t09

Il t09 è il caso `--a-effects 1`: stessi effetti del t08, nessuna scelta di ampiezza. Il t14
coincide con il t09 se la regola sceglie 1.
