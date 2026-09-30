# Esecuzione e risorse della revisione

29 settembre 2026. Responsabile: Codex, sessione `01a0ee03-b357-7012-81a9-e8d7de767478`.

## Colab

Il proprietario ha offerto Colab e Kaggle in chat. Il dispatcher Colab è osservato attivo
alle 17:11:44 UTC, nel log su Drive. I quattro input del banco HepG2 sono già su Drive.

Prima dell'avvio dei nuovi lavori, i due script mai avviati `057_rete_r1_s0_a.sh` e
`058_rete_r1_s0_b.sh` sono stati rinominati nella stessa coda aggiungendo
`.hold-lead-20260929`. I contenuti sono conservati integralmente. Sono lavori r1 del 27/09
che citano i percorsi precedenti al riordino del repository; le corse r1 a tre semi sono
già descritte nel report del 28/09. Prima di riattivarli verificare ridondanza e percorsi.
Nessun processo in esecuzione è stato fermato da questa operazione.

Il nuovo banco usa una copia privata del codice, input identificati da hash e output
nuovi. Lo sviluppo seleziona al massimo due candidati; la conferma usa bersagli disgiunti
e parte solo dalla selezione fissata dal programma. I file piccoli prodotti durante
l'esecuzione rendono verificabile l'avanzamento senza interpretare il silenzio del log
sincronizzato come arresto del processo.

## Kaggle

La configurazione indicata dal proprietario è in `.kaggle-codex`, fuori dal repository.
Il client installato risponde. Nessuna credenziale viene copiata nel codice o nei report.
I nuovi esperimenti usano risorse private distinte da quelle dei lavori preesistenti.

Il proprietario ha confermato esplicitamente i due payload dopo il blocco della revisione
automatica: «Sì, copia e avvia sul mio Colab» per archivio e manifest nella cartella
`runs/lead_generator_setup_2026-09-29_r1` e relativo banco; «Sì, carica e usa Kaggle privato»
per `davideferante/vcc-lead-generator-inputs-r1`, contenente HepG2 pubblico, bulk K562 pubblico,
effetti t19like, lista dei bersagli e codice senza credenziali (1,24 GB circa).

L'archivio di codice comune ai due runner è `code_snapshot.tar.gz` (269.663 byte), SHA256
`d58da4136a244d98aff7796e258c652cf07b7bebcc60df22a79ce50f69c02053`.
Colab riceve il job `059_lead_generator_dev_r1.sh`, sviluppo soltanto; avvio osservato
nel dispatcher alle 17:23:05 UTC. La conferma viene eseguita separatamente sugli stessi
hash e sui bersagli disgiunti congelati dal manifest.

### Correzioni tecniche prima dei primi punteggi

- **r1 / job 059:** preparazione conclusa (48 sviluppo, 96 conferma), poi arresto prima
  della lettura delle cellule: l'asse dei geni era salvato come array NumPy di oggetti,
  rifiutato correttamente dal caricamento senza pickle. Corretto in Unicode e aggiunto
  un test completo di preparazione e rilettura; nessun parametro scientifico cambiato.
- **r2 / job 060:** prima generazione terminata, ma scorer arrestato prima di restituire
  le metriche per un'operazione `repeat` non supportata dal backend CuPy disponibile.
  La configurazione del banco ora seleziona esplicitamente il device CPU dello scorer
  ufficiale; la definizione delle metriche resta quella di cell-eval2 0.16.0.
- **r3 / job 061:** avvio osservato alle 17:43:27 UTC. Archivio 270.431 byte, SHA256
  `f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860`.
  Nuove destinazioni di codice, dati e output; r1/r2 restano disponibili. Quindici test
  sintetici del banco passano, inclusi preparazione senza pickle e scorer CPU.

Questi arresti non hanno prodotto uno score dei candidati; non motivano cambiamenti
di selezione, suddivisione o soglie. I log originali rimangono in `runs/jobs/` su Drive.

### Sviluppo concluso e conferma

Il job 061 è terminato con `rc=0` alle 18:05:47 UTC. La selezione automatica sui
48 bersagli development conserva `1.5:1` e `1.5:0.5`, entrambi pooled; la proiezione
locale a cinque membri dà rispettivamente +0,0190934 e +0,0152998. Non sono score VCC
né stime già confermate. Il generatore a profondità con ampiezza 1 è terzo e non
viene aggiunto alla conferma dopo aver visto i risultati.

La creazione del dataset Kaggle del generatore ha restituito successo, ma status,
file e metadati continuano a dare 403 e il dataset non compare fra quelli posseduti
(`kaggle_remote/CREAZIONE_R1.md`). Per completare la prova autorizzata si usa dunque
Colab anche per la conferma, mantenendo codice, versioni, bersagli e tre semi uguali
al protocollo. Accodato `062_lead_generator_confirmation_r3.sh`, SHA256
`d2d7fb4cfe4616725678be47987e281a9b12b3aa85ba0ba5f0481dd5e92c49b5`.
Il launcher richiede la selezione conclusa e non accetta una cartella di conferma
preesistente; gli input congelati sono ricontrollati dal banco.

