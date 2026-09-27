# La rete su molti contesti: autoverifica e regola di r1

Disegno e codice: [DISEGNO.md](DISEGNO.md) (claude2, base di lancio, 27/09 sera; proposta, nulla eseguito da lui).

## Autoverifica (misurato, Kaggle, 27/09 alle 22:00 circa)

`train.py --selftest` in un notebook Kaggle privato su CPU (torch 2.10, numpy 2.0.2, pandas 2.3.3; i tre file
copiati con sha256 controllato). Esito in `autoverifica_kaggle_r1.txt`: **14 controlli su 14**, in 139 s. In breve:
- **fuga d'informazione:** con le 604 righe tenute fuori sovrascritte da rumore, tutto ciò che l'addestramento vede
  e le previsioni di prova restano identici al bit;
- **il profilo trasferito m** coincide con un calcolo a cicli semplici;
- **mondo con interazione piantata:**
  - la rete batte il trasferimento (+0,102 e +0,251 di skill, intervalli sopra zero) e la sua versione cieca
    (+0,056 e +0,326);
  - prevede la differenza fra due linee tenute fuori con correlazione 0,64, contro 0,010 delle permutazioni;
- **mondo nullo:** la rete non batte la sua versione cieca oltre il rumore (−0,0001 e +0,0000) e non perde sul
  trasferimento;
- cieco e scambio fanno quello che dicono; due addestramenti su CPU dallo stesso seme sono identici.

Il codice impara un'interazione quando c'è e non se la inventa quando manca, sui dati sintetici. **Non dice niente
sui dati veri.**

## Regola di r1, fissata alle 22:03 del 27/09 (prima di assemblare il dataset vero e di addestrare)

**Che cosa gira.**
- **Dati:** `data.py`, registro `contesti.csv` (K562, tre condizioni CD4, HCT116, HEK293T, KOLF2.1J; A549 è
  knockout e non entra, perché resta fuori senza `--modalities`). La prova a vuoto (`--dry-run`) conta 91.860 righe,
  12.477 geni e 6,88 GB previsti.
- **Disegni del §6.2 di DISEGNO:**
  - **E1**, regime C, una famiglia intera tenuta fuori alla volta: verità `k562`, `cd4_Rest`, `orion_hct116`,
    `orion_hek293t`, `kolf`;
  - **E2:** `orion_hct116` + `orion_hek293t`; `cd4_Rest` + `cd4_Stim48hr`;
  - **J:** `k562` e `orion_hct116`.
  - 1.000 bersagli di prova per verità, misurati nella verità e in almeno due gruppi visibili, fuori dal pannello e
    dallo schermo essenziale del K562. Iperparametri di default del codice.
- **Tre semi** (0, 1, 2) per disegno. La regola si legge sulla media delle previsioni dei tre semi, e vale solo se il
  segno di rete − cieca è lo stesso nei tre semi su almeno quattro verità E1 su cinque.
- **Misura:** `score_pred.py`, Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen con bootstrap appaiato al 95 %:
  - su tutti i bersagli: decide;
  - sullo strato forte (quartile alto di geni con |Z| ≥ 3 nella verità): riportato, da solo non decide.

**Letture.**
- **E1, uso del contesto:** rete − cieca.
  - Passa se Δ è positivo su almeno quattro verità su cinque, con l'intervallo sopra zero su almeno due e nessun
    intervallo interamente sotto −0,002.
  - Il contrario passa a segni invertiti.
- **E1, candidato:** rete − `excl`, stessa regola.
- **E1, diagnostica:** rete − scambio. Se la rete batte il cieco ma non lo scambio, il guadagno viene dalla forma e
  non dal contesto giusto: è la lezione di r1 del modello a cancelli.
- **E2:** per coppia, la correlazione media della rete è positiva se l'intervallo sta sopra zero e la media supera il
  quantile 97,5 % delle permutazioni.
  - Passa su entrambe le coppie; è parziale su una: un'ipotesi da replicare su HIPSCI.
- **J:** rete − ripiego (0,1 × partner STRING + testa cis). Passa se è positivo su entrambe le verità, con l'intervallo
  sopra zero su almeno una.

**Che cosa ne segue:**
- **uso del contesto ed E2 passano:** prima prova interna che una parte dell'interazione bersaglio × contesto si
  recupera dai controlli. Candidato per il banco sul pannello e per il banco HepG2 con lo scorer vero, ciascuno con
  una regola sua;
- **passa solo il candidato:** la rete è un trasferimento migliore, non un modello del contesto. Candidato come
  sostituto di `excl`, stessa trafila;
- **J passa:** valore per i bersagli nuovi del set finale, con la stessa trafila;
- **nulla passa:** esito negativo per questa rete con questi contesti. Prima di cambiare architettura va letta
  l'ablazione «più contesti» (§7, punto 5).

