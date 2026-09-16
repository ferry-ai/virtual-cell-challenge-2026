# CP-0017 — Gate di espressione sul contesto di destinazione: misurato, non promosso

- **Data:** 2026-09-16
- **Tipo:** esperimento
- **Redatto da:** agente Claude (Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

[CP-0013](0013-hepg2-terzo-contesto.md) ha misurato che i bracci che provano a
**imparare** la dipendenza dal contesto non generalizzano: il descrittore fa una
differenza reale (45 confronti su 48 con IC95 senza zero) ma il segno cambia con il
contesto tenuto fuori. Da qui la domanda di questo lavoro: se invece di farla
imparare la **scriviamo a mano** come regola, e la mettiamo alla prova con lo stesso
protocollo, regge?

La regola in una frase: un gene che nel contesto di destinazione non è acceso non può
essere spento di più, quindi la risposta prevista su quel gene va compressa verso
zero. Con un peso graduale, mai una soglia, e con due controlli obbligatori — il gate
permutato fra i geni (C1) e il gate costruito sulla sorgente invece che sulla
destinazione (C2) — senza i quali il risultato non è interpretabile.

Questo lavoro non adotta niente. Produce codice, test e una misura.

## 2. Cosa è stato fatto

### 2.1 Implementato — codice, non risultati

- `src/vcc2026/presence.py` — la presenza per gene (CPM dei controlli aggregati) e il
  peso logistico che ne deriva: `w = 1 / (1 + exp(-pendenza · (log10(CPM + 0,01) −
  log10(midpoint))))`, più la permutazione di controllo. **Nessun secondo lettore di
  controlli**: legge gli oggetti che i lettori esistenti già producono
  (`inference.read_basal_profile` per i controlli ufficiali, il `ControlProfile` che
  il banco carica per le sorgenti esterne, scritto da `scripts/55_control_profile.py`).
  Un gene che il profilo non misura ha peso **1**: evidenza mancante non è evidenza di
  assenza (D-009), e il gate non agisce senza evidenza.
- `src/vcc2026/benchmark/gate.py` — i bracci del banco. G1 (peso sul gene di uscita,
  simmetrico), G2 (asimmetrico: il peso agisce sulla parte negativa del delta, la
  positiva resta intatta o è attenuata da un secondo parametro), G3 (peso del gene
  **bersaglio** applicato a tutta la riga). Per ciascuna variante i due controlli:
  `_perm` (presenza permutata fra i geni dell'universo, seed 20260916, stessa mappa in
  selezione e in prova) e `_src` (stessa costruzione dai contesti di **partenza**).
- **Un solo fattore varia.** Un braccio gate è `shrunk_transfer` così com'è stato
  selezionato e calibrato nello stesso split — stesso `alpha`, stesso `prior_sd` —
  moltiplicato per un peso. Il run ricalcola quella base e **si ferma** se non ottiene
  lo stesso `pooled_mse_vs_null` della riga `shrunk_transfer` (controllo in
  `run_gate_arm`, `gate.base_check` in ogni riga).
- I parametri del gate (midpoint, pendenza, e per G2 l'attenuazione della parte
  positiva) sono scelti sulla **coppia interna al training** — la stessa su cui
  ShrunkTransfer calibra l'ampiezza — sui 32 bersagli di validazione interna e sui geni
  dell'universo del fold. La griglia contiene l'**identità** (peso costante 1) come
  primo candidato: a parità di MSE vince «non fare niente».
- `configs/benchmark_expression_gate.yaml` — protocollo e **regola di decisione scritti
  prima del run**, con i limiti attesi dichiarati prima di misurarli. Il file porta
  `owner_confirmed: false`: la regola è quella proposta nel brief e **non è stata
  confermata dal proprietario** prima dell'esecuzione.
- `scripts/69_expression_gate_decision.py` applica quella regola ai numeri;
  `scripts/70_context_presence_audit.py` conta, sui soli controlli ufficiali, quanto
  spazio la regola avrebbe dove conta. `tests/test_expression_gate.py`: 53 test.
- `src/vcc2026/benchmark/run.py`: estratti `_fit_shrunk_transfer` e
  `_inner_val_targets` perché il gate usi la stessa base e gli stessi bersagli di
  validazione invece di una seconda definizione; i bracci gate girano solo se la
  configurazione li dichiara, quindi i protocolli precedenti sono invariati.

### 2.2 Eseguito

```bash
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id x001 --config configs/benchmark_expression_gate.yaml --signatures <e001>/signatures <e003>/signatures
.\scripts\py.cmd scripts/69_expression_gate_decision.py --run-id x001 --out reports/expression_gate_2026-09-16 --reference-table reports/benchmark_3ctx_2026-09-14/comparison_table.csv
.\scripts\py.cmd scripts/70_context_presence_audit.py --out reports/expression_gate_2026-09-16
.\scripts\py.cmd -m unittest discover -s tests
python scripts/31_check_docs.py
```

Protocollo: `configs/benchmark_3ctx.yaml` invariato nei suoi tre fold, solo
`new_context_seen_target` (sul bersaglio mai visto ShrunkTransfer predice il nullo per
copertura zero, e moltiplicare zero non misura niente), seed di sviluppo 2026 e 2027 —
il seed di conferma 4242 resta chiuso (D-032). 108 righe = 18 bracci × 3 fold × 2 seed.
Niente è stato scaricato, nessuna previsione per A/B/C è stata generata, niente è stato
impacchettato o inviato, `configs/trials.yaml` non è stato toccato.

Costi misurati (`reports/expression_gate_2026-09-16/comparison_table.csv`,
`summary.json`): 300,0 s di training sommati su tutte le righe, 35,0 s di inferenza,
picco RSS 635,8 MiB. Macchina: 7,81 GiB di RAM totali, **1,04 GiB disponibili**, 8 CPU,
9,08 GiB liberi su disco. Artefatti del run: 82 MB in `artifact_root`.

## 3. Cosa si è osservato

Ogni numero di questa sezione ha un file. Se il file non c'è, la riga non è una misura.

### 3.1 Il protocollo è davvero lo stesso

Fonte: `reports/expression_gate_2026-09-16/decision.json`, campo `reproduction`.

Le **54 righe** dei nove bracci originali condivise con `m002` hanno differenza
assoluta **0,0** su `pooled_mse_vs_null`, `pearson_median` e `coverage_targets`.
Stessi split, stessa metrica, stessi numeri di CP-0013: ShrunkTransfer 0,952 / 0,949
(HepG2 fuori), 0,971 / 0,968 (RPE1 fuori), 0,999 / 1,000 (K562 fuori).

### 3.2 La regola di decisione, applicata

Fonte: `reports/expression_gate_2026-09-16/decision.json` e `decision_table.md`.
Statistica: differenza appaiata per bersaglio (`diff`, bootstrap 200), la stessa di
CP-0013. Sei split per clausola (3 fold × 2 seed).

| Variante | batte ShrunkTransfer | il permutato non la batte | la sorgente è peggio | promossa |
|---|---|---|---|---|
| G1 simmetrico | 1/6 | 4/6 | 1/6 | **no** |
| G2 asimmetrico | 1/6 | 5/6 | 1/6 | **no** |
| G3 sul bersaglio | 1/6 | 5/6 | 1/6 | **no** |

**Nessuna variante è promossa.** L'unico split in cui una variante batte
ShrunkTransfer è sempre lo stesso (RPE1+HepG2 → K562, seed 2027): G1 −0,01305, G2
−0,01219, G3 −0,00279, IC95 senza zero. Negli altri cinque la differenza è 0,00000
esatto (gate identità) oppure positiva, cioè peggiore: G1 +0,00338 e +0,00329, IC95
senza zero.

### 3.3 Che gate ha scelto la selezione

Fonte: `reports/expression_gate_2026-09-16/gate_rows.json`.

- Identità scelta in **30 righe su 54**. Ma la distribuzione non è uniforme fra i seed:
  **23 righe su 27 con seed 2026, 7 su 27 con seed 2027**. I due seed differiscono solo
  per quali 32 bersagli finiscono nella validazione interna.
- Sui soli bracci di destinazione (G1, G2, G3) il gate è diverso dall'identità in
  **6 righe su 18**.
- Quando un gate è scelto, il midpoint selezionato sta fra 1 e 10 CPM e la quota di
  massa |Δ| rimossa va dallo **0,40% al 27,6%**.
- Griglia: 11 candidati per G1 e G3, 21 per G2 (identità compresa), 32 bersagli di
  validazione in ogni split.

### 3.4 I due controlli

Fonte: come sopra.

- **C1, permutato.** Il gate con la presenza mescolata fra i geni **batte** il gate vero
  in 2 split su 6 per G1 e in 1 su 6 per G2 e G3. È misurabilmente *peggiore* del gate
  vero in 1 split su 6, per tutte e tre le varianti.
- **C2, sorgente.** Il gate costruito sui contesti di partenza **batte** quello
  costruito sulla destinazione in **4 split su 6** per G1, 3 su 6 per G2, 1 su 6 per G3.
  La clausola chiedeva il contrario, e vale in 1 split su 6.
- Lettura dichiarata prima del run: G2 batte G1 in 2 split su 6, quindi l'asimmetria non
  si distingue dalla simmetria in questo disegno.

### 3.5 Quanto spazio aveva il gate nel banco

Fonte: `reports/expression_gate_2026-09-16/splits/*.json`, campo `expression_presence`,
calcolato dal run prima di qualunque gate.

| Contesto di prova | geni < 5 CPM | < 10 CPM | < 30 CPM | CPM minimo | bersagli < 5 CPM |
|---|---:|---:|---:|---:|---:|
| HepG2 | 2 | 354 | 2.665 | 4,69 | 0 |
| RPE1 | 2 | 265 | 2.643 | 4,31 | 0 |
| K562 | 0 | 143 | 2.568 | 8,56 | 0 |

Su 6.477 geni dell'universo (34,9% dell'asse ufficiale). **Nell'universo del banco i
geni spenti non ci sono**: è l'intersezione di tre pannelli di perturbazione, che
escludono già i geni poco espressi. Dei 160 bersagli, 25–28 non sono misurati nel
profilo del contesto di destinazione, e per la regola scritta prima ricevono peso 1.

