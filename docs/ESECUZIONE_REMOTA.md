# Locale e remoto — che cosa gira dove, con quali risorse

Aggiornato il 2026-09-12. Le misure di questa pagina vengono da esecuzioni reali su
questa macchina; le estrapolazioni sono marcate come tali. **Nessun servizio a pagamento
è stato attivato** e nessuna acquisizione massiva è stata avviata (D-005).

## 1. La macchina locale, rimisurata il 2026-09-12

| | Valore | Come |
|---|---|---|
| RAM totale | 7,81 GiB (0,28–1,58 GiB disponibili durante le misure del 12 settembre sera) | `GlobalMemoryStatusEx` via `src/vcc2026/resources.py` |
| Disco libero | 31,11 GB alle 17:00; 33,25 → 23,65 GiB fra l'inizio e la fine delle due generazioni della sera | `shutil.disk_usage` |
| CPU | Intel i7-10510U, 8 thread logici | `Win32_Processor` |
| GPU CUDA | assente | `torch.cuda.is_available()` → False |
| `pdex` | non installato | `importlib.metadata` |

I valori di RAM e disco oscillano fra le sessioni: 8,4 GB / 28,0 GB l'11 settembre,
7,81 GB / 31,11 GB nel pomeriggio del 12. Vanno rimisurati prima di un job che si
avvicini al limite — e **anche durante**: la sera del 12 settembre il disco libero è
calato di 5,5 GiB fra due misure a poche decine di minuti di distanza, senza che il
progetto avesse scritto nulla di quella taglia. `src/vcc2026/resources.py` misura RAM,
disco e memoria di picco, e `require()` rifiuta un job che non finirebbe, con il
divario dichiarato, invece di lasciare un file troncato che somiglia a un artefatto.

## 2. Tempi misurati, non stimati

| Stadio | Lavoro | Tempo | Collo di bottiglia |
|---|---|---:|---|
| 40 build_signatures | 3 sorgenti, 2.694 bersagli, 7.492 firme | 254 s | allineamento e I/O HDF5 |
| 41 transfer_experiment | 3 coppie, 5 fold, 500 bootstrap | 288 s † | metriche per bersaglio |
| 42 null_calibration | 4.800 cellule reali + 4.800 previste, 6 perturbazioni | 392 s † | **DE con scanpy** |
| 44 calibrate_transfer | 1 coppia, 5 fold esterni × 4 interni, 1.000 bootstrap | 27,6 s | nessuno: tre prodotti scalari per bersaglio |
| 45 generate_prediction, controllo | 360.000 cellule reali ricampionate | 1.249 s | letture CSR sparse per riga |
| 45 generate_prediction, trasferimento | 360.000 cellule campionate Poisson | 1.153 s | campionamento e conversione CSR |
| 46 validate_package, verifica locale | 2,08·10⁹ valori riletti dal file | 58 s + 132 s | decompressione gzip |
| profilo basale di un contesto | 18.400 cellule, a blocchi | ~9 s | — |
| test suite | 166 test (103 il 2026-09-12, quando questa riga è stata scritta) | 2,4 s | — |
| censimento bersagli | 3 file, solo `obs` | 0,13 s | — |

† *Verificato il 2026-09-15: nessun artefatto registra la durata di questi due stadi.*
`manifest_41_transfer_experiment.json` e `manifest_42_null_calibration_A.json` hanno
`started_utc` e `finished_utc` a 0,38 s e 0,93 s di distanza, cioè misurano la scrittura
del manifesto, non l'esecuzione. I due numeri restano plausibili — sono osservazioni di
console — ma non sono ripetibili da un file, e vanno rimisurati registrando la durata.
Lo stadio 40 fa eccezione: il suo manifesto copre 250,84 s contro i 254 s riportati qui.

Lo stadio 44 sostituisce lo 41 per la calibrazione dell'ampiezza e costa un decimo del
tempo: precalcola tre prodotti scalari per bersaglio invece di ricostruire la matrice
di previsione a ogni fold. Nessun risultato cambia.

Lo stadio 45 scrive circa 3,9 GiB per previsione completa e non tiene mai più di un
blocco di 400 cellule in memoria: il picco misurato è **0,41 GiB**, contro i circa
34 GiB che costerebbe assemblare la matrice.

Il DE domina lo stadio 3 e domina qualunque cosa usi lo scorer. Con `scanpy` (fallback
attuale) 6 perturbazioni costano minuti; una griglia di calibrazione su decine di
bersagli è dell'ordine delle ore. **Installare `pdex` è il singolo intervento con il
rapporto beneficio/costo più alto** — e cambia i numeri DE, quindi va fatto una volta e
dichiarato (D-014).

## 3. Che cosa resta locale

