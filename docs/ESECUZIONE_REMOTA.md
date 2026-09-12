# Locale e remoto — che cosa gira dove, con quali risorse

Aggiornato il 2026-09-12. Le misure di questa pagina vengono da esecuzioni reali su
questa macchina; le estrapolazioni sono marcate come tali. **Nessun servizio a pagamento
è stato attivato** e nessuna acquisizione massiva è stata avviata (D-005).

## 1. La macchina locale, rimisurata il 2026-09-12

| | Valore | Come |
|---|---|---|
| RAM totale | 7,81 GiB (0,76 GiB liberi durante le misure) | `Get-CimInstance Win32_OperatingSystem` |
| Disco libero | 31,11 GB | `Get-PSDrive C` |
| CPU | Intel i7-10510U, 8 thread logici | `Win32_Processor` |
| GPU CUDA | assente | `torch.cuda.is_available()` → False |
| `pdex` | non installato | `importlib.metadata` |

I valori di RAM e disco oscillano fra le sessioni: 8,4 GB / 28,0 GB l'11 settembre,
7,81 GB / 31,11 GB oggi. Vanno rimisurati prima di un job che si avvicini al limite.

## 2. Tempi misurati, non stimati

| Stadio | Lavoro | Tempo | Collo di bottiglia |
|---|---|---:|---|
| 40 build_signatures | 3 sorgenti, 2.694 bersagli, 7.492 firme | 254 s | allineamento e I/O HDF5 |
| 41 transfer_experiment | 3 coppie, 5 fold, 500 bootstrap | 288 s | metriche per bersaglio |
| 42 null_calibration | 4.800 cellule reali + 4.800 previste, 6 perturbazioni | 392 s | **DE con scanpy** |
| test suite | 61 test | 1,3 s | — |
| censimento bersagli | 3 file, solo `obs` | 0,13 s | — |

Il DE domina lo stadio 3 e domina qualunque cosa usi lo scorer. Con `scanpy` (fallback
attuale) 6 perturbazioni costano minuti; una griglia di calibrazione su decine di
bersagli è dell'ordine delle ore. **Installare `pdex` è il singolo intervento con il
rapporto beneficio/costo più alto** — e cambia i numeri DE, quindi va fatto una volta e
dichiarato (D-014).

## 3. Che cosa resta locale

Orchestrazione, metadati, sviluppo, pilot, report, e **tutto ciò che è già stato fatto
qui**: le firme dei tre pseudobulk, la calibrazione dell'ampiezza, il nullo con lo
scorer vero. La macchina locale basta anche per R-1 della roadmap: il mirror HepG2 è
0,851 GB compressi e il disco ne ha 31,1 liberi.

Il vincolo che morde non è il disco, è la RAM. Regole che hanno già evitato un
esaurimento di memoria:

- **Selezionare i bersagli prima di ingerire.** Una firma è densa su 18.533 geni:
  9.866 bersagli sarebbero circa 4,7 GB fra Δ e SE. Il censimento che decide costa
  0,13 s e legge solo `obs`.
- **Non caricare mai una matrice densa intera.** HepG2 densa è circa 5,6 GB, RPE1 circa
  8,7 GB, entrambe oltre la RAM libera. Lettura a blocchi o *backed*.
- **Caricare un set di firme alla volta.** Tre residenti insieme sono circa 1,3 GB.
- **`np.load` su un `.npz` decomprime l'intero membro a ogni accesso.** Materializzare
  una volta sola; il contrario aveva esaurito la memoria.

## 4. Quando serve una macchina remota, e quale

Tre lavori la richiedono, per motivi diversi:

| Lavoro | Perché non qui | Profilo minimo |
|---|---|---|
| Ingestione CD4 su scala (R-3) | il pseudobulk è 44,57 GB; i single-cell sommano 1,736 TB | **CPU**, 32 GB RAM, 200 GB disco temporaneo, banda in ingresso |
| Griglia di calibrazione sulle sei metriche (R-2) | il DE è il collo di bottiglia e scala con bersagli × punti di griglia | **CPU molti core**, 32 GB RAM, `pdex` installato |
| Eventuale modello generativo di conteggi | non previsto prima che le baseline saturino | GPU, e solo con un guadagno held-out che lo giustifichi |

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
`reports/pipeline/` e i manifesti — 116 KB oggi. Le firme (519 MB per il run e001)
restano dove sono calcolate a meno che non servano localmente.

**Che cosa non deve mai lasciare la macchina.** Credenziali, token VCC, e il contenuto
di `.env`. Il `.gitignore` li esclude già; su un remoto condiviso valgono le stesse
regole.

## 6. Riassunto operativo

- Oggi tutto ciò che serve gira **in locale**, R-1 e R-2 compresi, con l'unica
  aggiunta di `pdex`.
- Il remoto serve quando si scala CD4 (R-3) o la griglia sulle sei metriche diventa
  troppo lunga: profilo **CPU con 32 GB di RAM**, non GPU.
- Il preventivo si costruisce da byte reali e amplificazione misurata, e l'attivazione
  passa da un'approvazione esplicita.
