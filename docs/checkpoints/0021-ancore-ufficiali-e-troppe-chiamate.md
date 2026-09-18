# CP-0021 — Le ancore ufficiali risolte, e una diagnosi che resta aperta

- **Data:** 2026-09-17
- **Tipo:** osservazione
- **Redatto da:** agente
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il generatore a singola cellula di [CP-0020](0020-singola-cellula-cis-generatore.md),
unito al trasferimento delle firme K562, supera lo 0,1 in classifica? E, qualunque sia la
risposta, che cosa premia davvero il punteggio ufficiale?

## 2. Cosa è stato fatto

1. Banchi a sei metriche su Colab (job 007 e 008): pannello K562 (`b002`) e trasferimento
   K562 → HepG2 (`h002`), in `reports/bench_2026-09-17/`.
2. Regola pre-registrata `configs/trial02_rule.yaml` (versione 2, scritta prima che i
   banchi avessero risultati), applicata meccanicamente da `scripts/81_choose_trial02.py`
   → `reports/trial02_decision_2026-09-17/decision.json`.
3. Generazione e impacchettamento su Colab di due file: `t02` (l'esito della regola,
   ampiezza di trasferimento 1,0; job 011) e `t03` (la stessa senza il tetto della regola,
   ampiezza 2,0; job 014). Prove in `reports/trial_2026-09-17/t02/` e `t03/`.
4. Sottomissione del solo `t02` (`entry_id` `49Gvtu504clN1mIu8T2V`), output verbatim in
   `reports/trial_2026-09-17/submit_49Gvtu504clN1mIu8T2V.json` e
   `status_49Gvtu504clN1mIu8T2V.json`.
