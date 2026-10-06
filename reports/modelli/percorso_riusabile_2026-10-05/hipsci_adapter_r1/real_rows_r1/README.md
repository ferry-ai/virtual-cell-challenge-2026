# HIPSCI mirato: identità reali delle righe persistenti

6 ottobre 2026. **Misurato:** recuperato soltanto `rows.csv` (596.795 byte),
mai letto prima; SHA256 uguale alla ricevuta del producer già archiviata.
[Riassunto completo](summary.json), [script](../inspect_rows.py).
Nessun recupero di matrici o grezzi, nuova ingestion, fit o invio.

- 8.474 righe BIO/target, 1.161.865 cellule sperimentali.
- 19 cloni iPSC riconoscibili, condizione `day3`, ciascuno con controlli NTC:
  da 86 a 668 cellule di controllo per clone.
- Il ventesimo BIO del conteggio storage è una sola cellula `NO_METADATA`,
  con contesto/donatore/condizione mancanti e senza controllo abbinato.
  È una lacuna esplicita, non una ventesima linea utilizzabile già certificata.
- La chimica è `MISSING` anche nelle 19 linee riconoscibili. Non imputarla da
  supposizioni: verificarla a monte oppure definire un ruolo esplicito di
  chimica ignota confinato a questo studio, prima di adottare l'adapter.

**Restano aperti:** crosswalk dei target (446 token non NTC complessivi), asse,
maschere e conteggi verificati nel consumer; ammissione/QC e gestione della
cellula senza metadata. Non escludere un intero clone per l'assenza della chimica.
La fixture r1 rifiuta BIO irrisolti: al momento non va lanciata sulla banca reale
senza queste decisioni. Pooling dei 19 donatori prima dello shrink e politica
originale del voto HIPSCI nel mixer devono essere verificati, conservando il
lineage BIO; blocchi separati nella fixture non autorizzano 19 voti indipendenti.

Questa verifica qualifica il conteggio dei contesti, non un errore o perdita dei
conteggi archiviati. HIPSCI mirato non ha contribuito a t36.
