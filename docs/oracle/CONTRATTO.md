# Contratto dell'oracolo di confronto pairwise sulla loss

**Versione del contratto:** 0.2.1
**Verificatore:** `oracle.pairwise_loss`
**Stato:** prototipo. Non valuta ipotesi biologiche.

Questo documento è l'autorità sulle formule, sulle soglie e sulla
mappatura degli esiti. Il JSON candidato è un dato **non fidato**:
non può modificare nulla di ciò che è scritto qui. Le soglie e le
tolleranze arrivano solo dalla configurazione dell'operatore.

Nessun modello linguistico interviene durante la verifica. Il
verificatore ricalcola da un CSV e confronta il ricalcolo con
un'affermazione numerica.

## 1. Cosa verifica, e cosa non verifica

Verifica un'unica affermazione:

> Sui casi contenuti nel CSV, con pesi uguali, la media aritmetica
> della loss del modello A, quella del modello B, e la differenza
> media `mean(loss_a − loss_b)` coincidono con i valori dichiarati,
> e la conclusione dichiarata coincide con quella derivata da quei
> valori e dalla soglia di equivalenza dell'operatore.

Una conclusione `A_lower` significa solo: **A ha una loss media
inferiore nei casi forniti, oltre la soglia di equivalenza**.

Non significa:

- A generalizza meglio;
- A è statisticamente superiore;
- A è biologicamente più corretto;
- il protocollo di valutazione è valido.

La prima versione non esegue test statistici, non pesa i casi, non
valuta il protocollo, non legge dati originali della gara, e non
parla con l'orchestratore multiagente.

## 2. Ingressi

Tre ingressi distinti. Solo il terzo è fidato.

| Ingresso | Fidato | Ruolo |
|---|---|---|
| CSV dei casi | come misura da ricalcolare, non come verità biologica | dati |
| JSON candidato | no | affermazione da verificare |
| JSON di configurazione dell'operatore | sì | tolleranze, soglia, regole |

Il CSV non viene modificato. Il candidato non viene eseguito come
codice. Non ci sono chiamate di rete.

### 2.1 CSV

Codifica UTF-8, virgola come separatore, punto come separatore
decimale. Intestazione obbligatoria. Colonne obbligatorie, in
qualsiasi ordine:

```
case_id,loss_a,loss_b
```

Colonne extra: ignorate. Una loss inferiore è migliore. Ogni riga è
un caso e pesa `1/n`.

Regole strutturali, tutte obbligatorie, nessuna riga scartata in
silenzio:

1. Il file è leggibile, ha l'intestazione, ha almeno una riga di dati.
2. I nomi delle colonne, dopo il trim, sono non vuoti e **univoci**.
   Un'intestazione con `loss_a` ripetuta è un `error`, non una
   lettura dell'ultima colonna omonima.
3. Ogni `case_id` è non vuoto dopo il trim e univoco nel file.
4. `loss_a` e `loss_b` sono numeri decimali finiti. Sono rifiutati:
   cella vuota, `NaN`, `Infinity`, `-Infinity`, testo non numerico,
   e il punto-e-virgola o la virgola come separatore decimale.
   I limiti di dimensione del §3.0 si applicano **prima** di
   costruire il valore.
5. Un'eccezione del parser CSV (`csv.Error`), in intestazione o
   nei dati — per esempio un campo più lungo del limite interno
   del parser — è `csv_readable: error`. Non si alza quel limite
   per aggirare l'errore, non si ricalcola.

### 2.2 JSON candidato

Oggetto JSON. Campi letti, e solo quelli:

| Campo | Tipo | Significato |
|---|---|---|
| `mean_loss_a` | numero JSON | media dichiarata della loss di A |
| `mean_loss_b` | numero JSON | media dichiarata della loss di B |
| `mean_difference` | numero JSON | differenza media dichiarata, `mean(loss_a − loss_b)` |
| `conclusion` | stringa | `A_lower`, `B_lower` oppure `equivalent_within_tolerance` |
| `claim_type` | stringa, opzionale | se presente deve essere `pairwise_loss_comparison` |

Un numero JSON (`0.2`, `3.0e-1`) è accettato. Una stringa, anche
se il contenuto è un decimale (`"0.2"`), è un errore di tipo:
`candidate_readable: error`. Booleani e costanti non finite
(`true`, `NaN`, `Infinity`) sono errori di tipo o di finitezza.
Il token originale del numero JSON è conservato come testo fino
ai controlli del §3.0: non viene convertito in float.

Qualunque altra chiave è ignorata. In particolare sono **chiavi di
autorità** e non hanno effetto, anche se presenti:

`abs_tol`, `rel_tol`, `tolerance`, `equivalence_threshold`,
`threshold`, `tau`, `formula`, `weights`, `n_cases`, `config`,
`operator_config`, `rules`.

Il candidato non può cambiare formule, soglie o regole. Un tentativo
resta visibile nel report (`ignored_candidate_fields`) e non sposta
l'esito da solo: l'esito dipende dal ricalcolo con la configurazione
dell'operatore.