5. Soluzione algebrica delle ancore ufficiali da due sottomissioni valutate,
   `scripts/82_solve_anchors.py` → `reports/anchors_2026-09-17/anchors.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** `t02` ha ottenuto media **−0,092774**, rango 764, contro lo
**0,045929** (rango 446) di trial-01 del 13 settembre. Peggiore, non migliore
(`reports/trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json`).

| membro | grezzo t01 | scalato t01 | grezzo t02 | scalato t02 |
|---|---|---|---|---|
| `pds_cosine` | 0,6870 | +0,4133 | 0,6094 | +0,2399 |
| `expr_mse_unbiased_capped_norm` | 1,2313 | 0 | 1,3659 | 0 |
| `de_wilcoxon_lfc_nmae` | 0,9849 | +0,0268 | 0,9728 | +0,0467 |
| `de_wilcoxon_direction_fidelity_yield_raw` | 0,4580 | −0,1825 | 0,2534 | **−0,8696** |
| `de_wilcoxon_direction_reach_raw` | 0,0980 | +0,0213 | 0,1382 | +0,0666 |
| `de_wilcoxon_sig_jaccard` | 0,0291 | −0,0034 | 0,0157 | −0,0402 |

**Misurato — le ancore.** `vcc status --json` restituisce sia il valore grezzo sia quello
scalato di ogni membro. Due sottomissioni sullo stesso `panel_id` (`vcc2026-val-1`) e sullo
stesso `anchor_version` (`vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4`) danno due
equazioni nelle stesse due incognite, e il sistema `scalato = (grezzo − base)/(replica − base)`
si risolve esattamente:

| membro | base | replica |
|---|---|---|
| `pds_cosine` | 0,5021 | 0,9495 |
| `de_wilcoxon_lfc_nmae` (meglio se basso) | 1,0012 | 0,3932 |
| `de_wilcoxon_direction_fidelity_yield_raw` | **0,5123** | 0,8101 |
| `de_wilcoxon_direction_reach_raw` | 0,0790 | 0,9687 |
| `de_wilcoxon_sig_jaccard` | 0,0304 | 0,3953 |
| `expr_mse_unbiased_capped_norm` | non risolta (entrambi gli scalati valgono 0) | — |

Le due soluzioni ricostruiscono tutti e dieci gli scalati che il server ha pubblicato
(`reports/anchors_2026-09-17/anchors.json`, campo `check`). La `mse` resta indeterminata
perché entrambe le sottomissioni sono state tosate a 0; se ne ricava solo che la base è
**almeno buona quanto 1,2313**, cioè che entrambi i nostri file hanno profili medi peggiori
della semplice media del contesto.

**Misurato — la definizione della metrica.** In `cell_eval2` 0.16.0,
`metrics/direction.py`, `_components` e `_direction_frame`: l'insieme valutato è
`{g : p_adj_pred(g) < alpha} ∩ {in_denom}` tolto il gene bersaglio, `n_pred` è la sua
cardinalità, `k` il numero di segni azzeccati al suo interno, e

```
direction_fidelity_yield_raw = k / max(n_pred, n_conf)
in_denom = il log2FC REALE e' definito, non NaN e non nullo   # NON "significativo nel riferimento"
match    = in_denom & il modello si e' esposto & i segni coincidono
```

`n_pred` è dunque **il numero di geni che la previsione stessa dichiara significativi**, e
`k` è limitato da `n_pred`, **non** da `n_conf`. Ne segue che `raw ≤ min(1, n_pred/n_conf)`:
quando `n_pred ≥ n_conf` la metrica **è esattamente la precisione** delle nostre chiamate, e
chiamare molto non tosa il punteggio di per sé, perché cresce anche il numeratore.

**Misurato — quante chiamate facciamo.** Stadio 80 sulle statistiche a singola cellula,
20 bersagli per contesto, pool di riferimento da 1.500 cellule
(`reports/call_budget_2026-09-17/c001/call_budget.json`): ad ampiezza 1,0 la mediana è
39/28/46 geni per bersaglio in A/B/C con media 207/179/193 — una distribuzione con una
coda lunga; ad ampiezza 2,0 la mediana sale a 571/481/560. Sul banco HepG2 la mediana di
`n_conf` è 130 (`reports/bench_2026-09-17/hepg2_h002_bench.json`).

**Misurato — la fedeltà grezza cresce con il numero di chiamate.** Il banco h002 conserva
i valori grezzi di ogni braccio (`reports/bench_2026-09-17/hepg2_h002_bench.json`, campo
`raw`), e lì le risposte perturbate vere ci sono:

| braccio | chiamate/bersaglio | `fidelity_yield_raw` |
|---|---|---|
| replica (cellule reali) | 430,2 | 0,6986 |
| trasferimento 2,0 + cis | 523,7 | 0,4855 |
| trasferimento 1,0 + cis | 126,6 | 0,2878 |
| baseline del banco | 8,5 | 0,1187 |
| generatore pulito, zero effetto | 0,13 | 0,0242 |

La mediana di `n_conf` sul banco è 130, ma il suo decile superiore è 1.660: su molti
bersagli il riferimento dichiara moltissimi geni.

**Misurato — il banco predice il valore grezzo, non quello scalato.** Per la configurazione
identica a quella sottomessa, la fedeltà grezza vale 0,2878 sul banco e 0,2534 dal server
(scarto 12%). Lo scalato invece differiva per intero (+0,29 locale contro −0,87 ufficiale)
perché il banco usava ancore proprie: la sua baseline ottiene 0,1187 dove quella ufficiale
ottiene 0,5123.

## 4. Interpretazione e incertezza

**Il fatto da spiegare.** `t02` ha fedeltà grezza 0,2534 contro una base di 0,5123 e uno
0,4580 di trial-01. Contemporaneamente `jaccard` scende (0,0291 → 0,0157) e `reach` **sale**
(0,0980 → 0,1382).

**Due letture, incompatibili fra loro, entrambe compatibili con questi numeri.** Quale valga
dipende da un solo numero che non abbiamo ancora misurato, `n_pred`:

- se `n_pred ≥ n_conf`, la metrica è la nostra precisione: **25%**, cioè sotto il caso — i
  segni che dichiariamo sarebbero sistematicamente sbagliati, e la cura è trovare l'errore
  di segno o l'artefatto composizionale che li produce;
- se `n_pred < n_conf`, la metrica è `k / n_conf`, cioè copertura: staremmo chiamando
  **troppo poco**, e la cura è chiamare di più.

Le due terapie sono opposte. `jaccard` in calo e `reach` in salita sono più facili da
leggere nel primo regime, ma è un indizio, non una misura.

**La misura del banco favorisce la seconda lettura.** Su HepG2, dove le risposte vere ci
sono, passare da 127 a 524 chiamate per bersaglio **alza** la fedeltà grezza da 0,2878 a
0,4855, e la replica stessa — cellule reali — ne dichiara 430 ottenendo 0,6986. Nell'intero
intervallo misurato, dal generatore muto alla replica, chiamare di più non costa: rende. Se
questo vale anche sui contesti A/B/C, il `t02` chiamava **troppo poco**, e limitare le
chiamate è la cura sbagliata. Resta da verificare che la relazione regga fuori da HepG2:
l'unico punto che abbiamo sui contesti ufficiali è il `t02` stesso.

**Errore di questa scheda, corretto prima della pubblicazione.** Una prima stesura, scritta
la sera stessa, affermava che con `n_conf ≈ 130` e qualche centinaio di chiamate il massimo
ottenibile era «0,26 anche indovinando ogni segno», e ne deduceva che né trial-01 né
trial-02 potessero superare lo 0,1. È sbagliato: presupponeva `k ≤ n_conf`, che
`_direction_frame` non impone. Il tetto reale è `min(1, n_pred/n_conf)`. L'errore è
annotato qui perché ha prodotto, nella stessa serata, una diagnosi categorica e una promessa
di recupero quantificata, entrambe senza base misurata.

**Interpretazione.** Il banco locale non sbaglia i confronti fra bracci, sbaglia il
**regime**: sul banco HepG2 il pool di riferimento ha 130 geni confidenti di mediana e i
nostri bracci ci stanno dentro, mentre i contesti ufficiali hanno 18.400 cellule di
controllo e fanno scattare molte più significatività sulla stessa previsione. Per questo
`h002` dava +0,63 di fedeltà scalata dove il server ne ha dati −0,87.

**Incertezza.** Le ancore sono risolte da due punti: sono esatte per costruzione, ma non
sono **verificate** finché una terza sottomissione non le userà per predire il proprio
scalato prima di vederlo. La `mse` resta indeterminata. Il valore di `n_pred` che il
server ha effettivamente visto sui nostri file non è stato misurato: è dedotto dalla
combinazione dei tre membri e dallo stadio 80 in un regime più piccolo.

**Ipotesi, non misura.** Che limitare le chiamate ai geni con l'effetto più forte alzi
anche la `mse` sotto la base — plausibile, perché i geni azzerati esattamente non
allontanano più il profilo medio dal controllo, ma non misurato.

## 5. Spiegazione semplice

La metrica che ci sta costando di più è una frazione: al numeratore i geni su cui abbiamo
indovinato la direzione, al denominatore il più grande fra «quanti ne abbiamo dichiarati» e
«quanti ne ha dichiarati il riferimento». Se ne dichiariamo più del riferimento, il voto
diventa semplicemente la percentuale di volte che ci azzecchiamo. Se ne dichiariamo meno, il
voto resta diviso per il numero del riferimento, e tacere costa.

Il nostro voto è 0,25 su una base di 0,51. Sappiamo che è basso; non sappiamo ancora se è
basso perché sbagliamo i segni o perché parliamo troppo poco. Sono due malattie opposte con
due cure opposte, e per distinguerle basta contare quante affermazioni facciamo — che si può
fare con le sole cellule di controllo.

## 6. Conseguenze

- **Nessuna seconda sottomissione prima della misura di `n_pred`.** Lo stadio 83
  (`scripts/83_prediction_calls.py`) la produce dalle sole cellule di controllo ufficiali e
  dalla previsione già generata; non produce `k` né `n_conf`, che richiedono i dati
  perturbati nascosti.
- Il numero di geni dichiarati diventa comunque **un parametro esplicito** del modello, non
  una conseguenza delle ampiezze: `--max-calls` negli stadi 76 e 80 tiene i K geni con
  `|log fold change|` maggiore e porta **tutto il resto esattamente a zero**. Il limite
  vincola `n_pred` dall'alto; quante di quelle K diventino significative va misurato.
- Ogni misura locale va d'ora in poi riportata in **forma grezza** e confrontata con le
  ancore di `reports/anchors_2026-09-17/anchors.json`, non con le ancore locali di un banco.
- Restano pronti, generati e verificati, tre file non sottomessi: `t03` (ampiezza 2,0, molte
  più chiamate), `t04` (K = 150) e `t05` (K = 40). Alla luce del banco, `t04` e `t05` sono
  esperimenti nella direzione che i dati **non** sostengono; sono stati generati prima che
  quella misura fosse letta e restano disponibili come controllo.
- La previsione del punteggio ufficiale del `t03`, calcolata dai grezzi del banco, dal punto
  di calibrazione `t02` e dalle ancore, è stata **registrata prima** dell'eventuale
  sottomissione: `reports/prediction_t03_2026-09-17/prediction.json`, media attesa +0,0338
  (stadio 84). Il suo confronto con il punteggio reale è l'unico modo che abbiamo di sapere
  se il banco è uno strumento o un'illusione.
- Le ancore dicono **a quale numero puntare**, non quale numero otterremo: non consentono di
  prevedere la media di una sottomissione non ancora valutata.

## 7. Cosa corregge

- Corregge l'aspettativa di [CP-0020](0020-singola-cellula-cis-generatore.md) e della
  D-034: un generatore pulito accoppiato a un predittore che «fa chiamate» non basta. La
  D-035 («niente sottomissioni senza chiamate») resta valida nella direzione ed è muta sul
  **numero**; questa scheda non stabilisce quale numero sia giusto, stabilisce che è una
  variabile da misurare e non da dedurre.
- Corregge la premessa della regola `configs/trial02_rule.yaml`: sceglie l'ampiezza
  massimizzando la media scalata **locale** del banco HepG2, cioè in un regime di `n_conf`
  che non è quello del pannello ufficiale. La regola è stata applicata correttamente; era
  il banco a misurare la cosa sbagliata.
- Non corregge i banchi come strumento di confronto fra bracci a parità di regime.

## 8. Domanda di comprensione

Un bersaglio ha 130 geni confidenti nel riferimento. Conviene dichiararne 130 con il 60% di
segni giusti, o 400 con l'80%? E quale delle due ipotesi su `t02` — segni sbagliati o troppe
poche chiamate — resterebbe in piedi se `n_pred` risultasse 3.000?
