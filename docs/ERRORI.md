# Imparare dagli errori e impedirne la ripetizione

Questa è la guida operativa per trasformare un guasto in una prova di regressione
e in un controllo obbligatorio del prossimo lavoro pertinente. La pipeline resta
descritta in [LAVORO.md](LAVORO.md); stato e risultati scientifici restano in
[PROGETTO.md](PROGETTO.md) e nei report. Non serve un altro `pipeline.md` parallelo.

Un esperimento concluso correttamente che smentisce un'ipotesi **non è un errore
infrastrutturale**. Per esempio, Stack A termina lo scoring ma perde il confronto:
si conserva il [risultato negativo](../reports/analisi/lead_scientist_2026-09-29/neural/RISULTATI_STACK_A.md)
e si applica il protocollo, senza cercare un guasto da correggere per promuoverlo.

## Prima del prossimo job

1. Leggere gli incidenti pertinenti nel [registro degli errori](../reports/analisi/lead_scientist_2026-09-29/learning/README.md).
   Riportare nel manifest del job i loro EID e le guardie applicate.
2. Dichiarare **tutti** gli input consumati: dati, metadata, predizioni, marker,
   bundle, snapshot del codice, configurazioni/ancore esterne allo snapshot.
   Per ogni file servono percorso locale e del runtime, dimensione e SHA256.
   Un marker `finished.json` non sostituisce gli H5AD, e un dataset esistente
   non prova che contenga i target necessari.
3. Preparare il manifest e validarlo localmente nel Python dichiarato. Verificare
   autorizzazioni già presenti in sessione: non richiederle di nuovo se coprono
   l'azione. Il preflight non concede né revoca autorizzazioni, e non consuma quota.
4. Il launcher deve verificare sul **runtime destinatario** lo stesso manifest
   e gli hash completi prima del calcolo e prima di creare l'output del job.
   Con Drive, attendere tutti i file fino al limite dichiarato; un hash corretto
   sul disco locale non dimostra che Colab abbia sincronizzato quel file.
5. Conservare ricevute locali e remote, nuovi output e hash del manifest,
   validatore e launcher. Usare lo stesso Python del job. Non installare pacchetti
   nel runtime base per aggirare una verifica fallita: correggere e registrare
   l'ambiente scelto.

Questi passaggi si applicano ai nuovi job preparati dopo l'introduzione della
guida. Non interrompono quelli già in esecuzione e non autorizzano nuovi lanci.
Non ricreano il vecchio orchestratore o i cicli ritirati il 23 settembre.

## Controllo eseguibile comune

Il codice riusabile è
[`learning/preflight.py`](../reports/analisi/lead_scientist_2026-09-29/learning/preflight.py),
con [test](../reports/analisi/lead_scientist_2026-09-29/learning/test_preflight.py).
Non è uno stadio produttivo: controlla un contratto esplicito senza avviare
training, inferenza, scoring, submission o installazioni.

Il manifest JSON versione 1 ha questi campi:

| Campo | Contenuto obbligatorio |
|---|---|
| `schema_version`, `job_id` | `1`, identificatore del nuovo job |
| `incident_ids` | EID pertinenti, oppure lista vuota motivata nella revisione |
| `inputs` | Lista con `id`, `paths.local`, `paths.runtime`, `bytes`, `sha256`; tutti i file effettivamente usati |
| `outputs` | Lista con `id`, i due percorsi assoluti e `must_be_absent: true` |
| `target_checks` | Per ogni NPZ di effetti: `input_id`, `npz_key: "targets"`, lista `required` dei target richiesti |
| `environment` | `python.paths.local/runtime`, `packages`, `imports`, `probes`; liste vuote esplicite dove non applicabile |

In `packages`, il valore stringa richiede la versione esatta; `null` controlla
presenza e registra la versione, senza inventare un pin. `imports` prova il
percorso Python reale, per esempio `stack.model_loading`, non soltanto `pip check`.
Il manifest è codice operativo revisionato: non si eseguono import da documenti
o risultati non attendibili.

