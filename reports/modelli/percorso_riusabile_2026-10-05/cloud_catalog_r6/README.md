# ARCHIVIO DATI — indice corrente r6

Percorso principale: archivio → banca/campioni persistenti → training esteso.
Manifest `manifest.json`, SHA256 `6ab797ff4813808d9971871ed15c69b7acf344ba7f0841385c37970882f0d27f`. Montare account/versioni/percorsi/hash,
mai un dataset storico per somiglianza del nome. R5 e i precedenti sono conservati.

- Grezzi perturbazionali: **395,75 GB**, invariati; [tabella fonti](../DATI_DISPONIBILI_r2.md).
- CD4, KOLF, HCT116 e HEK293T hanno campioni chiusi e unioni verificate.
  HEK293T 6/6, 27,26GB; codice/versioni/ricevute/lineage verificati, nessun nuovo download.
- Otto ulteriori job chiusi oltre a HepG2, in archive_completion_batch_r1.
- **Tian/Norman: tutte le cinque unità banca/campioni verificate**, in
  tian_resume_verified_r1. Norman e banca iPSC già riusciti sono riusati;
  i riferimenti ai diversi produttori restano espliciti. Le statistiche iPSC
  rimangono nel produttore ERROR recuperabile via API: ancora da rendere
  montabili al trainer, senza ripetere il calcolo. Locatori gzip originali
  preservati tramite alias binario nel dataset privato di input versione 2.
- HIPSCI genome-wide: due grezzi ora pubblici senza modifica dei file,
  assegnazioni CPU distribuite sui tre account. [Ledger e prossimi comandi](../PARALLELISMO_r3.md).
  Tre parti già verificate, unioni 12/12 per unità ancora aperte. Gli snapshot
  dei ledger sono congelati qui; i journal operativi possono crescere.
- Sette input grezzi pubblici verificati; gli altri dati e nuovi output
  ancora privati. L'utente autorizza la pubblicazione necessaria a togliere
  limiti di accesso della pipeline; evitare trasferimenti o ricalcolo inutili.

**Training esteso ancora non avviato.** Integrare reader delle parti e ancore,
hash nel runtime, split D-053, QC/ruoli e uso effettivo dei dati/loss anche dopo
resume; completare le altre voci del catalogo. Nessuna promozione dalla loss
dei 18 fit preliminari. Questo indice certifica gli artefatti indicati, non
copertura completa o consumo effettivo da parte del trainer.