Orchestrazione, metadati, sviluppo, pilot, report, e **tutto ciò che è già stato fatto
qui**: le firme dei tre pseudobulk, la calibrazione dell'ampiezza, il nullo con lo
scorer vero, e — dal 12 settembre — la **generazione completa** di una previsione
360.000 × 18.533 e la verifica del suo contratto. La macchina locale basta anche per
R-1 della roadmap: il mirror HepG2 è 0,851 GB compressi e il disco ne aveva 31,1
liberi al pomeriggio, 23,7 dopo le due generazioni.

Ciò che **non** resta locale è il passo successivo: `vcc prep`. Generare una previsione
costa 0,41 GiB di picco perché nulla è mai residente; impacchettarla ne costa 22–33
perché `prep` tiene tutto in memoria. Il confine fra locale e remoto passa esattamente
lì.

Il vincolo che morde non è il disco, è la RAM. Regole che hanno già evitato un
esaurimento di memoria:

- **Selezionare i bersagli prima di ingerire.** Una firma è densa su 18.533 geni:
  9.866 bersagli sarebbero circa 2,93 GB fra Δ e SE in float64, 3,11 GB con la
  maschera (ricalcolato il 2026-09-15: 9.866 × 18.533 × 8 byte × 2; il «4,7 GB» che
  si leggeva qui non è derivabile da quelle quantità). Il censimento che decide costa
  0,13 s e legge solo `obs`.
- **Non caricare mai una matrice densa intera.** HepG2 densa è circa 5,6 GB, RPE1 circa
  8,7 GB, entrambe oltre la RAM libera. Lettura a blocchi o *backed*.
- **Caricare un set di firme alla volta.** Tre residenti insieme sono circa 1,3 GB.
- **`np.load` su un `.npz` decomprime l'intero membro a ogni accesso.** Materializzare
  una volta sola; il contrario aveva esaurito la memoria. `SignatureSet.read_npz`
  accetta ora un filtro per bersagli: i 300 del pannello sono circa 90 MB contro gli
  890 dell'insieme completo di `k562_gwps`.
- **Scrivere la sottomissione a blocchi, mai assemblarla.** 360.000 × 18.533 a densità
  realistica sono circa 2,08·10⁹ valori memorizzati, circa 34 GB come CSR in memoria.
  `SubmissionWriter` appende una perturbazione alla volta e la scarta: picco misurato
  0,41 GiB.

## 4. Quando serve una macchina remota, e quale

Quattro lavori la richiedono, per motivi diversi. Il primo è nuovo dal
12 settembre e non è di calcolo: è di memoria.

| Lavoro | Perché non qui | Profilo minimo |
|---|---|---|
| ~~Packaging `.vcc` di una previsione completa~~ — **non più remoto dal 2026-09-13** | Era: `vcc prep` carica l'intera matrice, 33,5 GiB di picco a 2,17·10⁹ valori. Misurato ora: convalidando e scrivendo a blocchi si impacchetta **qui**, con 0,519 GiB di picco e 7,88 GiB di disco transitorio ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1). Il limite era dello strumento, non del problema | nessuno: gira in locale con `scripts/48_package_prediction.py` |
| Ingestione CD4 su scala (R-3) | il pseudobulk è 44,57 GB; i single-cell sommano 1,736 TB | **CPU**, 32 GB RAM, 200 GB disco temporaneo, banda in ingresso |
| Griglia di calibrazione sulle sei metriche (R-2) | il DE è il collo di bottiglia e scala con bersagli × punti di griglia | **CPU molti core**, 32 GB RAM, `pdex` installato |
| Eventuale modello generativo di conteggi | non previsto prima che le baseline saturino | GPU, e solo con un guadagno held-out che lo giustifichi |

**Due trappole del packaging, misurate il 2026-09-12.**

- `sizing.prep_memory_warning` esiste per evitare che `prep` venga terminato senza
  messaggio, ma dimensiona contro `os.sysconf`, che su Windows non esiste:
  `total_ram_gib()` torna `None` e l'avviso **non può scattare**. Verificato su questa
  macchina. L'assenza dell'avviso non è un via libera.
