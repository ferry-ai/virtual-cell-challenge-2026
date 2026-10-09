# Chiusura ESM2 e preparazione finale AMMI

9 ottobre 2026, snapshot successivo al consenso umano sui trasferimenti AMMI.
Responsabile MODELLI-ESTERNI. Nessuna modifica a file di altri responsabili,
nessun push o invio VCC. Leggere questa nota insieme alle evidenze, non come
prova autonoma di risultati.

## ESM2 concluso per questa versione

Leggere `RISULTATI_CHIUSURA_ESM2_r1.md` e `esm2_closure_verified_r1.json`:
sei fit recuperati, banco C/J completato, codice remoto e input verificati.
Fallback−T0 disc95 non risolto su entrambi i fold; il segnale iPSC della vistaT
non resta convincente in J quando è escluso anche il lignaggio. Non adottare
questa versione come miglioramento dimostrato. Non parte un'altra griglia.

`esm2_production_delivery_r1.json` consegna checkpoint, export di produzione e
contratto di inferenza. Controllo su8bersagli×8geni con scarto massimo0 e
maschere identiche. Tutti gli array stanno fuoriGit. Il caricamento privato
di126MB, inizialmente fermato dal controllo automatico, è stato autorizzato
espressamente dal proprietario, eseguito e consumato dal banco.

## AMMI implementato, training biologico non ancora avviato

Quattro fit iniziali: C-K562/C-iPSC × cells/none, seme17; swapped è inferenza.
`CONTRATTO_CHIUSURA_AMMI_r4.md` conserva le scelte anteriori ai risultati.
`ammi_code_package_r5/manifest.json` fissa il codice corrente.

Percorso eseguibile:

1. `build_ammi_runtime_v4.py`: verifica metadata di tutte le parti, ancore,
   viste, routing e codice; produce un template fuoriGit solo quando completo.
2. `package_ammi_cloud_v4.py`: incorpora il template e i locator già autorizzati
   in un pacchetto privato fuoriGit, con piano dei mount verificato.
3. Preflight finale di accessi/slot e `preflight_ammi_quota_v4.py`:
   verifica quota GPU residua e prenotata, account isolati, nessun acquisto.
4. `launch_ammi_cloud_v4.py`: un solo push per identità, lock e stato remoto.
5. `ammi_bootstrap_v4.py` e `run_ammi_v4.py`: hash sul runtime, CUDA reale,
   memoria/disco misurati, mergeNTC fissato, risposte lette un file alla volta,
   due epoche, checkpoint prima delle guardie e export nativo conservato anche
   se fallisce soltanto swapped.

Il builder è stato provato sui metadata reali: `ammi_runtime_boundary_r5.txt`
si ferma sulle esatte12partiNTCdf11 mancanti. Non è un PASS di training.
Le18partiMX sono verificate da DATI; il produttore delle12restanti
`davideferrante11/dt-ntc-inputs-01a11c34-r5` era ancoraRUNNING.
Sentinelle DATI: `df11_ntc_watch_result_r1.json` e `ntc_ready_manifest_r2.json`
nella cartella DATI-TRANSFER, da leggere quando esistono.

Il proprietario ha autorizzato105file derivati(1.639.694.217byte) più quelle
12partiNTC dopo verifica hash, verso i quattro job privati davidmaisterx.
Consenso in `autorizzazione_trasferimenti_AMMI_r1.json`; locator e pacchetti
non entrano in Git/log. DATI prepara gli accessi. Nessun RNA scaricato sul
portatile. Quota osservata `ammi_quota_preflight_r4.json`: MX~26,08h GPU,
df11~2,04h, df30h; il preflight va rifatto prima del lancio.

Produzione già specificata separatamente: ancore T0 e controlli ufficiali
verificati da DATI. Il fit richiede prima lettura cells−T0 e cells−none in
entrambi i fold, senza attribuire indipendenza ai dati poi riammessi.
Il consenso ai trasferimenti pilot non viene esteso silenziosamente ai
controlli ufficiali o alle ancore di produzione.

## Verifiche e limiti

- `combined_tests_r13.txt`:75test della componente superati.
- `resolver_tests_r1.txt`:3test aggiuntivi superati; hash errato respinto,
  mount mai eliminato, cache scaricata liberata, locator non esposto negli errori.
- `runtime_tests_r1.txt`:4test runtime inclusi nei75.
- `ammi_streaming_tests_r4.txt`:5test streaming inclusi nei75.
- `repo_tests_r9.txt`:290test,3errori preesistenti per `cell_eval2.config`
  mancante e1fallimento documentale durante una scrittura concorrente DATI;
  controllo documentale successivo `docs_check_r24.txt` PASS.

Le prime due prove streaming e la prova con poca RAM sono conservate. La
riserva di RAM della fixture è simulata soltanto nei test su pochi kilobyte;
la guardia biologica conserva la misura reale e il margine di1GiB. Le ricevute
AMMI erano state scritte per errore con nomi già usati dai test ridge:
`preserve_streaming_test_receipts_v1.py` ha conservato entrambe le serie,
ripristinando gli originali Git e dando ai nuovi log il prefisso `ammi_`.

Questi test non misurano un beneficio biologico AMMI. CoperturaD-053 non
dichiarata completa. Richiesta a VALIDAZIONE: usare le evidenze ESM2 per il
checkpoint e gli aggiornamenti condivisi; questa sessione non li modifica.