### 3.6 Quanto spazio avrebbe sui contesti ufficiali

Fonte: `reports/expression_gate_2026-09-16/context_presence.json` e `context_presence.md`
(`scripts/70_context_presence_audit.py`, sole cellule di controllo).

| Contesto | cellule | molecole | conteggi attesi a 1 CPM | geni a zero | geni < 1 CPM | geni < 5 CPM | bersagli < 5 CPM |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 18.400 | 3,889·10⁸ | 389 | 2.398 | 7.336 | 8.610 | 1 |
| B | 18.400 | 3,678·10⁸ | 368 | 2.853 | 7.470 | 8.923 | 5 |
| C | 18.400 | 3,893·10⁸ | 389 | 2.317 | 6.876 | 8.409 | 6 |

Su 18.533 geni. L'aritmetica dichiarata nel brief è confermata: un gene a 1 parte per
milione è contato 368–389 volte, quindi su questa scala uno zero aggregato è quasi
sempre biologia e non strumento.

Geni sotto 1 CPM in tutti e tre i contesti: 5.190; in almeno uno: 9.148. Geni **spenti
qui e accesi altrove** (< 1 CPM nella destinazione, ≥ 10 CPM nella sorgente), che sono
l'unica parte su cui un gate di contesto può fare qualcosa che un filtro globale non
farebbe: da **318** (B→C) a **839** (C→A) a seconda della coppia.

