# ARCHIVIO DATI — indice corrente r10

Manifest immutabile `manifest.json`, SHA256 `7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf`; r9 e precedenti conservati.
Account, versioni, hash e lineage identificano gli input. Nessun fallback storico.
Questo è un indice di storage, non una release ammessa al fit.

- HIPSCI mirato19: banca e campioni chiusi e verificati, 20 contesti BIO.
  Campioni: 497.355 / 520.464 / 622.353 cellule ai livelli 32 / 64 / 128.
  Ricevute, codice e versione in archive_completion_hipsci_targeted19_r1/state.json.
- HIPSCI genome-wide: entrambe le unioni verificate, 24/24 parti.
- Norman banca/campioni pubblici v1; iPSC statistiche pubbliche v3, byte originali.
  [Dettagli di accesso e riuso](../cloud_catalog_r9/README.md).
- K562 GWPS resta RUNNING nell'ultimo snapshot remaining_open_progress_r7.json.
  Il 50/50 è il primo blocco prima di salvataggio e campionamento, non la chiusura.
- Copertura dell'intero catalogo, ammissione QC/split, assi e hash nel runtime,
  consumo effettivo nel trainer ancora aperti. Grok stessa sessione r2, nessun fit esteso.
- [Grezzi e GB](../DATI_DISPONIBILI_r2.md): 395,75 GB, HIPSCI già inclusa.

Riutilizzare i derivati se input/asse/QC/codice/parametri coincidono; un nuovo
dataset aggiunge solo i suoi derivati e una nuova release globale.
