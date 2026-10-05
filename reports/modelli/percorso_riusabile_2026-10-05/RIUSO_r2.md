# Prossimo training: riuso con identità congelate

Aggiornamento del 5 ottobre: [r1 conservata](RIUSO_r1.md), sostituita per il riferimento
al ledger vivo. Stato, assegnazioni e autorizzazioni solo in
[R-LEAD](../../../docs/piani/strategia-scientifica.md).

1. Selezionare [storage r10](cloud_catalog_r10/manifest.json), SHA256
   `7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf`, e
   [expected r2](../../analisi/riconciliazione_banca_2026-10-05/frozen/expected_r2.json), SHA256
   `54e9d5107282f2aeaab8ca7d78dca5d24c6333837453c0af7234eed5fd3c128e`.
   Storage, copertura attesa e corpus realmente consumato sono tre oggetti distinti.
2. Riusare banche/statistiche/campioni se input, asse, QC, codice e parametri coincidono.
   Scegliere per versione/hash/provenienza, mai per titolo o anzianità. Copia locale
   facoltativa; montare direttamente output cloud accessibili. Un file di locatori
   non sostituisce una matrice cellulare. Nessun fallback al pilot aggregato.
3. Congelare una nuova release ammessa: tutti gli input attesi, usati e bloccati con
   motivi, ruoli e split. Copiare i ledger prima di fissarne lo SHA. Risolvere gli alias
   `supersedes_failed`; originale e retry non sono due fonti. H1 train/val condividono
   il pooling prima dello shrink, CD4 condizioni condividono una voce dopo il pooling
   dei donatori. K562 GWPS ed essential restano distinti.
4. Nel runtime verificare byte, assi, maschere, controlli/ancore e checkpoint dei producer.
   Il lineare usa pseudobulk `count_sum` e statistiche; un trainer cellulare usa anche
   matrici/probabilità/lineage. Integrare il contratto di copertura nell'effettivo consumer,
   con ricevute dei contributi, non soltanto un checker locale o un manifest.
5. Prima del compute censire i tre account, slot, input e RAM/disco disponibili.
   Deduplicare fra ledger/account; nuova destinazione per nuovi derivati. Un errore
   richiede diagnosi e riuso delle parti valide, mai rilancio cieco della campagna.
6. Alla chiusura conservare codice/parametri/versioni, piccoli manifest e hash output,
   contesti/target realmente contribuenti. Nei neurali anche esposizione/resume/loss;
   il lineare non ha loss/optimizer. D-053 non si chiude dalla presenza di file.

Un nuovo dataset richiede soltanto il proprio adapter e i derivati mancanti, più una
nuova release globale. Nuove normalizzazioni/QC/ancore/split rigenerano solo i derivati
dipendenti. Cambiare privacy o account non richiede ricalcolo: verificare accesso e byte.
I dispatcher e PID delle campagne passate sono prove, non la coda del prossimo training.

[Verifiche e limiti](../../analisi/riconciliazione_banca_2026-10-05/README.md): dati
archiviati non equivalgono a uso integrale; nessuna esclusione per dimensione/comodità/overlap.
Il cache K562 storico è riusabile con SHA esplicito, senza sostituire la nuova banca
single-cell e senza dichiararlo già consumato in un mix che non lo montava.