Dei 300 bersagli del pannello, sotto 5 CPM ce ne sono 1 in A (`S100A11`, 0,12 CPM), 5 in
B, 6 in C; sotto 10 CPM, 8 / 31 / 27.

## 4. Interpretazione e incertezza

**Misurato:** tutto il §3.

**Interpretazione, ed è la più importante.** Dove un gate ha aiutato, ha aiutato **di
più** quello costruito sulla sorgente: 4 split su 6 per G1. È esattamente la spiegazione
alternativa che C2 esisteva per smascherare. Quel poco che si guadagna non viene dal
legame gene-contesto, ma dal comprimere i geni poco espressi in generale: è un filtro di
rumore, e va chiamato col suo nome. Il permutato, che batte il gate vero in 2 split su 6
per G1, dice la stessa cosa da un'altra direzione. Senza i due controlli avremmo letto
lo split favorevole (−0,013, IC senza zero) come un successo parziale.

**Interpretazione.** La selezione del gate è **instabile**: identità in 23 righe su 27
con un seed e in 7 su 27 con l'altro, dove i due seed cambiano solo quali 32 bersagli
stanno in validazione interna. Una scelta che si ribalta così non è una regola: il
guadagno di uno split sta dentro la stessa variabilità che fa cambiare la scelta.

**Interpretazione.** Il banco a tre contesti non è il posto dove questa idea si può
falsificare. Il suo universo genico è l'intersezione di tre pannelli e non contiene geni
spenti (0–2 sotto 5 CPM); l'idea parla di geni assenti, che lì sono quasi assenti a loro
volta. I contesti ufficiali sono l'opposto — 8.409–8.923 geni su 18.533 sotto 5 CPM — ma
lì non esistono risposte perturbate con cui misurare alcunché. Questo limite era scritto
nella configurazione prima del run; adesso ha dei numeri.

**Perché potrebbe non significare questo.** Quattro cose, nessuna risolta qui.

1. L'ampiezza **non** è stata ricalibrata dopo il gate, per far variare un fattore solo.
   Un gate che comprime, valutato con un alpha ottimizzato senza gate, è misurato in
   modo conservativo. Quanto conservativo non è misurato.
