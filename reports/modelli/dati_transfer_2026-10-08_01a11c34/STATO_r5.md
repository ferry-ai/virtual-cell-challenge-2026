# DATI-TRANSFER — stato r5

Fotografia dell'8 ottobre 2026, dopo le verifiche delle 20:18 UTC (22:18 a Roma).
File posseduti: questa cartella e i suoi output nella radice dati.
Questo stato aggiorna r4; le ricevute precedenti restano immutate.

**Misurato:** T2 è completato e i tre array di produzione sono stati scaricati
e verificati indipendentemente. Il job privato
`davideferrante11/dt-final-t2-01a11c34-r1` ha consumato 16 fonti in 118,72 secondi,
con parità esatta del ramo nullo rispetto a T1. Gli effetti sono 300 × 18.533,
con assi e maschera invariati rispetto a T1; A/B/C sono identici. Il contratto
contiene già ampiezza 1,576 e cis, ma non l'emettitore.

Consegna: [CONSEGNA_T2_r1.md](CONSEGNA_T2_r1.md) e
[candidate_t2_r1.json](candidate_t2_r1.json). È un candidato di effetti,
non un pacchetto cellulare pronto per VCC. Nessun miglioramento predittivo
è dichiarato; il banco resta di VALIDAZIONE e t36 resta riserva storica.

La campagna precedente resta conclusa: 41/41 unità di produzione, 41/41 T/J,
6/6 ricomposizioni per regime e 2/2 medie CD4. Nessuno dei job di questa
campagna o del fit finale T2 risulta ancora attivo nelle ultime ricevute.

**Preparato, non ancora consumato da un trainer:** le viste CRISPRi congelate
sono di 203.975 righe / 47 contesti / 18.562 target in produzione e
163.143 righe / 47 contesti / 14.786 target con esclusioni T.
Le viste T possono fornire gli input target-esclusi a J, ma non attestano
da sole l'esclusione dei contesti di un fold J.

Il proprietario ha autorizzato esplicitamente il trasferimento dei derivati
HIPSCI, Tian 2019 iPSC/neuron, Tian 2021 CRISPRi e Xu dai cinque produttori
privati di `davideferante` ai soli job privati di `davideferrante11`:
1.164.005.881 byte in produzione e 929.902.301 byte T.
Prove: `runtime_access_transfer_plan_r1.json` e
`runtime_access_authorization_r1.json`.

Entrambi i pacchetti di accesso sono completi, con 24 mount nativi e
82 chunk privati in produzione / 63 in T. I riferimenti di download sono
custoditi fuori dal repository e dai log; non espongono una scadenza
verificabile, quindi la loro durata non è attestata. Le ricevute pubblicabili
`runtime_access_production_df11_r1.json` e `runtime_access_T_df11_r1.json`
contengono identità e quantità, nessun riferimento che abiliti il download.

`runtime_view_resolver.py` verifica la vista e ogni chunk per SHA256 e byte,
conserva pesi/split/assi e rifiuta input mancanti o differenti. Tre fixture
sintetiche passano in `resolver_tests_r1.txt`. L'accesso effettivo ai chunk,
gli assi e le maschere originali devono ancora essere verificati nel job
privato di MODELLI-ESTERNI, unico responsabile del primo fit ESM2.
La preparazione degli accessi non è una ricevuta del consumo.

La revisione automatica ha respinto una proposta di prova locale perché
avrebbe cambiato la destinazione autorizzata. La prova non è stata eseguita
e il suo ingresso è disabilitato in `probe_runtime_access.py`; la verifica
reale procede direttamente nel runtime df11 già autorizzato.

Colab ha come ultimo heartbeat verificato il 3 ottobre alle 19:57:48;
Kaggle ha slot disponibili nel preflight di `final_t2/preflight_r1.json`.
MODELLI-ESTERNI prepara il proprio job CPU privato df11 con misure reali
di risorse, verifica completa, prova numerica su dati reali e fit.
Non è necessario aprire un notebook manuale per questo percorso.

D-053 resta aperta: Datlinger 2017/2021 richiede il mapping delle guide;
HIPSCI genome-wide fitness/nonfitness richiede ricomposizione e verifica
dei controlli. KO e CRISPRa sono derivati ma senza consumer appreso attestato.
Per quantità e lacune del catalogo vale `coverage_ledger_r2.json`, senza
promuovere somme per unità a cellule fisiche uniche o lette da un trainer.

Restano validi i test scientifici e di struttura registrati in r4. La suite
generale precedente ha tre errori per `cell_eval2.config` mancante, quindi
non è interamente verde. Nessun acquisto, push Git o invio VCC effettuato.
VALIDAZIONE resta l'unico autore dei documenti condivisi.
