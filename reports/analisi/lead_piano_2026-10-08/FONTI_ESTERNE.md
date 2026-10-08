# Fonti esterne e catalogo consultato l'8 ottobre 2026

Lettura web di fonti primarie; nessuna installazione, acquisizione di dataset/pesi,
API di embedding a pagamento, inferenza o training. Le capacità descritte sono
degli autori, non replicate nel progetto. Perimetro: scelta dei componenti del
[piano lead](README.md), non un censimento completo della letteratura.

## PIE

- [Annuncio Arc del 5 ottobre](https://arcinstitute.org/news/pie): motivazione
  per generalizzazione a contesti/interventi nuovi e rilascio degli artefatti.
- [Codice ufficiale](https://github.com/ArcInstitute/pie): Perceiver IO,
  pacchetto `arc-pie`, Python 3.12, asset versionati. Codice CC BY-NC-SA 4.0.
- [Guida tecnica](https://raw.githubusercontent.com/ArcInstitute/pie/main/AGENTS.md):
  preparazione dei soli controlli, comandi e risorse delle corse pubblicate.
  Letta come documentazione esterna, non come istruzioni per questo repository.
- [wdataset](https://huggingface.co/arcinstitute/PIE_replogle_wdataset): quattro
  modelli distinti con una linea fuori ciascuno, metriche proprie C/T/J;
  un nome di cartella è la linea esclusa. Non mediare tutti i fold per valutare
  una linea: alcuni l'hanno usata nel training.
- [xdataset](https://huggingface.co/arcinstitute/PIE_replogle_xdataset): training
  su Tahoe, Jiang, VCC25 e Orion; Replogle usato per valutazione e ordinamento
  dell'asse. Le sei metriche pubblicate non sono i sei membri ufficiali VCC.
- [predict.py](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/predict.py):
  config/statistiche incorporate nei pesi e memoria dalle sorgenti del training;
  verificata staticamente la dipendenza, non eseguita.
- [datamodule.py](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/data/datamodule.py):
  separazione input di query e input della memoria, controllo delle dimensioni
  delle sorgenti e riferimenti allo split. Cambiare solo il percorso di input
  non sostituisce automaticamente la memoria di un checkpoint.
- [heads.py](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/model/heads.py):
  tre uscite; `p_de` da logits, non p-value sperimentale.
- [config xdataset corrente](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/configs/experiment/replogle_xdataset.yaml):
  pesi dataset 0,68 Tahoe, 0,30 Orion, 0,01 Jiang, 0,01 VCC25. Sono la
  configurazione degli autori, non i pesi da imporre al corpus D-053.

**Versioni:** la model card riferisce `PIE_sources@cb1aaa4e…`; il config `main`
consultato riferisce `PIE_sources@fb624a51…` e revisioni diverse di alcuni dataset.
Non è una prova di errore upstream: i rilasci possono evolvere. Per riusare un
checkpoint occorrono i riferimenti salvati con esso, non il `main` del giorno.

**Licenze:** le schede dichiarano per i pesi la specifica PIE Model Non-Commercial
License, distinta dal codice; condizioni complete e compatibilità del riuso
previsto devono essere lette prima dell'acquisizione/distribuzione. La pagina
integrale della licenza non è stata recuperata con successo in questa sessione;
nessun parere legale o permesso della competizione viene inferito.
Il DOI del preprint non è stato recuperato: nessuna analisi delle sue tabelle
o ablation è stata effettuata. L'analisi usa codice e schede ufficiali accessibili.

### Dati e fonti candidati: catalogo, non nuovi dati acquisiti

Tutti elencati nella [collezione ufficiale PIE](https://huggingface.co/collections/arcinstitute/pie).
I conteggi mostrati dal viewer HF sono record delle tabelle, non cellule.
Dimensioni scaricabili, checksum e condizioni dei singoli componenti **da verificare**.

| Repository HF | Contenuto/ruolo da verificare | Relazione con il catalogo del progetto |
|---|---|---|
| `arcinstitute/PIE_replogle_nadig_essential` | Dati preparati Replogle/Nadig, quattro linee | Stessa famiglia biologica di dati già usati; riconciliare accessioni/cellule, nessun secondo peso |
| `arcinstitute/PIE_x_atlas_orion` | Preparazione Orion per PIE | Sovrapposizione attesa con HCT116/HEK293T, da identificare esattamente |
| `arcinstitute/PIE_arc_vcc_25` | Preparazione della gara 2025 | Verificare split rispetto alla nostra riserva H1 prima di usare checkpoint/evidence |
| `arcinstitute/PIE_tahoe100m` | Preparazione perturbazioni farmacologiche Tahoe | Famiglia già a catalogo; modalità distinta dal KD, niente duplicazione biologica |
| `arcinstitute/PIE_jiang` | Dati Jiang usati nella corsa xdataset | Accessions, contesti, tipo di intervento, identità con fonti già presenti e licenza da riconciliare; nuova voce candidata |
| `arcinstitute/PIE_sources` | Embedding biologici, del contesto e chimici | Covariate/descrittori, non nuove cellule o misure RNA; provenance e compatibilità per componente |
| `arcinstitute/PIE_splits` | Liste di coppie train/val/test | Artefatto di valutazione; nessuna supervisione aggiuntiva |

La lettura delle pagine non autorizza il download. Prima di una richiesta di
acquisizione: elenco selettivo degli asset necessari, revisioni, byte e condizioni,
inclusa la memoria delle risposte che l'inferenza richiede. Il checkpoint da solo
non è la stima del volume totale.

## Altri riferimenti riaperti

| Fonte primaria | Uso nel piano | Limite |
|---|---|---|
| [STATE](https://raw.githubusercontent.com/ArcInstitute/state/main/README.md), [modelli disponibili](https://huggingface.co/collections/arcinstitute/state) | Distinguere SE per embedding e ST per predizione; interfacce per contesti esclusi | Nessun peso installato o audit completo dei checkpoint in questa sessione |
| [Arc Stack](https://github.com/ArcInstitute/stack) | Inferenza guidata da cellule come esempi | Il nostro esito locale negativo è già in CP-0051; non cancellarlo perché il modello è pubblico |
| [PRiMeFlow](https://raw.githubusercontent.com/altoslabs/primeflow/main/README.md) | Generazione flow matching; eventuale secondo esperimento sull'emissione | La vittoria Generalist 2025 non misura il beneficio cross-contesto 2026 |
| [GEARS a commit letto il 4/10](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/README.md) | Rappresentazioni biologiche del bersaglio | Il rapporto locale fornisce audit del codice e fixture; non prova un grafo reale allenato |

AMMI, STAR, PLE, HorNet, FiLM e GRN sono considerati attraverso il
[catalogo locale verificato del 5/10](../pezzi_adottabili_2026-10-05/CATALOGO.md),
con i suoi limiti. Le loro formule/licenze non sono state nuovamente verificate
qui e non se ne presenta una nuova validazione.