2. 160 bersagli su 2.315 e 32 bersagli di validazione interna: un effetto piccolo può
   stare sotto la risoluzione, e l'instabilità fra seed suggerisce che la risoluzione sia
   proprio questa.
3. Lo scorer ufficiale dichiara `filter_gene_min_cpm_cell: 5.0`
   (`reports/scorer_2026-09-12/vcc2026_contract.json`). La semantica esatta di quel
   filtro non è stata verificata qui: quanto dello spazio contato nel §3.6 sopravviva
   allo scorer resta da misurare.
4. La regola di decisione non è stata confermata dal proprietario prima del run
   (`owner_confirmed: false`). Cambiarla adesso che i numeri esistono la renderebbe
   post-hoc, e questo checkpoint lo direbbe.

**Ipotesi, non misurate.**

- Che una regola di presenza aiuti dove i geni spenti esistono davvero (contesti
  ufficiali, o un banco con l'asse genico intero della destinazione).
- Che ricalibrare l'ampiezza insieme al gate cambi il verdetto.
- Che i 318–839 geni «spenti qui, accesi altrove» del §3.6 siano abbastanza da spostare
  una delle sei metriche VCC. Qui non è stato calcolato nessun punteggio VCC.

## 5. Spiegazione semplice

Se un gene in un certo tipo di cellula è già spento, spegnerlo non può fare molto: la
previsione su quel gene andrebbe schiacciata verso zero. È un'idea sensata e l'abbiamo
scritta a mano invece di farla imparare alla macchina.

Poi abbiamo fatto due prove di controllo, ed è lì che è successa la cosa interessante.
Prima prova: abbiamo mescolato a caso «quanto è acceso» fra i geni. Se la regola
funzionasse davvero, la versione mescolata dovrebbe andare peggio; in due casi su sei è
andata **meglio**. Seconda prova: abbiamo costruito la stessa regola guardando le
cellule di **partenza** invece che quelle di arrivo — cioè togliendo proprio
l'informazione sul contesto nuovo. In quattro casi su sei è andata meglio così.

Conclusione: quel poco di guadagno non viene dal sapere cosa è acceso *là*, ma dallo
schiacciare i geni poco espressi in generale. È un filtro contro il rumore, non una
regola di biologia, e chiamarlo col nome giusto è tutto il valore di questo lavoro.

C'è anche un motivo più semplice per cui non poteva andare meglio: nel banco di prova i
geni spenti quasi non ci sono, perché i dati che usiamo tengono solo i geni ben
espressi. Nelle cellule della gara, invece, quasi la metà dei geni è sotto la soglia. La
prova è stata fatta dove si poteva fare, non dove servirebbe.

## 6. Conseguenze

- **D-033**: il gate di espressione non è adottato. Il codice resta, spento: nessun
  braccio gate gira se una configurazione non lo dichiara, e `configs/benchmark_3ctx.yaml`
  è invariato. Un esperimento negativo deve poter essere rifatto.
- Il prossimo passo che ridurrebbe incertezza su questa idea **non** è un altro giro sul
  banco a tre contesti: è un banco in cui i geni spenti esistano, cioè una destinazione
  con l'asse genico intero. Finché quello manca, la regola resta non misurabile dove
  conterebbe.
- Resta valido ciò che CP-0013 diceva: ShrunkTransfer è il braccio da battere, e non è
  stato battuto.
- Nessuna sottomissione, nessuna previsione per A/B/C, nessun pacchetto.

## 7. Cosa corregge

**Nessuna.** Questo checkpoint non corregge niente: riproduce esattamente le 54 righe
dei nove bracci di `m002` (differenza assoluta 0,0), quindi conferma CP-0013 invece di
correggerlo, e non tocca CP-0014 né CP-0015. Aggiunge una misura nuova — la
distribuzione dei CPM dei controlli, nel banco e nei contesti ufficiali — che prima non
esisteva in questo repository.

Una cosa che corregge, ed è una mia aspettativa e non un documento: il brief prevedeva
che G3 «toccherà molti più bersagli» su HepG2. Sui 160 bersagli condivisi dai tre
contesti, G3 ha compresso 0 bersagli in cinque split su sei e 7 su 160 nel sesto,
perché i bersagli condivisi da tre schermi CRISPRi sono geni espressi quasi ovunque.

## 8. Domanda di comprensione

Il gate costruito sulla **sorgente** batte quello costruito sulla destinazione in 4
split su 6 per G1. Perché questo, da solo, toglie forza all'idea anche negli split in
cui il gate «funziona» — e quale altro numero della stessa tabella dice la stessa cosa
da un'altra direzione?
