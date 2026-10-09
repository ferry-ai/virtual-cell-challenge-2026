# Input neurali: ancore verificate, estrazioni NTC avviate

Tipo: implementato e misurato tecnicamente; non è una valutazione biologica.
Le date delle osservazioni sono nelle ricevute collegate. Il nuovo consenso del
proprietario consente attività richieste dalle altre chat Codex; la richiesta del
Lead è registrata in [autorizzazione](neural_inputs_launch_authorization_r1.json).
Nessun servizio a pagamento, pubblicazione, training GPU o push Git.

## Ancore numeriche consegnate

[ammi_anchors_verified_r1.json](ammi_anchors_verified_r1.json) verifica tutti i 19
file del job privato `davideferrante11/dt-ammi-anchors-01a11c34-r4`: 17 richieste
AMMI e due confronti di parità T0. Ogni hash è stato ricalcolato sui file recuperati
in `C:/Users/ferra/vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/ammi_anchors_recovered_r1`.
Sono verificati assi/header, ricette, sorgenti effettivamente consumate, esclusioni,
codice remoto e versione. La parità dei due T0 è esatta. Non è stato eseguito un fit AMMI.
Il manifest riporta i pin di effetti, maschere incorporate e ricevute per ciascuna ancora.
La disponibilità locale non prova l'accesso dal runtime privato `davidmaisterx`.

## NTC: esecuzioni e contratto di consumo

[neural_inputs_status_r4.json](neural_inputs_status_r4.json) osserva RUNNING per:

- `davidmaisterx/dt-ntc-inputs-01a11c34-r4`: 18 parti;
- `davideferrante11/dt-ntc-inputs-01a11c34-r5`: 12 parti.

Le 30 parti coprono 47 contesti previsti. I completamenti numerici sono ancora da
verificare: RUNNING non prova avanzamento per contesto, integrità degli output o uso
nel training. [ammi_ntc_runtime_contract_r1.json](ammi_ntc_runtime_contract_r1.json)
fornisce `ntc_expected_parts`, con ogni part_id e plan SHA, i percorsi remoti attesi
e la mappa contesto/lignaggio. Il loader deve richiedere tutte le parti, anche quando
una parte mancante non cambia l'insieme dei context_id.

64 NTC per strato, priorità hash congelata, ricomposizione globale fra parti di
storage; identità di donatore, condizione, libreria e guida conservate. H1 val
non duplica i controlli train; H1 test resta chiuso. Il denominatore è
`obs/depth_native`, mai la somma sull'asse allineato. Lo zero misurato è distinto
dal gene non misurato. Mean usa gli stessi vettori per cellula del braccio cells.
Nessun RNA è stato scaricato sul portatile da questa ripresa.

Il preflight ha verificato 59 mount e gli ultimi 20 job per account. Colab ha ancora
heartbeat del 3 ottobre; quota residua non esposta dall'API. CPU/RAM/disco si verificano
all'inizio del calcolo remoto. Il tentativo df11 r4 ha avuto TLS EOF durante SaveKernel;
due letture dell'account proprietario hanno confermato `Not found` prima del recupero r5.
Lock e ricevute sono in `neural_launches/`: nessun duplicato intenzionale.

## Routing della guardia interna

[C-K562](ammi_inner_truth_C-K562_r1.json) e
[C-iPSC](ammi_inner_truth_C-iPSC_r1.json) forniscono i pin originali di raw/shrunk/SE,
le sorgenti e il ruolo proposto di tutti i contesti interni. L'asse esterno è
`raw/controls/gene_names.csv`, SHA256
`25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201`.
I cache legacy non vengono rifittati o riscritti solo per aggiungere l'asse.

Il routing resta **pending VALIDAZIONE**: CD4 usa verità aggregate sui donatori,
mentre K562 primaria è una tabella BULK storica, non campioni abbinati agli NTC
single-cell GWPS/essential. Essential non ha bersagli del pannello nella vista.
Non contare il riuso della stessa verità come repliche indipendenti, non cancellare
contesti e non scegliere un pooling dopo i risultati. Ogni context_id conserva
il proprio output; l'eventuale statistica primaria va fissata prima del fit.

Restano necessari: completamenti NTC verificati, accesso privato ai derivati df11
dal runtime di MODELLI, revisione indipendente del routing e preflight del trainer.
D-053 resta aperto; i contesti senza target di pannello non contano come loss.

## T3 conservato, senza riaprire la consegna

[t3_preserved_handoff_r1.json](t3_preserved_handoff_r1.json) documenta il refit T3/t38
già completo e distinto da t36, inclusi percorso locale e pin degli effetti e della
maschera `observed`. Il file NPZ esistente di VALIDAZIONE è stato rihashato, senza modificarlo.
SHA effetti `b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6`.

L'inventario remoto del job `davideferrante11/dt-t3-generate-01a11c34-r5`, in ERROR,
contiene `recovery_prediction.h5ad`. Le ricevute indicano 360.000 cellule e
2.086.912.955 valori memorizzati. Il digest del vecchio manifest è campionato
head+tail, non un hash completo del file recuperabile. Non è stato scaricato o
rihashato il file cellulare. Mancano verifica integrale nel cloud, confezionamento,
validazione del contenitore e confronto bit per bit prima di qualsiasi consegna.
Nessuna rigenerazione, confezionamento o upload è stato avviato nella ripresa.
T3 resta candidato non validato C/J e non prova copertura totale D-053.

## Verifiche

- [ntc_cells_tests_r5.txt](ntc_cells_tests_r5.txt): nove test PASS, incluso avvio
  completo da cartelle mancanti e asse condiviso, perturbazioni avversarie e maschere.
- [neural_inputs_packages_verified_r2.json](neural_inputs_packages_verified_r2.json)
  e [r3](neural_inputs_packages_verified_r3.json): payload, assi, cutout e ricette verificati.
- Sei ricevute `esm2_*_consumption_verified_r1.json`: verifica indipendente del consumo
  delle viste congelate; nessun beneficio predittivo dedotto da questo audit.
- La precedente suite generale `repo_tests_r15.txt` ha tre errori ambientali
  `cell_eval2.config`; non viene dichiarata tutta superata.
