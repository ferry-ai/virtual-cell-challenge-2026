# Rete dei pesi delle sorgenti: impara quanto pesare ogni linea, dai controlli e dal consenso

5 ottobre 2026, verso le 18:55 CEST. Claude Code per Alfredo, che in chat ha scelto l'«opzione 2»: una rete piccola
nella catena del transfer `all`, provata entro stasera.

**Registrato prima del codice della rete e di ogni suo numero.** Le soglie non si spostano dopo i risultati.

## 1. Domanda e tetto noto

Una rete che sceglie per ogni bersaglio il peso di ciascun gruppo sorgente migliora la direzione di `all` sulla linea
tenuta fuori? `all` è la media a pesi uguali sui gruppi che misurano la coppia.

**Il tetto è già misurato** ([ESITO](ESITO.md) §3.2): pesi per linea scelti guardando la verità danno da +0,004 a
+0,013 di coseno. La rete ha più libertà dell'oracolo, perché pesa per bersaglio, ma usa meno informazione. Quindi il
guadagno atteso è piccolo, e la soglia sotto è dimensionata su questo tetto.

## 2. Modello

- **Uscita:** T_w[k, j] = Σ_g w[k, g] · P_g[k, j] / Σ_g w[k, g], sommando solo sui gruppi g con P_g[k, j] finito.
  - P_g è la media del gruppo g di Davide (`group_stats`, identica a `arms.group_mean`).
  - w[k, ·] = softmax degli score sui gruppi che misurano il bersaglio k.
- **All'inizio** l'ultimo strato è a zero, quindi tutti i pesi sono uguali e **T_w = T_all esattamente.** La parità si
  verifica.
- **Score:** MLP 6 → 16 → 16 → 1 (ReLU) sulle caratteristiche della coppia (bersaglio k, gruppo g), viste dalla linea X
  da prevedere:
  1. correlazione dei profili basali (log1p CPM) di X e g sui geni del cubo;
  2. log1p delle cellule di g per k;
  3. log dell'SE medio della media di g per k;
  4. log della norma di P_g[k];
  5. **consenso:** coseno fra P_g[k] e la media degli altri gruppi per k;
  6. quota dei geni misurati da g per k.

## 3. Addestramento, per ogni linea tenuta fuori L

- **Righe:** i gruppi h ≠ L con almeno 50 chiavi, fino a 300 chiavi ciascuno (hash `fit`, come nello stadio 1).
  - Le sorgenti sono i gruppi ≠ L, h.
  - La verità è il raw di h; la basale X è quella di h.
  - Le medie comuni sono quelle senza L (`Context`).
- **Geni:** 6.000 colonne casuali per h (seme 0).
- **Perdita:** meno il coseno medio per bersaglio fra T_w·d e y·d, con d = x/(1+x) e x = 0,05·CPM dei controlli di h.
  È la geometria della MSE dello scorer al primo ordine. Il gene bersaglio è escluso.
- **Ottimizzazione:** Adam, lr 3e-3, decadimento 1e-4, 300 passi a batch intero su GPU, seme 0. Nessuna scelta di
  iperparametri.
- **Applicazione a L:** caratteristiche viste da L (basale di L), sorgenti ≠ L.

## 4. Misura e regola

Stesse misure, bersagli e bootstrap dello stadio 1 (`guadagno.measures` e `boot_diff`), braccio `pesi` contro `all`.
La norma è riportata a quella di T_all per bersaglio.

**La rete passa all'invio di stasera (t36 = `pesi` al posto di `all`) solo se:**
- la media sulle 5 linee di `pesi − all` nel coseno è ≥ **+0,005**;
- su almeno 3 linee su 5 il limite inferiore all'IC 90% della differenza di coseno è > 0;
- su nessuna linea l'indice di discriminazione scende di più di **0,005**.

**Altrimenti** si invia `all` da solo, se il proprietario conferma, e la rete dei pesi si chiude in questa forma.

**Si riportano:** la distribuzione dei pesi per gruppo e linea, e la parità all'inizio.

## 5. Produzione, solo se passa

- La stessa rete viene riaddestrata su tutti i 10 gruppi: ogni gruppo h fa da linea, con sorgenti gli altri.
- Si applica ad A, B e C con la basale dei controlli ufficiali del contesto (`competition_A/B/C` del `basal.npz` del
  cubo, solo come ingresso).
- Esportazione con lo stesso formato di [esporta_all.py](esporta_all.py), × 1,576.
- Emissione t28 allo stadio 45.

## 6. Previsione (soggettiva)

- **`pesi − all`, coseno:** da +0,000 a +0,008, media +0,003.
- **Fiducia 0,3** che la regola passi.

## 7. Limiti

Valgono gli stessi dello stadio 1 (effetti, non cellule; 10 gruppi già letti; regime C). Inoltre un guadagno di
+0,005 di coseno è sotto il rumore del sito: anche se la regola passa, non è una promessa di punteggio.
