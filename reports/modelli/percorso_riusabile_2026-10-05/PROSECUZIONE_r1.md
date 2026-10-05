# Chiusure e recuperi del 5 ottobre, supervisione

Misurato: HEK293T ha tutte le sei parti e unione verificata in snapshot_parts_r5,
27.256.435.767 byte, 2.329.024 cellule nel livello 128. CD4, KOLF e HCT116 restano
chiusi; non recuperare di nuovo i manifest immutati né le matrici.
archive_completion_batch_r1 verifica otto nuovi job, oltre a HepG2 già chiuso:
Jurkat, H1 train/val, RPE1, K562 essenziale, SCP Tcells, SCP K562/HEK,
KOLF piccoli/forte. Codici/versioni/ricevute/file presenti e conteggi verificati;
hash completi delle matrici da controllare nel runtime consumatore.
Indice corrente cloud_catalog_r5, precedente r4 conservato. Training esteso non avviato.

## HIPSCI genome-wide

Entrambi i job r1 falliscono per capienza output; log conservati in hipsci_failure_r1
e hipsci_nonfit_failure_r1. Nessun rilancio identico. archive_partition_v1 copia
il banco congelato e distribuisce le chiavi ordinate BIO/target intere su 12 parti:
assi/maschere fissati sull'intero input prima di dividere, stessi momenti e
campionamenti stratificati globali per gruppo, controlli presenti una volta.
test_archive_partition_v1 verifica uguaglianza numerica, maschere, selezioni,
probabilità e conservazione di righe/cellule, incluso zero depth (fixture passata).
La capienza è limitata anche nell'ipotesi pessimista di una riga per cellula.

hipsci_partition_r1/launches.jsonl: tre nuove parti accettate e RUNNING con avanzamento;
21 parti pianificate non ancora lanciate, slot liberi solo sul proprietario con accesso.
launch_archive_partitions_v1.py --snapshot <nuovo_nome> riprende soltanto parti non
lanciate; archive_partition_state_v1.py --out <nuovo_snapshot> [--previous ...]
certifica le chiusure e l'unione solo dopo tutte le parti. Il consumer deve risolvere
le ancore fra parti e verificare gli hash, senza duplicare NTC né trattare una parte
come corpus completo. La maggiore scansione I/O rende obsoleta una ETA certa di 1–3h.

## Tian/Norman

tian_failure_r1 conserva il nuovo errore di copertura campioni: alcune righe di
banca hanno n=0 dopo l'asse misurato. Queste righe restano in banca e nel conteggio
degli esclusi a profondità zero, ma non hanno campioni cellulari. Il controllo ora
richiede tutti e soli i gruppi con n>0 e mantiene il conteggio totale dei campioni.
Non è una decisione sull'ammissibilità QC dei droplet o sugli UNASSIGNED.

tian_partial_r1 verifica Norman completo e banca iPSC salvati nel produttore ERROR.
Kaggle rifiuta quel notebook come kernel_source: il primo resume r2 ha quindi
fallito; ricevuta conservata in tian_resume_r1, conclusione ERROR verificata.
La banca iPSC non si ricalcola: soltanto rows.csv, mask.npz e samples.jsonl.gz
(35.028.187 byte) più complete.json sono recuperati una volta, hash verificati,
e salvati nel dataset privato davideferante/vcc-tian-ipsc-sample-input-r1, pronto.
Prove tian_rehouse_r1.json e metadata tian_rehouse_verified_r1. Non è una copia
della banca completa: le statistiche di popolazione restano nel produttore salvato,
da rendere accessibili al trainer quando necessario. Tentativi SDK prima della
pubblicazione non hanno caricato dati; il recupero riuscito riusa i file già scaricati.

launch_tian_resume_v2.py --snapshot <nuovo_nome> usa tian_resume_r2/launches.jsonl:
salta Norman, riusa iPSC per i soli campioni, prepara le altre unità separate dal
medesimo archivio. Verificare stato/avanzamento e chiusure, distinguendo i riferimenti
bank del produttore originale dai nuovi samples. Nessun fallback al pilot aggregato.

## Passo principale successivo

Integrare sample_reader, population_reader, release_lock e training_contract nel
trainer reale: parti e ancore, assi/maschere, hash sul consumatore, split D-053,
QC/ruoli espliciti e ricevute di uso/loss anche dopo resume. Conciliare le ulteriori
voci del catalogo senza esclusioni per comodità. Le chiusure dei derivati non
certificano né questo collegamento né un miglioramento del modello.