### 2.3 Configurazione dell'operatore

| Campo | Vincolo | Predefinito |
|---|---|---|
| `abs_tol` | numero JSON finito ≥ 0 | `1e-12` |
| `rel_tol` | numero JSON finito ≥ 0 | `0` |
| `equivalence_threshold` | numero JSON finito ≥ 0 | `0.01` |

La stessa distinzione del §2.2: una stringa (`"1e-12"`) non è un
numero JSON e rende `operator_config` un `error`.

Chiavi sconosciute: errore di configurazione. Chiavi assenti: valore
predefinito. Il file, se indicato, è dell'operatore; il candidato
non lo sostituisce.

## 3. Formule

Sia `n ≥ 1` il numero di righe di dati. Indice `i = 1 … n`.
Aritmetica razionale esatta (`fractions.Fraction`). I confronti
con `abs_tol`, `rel_tol` e `equivalence_threshold` usano le stesse
frazioni. L'arrotondamento decimale è **solo** per il report (§3.3)
e non entra nel verdetto.

### 3.0 Limiti di dimensione, prima della costruzione

Un token numerico (cella CSV o numero JSON, non una stringa JSON)
è rifiutato **prima** di costruire una `Fraction` se viola uno di
questi limiti:

| Limite | Valore |
|---|---|
| caratteri del token dopo il trim | 80 |
| valore assoluto dell'esponente (notazione `e`) | 24 |
| cifre significative | 24 |

`1e1000000` è un `error` (esponente). Un intero con migliaia di
cifre è un `error` (lunghezza del token). Non si costruisce il
valore e non si formatta una stringa decimale enorme.

### 3.1 Medie e differenza

Media di A:

```
mean_a = (1/n) * Σ loss_a[i]
```

Media di B:

```
mean_b = (1/n) * Σ loss_b[i]
```

Differenza media, segno esplicito **A meno B**:

```
delta = (1/n) * Σ (loss_a[i] − loss_b[i])
```

Per linearità, `delta = mean_a − mean_b` vale **esattamente** sulle
frazioni. Il verificatore calcola entrambe; una divergenza è un
errore interno, non un `fail` del candidato.

Interpretazione del segno:

- `delta < 0` → la loss media di A è inferiore a quella di B;
- `delta > 0` → la loss media di B è inferiore a quella di A;
- `delta = 0` → le due medie coincidono.

### 3.2 Confronto dei valori dichiarati

Sia `x` il valore dichiarato e `x*` quello ricalcolato. I due
coincidono se e solo se:

```
|x − x*| ≤ abs_tol + rel_tol * |x*|
```

Il riferimento è il ricalcolo. `abs_tol` e `rel_tol` arrivano solo
dall'operatore. I tre campi `mean_loss_a`, `mean_loss_b` e
`mean_difference` sono confrontati ciascuno con questa regola.

### 3.3 Arrotondamento del report (solo visualizzazione)

Le stringhe decimali nel JSON e nel riepilogo **non** sono il valore
usato per i confronti. Il report porta anche il razionale esatto
(`p/q`).

Regole di visualizzazione:

- separatore decimale: punto, mai virgola, mai notazione scientifica;
- se il razionale ha sviluppo decimale finito, si scrive quello,
  con almeno una cifra dopo il punto (`3/10` → `0.3`);
- altrimenti si arrotonda a 18 cifre decimali, **half-even**
  (`1/3` → `0.333333333333333333`).

Un confronto fatto sulle stringhe del report può quindi differire
dal confronto del verificatore. Il verdetto segue sempre le frazioni.

### 3.4 Conclusione derivata dai dati

Sia `τ = equivalence_threshold` (operatore). Sia `Δ` il `delta`
ricalcolato. La conclusione **ricalcolata** è:

```
se |Δ| ≤ τ     → equivalent_within_tolerance
se Δ < −τ      → A_lower
se Δ >  τ      → B_lower
```

Comportamento al confine: l'intervallo di equivalenza è **chiuso**.
Se `|Δ| = τ`, la conclusione è `equivalent_within_tolerance`, non un
vincitore. Per dichiarare un vincitore serve `|Δ| > τ`.

`τ = 0` è ammesso: solo la differenza esattamente zero è
equivalenza.

La conclusione dichiarata coincide se e solo se è uguale, come
stringa, a quella ricalcolata. Non c'è una seconda tolleranza sulla
conclusione: o è quella, o non lo è. Le tolleranze numeriche del
§3.2 non spostano questo confronto.

## 4. Controlli e mappatura degli esiti

Quattro esiti possibili, in ordine di gravità:

| Esito | Significato | Si può arrivare a `pass`? |
|---|---|---|
| `error` | input malformato o problema tecnico | no |
| `unverified` | mancano dati necessari, oppure un controllo precedente ha impedito di eseguirlo | no |
| `fail` | i dati bastano e l'affermazione contraddice il ricalcolo | no |
| `pass` | tutti i controlli richiesti sono stati completati e sono coerenti | sì, solo in questo caso |

