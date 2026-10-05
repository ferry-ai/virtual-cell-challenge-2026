# ARCHIVIO DATI â€” indice corrente

**Percorso principale: archivio â†’ banca pronta e campioni â†’ training esteso.**

Manifest `manifest.json`, SHA256 `f9c76e3034e0fa44bbee74af3158481e3356b8cca3566c4eca199461d42e53e2`. Selezionare account/versione/percorso/hash;
non usare un dataset precedente per somiglianza del nome o come fallback.

- [Dati disponibili, contesti e dimensioni](../DATI_DISPONIBILI_r2.md): **395,75 GB**
  di grezzi perturbazionali conservati; 17 archivi precedenti nominati e versionati.
- 15 banche della nuova ingestione verificate. Campioni CD4, KOLF e HCT116 chiusi;
  HEK293T 3/6 nell'ultimo snapshot verificato, gli altri job giÃ  lanciati.
- **Prima catena riusata verificata su dati veri:** HepG2 Nadig dall'archivio
  esistente produce banca e matrici cellulari persistenti, codice/versione/conteggi/
  lineage/ricevute verificati (`archive_completion_hepg2_r1`). Nessuna reingestione.
- Sedici nuovi job accettati sui tre Kaggle in `archive_launches_r2.jsonl` e `remaining_archives_r1/launches.jsonl`.
  I Colab non sono partiti e sono sostituiti: non avviarli nÃ© duplicare i job.
- Cinque sorgenti esplicitamente autorizzate sono pubbliche: SCP KO, SCP Tcells,
  SCP K562/HEK, Tian/Norman e HIPSCI targeted19. Prove in `public_archives_r2`.
  Gli altri archivi e i nuovi output restano privati; prima del trainer verificare
  gli accessi reali del consumatore, senza ricalcolo per aggirare una permission.

Un teammate puÃ² montare le cinque sorgenti pubbliche; per gli altri riferimenti
servono i permessi. Non trasferire credenziali. I manifest di Git sono metadati,
non copie delle matrici nÃ© accesso automatico ai dataset privati.

Le aggiunte sono incrementali: adattatore e derivati della sola nuova sorgente,
poi nuova release dell'indice. Riutilizzare i derivati se input, asse, QC, codice
e parametri coincidono; conservare le versioni precedenti.

**Il training esteso non Ã¨ ancora avviato.** Copertura del catalogo, QC/ruoli,
lettori e ricevute di consumo/loss nel trainer restano da integrare con D-053.
Il cubo `rlead-bench-cube-r2` resta un pilot, non la banca completa.

Le unità effettivamente pubblicate di ciascun dataset sono legate a `files.json`;
`complete.json` può descrivere anche unità sorelle dello stesso job che non sono
in quel dataset. La r2 del resoconto corregge questa sovrapposizione della tabella r1;
GB e righe totali erano già calcolati dai soli file effettivi e non cambiano.
