# Adapter HIPSCI count_sum: prova piccola, non fit reale

6 ottobre 2026. [adapter.py](adapter.py) prepara blocchi per studio, contesto,
condizione, modalità e chimica, mantenendo i donatori. Chiama lo stimatore originale
`effects_from_pseudobulk` con la ricetta pseudo0,5/min_expected1, senza media post-shrink.
Include tutti i controlli dei donatori della condizione, anche senza target osservato.
Le risoluzioni biologiche sono esplicite; nessuna inferenza da separatori o overlap.
Split/hidden/componenti vengono filtrati prima delle statistiche. BIO opachi,
controlli mancanti e QC non risolto bloccano l'adapter.

**Misurato su fixture:** [ricevuta](fixture_result_r1.json), quattro test,
uguaglianza esatta raw/SE/shrunk/control_mean/n_cells con input originali equivalenti;
chimiche distinte, controlli di un terzo donatore, hidden prima dei conteggi e guardie.

**Non ancora eseguito:** consumer cloud della banca reale, verifica hash/asse,
crosswalk/QC reali, pooling e pesi fra blocchi/fonti nel mixer, contributi effettivi
e split C/J completi. La fixture non certifica ammissione scientifica né 20 contesti
consumati. Non è un nuovo training o invio. Gli input devono essere verificati nel
runtime prima di passare gli array all'adapter.

[Banca persistente da riusare](../HIPSCI_RIUSO_COUNT_SUM_r1.md).
Stato operativo in [R-LEAD](../../../../docs/piani/strategia-scientifica.md).
