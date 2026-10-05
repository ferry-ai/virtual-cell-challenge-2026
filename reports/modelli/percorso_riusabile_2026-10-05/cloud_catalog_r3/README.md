# ARCHIVIO DATI — indice corrente

**Percorso principale: archivio → banca pronta e campioni → training esteso.**

Manifest `manifest.json`, SHA256 `111c0ab81dd9802b7da8d8dc7d7b76d2df9b580d05d58c4b5455eb38743fb193`. Selezionare account/versione/percorso/hash;
non usare un dataset precedente per somiglianza del nome o come fallback.

- [Dati disponibili, contesti e dimensioni](../DATI_DISPONIBILI_r1.md): **395,75 GB**
  di grezzi perturbazionali conservati; 17 archivi precedenti nominati e versionati.
- 15 banche della nuova ingestione verificate. Campioni CD4, KOLF e HCT116 chiusi;
  HEK293T 3/6 nell'ultimo snapshot verificato, gli altri job già lanciati.
- **Prima catena riusata verificata su dati veri:** HepG2 Nadig dall'archivio
  esistente produce banca e matrici cellulari persistenti, codice/versione/conteggi/
  lineage/ricevute verificati (`archive_completion_hepg2_r1`). Nessuna reingestione.
- Dodici nuovi job accettati sui tre Kaggle in `archive_launches_r2.jsonl`.
  I Colab non sono partiti e sono sostituiti: non avviarli né duplicare i job.
- Cinque sorgenti esplicitamente autorizzate sono pubbliche: SCP KO, SCP Tcells,
  SCP K562/HEK, Tian/Norman e HIPSCI targeted19. Prove in `public_archives_r2`.
  Gli altri archivi e i nuovi output restano privati; prima del trainer verificare
  gli accessi reali del consumatore, senza ricalcolo per aggirare una permission.

Un teammate può montare le cinque sorgenti pubbliche; per gli altri riferimenti
servono i permessi. Non trasferire credenziali. I manifest di Git sono metadati,
non copie delle matrici né accesso automatico ai dataset privati.

Le aggiunte sono incrementali: adattatore e derivati della sola nuova sorgente,
poi nuova release dell'indice. Riutilizzare i derivati se input, asse, QC, codice
e parametri coincidono; conservare le versioni precedenti.

**Il training esteso non è ancora avviato.** Copertura del catalogo, QC/ruoli,
lettori e ricevute di consumo/loss nel trainer restano da integrare con D-053.
Il cubo `rlead-bench-cube-r2` resta un pilot, non la banca completa.
