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