### Modelli neurali

**Aggiornamento dopo la conferma:** il job 062 ha concluso con `rc=0` alle
18:50:23 UTC. Entrambi i finalisti passano; ampiezza1,5/dispersione1 è registrato
come t28 alle18:56UTC. Risultati e limiti sono in `RISULTATI_GENERATORE_CONFERMA.md`
e CP-0047. Il job `070_lead_t28_generate_r1.sh` è stato osservato avviato alle
19:03:23 UTC: generazione completa e packaging verificato, senza comando di invio.
Launcher SHA256 `e8190327a2c5d116f7949dcb6f5857a8c4c8ad24edac2235dfcb6b6392516137`.

La preparazione dell'ambiente ha incontrato `ensurepip` non disponibile nel Python
3.13 di Colab (job067). Il nuovo job069 usa una venv isolata senza ensurepip e il
pip ereditato, con destinazioni e versioni controllate: `rc=0` alle19:00:22UTC,
base invariata e roundtrip HDF5 verificato. Il generatore e il packager usano entrambi
`/content/lead_candidate_environment_r2/venv/bin/python`. I fallimenti sono preservati.

La preparazione prompt Stack job064 ha concluso con `rc=0` alle18:59:27UTC.
Il preflight dipendenze job066 aveva incontrato lo stesso problema ensurepip prima
di installare uv; job068 usa uv in una directory dedicata e CPython3.11.13 gestito.
Ha risolto le dipendenze con `rc=0` alle19:00:02UTC. Questa è una prova del resolver,
non ancora di import, caricamento pesi o inferenza.

Il pilot Stack `071_lead_stack_infer_r1.sh` è partito alle 19:16:24 UTC e si è
fermato alle 19:23:04 con `rc=1`: installazione e test del contratto completati,
ma l'import di scvi richiede `pooch`, non installato dai suoi requisiti base.
Il controllo ha arrestato il job prima del download dei pesi. Sono conservati
ambiente, freeze e traceback in `runs/lead_stack_infer_2026-09-29_r1/` su Drive.
La ripresa prepara un output nuovo e mantiene adattatore e piano congelati.

La replica neurale seed 1 è stata anticipata prima di vedere qualunque risultato
seed 0, con split e training invariati: `EMENDAMENTO_NEURALE_SCHEDULING_01.md`.
Il notebook privato `davidmaisterx/vcc-lead-neural-seed1-r1`, versione 1, è stato
accettato e osservato RUNNING alle 19:25 UTC. Payload
`4c5b7b53069b0642d0b9273c87c1128b6ccf299275e816271e3f79b7cbd52665`;
prove di push e verifica in `kaggle_neural_seed1_r1/`. I due semi saranno letti
entrambi; il fit di produzione conserva il gate positivo completo.

Il secondo account già configurato, `davidmaisterx`, possiede il dataset privato r2
verificato ready. Il nuovo notebook privato `vcc-lead-neural-sources-r1` è stato
inviato come versione 1 e osservato RUNNING. Nessun nuovo dato caricato, cinque fold
C, una T4 visibile al codice, internet disabilitato. Manifest e log del push sono in
`kaggle_neural_r1/`. Un problema del solo lettore finale (`null` interpretato come
valore mancante da pandas) è documentato e corretto separatamente: non si riavvia
l'addestramento per questo e non si scartano i file dei fold.

Accodato inoltre `063_lead_stack_prepare_r1.sh`, SHA256
`656c7ee167ce5f9b49a390dafcd4435a83e12fabec351d73aa65b9294817608f`:
solo estrazione di prompt reali K562 e controlli HepG2 dai file pubblici già su Drive,
senza copia del file intero K562, senza pesi Stack, inferenza o scoring. Il payload
di codice è 28.868 byte e il piano è congelato prima dell'estrazione. Dettagli in
`neural/stack_setup_r1/setup_manifest.json`.

Il job 063 si è fermato prima di leggere le espressioni perché l'hash del JSON
generato su Linux differiva dal piano locale Windows solo per i fine-riga. Tutti
i campi sono identici, inclusi hash di dati, protocollo e adattatore. La ripresa
`064_lead_stack_prepare_r2.sh`, avviata alle 18:15:30 UTC, confronta ogni campo JSON
con il piano congelato nello stesso archivio e scrive in una cartella r2 nuova.
Evidenza dell'arresto in `neural/prepare_failure_r1/`. Il proprietario ha confermato
partecipazione personale/non commerciale; l'uso dei checkpoint è ammesso dalla FAQ
VCC 2026 verificata in `rules_2026/LETTURA.md`.

## Portatile

Il packaging t27 è terminato alle 17:04:39 UTC con convalida ufficiale e verifica bit
per bit del payload. Lo sha256 del pacchetto è
`b4eb8b75f184ad3c4c5c8a73424b7f9b8a4106464b801e846d0aeff97f02b890`.
Il pacchetto resta pronto, senza invio, secondo l'indicazione del proprietario.
Un'altra sessione prepara il banco K562 sul portatile: i nuovi banchi pesanti di questa
sessione sono quindi destinati al calcolo remoto.