`probes: ["h5ad_nullable_roundtrip"]` verifica scrittura e rilettura di conteggi,
assi e label nullable in un file temporaneo. `allow_write_nullable_strings: true`
applica l'opzione **soltanto nel processo del preflight**. Non configura i processi
Python successivi: il produttore deve applicarla nel proprio wrapper, come
[`stack_pack_runtime.py`](../reports/analisi/lead_scientist_2026-09-29/neural/stack_pack_runtime.py).
La ricevuta esplicita questo limite. Per uno scorer che non scrive H5AD il probe
rimane una verifica di capacità, non una modifica scientifica.

Esempio di comandi; `job.json` deve contenere input reali, nessun segnaposto:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/learning/preflight.py validate --manifest job.json --site local --receipt receipts/job_local_r1.json
```

Nel launcher remoto, con `$PY` impostato al Python revisionato del job:

```bash
"$PY" preflight.py validate --manifest job.json --site runtime --receipt receipts/job_runtime_r1.json --attempts 45 --interval-seconds 20
```

Solo codice d'uscita zero permette il passo successivo. Il launcher verifica
prima anche gli hash del validatore e del manifest trasferiti. `--receipt` deve
stare fuori dagli output del job: la sua creazione non deve farli sembrare già
esistenti. Una ricevuta locale non vale come ricevuta remota.

Il controllo legge il solo array NPZ dei nomi target con `allow_pickle=False`,
non le matrici di effetti. Rifiuta target mancanti, duplicati, metadata object e
output preesistenti. Verifica presenza/dimensione di tutti gli input prima dei
loro hash completi. Può controllare soltanto i file **dichiarati**: la revisione
del launcher deve verificarne la completezza, inclusi gli snapshot. Non fornisce
un lock contro modifiche successive; usare input congelati e ricontrollare la
provenienza nei lettori scientifici.

## Quando qualcosa fallisce

Conservare tentativo, log e output parziali; classificare prima il problema:
input, ambiente, serializzazione, perdita del runtime, difetto del codice o
risultato scientifico. Aprire un incidente per un guasto operativo reale; una
nuova ipotesi scientifica ha un protocollo e una valutazione separati.

Ogni record include **sintomo → causa verificata o ancora ipotetica → correzione
→ test che riproduce il guasto → stato della verifica → guardia del prossimo job**.
Citare file e SHA256, distinguere il momento del guasto da quello della scrittura
del record. Non attribuire al provider una causa di disconnessione non dimostrata.

## Registro immutabile e chiusura

Le registrazioni sono in
[`learning/incidents/`](../reports/analisi/lead_scientist_2026-09-29/learning/incidents/).
Un EID è `E-AAAAMMGG-NNN`; ogni revisione è un nuovo JSON `E-…r001.json`,
`r002.json`, ecc. La revisione cita lo SHA256 della precedente. Non si sovrascrive
il record iniziale per far scomparire un guasto o anticipare un successo.

| Stato | Che cosa dimostra |
|---|---|
| `observed` | Il guasto è documentato; causa/fix possono essere ancora incerti |
| `implemented` | La correzione esiste; non prova una verifica riuscita |
| `verified_locally` | Test pertinente superato localmente; runtime remoto ancora da verificare |
| `verified_remotely` | Criterio esplicito superato nel runtime interessato, con evidenza e hash |

`verified_remotely` richiede un criterio circoscritto: un H5AD recuperato non prova
che il pacchetto VCC sia finito; un import corretto non prova che il modello sia
accurato. Un `.done` scritto anche per codice d'uscita nonzero non prova successo.
Se la correzione fallisce ancora, aggiungere una revisione e registrare la causa
nuova; non abbassare retroattivamente il criterio di chiusura.

[`learning/ledger.py`](../reports/analisi/lead_scientist_2026-09-29/learning/ledger.py)
valida campi, identità, sequenza e catena degli hash. L'indice è derivabile:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/learning/ledger.py index --directory reports/analisi/lead_scientist_2026-09-29/learning/incidents
```

Per aggiornare: preparare un nuovo record completo con revisione successiva e
`previous_sha256`, poi `ledger.py append --directory <incidents> --record <nuovo.json>`.
Per salvare un indice usare `--out <nuovo-indice.json>`; il file è un derivato,
non la fonte degli stati. Testare la correzione, leggere l'esito remoto completo
e aggiungere la revisione di verifica prima di dichiarare l'incidente chiuso.
