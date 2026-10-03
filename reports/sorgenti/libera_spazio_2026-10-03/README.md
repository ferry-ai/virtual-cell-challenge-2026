# Liberare le copie locali già archiviate

Codex, sessione `01a10114-058a-7342-9f0e-7942cc43ad6c`, 3 ottobre 2026, portatile Windows.
Richiesta del proprietario: liberare spazio appena possibile, conservando i dati tra Drive e Kaggle.
Sottoattività disgiunta dai training R-LEAD e dall'ingestion Claude2: sole copie locali di vecchi input.

## Esito della prima rimozione

**Misurato, 3 ottobre alle 12:49 CEST:** rimossi tutti i nove percorsi selezionati, senza errori.
La [ricevuta](removal_r1.json) e il [giornale per file](removal_r1.json.jsonl) registrano
15.587.596.056 byte di copie rimosse, pari a 14,517 GiB. Lo spazio libero misurato dal processo
passa da 11.157.467.136 a 26.660.253.696 byte: guadagno netto 15.502.786.560 byte;
la differenza rispetto ai byte rimossi è compatibile con le scritture concorrenti sul disco,
non attribuite a un processo specifico. Il controllo successivo conferma l'assenza dei nove file
e la permanenza dei metadati r1. Nessun dato cloud viene rimosso.

È passata prima la [prova senza rimozione](dry_run_r1.json). Il controllo con l'hash del piano
alterato viene rifiutato prima di aprire i dati o scrivere una ricevuta.

## Prova e perimetro

**Misurato:** nove percorsi, sei file fisici, 15.587.596.056 byte (14,517 GiB):
`raw.npy`, `se.npy`, `shrunk.npy` in `processed/rete_contesti_r1/`,
`processed/rete_contesti_r2/` e nello staging `kaggle/rete_data_r1/` della radice dati.
R1 e il suo staging sono hard link: valgono una sola volta nello spazio recuperabile.
Queste reti sui contesti del 27–28 settembre non sono la rete cellulare attiva del 3 ottobre.

Ogni SHA256 locale è stato ricalcolato e coincide con la verifica indipendente svolta
sui server Kaggle, conservata in
`C:/Users/ferra/vcc2026-data/processed/archivio_cloud_2026-10-02/r1/kaggle_verify_r2/compare_full.json`.
La prova, il suo hash e i riferimenti di recupero per file sono in
[verified_candidates_r1.json](verified_candidates_r1.json).
Le matrici canoniche risultano anche su Drive, con le stesse dimensioni:
[drive_presence_r1.json](drive_presence_r1.json). Questa seconda prova dimostra presenza e
dimensione, non integrità: il connettore omette i campi checksum anche quando richiesti.
Per l'integrità si usa esclusivamente il confronto fra SHA256 Kaggle e SHA256 locale appena ricalcolato.

L'audit delle dipendenze della migrazione non trova riferimenti nel codice vivo per questi tre gruppi.
Una nuova ricerca in `configs/`, `src/`, `scripts/` e nei due report della ricerca attiva non trova
questi percorsi. Il controllo in sola lettura delle righe di comando dei processi Python attivi non
trova riferimenti ai tre gruppi; ciò non è un inventario universale dei file aperti.
I lettori delle ricerche storiche dovranno ripristinare queste matrici quando occorrono.

## Esecuzione

- [verify_local_copies.py](verify_local_copies.py): lista chiusa di nove percorsi, hash locali,
  confronto con Kaggle, conteggio degli hard link; non cancella.
- [remove_verified_copies.ps1](remove_verified_copies.ps1): prova senza rimozione per default;
  con `-Apply` rimuove soltanto i nove file nominati dopo averli aperti negando nuove scritture,
  ricontrollato tutti gli hash e validato radice, antenati e impronta del piano.
  Non opera ricorsivamente né usa wildcard. Scrive ricevuta e giornale di ogni rimozione.
- La rimozione delle sole copie archiviate libera i byte effettivi; nessun oggetto remoto viene
  modificato. Metadati, log, configurazioni, codice e risultati piccoli restano locali.

Per ripristinare una matrice canonica da Drive si usa
`reports/sorgenti/archivio_cloud_2026-10-02/riporta.py --prefix processed/rete_contesti_r1/raw.npy`
(o il percorso r2 desiderato), passando `--manifest`
`C:/Users/ferra/vcc2026-data/processed/archivio_cloud_2026-10-02/r1/manifests/a_specchio_r1.json`.
Lo script rilegge e verifica il SHA256 prima di finalizzare la copia e non sovrascrive file esistenti.
Gli alias nello staging Kaggle possono essere ricreati dalla matrice canonica, senza riscaricarla.
I riferimenti dei dataset Kaggle e i nomi dei file sono conservati nel piano verificato.

## Controlli del repository

`31_check_docs.py`: PASS, 57 checkpoint e collegamenti coerenti.
Suite completa: 287 test, 286 passati e un controllo dell'indice dei report fallito perché
la cartella nuova non era ancora nell'indice Git. Dopo aver aggiunto esplicitamente i soli
file della pulizia all'indice, rieseguita l'intera suite `test_live_tree.py`: 11/11 PASS.
`git diff --cached --check`: PASS. Nessun codice della pipeline scientifica modificato.

## Dipendenza per il resto dell'archivio

Il giro di copia r1 è finito alle 05:46 CEST: manifest di 173,141 GiB, ma nessuna ricevuta Colab
è presente nella cartella di verifica al controllo di questa sessione.
I job `130_archivio_verify_b_r1.sh` e `131_archivio_verify_a_r1.sh` sono in coda senza `.started`;
sono gli unici due `.sh` ancora non avviati nella coda principale al controllo delle 12:43 CEST.
Il proprietario è stato invitato ad avviare il dispatcher CPU, direttamente o con Claude.
Il notebook è `notebooks/colab_sc_training.ipynb`, celle 1 e 2, con autorizzazione Drive.

Le copie locali del CD4 non archiviato, gli universi degli effetti, i controlli ufficiali,
i basali attivi e le cartelle delle ricerche del 2–3 ottobre restano fuori da questa rimozione.
Nessun nuovo training, download dalla sorgente o cambiamento di split è parte di questa attività.
