# HIPSCI mirato: riusare i conteggi prima dello pseudocount

6 ottobre 2026. **Verificato su evidenza locale:** la ricevuta della banca
[HIPSCI mirato](archive_completion_hipsci_targeted19_r1/bank_receipts/davideferante/vcc-derivatives-hipsci-targeted19-r1/bank/hipsci_targeted_19/complete.json)
conserva `count_sum.npz` (213.024.236 byte, SHA256
`d5110b8133191e7a8f96377e06a22543dd131537c11b6c8195b684e2202c2285`),
`rows.csv` e `mask.npz`. Il codice archiviato
[bank.py](fallback_hipsci_r1/bank.py) somma i conteggi osservati e salva count_sum
prima di calcolare le proporzioni; non applica uno pseudocount a quei conteggi.

**Conseguenza tecnica:** il vecchio cache HIPSCI pseudo2 non va riusato nel
confronto pseudo0,5, ma non occorre rifare ingestion delle 59 shard per questo
motivo. L'adapter può partire dai count_sum persistenti e applicare la ricetta
originale, conservando BIO, donatori, controlli e maschere.

**Ancora da eseguire:** montare il producer già chiuso nel consumer, verificare
hash dei tre file e binding dell'asse, risolvere identità/componenti e ammissione
QC/controlli, confrontare l'adapter a parità di input con il metodo originale.
Non collassare i 20 BIO a una sola identità e non mediare effetti già shrunk.
L'accessibilità e il consumo del nuovo adapter non sono dimostrati da questa
lettura locale. Nessun job, trasferimento o nuovo invio è stato avviato.

Stato operativo in [R-LEAD](../../../docs/piani/strategia-scientifica.md).
