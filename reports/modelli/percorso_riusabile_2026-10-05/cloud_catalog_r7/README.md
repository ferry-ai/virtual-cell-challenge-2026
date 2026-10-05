# ARCHIVIO DATI — indice corrente r7

Manifest immutabile `manifest.json`, SHA256 `0c786da9155360e2cbe01604dba37ab5141e71022880be1ab20a4e4fb2f03678`. R6 e versioni precedenti conservati.
Account, versioni, percorsi e hash identificano i dati: mai scegliere per somiglianza del nome.

- Grezzi **395,75 GB, HIPSCI già inclusa**; [fonti e GB](../DATI_DISPONIBILI_r2.md).
  Con banca e campioni l'archivio complessivo supera 400 GB; questo non è il volume letto per ogni fit.
- Nuova chiusura A549, banca e campioni verificati: `archive_completion_a549_r1`.
- HIPSCI: tutte **24/24 parti avviate**, **14/24 verificate** (7 per unità);
  unioni ancora aperte. `hipsci_verified_r2/state.json`; entrambi i ledger congelati qui.
- iPSC: statistiche originali rese montabili nel dataset privato
  `davideferante/vcc-tian-ipsc-sample-input-r1`, **versione 3 ready**.
  Riparazione dell'accesso al produttore ERROR; 485,43 MB mancanti trasferiti una volta,
  hash originali verificati, locatori già presenti riusati, nessun ricalcolo.
  Verifica hash nel runtime del trainer e accesso fra account ancora necessari.
- [Collegamento al training e confronto transfer](../TRAINER_r1.md).
  Il nuovo loop esegue ottimizzazione reale sulle fixture, con controlli fra parti e
  ricevute di consumo/resume. Questo NON prova un training esteso su dati reali:
  catalogo/QC, feature di transfer congelate, accessi e launcher restano da completare.
