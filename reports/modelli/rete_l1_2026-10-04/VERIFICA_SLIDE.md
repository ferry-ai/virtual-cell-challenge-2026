# Controllo dello spostamento dei conteggi (4/10 sera, prima della generazione)

Sei blocchi campione (due per contesto) generati come lo stadio 45, con un generatore casuale indipendente.
Wilcoxon contro 4.000 controlli, BH a 0,05. Uscite in [esito/](esito/).

| Versione | Totali per gene | Elementi salvati | Variazione massima di profondità | Obiettivo raggiunto | Jaccard delle chiamate DE prima/dopo |
|---|---|---|---|---|---|
| Senza tetto | identici | identici | **fino a +163%** | 87–97% | 0,64–0,68 |
| Tetto ±2% per cellula (`DEPTH_CAP`) | identici | identici | 2% | 73–94% | **0,64–0,67** |

- **Misurato:** il bulk resta identico, ma lo spostamento **non è neutro sui ranghi**. Circa un terzo delle chiamate DE
  cambia anche con il tetto. I membri Jaccard, reach e fedeltà non resteranno quelli del t34: la previsione
  registrata (±0,01 ciascuno) è a rischio.
- **Decisione del proprietario in chat:** «manda la rete sulla vcc senza pregrading». Si genera con il tetto ±2% e si
  invia nel primo slot libero (5/10, 00:00 UTC).