- La soglia dei **2.147.483.648 valori memorizzati** cambia il regime: SciPy indicizza
  CSR con int32 finché può e promuove a int64 sopra, quindi il costo per valore passa
  da 8 a 12 byte e il picco di `prep` salta del 50%. Una previsione completa a densità
  realistica sta a circa il 97% di quella soglia, quindi da che parte cade è una
  proprietà del modello, non una costante. Vedi
  [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5.

**Un percorso remoto resta documentato e pronto, per il set finale.**
`notebooks/kaggle_package_trial01.ipynb` esegue la stessa implementazione su un runtime
Kaggle CPU (31,3 GiB di RAM, circa 1 TB di filesystem di lavoro, **19,5 GiB di output
salvato** — numeri diversi, e solo il terzo limita ciò che sopravvive alla sessione).
Il notebook misura RAM e mount prima di scegliere i percorsi, riverifica lo sha256 dopo
il trasferimento, installa `vcc-cli==0.2.0`, **rigira i test di parità su quella
macchina** prima di produrre qualcosa, e tiene i transitori fuori da `/kaggle/working`.
Non è stato eseguito: il run locale è riuscito. Il trasferimento dell'input è a carico
del proprietario — un dataset Kaggle **privato**, caricato da lui, non da qui.

**Una GPU non serve oggi.** Le baseline attuali sono algebra lineare su matrici da
poche migliaia di righe; il costo è nel DE e nell'I/O, che sono CPU e rete. Una GPU
avrebbe senso solo per il backend `gpudge` dello scorer o per un modello generativo, e
il secondo non è giustificato finché le baseline non saturano (R-4). Proporre una GPU
adesso sarebbe comprare capacità per un lavoro che non abbiamo ancora deciso di fare.

### Come stimare il costo senza inventarlo

**Non sono stati usati prezzi in questo documento, perché non ne ho di verificati a
oggi.** Il preventivo va costruito così, al momento della proposta:

1. **Byte reali.** Dimensione del file dal registry (`bytes_total`), non dalla prosa.
2. **Amplificazione di traffico misurata.** Il pilot CD4 ha trasferito 92.475.050 byte
   per produrne 1.630.799: circa **57× di amplificazione**, ovvero circa 1,4 MB di
   traffico per cellula estratta. Una frazione piccola di dati **non** implica un
   trasferimento piccolo. Rifare un probe prima di fissare il tetto.
3. **Throughput dallo stadio equivalente già eseguito**, scalato sui core.
4. **Storage** temporaneo e persistente separati, ed **egress** se i risultati tornano
   indietro (i nostri sono piccoli: `reports/pipeline/` è 116 KB).
5. Prezzi **verificati quel giorno** sul listino del fornitore concreto.

### Prima di attivare qualcosa a pagamento

Serve una proposta con: job concreto, costo massimo, tetto di storage e di traffico,
criterio di arresto, e poi l'approvazione esplicita del proprietario del progetto
(D-005). Nessuna delle voci di roadmap R-1..R-4 la richiede.

> Nota operativa: in questa sessione i connettori Runpod, GitHub e simili risultano
> presenti ma **non autenticati**, e la sessione non è interattiva, quindi non è
> possibile avviare l'OAuth da qui. Vanno autorizzati dal proprietario in una sessione
> interattiva prima che quella strada sia percorribile.

## 5. Portabilità: che cosa rende un run rieseguibile altrove

**Radici configurabili.** `data_root` (input, può essere un mount in sola lettura) e
`artifact_root` (tutto ciò che un run scrive). Entrambe sovrascrivibili da ambiente:

```bash
export VCC2026_DATA_ROOT=/mnt/data/vcc2026
export VCC2026_ARTIFACT_ROOT=/mnt/artifacts
python scripts/40_build_signatures.py --run-id e001
```

Un test (`test_no_hardcoded_data_root_in_new_modules`) fallisce se un modulo nuovo
reintroduce un percorso Windows. I wrapper `.cmd` restano per la macchina locale; su
Linux si invoca `python` direttamente con `PYTHONPATH=src`.

**Dipendenze.** `requirements.lock.txt` fissa le versioni. Sul remoto vanno aggiunti
`pdex` (velocità del DE) e `pyarrow` (Orion); qui pyarrow vive solo in `.runtime-deps`,
ignorato da Git.

**Checkpoint e ripresa.** Ogni stadio scrive in una cartella di run e non sovrascrive
mai: una riesecuzione va in un `--run-id` nuovo. Le firme sono l'unità di ripresa —
costano minuti, sono immutabili, e `41_transfer_experiment.py --signatures <dir>` le
riusa. **Un'interruzione non richiede di riscaricare nulla**: si ripete lo stadio
fallito puntando alle firme già calcolate.

**Che cosa spedire avanti e indietro.** Verso il remoto: il repository (piccolo) e i
percorsi delle fonti; le fonti si scaricano lì, non da qui. Verso casa: la cartella
`reports/pipeline/` e i manifesti — 116 KB oggi. Le firme (541,1 MB per il run e001)
restano dove sono calcolate a meno che non servano localmente.

**Che cosa non deve mai lasciare la macchina.** Credenziali, token VCC, e il contenuto
di `.env`. Il `.gitignore` li esclude già; su un remoto condiviso valgono le stesse
regole.

## 6. Riassunto operativo

- Oggi tutto ciò che serve gira **in locale**, R-1 e R-2 compresi, con l'unica
  aggiunta di `pdex`. Il packaging `.vcc`, che il 12 settembre sembrava l'eccezione,
  gira anch'esso qui dal 13: 0,52 GiB di picco, 16,8 minuti.
- Il remoto serve quando si scala CD4 (R-3) o la griglia sulle sei metriche diventa
  troppo lunga: profilo **CPU con 32 GB di RAM**, non GPU.
- Il preventivo si costruisce da byte reali e amplificazione misurata, e l'attivazione
  passa da un'approvazione esplicita.