**Falsificazione** (dal §6.4 di DISEGNO, fissata qui): uno qualunque dei sette punti di quella lista toglie alla rete
il valore corrispondente.

**Modifiche al codice prima di r1:** solo quelle necessarie a farlo girare sui dati veri, dichiarate qui con l'ora,
senza guardare risultati sui dati veri.

## Sera del 27/09: la corsa di produzione su Colab (misurato; `prod_r1/`)

**Che cosa è girato.** Job Colab 053, GPU (torch 2.11, CUDA 12.8), dataset `rete_contesti_r1`, con tutti i contesti
CRISPRi visibili e previsione dei 300 bersagli del pannello in A, B e C:
- fase 1: famiglia di validazione `orion` (HCT116 e HEK293T) tenuta fuori, addestramento su CD4, K562 e KOLF2.1J;
- fase 2: di nuovo su tutto, per il numero di passi migliore.

Una prova di 40 passi sul portatile misura 3,7 s per passo su CPU; su GPU sono 0,22 s.

**La curva di validazione.** La famiglia `orion` fa da contesto nuovo.

| Passo | Perdita sulle famiglie di training | Perdita su `orion` tenuta fuori |
|---|---|---|
| 250 | 0,01077 | **0,009415** (la migliore) |
| 500 | 0,01067 | 0,009516 |
| 1.000 | 0,01031 | 0,009609 |
| 1.500 | 0,00988 | 0,009694 |
| 2.250 | 0,00970 | 0,009658 (arresto: 8 valutazioni senza miglioramento) |

- L'ampiezza del trasferimento scende da 0,0156 a 0,0140, quella dei partner STRING sale da 0,0207 a 0,0262.
- La fase 2 riaddestra per 250 passi: la rete finale resta vicina al suo punto di partenza, cioè il trasferimento
  calibrato più il termine dei partner.
- Calibrazione della fase 2: A = 0,028, A_q = 0,035. La direzione trasferita spiega pochissimo della scala degli
  effetti grezzi dei bersagli presi a caso, come nel modello a cancelli (A_fit 0,01–0,03).

**Lettura (interpretazione).** Quello che la rete impara oltre il punto di partenza è specifico delle linee viste: la
perdita di training scende del 10 %, quella sulla famiglia nuova sale del 2,6 %. È lo stesso messaggio di r1 del
modello a cancelli e della letteratura. **Non è la regola di r1:** una sola famiglia di validazione, un seme, nessun
proxy.

**La direzione, prima di imparare (misurato; prova di 5 passi, contesto A, 183 bersagli).** Coseno mediano con gli
effetti del t25 sui geni che la rete prevede:

| Componente | Coseno con il t25 |
|---|---|
| il trasferimento della rete (con KOLF2.1J e le condizioni CD4 pesate a parte) | 0,68 (0,54–0,84) |
| il termine dei partner (circa il 26 % della norma) | 0,01 |
| l'uscita della rete | 0,32 |

La rete propone una direzione lontana da quella del t22 per scelte di disegno, prima di aver imparato qualcosa.

**Decisione del proprietario, 27/09 alle 23:30 circa:** niente invio della rete stanotte, lo slot va al t24 (rumore
fra semi). La notte serve a capire se la rete funziona e a integrare altri dataset. Varianti esplorative su Colab
(job 056: senza partner, peso sui bersagli forti, solo cancelli, apprendimento lento, sola ampiezza, disegno di
default con valutazioni ogni 50 passi). Sono descrittive e non sono r1.

**Quanto la rete di produzione usa il contesto (misurato sulle sue previsioni per A, B e C, 300 bersagli).**
- La rete si allontana dalla sua versione cieca: coseno mediano fra 0,90 e 0,91; la differenza vale dal 42 al 45 %
  della norma.
- Le previsioni per i tre contesti di gara si allontanano fra loro: coseno fra 0,86 e 0,91; le differenze valgono dal
  42 al 54 % della norma.
- In 250 passi, quindi, la rete ha imparato a differenziare molto i contesti. La curva della famiglia tenuta fuori
  non dice se queste differenze aiutano: ha il minimo alla prima valutazione e nessuna misura al passo 0. Lo diranno
  la variante con valutazioni ogni 50 passi e l'E2 di r1.

**Variante senza partner (job 056, misurato; `runs/rete_abl_r1/nopart` su Drive).** Perdita su `orion` tenuta fuori:

| Passo | 50 | 100 | 250 | 500 | 1.100 |
|---|---|---|---|---|---|
| Perdita | 0,009385 | **0,009382** | 0,009418 | 0,009534 | 0,009666 |

Senza partner il punto migliore è un poco più basso di quello del disegno di default (0,009415). Dal passo 100 in poi
la perdita sulla famiglia nuova sale: anche qui ciò che la rete impara non si porta su una linea nuova.
