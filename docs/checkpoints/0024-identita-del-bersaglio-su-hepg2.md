# CP-0024 — Il controllo d'identita' del bersaglio: il trasferimento e' specifico, il vantaggio di RPE1 e' soprattutto comune

- **Data:** 2026-09-18
- **Tipo:** esperimento
- **Redatto da:** agente
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il vantaggio di RPE1 su K562 nel banco HepG2 ([CP-0023](0023-rpe1-contro-k562-su-hepg2.md))
dipende da **quale** bersaglio viene spento, oppure da una risposta che qualunque firma della
sorgente porterebbe con sé? La domanda l'ha posta il proprietario per il caso di vittoria di
RPE1. Decide perché RPE1 non ha perturbato nessuno dei 300 bersagli ufficiali.

## 2. Cosa è stato fatto

1. Braccio di controllo nuovo nello stadio 75, `shuffled_aX`: a ogni bersaglio l'effetto di un
   altro bersaglio della stessa sorgente, con un accoppiamento fisso (`derangement`, seme
   2027, lo stesso per le due sorgenti), senza il gene bersaglio del partner. Conserva le
   ampiezze e la componente comune della sorgente, toglie solo l'identità.
2. `Bench` registra ora `k`, `n_pred` e `n_conf` per bersaglio (`components_<braccio>.csv`),
   letti dalla funzione interna dello scorer. Un test verifica che `k / max(n_pred, n_conf)`
   riproduca la fedeltà dello scorer alla dodicesima cifra, e un secondo controllo verifica
   che il test fallisca se la soglia è sbagliata.
3. Job 022 (K562) e 023 (RPE1), avviati alle 11:55 UTC: bracci `null_new transfer_a0.5
   transfer_a1.0 transfer_a2.0 shuffled_a0.5 shuffled_a1.0 shuffled_a2.0`, stesso pannello,
   seme e sorgenti di 020/021. I primi quattro bracci, nello stesso ordine, estraggono gli
   stessi numeri casuali.
4. Regola `configs/specificity_rule.yaml`: la versione 1 è stata scritta prima di mettere in
   coda i job; la **versione 2** dopo il loro avvio e prima di ogni output. Un test sintetico
   a risposta nota aveva mostrato che la versione 1 chiamava `MIXED` una sorgente nulla, e la
   versione 2 aggiunge una soglia pratica di 0,03. `owner_confirmed: false`.
5. Stadio 89 → `reports/source_lineage_2026-09-18/c003/specificity.json`. Stadio 90
   (esplorativo, scritto dopo i risultati) → `c004/precision.csv`. I due `bench.json` sono
   copiati come `*_r3_bench.json`.

## 3. Cosa si è osservato

**Misurato — riproducibilità.** Anchors e bracci di trasferimento coincidono con 020/021 entro
1e-9 per entrambe le sorgenti (`c003/specificity.json`, `reproducibility_gate`): il banco è
deterministico, e le modifiche a `bench.py` e allo stadio 75 non cambiano le metriche.

**Misurato — il controllo conserva il volume.** Chiamate per bersaglio, trasferimento contro
rimescolato: K562 12/11, 92/86, 411/392; RPE1 100/96, 541/513, 1.557/1.554.

**Misurato — specificità per sorgente** (S = fedeltà del trasferimento − fedeltà del
rimescolato, appaiata per bersaglio, intervallo bootstrap al 95% sui bersagli):

| sorgente | a0.5 | a1.0 | a2.0 | verdetto |
|---|---|---|---|---|
| K562 | −0,000 [−0,030, +0,029] | +0,045 [−0,001, +0,088] | **+0,142** [+0,097, +0,186] | `MIXED` |
| RPE1 | +0,055 [+0,012, +0,099] | **+0,184** [+0,139, +0,230] | **+0,162** [+0,128, +0,197] | `SPECIFIC` |

**Misurato — scomposizione del vantaggio di RPE1** alla coppia con volume vicino (RPE1 a0.5,
circa 100 chiamate; K562 a1.0, circa 92), su 256 bersagli: vantaggio +0,075 [+0,036, +0,116],
di cui parte **comune +0,055 [+0,024, +0,087]** e parte **specifica +0,021 [−0,029, +0,071]**.
Verdetto: `MAINLY_COMMON`.

**Misurato — precisione dei segni** (`k/n_pred`, `c004/precision.csv`). La precisione
**aggregata** del trasferimento vale 0,786/0,740/0,677 per K562 e 0,833/0,763/0,693 per RPE1.
Il rimescolato vale 0,540/0,539/0,535 per K562 e 0,631/0,614/0,586 per RPE1. La replica vale
0,955, la baseline 0,606.

