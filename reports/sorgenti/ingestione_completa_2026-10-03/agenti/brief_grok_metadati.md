# Brief per Grok: metadati di tre sorgenti GEO (sola lettura e ricerca web)

Da: regia dell'ingestione completa del progetto VCC 2026 (Claude Code, sessione `22d21f`), 3/10/2026. Lanciato con
l'autorizzazione del proprietario. È un compito di **sola ricerca**: niente file modificati, niente download di dati.

## Domanda

Per ognuna di queste tre serie GEO, che cosa si può scaricare a livello di **singola cellula** e quanto pesa?
- **GSE335887**: schermo di perturbazione in microglia;
- **GSE291147**: PerturbFate;
- **GSE337988**: DLD-1, perturbazioni CRISPR.

## Che cosa riportare, con le fonti

Per ogni serie:
- **i file supplementari:** nome, dimensione in byte o come la dichiara GEO, formato (h5ad, h5, mtx, rds, csv,
  tar) e link diretto;
- **i conteggi per cellula:** se esistono, o solo matrici aggregate o DE;
- **la biologia:** modalità della perturbazione (CRISPRi, CRISPRa o KO), tipo o linea cellulare, numero di cellule,
  di bersagli e di controlli non-targeting, se dichiarati;
- **l'assegnazione delle guide:** se c'è e in quale file;
- **il dosaggio della chimica:** 10x 3', 5' o Flex, se dichiarato;
- **pubblicazione e licenza:** articolo o preprint collegato, licenza o termini;
- **le incertezze:** campi che non hai potuto verificare.

Cita l'URL di ogni dato: pagina GEO, FTP, articolo. Non inventare dimensioni o conteggi; se un valore manca,
scrivi «non trovato».

## Formato

Una sezione per serie, con una tabella dei file, poi una sintesi di 5 righe: quale serie vale la pena acquisire per
intero per un corpus di training su singole cellule, e con quale costo in GB.
