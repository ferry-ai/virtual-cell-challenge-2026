# CP-0004 — Primo trial locale: calibrazione annidata, inferenza A/B/C e limite di packaging

- **Data:** 2026-09-12
- **Tipo:** osservazione
- **Redatto da:** agente (Claude Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Tre domande, in ordine di dipendenza.

1. Qual è **esattamente** il contratto di sottomissione oggi, e che cosa va consegnato
   oltre alle previsioni?
2. Si riesce a produrre, **in locale**, due previsioni complete a forma di
   sottomissione per i contesti A/B/C — un controllo senza modello e il trasferimento
   calibrato — senza esaurire le risorse e senza sovrastimare che cosa dicono?
3. L'ampiezza di trasferimento α, che CP-0003 aveva dato a 0,25, regge a un protocollo
   di selezione più stretto?

## 2. Cosa è stato fatto

**Contratto.** Consultate le pagine ufficiali *Evaluation*, *Rules* e le FAQ di
virtualcellchallenge.org il 2026-09-12, più `vcc prep --help` e `vcc submit --help`
della CLI installata (`vcc 0.2.0`, `cell-eval2 0.16.0`). Controllo di sola lettura
sull'account con `vcc whoami --json`. Il contratto verificato è in
[`docs/SOTTOMISSIONE.md`](../SOTTOMISSIONE.md) §1. **Nessun token è stato stampato,
copiato o scritto in un file del repository.**

**Codice nuovo.** `src/vcc2026/inference.py` (log2FC → conteggi, vincolo compositivo,
maschere di supporto, diagnostiche del generatore, verifica di provenienza dei
contesti), `resources.py` (RAM, disco, memoria di picco), `trials.py` (definizione dei
trial); `configs/trials.yaml`; cinque stadi nuovi — `scripts/43_freeze_trial.py`,
`scripts/44_calibrate_transfer.py`, `scripts/45_generate_prediction.py`,
`scripts/46_validate_package.py`, `scripts/47_resource_report.py` —
e 42 test in `tests/test_trial_inference.py`. `SubmissionWriter` corretto (§3.6);
`SignatureSet.read_npz` ha ora un filtro per bersagli.

```powershell
.\scripts\py.cmd scripts/43_freeze_trial.py --run-id c002 --trial trial-01-transfer
.\scripts\py.cmd scripts/44_calibrate_transfer.py --run-id c002 `
    --signatures C:\Users\ferra\vcc2026-data\artifacts\e001\signatures `
    --outer-folds 5 --inner-folds 4 --n-boot 1000
.\scripts\py.cmd scripts/45_generate_prediction.py --run-id q00pilot `
    --trial trial-00-controls --n-perts 6
.\scripts\py.cmd scripts/45_generate_prediction.py --run-id q01pilot `
    --trial trial-01-transfer --n-perts 6 `
    --fitted-state ...\c002\fitted_state.json --signatures ...\e001\signatures
.\scripts\py.cmd scripts/45_generate_prediction.py --run-id q00full --trial trial-00-controls
.\scripts\py.cmd scripts/45_generate_prediction.py --run-id q01full `
    --trial trial-01-transfer `
    --fitted-state ...\c002\fitted_state.json --signatures ...\e001\signatures
.\scripts\py.cmd scripts/46_validate_package.py --run-id q00full --skip-prep
.\scripts\py.cmd scripts/46_validate_package.py --run-id q01full --skip-prep
.\scripts\py.cmd scripts/47_resource_report.py --runs q00pilot q01pilot q00full q01full `
    --out reports/trial_2026-09-12/resources.json
```

Dati usati: solo materiale già locale — i tre controlli ufficiali e le firme del run
`e001`. Nessun download di dataset, nessun servizio a pagamento, nessuna GPU.
Artefatti leggeri in `reports/trial_2026-09-12/`; previsioni in
`C:/Users/ferra/vcc2026-data/artifacts/`. Ogni run ha un `freeze.json` con commit,
patch delle modifiche non committate, impronte degli input, versioni e seed.

**Nulla è stato caricato.** La quota giornaliera è intatta e non esiste alcun punteggio
di leaderboard.

## 3. Cosa si è osservato

### 3.1 Il contratto, e che cosa non va consegnato

Fonte: pagina *Evaluation*, FAQ e *Rules*, riportate riga per riga in
`docs/SOTTOMISSIONE.md` §1. Le voci che il progetto non aveva scritto da nessuna parte:

- **Codice e pesi non si consegnano.** Solo i finalisti devono fornire una descrizione
  di alto livello che verrà pubblicata: dataset di training, preprocessing e
  costruzione degli input, modelli usati o adattati, architettura dei modelli non
  pubblici, componenti non appresi o mescolati all'output, fasi di training e
  inferenza; il compute è opzionale. «You need not disclose code or model weights»
  (*Rules*, §Finalists). Nessuna scadenza separata: è una condizione per incassare il
  premio, non per sottomettere.
- **Due sottomissioni al giorno**, non una: il giorno cambia a mezzanotte UTC, contano
  solo quelle che arrivano al passo di punteggio, e una squadra può averne **una sola
  in volo** alla volta. `configs/config.yaml` diceva già 2; ora è verificato.
- **Le previsioni devono essere generate soltanto da modelli di machine learning**
  (*Rules*, §Machine Learning Predictions Only), e «the control cells you downloaded
  are model inputs only — do not copy them into your prediction» (*Evaluation*).
  Queste due frasi riguardano direttamente `trial-00-controls`: vedi §4 e D-017.
- Il limite di densità è 4.750.000.000 valori **memorizzati**, e conta anche uno zero
  salvato esplicitamente. La FAQ dà due riferimenti utili: i dati reali stanno intorno
  a 5.800 non-zeri per cellula, e un baseline che predice la media del contesto arriva
  vicino a 11.800, dentro il tetto con circa il 10% di margine.
- Account verificato il 2026-09-12: `can_submit: true`, `blockers: []`. La sottomissione
  è tecnicamente possibile; non è stata fatta.

### 3.2 α non è 0,25, ed è l'ampiezza globale a fare tutto il lavoro

`reports/trial_2026-09-12/calibration_c002.json`, run `c002`. Protocollo annidato:
ciclo interno per selezionare, esterno per riportare; le guide di un bersaglio sono
collassate prima dello split; il bootstrap ricampiona **solo** previsioni fuori
campione. Esperimento di sviluppo esterno K562 genome-wide → RPE1, 2.350 bersagli
condivisi, 6.714 geni condivisi.

| Modello | MSE / MSE del nullo, fuori campione |
|---|---:|
| **selezionato**, α = 0,1974, `prior_sd` = 4 | **0,98991** — IC95 [0,98866, 0,99114] |
| risposta prevista zero (il nullo) | 1,00000 |
| trasferimento a piena ampiezza, α = 1 senza shrinkage | 1,16228 |

α scelto su cinque fold indipendenti: 0,1947 / 0,2006 / 0,1971 / 0,1970 / 0,1975.
Pearson mediana per bersaglio fuori campione 0,0931, IC95 [0,0879, 0,0992]; frazione di
bersagli con Pearson positiva 0,933; accordo di segno sui geni |Δ|≥0,5 pari a 0,5558.
Tempo 27,6 s, picco di memoria 1,79 GiB.

Due cose nuove rispetto a CP-0003:

- **Il valore 0,25 era il punto di griglia più vicino.** La selezione continua dà
  0,1974. La differenza è praticamente irrilevante — sul primo fold α = 0,25 dà 0,98964
  contro 0,98929 — ma il numero da citare è quello misurato.
- **Lo shrinkage per gene è quasi inattivo.** Nella tabella di selezione interna
  `prior_sd` = 4 batte «nessuno shrinkage» (`prior_sd` = 10⁶) di 0,00003 in MSE
  cross-validata: una parità. Con SE mediana 0,175, a `prior_sd` = 4 il peso per gene è
  16/(16+0,03) ≈ 0,998, cioè non tocca nulla. La compressione utile è **tutta**
  nell'ampiezza globale, non nella precisione per gene.

Il confronto completo, con il costo e i limiti dichiarati riga per riga, è in
[`reports/trial_2026-09-12/held_out_comparison.md`](../../reports/trial_2026-09-12/held_out_comparison.md).

### 3.3 Il vincolo compositivo spostava i geni senza evidenza, e ora non più

I conteggi di una cellula sono una composizione: non possono salire tutti. Riscalare
`basale × 2^Δ` a una dimensione di libreria divide via un fattore globale, e quel
fattore cade su **ogni** gene — compresi i 10.852 su 18.533 che `k562_gwps` non misura
e che per D-009 non devono portare alcuna previsione. `compositional_shift` risolve in
forma chiusa lo scalare che conserva la massa totale e lo applica solo ai geni
osservati, così un gene non osservato conserva esattamente la sua quota di
composizione: log2FC realizzato **0**, non −c.

Misurato sul pilot (`reports/trial_2026-09-12/q01pilot_generation_diagnostics.json`):
spostamento mediano 0,0021 log2, massimo 0,0097. Piccolo, ma sistematico nella
direzione e su tutte e 300 le perturbazioni. Test:
`test_unobserved_genes_realise_exactly_zero_log2fc`.

### 3.4 Due previsioni complete, entro le risorse locali

`reports/trial_2026-09-12/resources.json`. Forma ufficiale verificata: 300
perturbazioni × 400 cellule × 3 contesti = 360.000 cellule × 18.533 geni.

| | trial-00-controls | trial-01-transfer |
|---|---:|---:|
| cellule | 360.000 | 360.000 |
| valori memorizzati | 2.084.061.983 | 2.167.562.410 |
| per cellula | 5.789 | 6.021 |
| frazione del tetto di densità | 43,9% | 45,6% |
| massimo memorizzato in una cellula | 8.482 (budget 13.194) | 8.555 (budget 13.194) |
| massimo di conteggi in una cellula | 52.420 (tetto 1.000.000) | 52.823 (tetto 1.000.000) |
| file | 3,93 GiB | 3,97 GiB |
| generazione | 1.221 s (20,4 min) | 1.131 s (18,9 min) |
| tempo totale | 1.249 s | 1.153 s |
| picco di memoria del generatore | 0,41 GiB | 0,48 GiB |
| `indptr` / `indices` CSR | int32 / int32 | **int64** / int32 |

Il pilot aveva previsto bene: 6 perturbazioni × 3 contesti davano 2,088·10⁹ valori
proiettati contro 2,084·10⁹ misurati (−0,2%) e 3,97 GiB proiettati contro 3,93 GiB
(−1,0%). La proiezione del tempo era 25,7 min contro 20,4 misurati, cioè pessimistica
del 26%.

**La densità reale è 5.789 valori per cellula, non 11.800.** Campionare Poisson dal
profilo medio produce cellule con la sparsità di cellule vere — i controlli reali
rilevano 6.147 / 5.756 / 6.006 geni per cellula di mediana in A / B / C — mentre
submettere il profilo medio *stesso* in ogni cellula
lascerebbe non-zeri quasi due terzi dei geni. È la differenza fra il 44% e il 90% del
tetto, e ha una seconda conseguenza in §3.5.

Verifica del contratto ricavata **dal file scritto**, non dal writer che l'ha prodotto
(`scripts/46_validate_package.py`): 18 controlli su 18 superati per entrambi i trial.
Costo: 56–61 s per rileggere i 2,1 miliardi di valori e ricontrollare ogni invariante,
più 114–139 s per la sola verifica di provenienza dei contesti.

### 3.5 `vcc prep` non gira su questa macchina, e non lo avrebbe detto

`vcc prep` carica l'intera matrice in memoria prima di validare qualunque cosa
(`vcc/prep.py`, riga 1104: `adata = read_h5ad(input_path)`), quindi anche `--dry-run`
paga il costo pieno.

Misurato: `ad.read_h5ad` su una previsione pilota costa **8,60 byte per valore
memorizzato** (43.318.618 valori, 0,347 GiB di incremento di working set,
anndata 0.13.3). Per la previsione completa del controllo sono 16,7 GiB per la sola
lettura, su una macchina con **7,81 GiB totali**.

Il modello di dimensionamento della CLI stessa (`vcc/sizing.py`, tarato su 254
esecuzioni di produzione del servizio di scoring) dà il picco di packaging:

| | valori memorizzati | byte per valore | picco `vcc prep` |
|---|---:|---:|---:|
| trial-00-controls | 2.084.061.983 | 8 | **22,19 GiB** |
| trial-01-transfer | 2.167.562.410 | 12 | **33,49 GiB** |

**Tentato, non dedotto.** `vcc prep --dry-run` è stato eseguito su entrambe le
previsioni complete, con un tetto di 900 s. Entrambe falliscono, in fretta e con un
messaggio leggibile — non con un SIGKILL silenzioso — perché numpy solleva
`MemoryError` prima di arrivare a paginare:

| Previsione | Esito | Tempo | Messaggio |
|---|---|---:|---|
| trial-00-controls | exit 1 | 52 s | «Unable to allocate 7.76 GiB for an array with shape (2084061983,) and data type int32» |
| trial-01-transfer | exit 1 | 68 s | «Unable to allocate 8.07 GiB for an array with shape (2167562410,) and data type int32» |

Log completi in `reports/trial_2026-09-12/q00prep_prep_dry_run.log` e
`q01prep_prep_dry_run.log`. Entrambe cadono sul **solo array degli indici**, prima
ancora di arrivare ai dati: 7,76 GiB da allocare su 7,81 GiB di macchina. Il picco
completo di 22–33 GiB non viene nemmeno raggiunto, perché la prima allocazione già non
entra.

Questo è il collo di bottiglia, misurato. Non è di disco — ne restavano 22,05 GiB — e
non è di CPU.

Due dettagli che contano:

- **La CLI non avvisa su Windows.** `sizing.prep_memory_warning` esiste esattamente per
  evitare un SIGKILL senza messaggio, ma dimensiona contro `os.sysconf`, che su Windows
  non esiste: `total_ram_gib()` torna `None` e l'avviso non può scattare. Verificato:
  ritorna `None` per 2,084·10⁹ valori su questa macchina. **L'assenza dell'avviso non è
  un via libera.**
- **La soglia di 2³¹ valori memorizzati cambia il regime.** SciPy indicizza CSR con
  int32 finché può e promuove a int64 sopra 2.147.483.648 valori, quindi il costo per
  valore passa da 8 a 12 byte. trial-00 sta sotto la soglia del 2,95%;
  trial-01, con 2.167.562.410 valori, la **supera**, e infatti il suo
  `indptr` è stato scritto in int64 (§3.6) e il suo costo per valore è 12 byte anziché
  8. La stessa forma di sottomissione, con un modello leggermente più denso, cade
  dall'altra parte di quella soglia: non è una costante del problema.

Nessun limite di convalida è stato aggirato. I due pacchetti `.vcc` **non esistono**:
questa è la parte del lavoro che si ferma qui.

### 3.6 Un difetto silenzioso nel writer di sottomissione, trovato prima di usarlo

`SubmissionWriter.close` scriveva gli offset CSR con `indptr.astype(np.int32)`. Gli
offset arrivano a `nnz`, e una sottomissione completa a densità realistica sta entro il
3% del tetto di int32 (2.147.483.647): trial-00 lo sfiora dal basso con
2.084.061.983, e la previsione proiettata di trial-01 lo **supera**. Oltre la soglia
`astype` non solleva nulla, avvolge in silenzio a offset negativi, e il risultato è un
file che si apre come un h5ad valido e la cui matrice è spazzatura.

Corretto in `src/vcc2026/submission.py` con `indptr_dtype(nnz)`, che scegle la
larghezza dal conteggio. Aggiunti tre test sulla soglia e un controllo diretto nella
verifica del contratto (`csr_offsets_monotonic`, `csr_offsets_non_negative`,
`csr_offsets_match_stored_values`), perché un array di offset avvolto è esattamente il
tipo di errore che va rilevato sul file, non dedotto dall'intenzione del writer.

Il difetto non ha toccato trial-00, generato prima della correzione: il suo `indptr` è
int32 e i tre controlli passano sul file scritto.

### 3.7 L'identità dei contesti è verificabile, e i contesti sono distinguibili

La FAQ ufficiale dice che due contesti scambiati fanno degradare ogni metrica verso il
caso e «looks like a weak model rather than a bug»: la convalida di formato non se ne
accorge. Ogni previsione qui è costruita dai controlli del proprio contesto, quindi il
profilo aggregato di un contesto deve essere più vicino al proprio basale.

Misurato sul file scritto, per trial-00 (`validation.json`, campo
`context_provenance`):

| Etichetta | somiglianza con A | con B | con C | margine |
|---|---:|---:|---:|---:|
| A | **0,9999987** | 0,8988 | 0,8882 | 0,1012 |
| B | 0,8988 | **0,9999986** | 0,9279 | 0,0721 |
| C | 0,8882 | 0,9279 | **0,9999986** | 0,0721 |

Le somiglianze incrociate fra i tre basali (0,888–0,928) dicono che il test è
informativo: se i tre stati basali fossero indistinguibili, uno scambio sarebbe
invisibile anche qui. Test: `test_a_swap_is_detected`.

### 3.8 Il generatore ha un artefatto misurabile anche a effetto previsto zero

Campionare Poisson da un profilo medio non è campionare una cellula: la media su 18.400
cellule ha perso la variazione fra cellule che mette gli zeri in una cellula vera.
Misurato sui blocchi del pilot di trasferimento
(`q01pilot_generation_diagnostics.json`):

| | generato | controlli reali |
|---|---:|---:|
| geni rilevati per cellula (mediana) | 6.522 | 6.147 |
| rapporto, mediana sui blocchi campionati | **1,041** (min 1,021, max 1,063) | — |
| CV della dimensione di libreria | 0,443 | 0,438 |
| CV dei geni rilevati | 0,199 | 0,199 |

Il rapporto è **1,061 sul blocco di `ABCD1`, che è un bersaglio non coperto e ha
dunque effetto previsto esattamente zero**: l'artefatto esiste prima di qualunque
previsione. I due CV invece coincidono, perché le dimensioni di libreria sono
ricampionate da quelle reali. Per trial-00 il rapporto è 0,997, come deve essere: quelle
cellule sono reali.

Grandezza da confrontare: dopo la calibrazione il log2FC efficace mediano sui geni
supportati è **0,0246**, cioè un cambiamento di espressione dell'1,7%; il massimo su un
singolo gene arriva a 0,776 log2, cioè 1,71×. Un artefatto di rilevazione del 4–6% e un
effetto biologico mediano dell'1,7% sono quantità diverse e non si sommano, ma sono
dello stesso ordine, e questo è il motivo per cui il punteggio di trial-01 **non è
prevedibile** da queste misure.

### 3.9 Supporto e ricadute del fallback

`k562_gwps` copre **272 dei 300 bersagli** del pannello e **7.681 dei 18.533 geni**. I
28 bersagli scoperti e i 10.852 geni fuori dall'universo della sorgente ricevono una
previsione di nessun effetto, registrata come **fallback** e non come nullo misurato
(D-009). La maschera di supporto vive in `generation_diagnostics.json`, campo
`support`, mai nella matrice sottomessa.

La provenienza delle cellule di trial-00 — quale cellula di controllo ha prodotto quale
riga — vive in `provenance_<contesto>.npz`, 300 × 400 interi per contesto, fuori dalla
matrice: il formato non ha un posto per quell'informazione e inventare una colonna
`obs` violerebbe il contratto. Verificato: nessuna perturbazione riusa la stessa
cellula due volte, e ogni cellula di controllo è riusata una mediana di 6 volte
(intervallo 0–18) fra le 300 perturbazioni.

### 3.10 Risorse della macchina, rimisurate

| | Valore | Quando |
|---|---|---|
| RAM totale | 7,81 GiB | 2026-09-12 |
| RAM disponibile | 0,28–1,58 GiB, oscillante | durante i run |
| Disco libero | 33,25 → 23,65 GiB | prima e dopo le due generazioni |
| CPU | Intel i7-10510U, 8 thread | — |
| GPU CUDA | assente | — |
| backend DE risolto | `scanpy` (`pdex` e `torch` assenti) | D-014 |

Il disco è calato di 5,5 GiB fra due misure a inizio sessione **senza** che il progetto
avesse scritto niente di quella taglia: va rimisurato prima di ogni job, non dedotto da
un documento.

## 4. Interpretazione e incertezza

**Misura.** Tutto il §3 è ricalcolabile con i comandi del §2. Ogni numero ha un file di
evidenza in `reports/trial_2026-09-12/`.

**Misura.** Il percorso locale funziona end-to-end fino al packaging: freeze,
calibrazione, generazione completa per A/B/C, verifica del contratto sul file scritto,
verifica della provenienza dei contesti. Due previsioni complete esistono e passano 18
controlli su 18.

**Il limite, ed è duro.** `vcc prep` — l'unica autorità sul formato — non gira qui.
Serve una macchina con abbastanza RAM: almeno **32 GiB** per trial-00 e **48 GiB** per
trial-01 con margine, secondo il modello della CLI stessa. Non è un limite di disco né
di CPU; è di memoria, e nasce dal fatto che `prep` tiene la matrice residente.

**Interpretazione, non misura.** Che ridurre la densità per far entrare `prep` sia una
cattiva idea. L'argomento: scendere ai circa 1.150 valori per cellula che entrerebbero
in 7,81 GiB renderebbe le cellule quattro volte più sparse dei dati reali, e quattro
delle sei metriche dipendono da chiamate DE su quella distribuzione. Non abbiamo
misurato di quanto cambierebbero. D-016 sceglie di dichiarare il collo di bottiglia
invece di falsare il modello.

**Ipotesi, non misura.** Che α = 0,1974 e `prior_sd` = 4 valgano per A, B e C. Stimati
su K562 e RPE1; nei contesti ufficiali nessuna perturbazione è osservabile, quindi la
scelta **non è verificabile localmente**. Ciò che trasferisce è il protocollo (D-012),
non il numero.

**Ipotesi, non misura.** Che una riduzione dell'1,01% di MSE pseudobulk corrisponda a
un qualunque punteggio VCC. Le sei metriche ufficiali sono riscalate contro la media
del contesto e un replicato reale, quattro dipendono da chiamate DE su conteggi a
singola cellula, e le ancore `b` e `r` restano ignote. **Nessuna conversione fra i due
mondi è stata misurata, e non va inventata.**

**Ipotesi, non misura.** Che trial-01 batta trial-00 sul punteggio ufficiale. L'effetto
mediano previsto (1,7%) e l'artefatto di rilevazione del generatore (4–6%) sono dello
stesso ordine: quale domina le quattro metriche DE dipende da come lo scorer aggrega, e
non è stato misurato. È una ragione per non aspettarsi molto, non una previsione.

**Rischio di regole, non risolto.** `trial-00-controls` ricampiona le cellule di
controllo reali. `vcc prep` lo accetterebbe, ma le regole dicono che i controlli sono
soltanto input del modello e che le previsioni devono essere generate soltanto da
modelli di machine learning. Un ricampionamento non è la previsione di un modello.
D-017 lo tiene come controllo operativo e vieta di inviarlo finché la questione non è
chiarita. Il trial resta utile per una ragione precisa: le sue cellule sono reali,
quindi è l'unico riferimento di dispersione corretto che abbiamo.

**Il nullo non è battuto di molto, ed è un risultato valido.** α ottimo intorno a 0,2
con un guadagno dell'1% significa che il trasferimento, compresso, non fa danno e
aggiunge quasi niente. La lettura sbagliata sarebbe «il trasferimento funziona».
trial-01 va conservato come test operativo ed etichettato così.

## 5. Spiegazione semplice

Immagina di dover consegnare 360.000 schede compilate, in un formato che un
controllore automatico verifica riga per riga. Abbiamo fatto tre cose.

Primo, abbiamo letto il regolamento fino in fondo e scoperto due cose che non
sapevamo: le consegne sono due al giorno e non una, e **il codice non va consegnato** —
solo chi arriva in finale deve scrivere una relazione su come ha fatto.

Secondo, abbiamo compilato le schede in due modi. Nel primo abbiamo copiato schede
vere di cellule non toccate, cambiando solo l'etichetta: serve a provare che la
macchina da consegna funziona, non a indovinare qualcosa. Nel secondo abbiamo applicato
la previsione del modello, ridotta a un quinto della sua ampiezza, perché misurando si
vede che copiarla intera sbaglia più che non dire niente.

Terzo, siamo arrivati allo sportello e non siamo entrati. Il programma ufficiale che
sigilla il pacco carica tutte le 360.000 schede in memoria in una volta: gli servono
circa 22 gigabyte, e questo computer ne ha 7,8. Le schede ci sono, sono state
controllate una per una con un lettore che ne guarda un pezzo alla volta, e il pacco
non è sigillato. Non abbiamo reso le schede più povere per farle entrare: sarebbe stato
come rimpicciolire il carico per far stare il camion in garage.

Una cosa che ci è andata bene per caso, e che è il pezzo più istruttivo: il contatore
degli indirizzi interni al file era un numero a 32 bit, e una consegna completa arriva
al 97% del suo massimo. Un filo più densa e quel contatore sarebbe andato in negativo
senza dire nulla, producendo un file che si apre benissimo e contiene spazzatura.

## 6. Conseguenze

- `docs/DECISIONI.md`: tre decisioni nuove — **D-015** (il vincolo compositivo si
  assorbe sui geni supportati), **D-016** (non si riduce la densità per far entrare
  `vcc prep`), **D-017** (trial-00 non si invia finché la conformità alle regole non è
  chiarita). Aggiornate D-006 e D-012 con α = 0,1974 e con il protocollo annidato.
- `docs/SOTTOMISSIONE.md`: nuovo. Contratto verificato, comandi esatti per rigenerare,
  convalidare, inviare e leggere i punteggi, e la distinzione fra punteggi normalizzati
  e metriche locali.
- `docs/ESECUZIONE_REMOTA.md`: al profilo minimo remoto si aggiunge un lavoro nuovo —
  **il packaging `.vcc`**, che è un vincolo di RAM (32–48 GiB) e non di CPU né di rete.
- `docs/REGISTRO.md`: nuove voci per `docs/SOTTOMISSIONE.md`,
  `reports/trial_2026-09-12/`, `configs/trials.yaml`, i tre moduli e i cinque script
  nuovi; scheda [R-011](../REGISTRO.md#r-011--reportstrial_2026-09-12). Aggiunta
  l'affermazione 6 alla scheda [R-001](../REGISTRO.md#r-001--readmemd), vedi §7.
- `docs/PROGETTO.md`: lo stato passa da «nessuna sottomissione» a «due previsioni
  complete generate e verificate localmente, packaging ufficiale bloccato dalla RAM».
- Il collo di bottiglia predittivo **non** è cambiato: senza cellule perturbate reali
  non esiste un punteggio VCC. Se ne è aggiunto uno operativo, e ha un numero.

## 7. Cosa corregge

Non corregge nessun checkpoint. Corregge **tre affermazioni** in materiale vivo.

1. **L'α di trasferimento.** CP-0003 §3.4 riporta 0,25 per K562 → RPE1. Il valore è il
   punto di griglia più vicino all'ottimo; la selezione continua dà 0,1974. CP-0003
   resta leggibile com'è — era vero della griglia che usava, e il suo α oracolo di
   0,216 andava già nella direzione giusta. D-006 e D-012 sono aggiornate.
2. **L'intervallo di confidenza di CP-0003.** Lo stadio 41 calcolava il bootstrap su
   **tutti** i bersagli usando i parametri che i fold avevano già scelto: l'intervallo
   descriveva i dati di training. Qui il bootstrap ricampiona solo previsioni fuori
   campione. I due intervalli si somigliano ([0,0891, 0,0997] contro
   [0,0879, 0,0992]), quindi la conclusione non cambia — ma solo il secondo è onesto.
3. **«Streaming submission writer verified against official `prep`»**, in
   `README.md` §Plan, fase 0, e la sua eco nella tabella di pulizia del registro
   («già superata dal fatto che `vcc prep` ha validato»). **Non esiste alcun log di
   `vcc prep` anteriore a oggi**, e l'unico artefatto candidato, `smoke.h5ad`, ha 3
   perturbazioni su 300. Misurato oggi: `vcc prep` con le opzioni predefinite rifiuta
   un file che non predice esattamente le 300 perturbazioni ufficiali per contesto.
   Resta possibile che sia stato eseguito con `--no-verify-targets`; in quel caso
   avrebbe verificato asse genico, contesti, conteggi per perturbazione e conteggi
   grezzi, ma non la lista delle perturbazioni. L'affermazione sostenuta è «il writer
   produce un h5ad strutturalmente valido», da `scripts/02_smoke_test_submission.py`.
   Aggiunta come affermazione 6 alla scheda R-001; il testo originale resta.

Conferma esplicitamente, senza modificarle: le coperture misurate, i clamp dello
scorer, i vincoli hardware, la distinzione fra pseudobulk e valutazione a singola
cellula, e il fatto che **nessuna sottomissione sia stata inviata e nessun punteggio di
leaderboard esista**.

## 8. Domanda di comprensione

Il pacchetto `trial-00-controls` passa 18 controlli di contratto su 18 e la verifica di
provenienza dei contesti. Un collega conclude che è pronto da inviare e che, essendo
fatto di cellule reali, dovrebbe prendere un punteggio decente. Quali due cose
distinte gli mostri — una sulle regole e una su che cosa la convalida di formato non
dice — e perché la seconda vale anche per `trial-01-transfer`?