**Misurato, lettura esplorativa per bersaglio** (bersagli con almeno 10 chiamate). La mediana
della precisione del trasferimento è quasi uguale fra le sorgenti: 0,868/0,778/0,709 per
K562, 0,846/0,770/0,705 per RPE1. RPE1 però la ottiene con molte più chiamate per bersaglio
(mediane 121/596/1.897 contro 31/72/320) e su più bersagli (159/214/235 contro 47/128/199).
Il rimescolato ha mediana 0,583/0,566/0,544 per K562 e 0,678/0,651/0,607 per RPE1.

**Misurato — `pds_cosine` dei rimescolati** vale 0,47–0,51, cioè il livello di `null_new`
(0,502): senza identità del bersaglio il profilo non distingue i bersagli fra loro, come
atteso.

## 4. Interpretazione e incertezza

**Interpretazione.** Su HepG2 il trasferimento porta informazione legata all'identità del
bersaglio, per entrambe le sorgenti: per RPE1 a tutte le ampiezze, per K562 solo quando
chiama abbastanza (ampiezza 2,0). Il trasferimento fra contesti **non è morto**, almeno fra
due linee che non sono A, B o C.

**Interpretazione.** Il vantaggio di RPE1 su K562, alla sola coppia a volume confrontabile,
sta soprattutto in ciò che tutte le firme RPE1 condividono. È la parte che si potrebbe usare
anche senza coprire i bersagli ufficiali. Coerentemente, quando le due sorgenti chiamano, la
loro precisione per bersaglio è simile: RPE1 guadagna chiamando di più con la stessa
precisione, e con una componente comune più spesso nel verso giusto.

**Incertezza.**
- La scomposizione è letta a una sola coppia, circa 100 chiamate per bersaglio, dove la
  specificità di K562 è piccola. A volumi più alti non c'è una coppia confrontabile.
- Il bootstrap copre solo l'estrazione dei bersagli, e c'è un solo seme.
- La soglia di 0,03 è una regola pratica.
- La lettura per bersaglio è esplorativa e seleziona insiemi di bersagli diversi da braccio a
  braccio.

**Che cosa è la parte comune: non lo sappiamo.** Può essere un programma di stress o p53
condiviso dai knockdown, una differenza di espressione di base legata al lignaggio, o
l'errore della media dei controlli della sorgente, che si sottrae a tutti i bersagli allo
stesso modo. Il banco non separa queste possibilità.

**Il limite più serio per l'uso in gara, ipotesi non misurata.** I bersagli del banco sono
geni essenziali: le loro risposte sono forti e si somigliano, con una mediana di 63,5 geni
confidenti per bersaglio secondo la definizione dello scorer (`components_*.csv`). I 300
bersagli ufficiali non compaiono in nessuno screen di geni essenziali (K562 essential 0/300,
RPE1 0/300). La risposta comune dei knockdown essenziali potrebbe non esserci, o essere
diversa, nei knockdown ufficiali.

## 5. Spiegazione semplice

Abbiamo dato a ogni studente le risposte di un compagno invece delle proprie. Se il voto non
cambiava, voleva dire che le risposte erano generiche. Il voto è sceso per entrambi, quindi
le risposte erano davvero sulla domanda giusta. Ma il vantaggio del secondo studente sul primo
veniva soprattutto da un'abitudine che applica a tutte le domande. Resta da capire se
quell'abitudine vale anche per le domande dell'esame vero, che sono di un altro tipo.

## 6. Conseguenze

- La risposta alla domanda del proprietario è: **soprattutto comune**, alla coppia misurata.
  Quindi RPE1 **potrebbe** entrare in una sottomissione, ma solo come componente comune
  accanto alle firme K562 specifiche (272 bersagli ufficiali su 300). È un candidato da
  misurare, non una strategia adottata.
- Prima di costruirlo, due misure distinguono se ha senso:
  1. in K562 genome-wide, che contiene sia geni essenziali sia i bersagli ufficiali, si
     misura se la risposta comune dei knockdown essenziali compare anche nei knockdown dei
     272 bersagli ufficiali (direzione e ampiezza). Se non compare, aggiungerla alle
     previsioni ufficiali aggiungerebbe chiamate sbagliate;
  2. sul banco HepG2, un braccio «trasferimento K562 + componente comune RPE1» contro il
     solo trasferimento K562. Richiede un termine comune preso da una seconda sorgente, che
     oggi non esiste.
- I bracci rimescolati e i componenti per bersaglio restano nello stadio 75 e in `Bench`.

## 7. Cosa corregge

- Nessun checkpoint precedente.
- Precisa [CP-0023](0023-rpe1-contro-k562-su-hepg2.md) §4: là il vantaggio di RPE1 a parità
  di chiamate medie restava «non spiegato dal volume». Qui, alla coppia confrontabile, risulta
  in maggior parte non legato all'identità del bersaglio.

## 8. Domanda di comprensione

Perché un braccio rimescolato con `pds_cosine` al livello del modello nullo può avere comunque
una fedeltà direzionale di 0,40?
