# CP-0005 — Packaging in memoria limitata: parità con `vcc prep` e `.vcc` di trial-01

- **Data:** 2026-09-13
- **Tipo:** osservazione
- **Redatto da:** agente (Claude Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

[CP-0004](0004-primo-trial-locale-e-pacchetti.md) §3.5 ha misurato che `vcc prep`
non gira su questa macchina: carica l'intera matrice prima di validare qualunque
cosa e fallisce con «Unable to allocate 8.07 GiB» su 7,81 GiB totali. Ne
concludeva che serviva una macchina da 48 GiB.

La domanda di oggi: **la memoria è davvero necessaria, o è solo il modo in cui la
CLI è scritta?** E se si può impacchettare a memoria limitata, si riesce a farlo
senza indebolire una sola delle convalide ufficiali?

## 2. Cosa è stato fatto

**Inventario dell'implementazione ufficiale.** Lette riga per riga `vcc/prep.py`
(1.458 righe), `vcc/vccfile.py` e `vcc/sizing.py` della versione installata,
`vcc-cli` 0.2.0. Separate le convalide che lavorano su metadati piccoli (obs, var,
liste ufficiali) da quelle che devono toccare ogni valore memorizzato. Sondato
empiricamente che cosa `prep` **scrive**, con un fixture minimo, invece di dedurlo
dal codice.

**Implementazione.** `src/vcc2026/packaging.py`: convalida a blocchi di righe e
scrittura del `.vcc` senza mai materializzare la matrice. Le convalide sui metadati
**sono quelle ufficiali**, chiamate direttamente — `read_gene_list`,
`read_pert_counts`, `validate_contexts`, `validate_targets`,
`_report_target_mismatch`, `_report_cell_count_mismatch`, `_gene_mismatch_message`,
`_has_fractional_values`, `sizing.too_dense_message` — su un oggetto che espone il
solo `.obs` che quelle funzioni leggono. Nuovo stadio
`scripts/48_package_prediction.py`.

**Parità.** `tests/test_packaging_parity.py`: 41 test, fixture a **forma
ufficiale completa** — 300 perturbazioni × 400 cellule × 3 contesti, 18.533 geni,
i veri `gene_names.csv` e `pert_counts.csv`, tutti i limiti attivi — con densità
sintetica (un valore per cellula) per farle costare secondi. Per ogni regola un
fixture che la viola, e l'asserzione che **entrambe** le implementazioni lo
rifiutino: un rifiuto solo nostro bloccherebbe una sottomissione valida, uno solo
di `prep` ne spedirebbe una invalida.

```powershell
.\scripts\py.cmd -m unittest tests.test_packaging_parity          # 41 test, 98 s
.\scripts\py.cmd scripts/48_package_prediction.py --run-id k01pack `
    --prediction C:\Users\ferra\vcc2026-data\artifacts\q01full\prediction.h5ad `
    --expect-sha256 1b7e15f49104bdb9360eb22bd69574caf3dbf8ff9de3f27991e207850dc091e2
.\scripts\py.cmd -m unittest discover -s tests                    # 149 test, 96 s
```

Evidenza: [`reports/trial_2026-09-13/k01pack_packaging.json`](../../reports/trial_2026-09-13/k01pack_packaging.json).
**Nulla è stato caricato.**

## 3. Cosa si è osservato

### 3.1 Il `.vcc` di trial-01 esiste, e il picco è 0,52 GiB

| | Valore |
|---|---|
| input | 360.000 × 18.533, 2.167.562.410 valori memorizzati, 3,97 GiB |
| sha256 dell'input, verificato prima e dopo | `1b7e15f4…c091e2`, **invariato** |
| archivio | `prediction.vcc`, 4.203.520.000 byte (3,91 GiB) |
| sha256 dell'archivio | `681b0aac…a1a2a6` |
| `meta.json` | `{"schema":1,"nnz":2167562410,"n_obs":360000,"n_vars":18533,"cli_version":"0.2.0"}` |
| **picco di memoria (working set)** | **0,519 GiB** |
| picco di disco transitorio | 7,88 GiB |
| convalida | 156 s |
| packaging | 756 s |
| verifica | 216 s |
| totale | 1.005 s (16,8 min) |

Il modello di dimensionamento della CLI stessa dà **33,49 GiB** di picco per questo
file. Misurato: **0,519 GiB**, cioè un sessantaquattresimo. La macchina ne ha 7,81
totali e ne aveva 0,97 disponibili quando il run è partito.

**Il vincolo non era la RAM del problema, era la RAM di una riga di codice.**
`vcc/prep.py` riga 1104, `adata = read_h5ad(input_path)`, prima di ogni convalida.

### 3.2 Ventiquattro controlli su ventiquattro, nessuno indebolito

Sedici controlli di contratto e otto di integrità CSR, tutti passati:

| Gruppo | Controlli |
|---|---|
| asse genico | unicità dei nomi, ordine identico a `gene_names.csv`, dimensione 18.533 |
| obs | cellule presenti, tetto di 400.000 cellule, colonna delle perturbazioni, **nessuna riga di controllo** |
| contesti | A/B/C completi, nessuna etichetta sconosciuta, nessun contesto vuoto |
| bersagli | insieme esatto per contesto, **esattamente 400 cellule** per bersaglio e contesto |
| matrice | densità sotto il tetto, indici di colonna in intervallo, valori finiti, non negativi, interi, tetto di conteggi per cellula, nessuna perturbazione tutta a zero |
| CSR | lunghezza di `indptr`, inizio a zero, non negatività, monotonia, coerenza con la lunghezza dei dati, `data` e `indices` della stessa lunghezza, `nnz` rappresentabile nel dtype di `indptr`, `n_vars` rappresentabile in quello di `indices` |

Gli otto controlli CSR **non esistono in `vcc prep`**, che lascia ricostruire la
matrice a scipy e eredita ciò che scipy accetta. Servono qui perché questo
packager *copia* gli array invece di ricostruirli: un array di offset corrotto
verrebbe portato nell'archivio intatto. È lo stesso difetto che CP-0004 §3.6 ha
trovato nel writer, visto dall'altra parte.

Misurato sul file reale: valore minimo 0,0, massimo 411,0, massimo totale per
cellula 52.823 (tetto 1.000.000), 120.000 cellule e 300 bersagli per ciascun
contesto.

### 3.3 Che cosa è preservato, e l'unica cosa che cambia

Verificato rileggendo l'archivio e confrontandolo **con l'input**, non con una
seconda derivazione del payload — confrontare con una ri-derivazione metterebbe alla
prova lo scrittore contro sé stesso:

- `X/data`, `X/indices`, `X/indptr`: **identici bit a bit**, dtype compresi.
- asse genico: identico.
- `obs['target_gene']` e `obs['context']`: identici, cellula per cellula.
- **`obs` index: sostituito con `'0'..'359999'`.**

Quest'ultima è l'unica trasformazione, ed è quella che `vcc prep` applica: il suo
`new_obs` usa `index=np.arange(n_cells).astype(str)`. Il nome originale della
cellula non entra in un `.vcc`, né dal nostro percorso né dal suo. Le altre
trasformazioni documentate — obs ridotta a due colonne, var ridotta all'indice,
`layers`/`obsm`/`varm`/`obsp`/`varp`/`uns`/`raw` scartati — sul nostro file non
tolgono nulla, perché il file non ha altro.

`payload_transformations()` restituisce l'elenco come dati, non come prosa, così un
report non può dichiarare "lossless" mentre una trasformazione resta taciuta.

### 3.4 Una divergenza di codifica, trovata sondando invece di assumendo

Il primo payload scritto aveva `obs/target_gene` codificato
`nullable-string-array`, mentre quello ufficiale lo codifica `categorical`. Le
etichette si rileggono identiche in entrambi i casi, quindi **nessun confronto sui
valori lo avrebbe visto**.

La causa: `prep` passa i suoi DataFrame a `ad.AnnData(...)`, e il costruttore di
AnnData converte le colonne di stringhe in categoriche. Scrivendoli direttamente
con `write_elem` quel passaggio non avviene. Corretto facendo girare la
sanitizzazione vera di anndata su una AnnData con matrice a zero colonne, invece di
reimplementarne l'euristica. Due test nuovi confrontano ora **le codifiche e i
dtype HDF5** elemento per elemento fra il nostro payload e quello ufficiale.

### 3.5 Due cose imparate sul comportamento ufficiale

- **La regola "nessuna perturbazione tutta a zero" è globale, non per contesto.**
  Un fixture che azzerava un bersaglio nel solo contesto A è stato **accettato** da
  `vcc prep`: il controllo somma le cellule di quel bersaglio su tutta la matrice.
  Scoperto perché il test di rifiuto è fallito dalla parte di `prep`, non dalla
  nostra. Ora ci sono due test: uno che azzera il bersaglio in tutti e tre i
  contesti e deve essere rifiutato da entrambi, e uno che lo azzera in un contesto
  solo e deve essere **accettato** da entrambi — è una forma di previsione reale, e
  rifiutarla bloccherebbe una sottomissione valida.
- **Il tetto di conteggi per cellula è stretto (`>`).** Una cellula esattamente a
  1.000.000 è legale. Verificato che entrambe le implementazioni la accettino.

### 3.6 Un difetto nel nostro validatore, trovato dai test di parità

Con la colonna `context` assente, `validate_contexts` ufficiale solleva e `prep` si
ferma lì. Il nostro report continua di proposito, per mostrare tutti i fallimenti
insieme — e arrivava a `validate_targets`, che raggruppa per quella colonna e
moriva con `KeyError` invece di produrre un fallimento. Corretto: il controllo dei
bersagli si salta dichiarandolo, e qualunque eccezione imprevista di un validatore
diventa un fallimento, perché «il controllo non ha potuto girare» è di per sé una
ragione per non impacchettare.

### 3.7 I difetti di consegna di CP-0004, corretti

- `scripts/46_validate_package.py` ora **esce con codice diverso da zero** quando un
  controllo fallisce, e **non impacchetta** se il contratto o la provenienza dei
  contesti falliscono. Prima usciva 0 comunque: uno script chiamante non poteva
  accorgersi di niente.
- Ogni tentativo scrive in percorsi unici — `validation_<AAAAMMGGTHHMMSSZ>.json` e i
  log con lo stesso suffisso — quindi una riesecuzione non collide con l'evidenza
  della precedente. `--attempt` sceglie l'etichetta.
- `docs/SOTTOMISSIONE.md` non indica più `c002` nel comando che rigenera tutto: il
  passo 3 punta allo stato fittato **del run appena calibrato**. Puntare a un run
  precedente produrrebbe una previsione che non corrisponde alla calibrazione
  eseguita, e i due file hanno la stessa forma.
- `snapshot_source()` archivia il **codice**, non i suoi hash. Un freeze i cui
  moduli non tracciati esistono solo come sha256 identifica codice che nessuno può
  recuperare, e una patch contro HEAD non può contenere un file che git non ha mai
  visto. Lo stadio 43 scrive ora `source_snapshot.tar.gz` accanto al freeze.

### 3.8 Il percorso remoto resta pronto, e non serve

`notebooks/kaggle_package_trial01.ipynb` esegue **la stessa implementazione** su un
runtime Kaggle CPU: misura RAM e mount prima di decidere i percorsi, riverifica lo
sha256 dopo il trasferimento, installa `vcc-cli==0.2.0`, **rigira i test di parità
su quella macchina** prima di produrre qualcosa, tiene i transitori in
`/kaggle/temp` e solo il `.vcc` in `/kaggle/working` — perché il filesystem da circa
un terabyte e il tetto di output salvato da 19,5 GiB sono numeri diversi e solo il
secondo limita ciò che sopravvive alla sessione.

Non è stato eseguito, perché il run locale è riuscito. Resta per il set finale
D/E/F, che sarà un packaging della stessa taglia.

## 4. Interpretazione e incertezza

**Misura.** Il `.vcc` di trial-01 esiste, è valido secondo il validatore ufficiale
del contenitore, e il suo payload porta la matrice dell'input bit a bit. Il picco di
memoria è 0,519 GiB contro i 33,49 del modello ufficiale.

**Correzione a CP-0004.** «Serve una macchina con almeno 48 GiB di RAM» era una
conclusione corretta *su `vcc prep`* e sbagliata *sul problema*. Il file non è
troppo denso — sta al 45,6% del tetto ufficiale — è solo troppo grande per essere
letto tutto insieme. Dettagli in §7.

**Interpretazione.** La parità è forte ma ha un confine preciso: vale **per gli
input che questo packager accetta**. Matrice densa, CSC, dtype diverso da float32,
geni fuori ordine, percorso log-normalizzato, colonna di tipo cellulare: rifiutati
esplicitamente, con il motivo e con `vcc prep` indicato come lo strumento che li
gestisce. Un packager che li approssimasse in silenzio sarebbe peggio di uno che si
ferma.

**Limite dei fixture.** Sono a forma ufficiale completa ma a densità sintetica: un
valore memorizzato per cellula contro i circa 6.000 reali. La densità è l'unica
proprietà che i test di parità non esercitano, ed è esercitata dal controllo sul
tetto e dal run reale.

**Non stabilito, e va detto ogni volta.** *L'accettazione da parte del server.*
Nessuna sottomissione è stata inviata. Il servizio di scoring applica i propri
controlli, e solo una sottomissione valutata dimostra che accetta questo artefatto.
Un archivio valido è un'affermazione sul **formato**: non dice nulla sulla qualità
predittiva, che resta quella misurata in CP-0004 — una riduzione dell'1,01% di MSE
pseudobulk rispetto al nullo, in un esperimento su K562 e RPE1.

**Ipotesi, non misura.** Che il picco di 0,52 GiB si mantenga su un file più denso.
Il picco è governato da `VALUES_PER_BLOCK` e non dalla dimensione della matrice, ma
è stato misurato su una densità sola.

## 5. Spiegazione semplice

Ieri il pacco non si chiudeva. Il programma ufficiale che lo sigilla vuole prima
appoggiare tutto il contenuto sul tavolo, e il tavolo è di 7,8 gigabyte mentre il
contenuto ne vuole 33. La conclusione di ieri era: serve un tavolo più grande.

Oggi si è guardato che cosa il programma fa davvero, e si è visto che appoggiare
tutto sul tavolo non serve a niente: i controlli si possono fare una manciata di
righe alla volta, e il contenuto si può travasare da una scatola all'altra senza mai
tirarlo fuori tutto. Il pacco si è chiuso usando mezzo gigabyte.

La parte delicata non era travasare, era **non barare**. Il pacco deve superare gli
stessi controlli, tutti. Così i controlli sui metadati sono letteralmente le
funzioni del programma ufficiale, chiamate da noi; e per ciascuna regola c'è un
pacco fatto apposta per violarla, con la verifica che **entrambi** i programmi lo
rifiutino. Se solo noi rifiutassimo, blocceremmo una consegna buona; se solo loro,
ne spediremmo una rotta.

Due cose sono venute fuori da quel confronto. Una: il nostro pacco scriveva
l'etichetta con un inchiostro diverso — stesse parole, codifica diversa — e nessun
confronto sulle parole se ne sarebbe accorto. Due: la regola «nessuna perturbazione
completamente vuota» guarda tutta la spedizione, non un contesto per volta; lo
sappiamo perché il programma ufficiale ha **accettato** un pacco che noi credevamo
invalido.

Quello che ancora non sappiamo è se l'ufficio postale accetterà il pacco. Non gliene
abbiamo spedito nessuno.

## 6. Conseguenze

- `docs/DECISIONI.md`: **D-016 riaperta e sostituita da D-018** — non si riduce la
  densità, e non serve più nemmeno una macchina più grande: si impacchetta a memoria
  limitata. **D-019**: la parità con `vcc prep` si dimostra con fixture a forma
  ufficiale completa e test di rifiuto bilaterali, non per ispezione del codice.
- `docs/PROGETTO.md`: il packaging esce da «bloccato» ed entra in «fatto, verificato
  localmente». Resta bloccata la sottomissione, per autorizzazione e per la
  questione di regole di D-017.
- `docs/ESECUZIONE_REMOTA.md`: il packaging esce dalla tabella dei lavori che
  richiedono una macchina remota. Kaggle resta documentato come percorso pronto.
- `docs/SOTTOMISSIONE.md`: comandi aggiornati; il passo di packaging ora esiste.
- `docs/REGISTRO.md`: voci nuove per `src/vcc2026/packaging.py`,
  `scripts/48_package_prediction.py`, `tests/test_packaging_parity.py`,
  `notebooks/kaggle_package_trial01.ipynb` e `reports/trial_2026-09-13/`.
- Il collo di bottiglia **predittivo** non è cambiato: senza cellule perturbate
  reali non esiste un punteggio VCC. Quello **operativo** è chiuso.

## 7. Cosa corregge

Corregge **una conclusione di [CP-0004](0004-primo-trial-locale-e-pacchetti.md)**,
e conferma i suoi dati.

**CP-0004 §3.5 e §4 concludono che il packaging richiede una macchina con 32–48 GiB
di RAM.** La misura su cui poggiava è corretta e resta valida: `vcc prep` **fallisce
davvero** su questa macchina, con l'errore registrato, e il modello di
dimensionamento della CLI **dà davvero** 33,49 GiB. Sbagliato è il passaggio da lì a
«serve una macchina più grande»: è una proprietà di come `prep` è scritto, non del
problema. Misurato oggi: 0,519 GiB di picco, sulla stessa macchina, sullo stesso
file, con le stesse convalide.

CP-0004 resta leggibile com'è — era vero di ciò che aveva provato. La colonna
"Corretto da" dell'indice rimanda qui. Le decisioni sono documenti vivi: D-016 è
sostituita.

Conferma esplicitamente, senza modificarle: la forma e il contenuto della previsione
di trial-01 (360.000 × 18.533, 2.167.562.410 valori, sha256 invariato), i 18
controlli di contratto di CP-0004 §3.4, la provenienza dei contesti, il difetto
int32 degli offset CSR e la sua correzione, e il fatto che **nessuna sottomissione
sia stata inviata e nessun punteggio di leaderboard esista**.

## 8. Domanda di comprensione

I test di parità confrontano il nostro payload con quello ufficiale leggendo
entrambi e verificando che matrice, geni ed etichette coincidano. Quel confronto è
passato anche mentre il nostro payload scriveva le etichette con una codifica HDF5
diversa da quella ufficiale. Che cosa rende quel confronto insufficiente, e perché
il controllo che l'ha scoperto non poteva essere un confronto sui valori?
