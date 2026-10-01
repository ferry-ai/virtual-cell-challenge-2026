# R3 completato durante la revisione: collasso e nuova diagnosi del gradiente

1 ottobre 2026. La chiamata di stato Kaggle avviata alle 14:38 CEST restituisce `COMPLETE`;
gli output locali, pubblicati dall'agente R-LAB durante questa revisione, permettono una
rianalisi separata. Non sostituisce la sua [lettura del protocollo](../../modelli/cellnet_completo_2026-10-01/ESITO.md).
Script `analyze_r3.py`, output e hash in [r3_followup_r1](r3_followup_r1/diagnostics.json).

## Risultato e confronto appropriato

Il job ha visto tutte le 4.382.321 cellule ammesse, per 1,857 epoche e 31.808 passi;
63,7% di attesa dati. Passano le verifiche tecniche, inclusa ripresa identica.
Coseni diagnostici del ramo `desc`, non punteggi VCC:

| Regime | Gruppi | Rete r3 | Confronto |
|---|---:|---:|---:|
| C | 400 | 0,30339 | transfer 0,40537 |
| T | 400 | 0,06874 | risposta generica 0,19745 |
| J | 206 | 0,19402 | risposta generica −0,17684 |

Su C la rete vince contro transfer nel 40% dei target, ma perde in media di 0,10198.
Su T, 119 gruppi hanno insieme likelihood migliore di unknown e coseno negativo.
J fornisce un segnale esplorativo promettente, da confrontare con modelli semplici che
abbiano gli stessi descrittori e con controlli corretti.

Rispetto a r2 restano nello stesso regime e gruppo solo **345 C, 29 T e 20 J**. Sui 20 J
comuni il coseno medio passa da −0,01683 a +0,03673, mentre la media sull'intera nuova
coorte J è +0,19402. Non sono gli stessi target: leggere 0,108 → 0,194 come progresso sullo
stesso test è scorretto. Anche il confronto sui comuni è descrittivo: cambiano corpus,
controlli, budget, epoche e parametri appresi. R3 non dimostra l'effetto causale dei dati aggiunti.

## Il collasso identity è reale e il clamp può ostacolare il recupero

L'agente R-LAB ha già rilevato il collasso della probabilità di risposta `pi`. La nostra
rianalisi trova la media `pi` sotto 10⁻⁶ in **399/400 C, 400/400 T e 206/206 J**;
il guadagno di likelihood è zero per tutti questi gruppi di valutazione. È un problema di
ottimizzazione, non evidenza che quelle cellule non rispondano biologicamente.

**Nuova prova numerica:** `train_cellnet.py:977–978` usa
`log(pi.clamp_min(1e-6))` nella miscela. Quando `pi` è già sotto il limite, il ramo perturbato
non può aumentare il gate attraverso quel termine perché il clamp ha derivata zero.
Il ramo non perturbato continua invece a favorire la sua chiusura.

Controesempio eseguito in float64 con `pi = 1e-8`, log-likelihood del componente perturbato
−1 e del basale −2, quindi la risposta è migliore:

| Formula | Derivata della loss rispetto al logit del gate | Passo di discesa |
|---|---:|---|
| Clamp attuale | +9,99997 × 10⁻⁹ | Chiude ancora il gate |
| Pesi logaritmici con `logsigmoid(z)` e `logsigmoid(-z)` | −1,71828 × 10⁻⁸ | Lo riapre |

Gli assert verificano entrambi i segni. Questo prova un difetto del recupero sotto soglia,
**non la causa iniziale del collasso di r3**. Anche la derivata corretta è piccola: usare
pesi numericamente stabili non garantisce da solo il recupero durante un training finito.

**Correzione prioritaria candidata:** calcolare la miscela direttamente dai logit con
log-sigmoid stabili e verificare i gradienti nei casi limite. Non aggiungere semplicemente
un altro clamp rigido a `pi`, che mantiene la zona senza gradiente. Confrontare poi un warm-up
del gate o un prior regolarizzante, controllando la distorsione su veri non-rispondenti;
monitorare per studio i quantili di `pi`, le responsabilità posteriori, le norme di `delta`
e i gradienti. Registrare il criterio di collasso prima del training successivo.

Il confronto descrittori contro identity collassato non identifica l'utilità biologica dei
descrittori. Restano necessari generico addestrato, bilineare a stessi input e descrittori
permutati. Nessun file di training è stato modificato da questa analisi.
