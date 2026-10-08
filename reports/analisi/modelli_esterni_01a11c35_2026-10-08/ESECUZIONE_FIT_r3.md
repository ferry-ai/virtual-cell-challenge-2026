# Avanzamento reale e accesso fra account

Osservazione dell'8 ottobre 2026, circa 23:32 Europe/Rome. Misure operative,
non risultati di validazione biologica. Supersede gli stati di avvio delle r1/r2,
conservate insieme a tutti i tentativi.

## Fit in corso, misurato

`live_progress_r1.json` conserva estratti JSON dei log remoti. Tutti su df11:

| Job | Ultima misura conservata |
|---|---|
| produzione r4 | 2.240 geni di risposta su 18.533, checkpoint salvato |
| T r3 | 3.072 su 18.533, checkpoint salvato |
| C-K562 r1 | costruzione dello store completo, dopo risoluzione degli input |
| J-K562 r1 | 192 su 18.533, checkpoint salvato |

Il passaggio a full_fit segue la prova numerica reale nel runner, ma la ricevuta
completa deve ancora essere recuperata. Non si dichiara il training completo dal
solo caricamento o dalla presenza del job. Nessuna riduzione di contesti o target.

Il proprietario ha autorizzato esplicitamente i quattro fit C/J nella risposta
alla domanda `call_19aa555691d3489b86f2cb1e6acd364e`, item 0. Preflight r4:
prima dei quattro nuovi tentativi, df11 aveva due job attivi, davidmaisterx uno,
davideferante zero. Gli ultimi 50 job di ciascun account sono stati interrogati;
la quota residua non era esposta. Colab: file dispatcher accessibile, ultima
modifica 3 ottobre alle 19:57 UTC, nessuna prova di runtime attivo.

## Due tentativi iPSC r2 falliti prima del fit

Il proprietario ha chiesto di usare altri account Kaggle, autorizzando la
pubblicazione se necessaria. Dopo un rifiuto dell'auto-review, ha inoltre
autorizzato specificamente i trasferimenti privati Tian 2019 neuroni, Tian 2021
CRISPRi e Xu verso C-iPSC/davidmaisterx e J-iPSC/davideferante (53,5/43,8 MB),
risposta `call_f35d9965d6a941308163b640c833f8eb`, item 0.

I due push sono stati accettati da Kaggle **con sorgenti rifiutate**. La vecchia
ricevuta `accepted: true` non prova un pacchetto utilizzabile:

- C-iPSC r2: due mount df11 privati, joint H1 e joint K562 produzione;
- J-iPSC r2: sedici mount df11 privati, quattordici sorgenti T e due joint T.

Entrambi ERROR, ricevute `retrieval_C-iPSC_r2.json` e
`retrieval_J-iPSC_r2.json`. I file recuperati sono soltanto quelli ammessi dalla
allowlist; nessun notebook, HTML, bundle o locator. Failure entrambe in
`resolve_all_chunks`, prima della costruzione dello store e del fit.

**Causa verificata:** una sorgente montabile nell'account proprietario non è
necessariamente pubblica o montabile negli altri account. L'assunzione iniziale
era errata. Kaggle può avviare il codice anche scartando alcuni kernel_sources.
Il resolver ha impedito un fit con corpus incompleto. Non sono fallimenti
scientifici del modello.

**Correzione implementata:** `source_access_preflight.py` interroga le sorgenti
con l'account destinatario prima del push. Su C-iPSC r2 riproduce FAIL sui due
mount (`source_access_C-iPSC_r2.json`). `launch_cloud_fit_v4.py` richiede questa
ricevuta PASS, recente e legata al pacchetto per SHA. `push_private_v2.py`
rifiuta come successo qualsiasi risposta con invalidKernelSources. Fixture
dedicata in `test_source_access.py`. La correzione dell'accesso ai dati resta
in coordinamento con DATI-TRANSFER; nessun rilancio iPSC valido ancora attestato.

Nessun notebook ESM2 viene pubblicato: incorpora locator temporanei. Eventuali
artefatti pubblici devono essere separati, controllati e privi di credenziali.
Le viste, i pesi, gli split e i byte scientifici restano congelati.

## Raccolta e verifica a completamento

`collect_when_terminal.py` è un processo una tantum per i quattro job df11
esplicitamente elencati in `terminal_collection_r1.lock`. Non lancia altri job,
non pubblica e non effettua scoring. Dipende dalla permanenza del processo locale;
non è un servizio persistente né una promessa di riavvio dopo spegnimento.

Recupera con `collect_cloud_fit_v2.py` solo modello, predizioni, manifest e
ricevute ammesse. Destinazione fuori Git:
`C:/Users/ferra/vcc2026-data/external_models/01a11c35/verified_cloud_outputs/`.
Gli output reali compaiono sotto `<job>/<job>/`. Le ricevute piccole di raccolta,
verifica e stato terminale vengono scritte in questa cartella.

`verify_fit_outputs.py` verifica checksum, assi, valori e maschere di tutte le
predizioni a blocchi, poi confronta poche query col modello ricaricato senza
rifit. Quattro fixture passano, comprese corruzioni con checksum aggiornati.
La verifica indipendente del consumo appartiene a DATI-TRANSFER; lo scoring e
la decisione di adozione appartengono a VALIDAZIONE.

Restano espliciti: modello target-only; feature assente per TMEM104; esclusioni
C/T/J; copertura della release distinta dalla chiusura D-053 dell'intero catalogo;
scala nativa distinta dall'input finale del generatore. Nessun beneficio predittivo
misurato e nessuna promozione per rispettare il freeze.