L'esito complessivo è il più grave fra i controlli. `pass` richiede
in più che **ogni** controllo richiesto sia presente e in `pass`.
Non si emette un'approvazione se un controllo è stato saltato.

Controlli richiesti, in questo ordine:

| `id` | Cosa controlla | `error` | `unverified` | `fail` | `pass` |
|---|---|---|---|---|---|
| `operator_config` | configurazione leggibile e nei vincoli | file illeggibile, JSON non oggetto, chiavi sconosciute, valori non ammessi (stringa al posto di un numero, booleano, non finito) | percorso indicato ma file assente | — | configurazione usabile (file o predefiniti) |
| `candidate_readable` | JSON candidato leggibile, campi dell'affermazione presenti e del tipo atteso | JSON non oggetto, tipi sbagliati (stringa al posto di un numero, booleano), valori non finiti, `conclusion` fuori enumerazione, `claim_type` diverso da quello atteso | file assente, oppure un campo obbligatorio dell'affermazione manca o è `null` | — | affermazione leggibile |
| `csv_readable` | CSV UTF-8, intestazione univoca, colonne obbligatorie, almeno una riga | file illeggibile, vuoto, senza intestazione, intestazioni duplicate o vuote, colonne mancanti, zero righe di dati, eccezione del parser (`csv.Error`) | file assente | — | CSV utilizzabile |
| `identifiers` | `case_id` non vuoti e univoci | identificativo vuoto o duplicato | non eseguito perché il CSV non è utilizzabile | — | identificativi validi |
| `finite_values` | `loss_a` e `loss_b` finiti e nei limiti di dimensione | cella mancante, non numerica, NaN, infinito, esponente o token oltre i limiti | non eseguito perché il CSV non è utilizzabile | — | tutti i valori finiti |
| `recompute` | calcolo di `mean_a`, `mean_b`, `delta` | errore interno (le due forme di `delta` non coincidono) | non eseguito perché CSV, identificativi o valori non sono utilizzabili | — | tre valori ricalcolati |
| `declared_values` | tre numeri dichiarati contro i tre ricalcolati, con le tolleranze dell'operatore | — | non eseguito se manca il ricalcolo o manca un numero dichiarato | almeno un valore dichiarato fuori tolleranza | tutti e tre dentro tolleranza |
| `declared_conclusion` | conclusione dichiarata contro quella derivata al §3.4 | — | non eseguito se manca il ricalcolo o manca la conclusione dichiarata | stringhe diverse | stringhe identiche |

File assente = `unverified` (mancano i dati). File presente ma
malformato = `error`. Nessuna riga viene eliminata per recuperare un
ricalcolo parziale: un solo valore non finito rende `finite_values`
un `error` e blocca `recompute`.

## 5. Uscita

Due artefatti: un report JSON e un riepilogo testuale in italiano.
Il report contiene almeno:

- esito complessivo e esito per controllo, con motivo;
- numero di casi;
- valori dichiarati e ricalcolati, come stringhe con punto decimale;
- `abs_tol`, `rel_tol`, `equivalence_threshold` effettivamente usati,
  e la loro fonte (`operator` o `defaults`);
- chiavi del candidato ignorate;
- SHA-256 (hex minuscolo) dei byte **effettivamente letti** da ciascun
  file di ingresso;
- nome e versione del verificatore;
- i limiti del §1, copiati nel report, non riassunti.

Codici di uscita della CLI: `0` pass, `1` fail, `2` unverified,
`3` error. La CLI non sovrascrive un file di uscita già esistente,
salvo `--force`.

## 6. Esempio numerico di riferimento

CSV:

```
case_id,loss_a,loss_b
c1,0.20,0.30
c2,0.40,0.35
c3,0.30,0.40
```

Calcolo a mano, non dal verificatore:

```
mean_a = (0.20 + 0.40 + 0.30) / 3 = 0.90 / 3 = 0.30
mean_b = (0.30 + 0.35 + 0.40) / 3 = 1.05 / 3 = 0.35
delta  = ((0.20 − 0.30) + (0.40 − 0.35) + (0.30 − 0.40)) / 3
       = (−0.10 + 0.05 + −0.10) / 3
       = −0.15 / 3
       = −0.05
```

Con `equivalence_threshold = 0.01`, `|−0.05| > 0.01` e `delta < 0`,
quindi la conclusione ricalcolata è `A_lower`.

Con `equivalence_threshold = 0.05`, `|−0.05| = 0.05`, quindi
`equivalent_within_tolerance`.

Con `equivalence_threshold = 0.10`, `|−0.05| < 0.10`, quindi
di nuovo `equivalent_within_tolerance`.

## 7. Confine con l'orchestratore

Questo prototipo vive in `src/oracle/` e non importa
`orchestrator` né `vcc2026`. L'orchestratore non lo chiama. Un
allaccio futuro è una decisione nuova, non un fatto di questa
versione.
