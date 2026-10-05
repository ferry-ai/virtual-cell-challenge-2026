# Condivisione e redistribuzione dopo autorizzazione del proprietario

Il proprietario osserva una sola sessione su davideferrante11 e autorizza:
«pubblica tutto se ti limita». Confermato: K562 GWPS unico RUNNING su
quell'account al controllo; 50/50 riguarda k562_gwps_a, prima delle due unità.
Il job continua salvataggio statistiche/campioni; non è ancora una chiusura.
Prova: k562_phase_r1/progress.json. Gli altri derivati di quell'account erano chiusi.

I due archivi davidmaisterx/rlab-hipsci-gwfit e rlab-hipsci-gwnonfit sono ora
pubblici, verificati in public_hipsci_r1/publication.jsonl, senza upload,
nuove versioni dei grezzi o modifiche dei file. Questa condivisione rimuove
l'ostacolo degli input privati sugli altri due account. L'autorizzazione riguarda
la pubblicazione necessaria a questa pipeline; non è una richiesta di pubblicare
modelli o altri lavori estranei. Gli output finora restano privati.

dispatch_hipsci_shared_v1.py --snapshot <nuovo_nome> sostituisce il dispatcher
del solo proprietario. Ledger globale delle parti: hipsci_partition_r1/launches.jsonl
più hipsci_shared_r1/launches.jsonl. Mai usare ancora launch_archive_partitions_v1:
non conosce il secondo ledger e potrebbe duplicare parti su account diversi.
Chiave univoca: unità + indice di parte; lo slug può appartenere a un altro account.
Validatori: archive_partition_state_v2.py --out <nuovo_snapshot> [--previous ...].

Dieci nuovi push accettati: quattro su davideferrante11, tre su davideferante,
tre su davidmaisterx. Preflight: 1, 2 e 2 job attivi rispettivamente; dopo i push
sono stati assegnati tutti i 15 slot CPU previsti, entro ammissione del provider.
Tredici delle 24 parti HIPSCI lanciate (tre nella prima ondata), undici pianificate
in attesa di slot. Verificare l'esecuzione effettiva in hipsci_shared_r1/progress_r1.json
e le chiusure in hipsci_verified_r1: un push non dimostra RUNNING né output corretto.

## Recupero iPSC senza rifare banca

Il secondo tentativo iPSC r3 si ferma perché Kaggle espande samples.jsonl.gz
nel mount: il file gzip atteso dal contratto non è presente. Il dataset privato
vcc-tian-ipsc-sample-input-r1 è ora versione 2, conservando anche l'alias
samples.jsonl.gz.bin con gli stessi byte SHA256 originali; versione 1 mantenuta.
Nessun nuovo download, ricampionamento, ingestion o calcolo della banca.
Il job r4 copia nel proprio workspace i soli file necessari (circa 35 MB),
ripristina il nome atteso, verifica gli stessi hash e materializza i campioni.
Ricevute: tian_rehouse_version2_r1.json e tian_ipsc_r4/launches.jsonl.
Seguire r4 per iPSC, r3 per le altre tre unità, Norman già chiuso nel produttore.
Non rilanciare gli iPSC r2/r3 falliti. tian_resume_state_v1.py --out <nuovo_snapshot>
[--previous ...] verifica questi produttori distinti, banca riusata inclusa.

Il trainer esteso resta aperto: tutte le nuove chiusure vanno rese accessibili
al consumatore, integrate nei reader con ancore fra parti, split D-053,
hash completi e ricevute di contesti/target/strati/loss anche dopo resume.
