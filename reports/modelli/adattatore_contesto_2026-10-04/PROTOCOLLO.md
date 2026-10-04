# Adattatore di contesto: protocollo registrato prima di ogni numero

4 ottobre 2026, notte. Ora esatta: il commit che aggiunge questo file. Su richiesta del proprietario: «io voglio
migliorare un modello, hai tutta la notte». Sostituisce, come strada, la [propagazione con i soli
controlli](../propagazione_contesto_2026-10-04/PROTOCOLLO.md), che era un transfer e per cui in locale mancano le
cellule di controllo. Nessun braccio è stato calcolato. Gli unici conti fatti prima sono i conteggi
dell'[inventario](../propagazione_contesto_2026-10-04/inventario.json).

## 1. Domanda

Un modello **appreso** che trasforma l'effetto misurato in K562 nell'effetto in una linea nuova, guardando solo il
profilo dei controlli di quella linea, prevede la direzione vera meglio della copia di K562? La copia di K562 è ciò che
il t31 fa su 260 bersagli su 272 ([CP-0058](../../../docs/checkpoints/0058-t31-solo-k562.md)). La previsione deve
coprire anche i geni che K562 non misura.

## 2. Dati, tutti in locale

Sono le chiavi in `vcc2026-data/kaggle/rete_sorgenti_r1_train_output/consegna/chiavi`: effetti aggregati per bersaglio
(lfc in ln, NaN = non usabile), profilo basale e geni misurati.

- **Ingresso:** K562 gwps, 9.510 bersagli, 7.681 geni misurati.
- **Linee d'uscita:** HipSci (19 chiavi), RPE1, Tian 2019 iPSC, Tian 2019 neuroni, Tian 2021 neuroni.
- **Escluso:** K562 essential, perché è la stessa linea della sorgente.
- **Spazio:** ogni effetto si porta nello spazio bulk-lognorm a 50.000, quello di MSE e PDS:
  `d = log1p(5e4 p e^{lfc}) − log1p(5e4 p)`, con `p = expm1(basal)/1e4` della linea a cui l'effetto appartiene.

## 3. Divisione, fissata ora (seme 0)

- **Bersagli:** l'insieme dei bersagli delle linee d'uscita che K562 gwps misura, diviso a caso in 60% addestramento,
  15% validazione e 25% test. Un bersaglio di test non compare come uscita in nessuna linea d'addestramento. Imita la
  gara: i bersagli ufficiali quasi non compaiono nelle linee pubbliche.
- **Linee (pieghe):**

  | Piega | Linea di test | Linee d'addestramento | Ruolo |
  |---|---|---|---|
  | **R** | RPE1 | HipSci, Tian (tutte) | **primaria** |
  | **T** | neuroni Tian 2021 | HipSci, RPE1, Tian 2019 iPSC (fuori anche Tian 2019 neuroni, stesso tipo cellulare) | replica |
  | **H** | 2 donatori HipSci (le loro 4 chiavi, i primi due donatori in ordine alfabetico) | il resto | replica |

- **Valutazione:** sulle coppie (linea di test, bersaglio di test). L'arresto anticipato e la scelta degli iperparametri
  usano solo le coppie (linee d'addestramento, bersagli di validazione).

## 4. Bracci

| Braccio | Che cos'è | Appreso? |
|---|---|---|
| `k562` | Copia di `d_K` sui geni che K562 misura, 0 sugli altri: la forma del t31 | no, base |
| `ridge` | Mappa lineare da `d_K` (7.681 geni) a `d_L` (tutti i geni), ridge in forma duale, uguale per tutte le linee; λ scelto sulla validazione | sì |
| `adapter` | Rete: percorso identità con un guadagno per gene, più una mappa di rango 64 dai geni K562 a tutti i geni. Guadagni e mappa sono modulati da un MLP sulle caratteristiche del gene: embedding appreso, basale della linea, basale di K562 | sì |
| `adapter_swap` | `adapter` con il basale della linea di test sostituito dalla media dei basali d'addestramento | controllo del contesto |

**Addestramento di `adapter`:**
- **Perdita:** 1 − coseno per coppia, sui geni non NaN della linea d'uscita, più 0,1 × l'errore quadratico relativo.
- **Ottimizzatore:** AdamW, lr 1e-3, weight decay 1e-4, batch di 64 coppie.
- **Arresto:** al massimo 3.000 passi, arresto anticipato dopo 10 valutazioni (ogni 100 passi) senza miglioramento del
  coseno di validazione.
- **Ripetizioni:** un seme per piega; due semi in più solo se la regola passa.

## 5. Misure

- **Primaria:** media sulle coppie di test del coseno fra `d` previsto e `d` vero, sui geni non NaN della linea di
  test.
- **Secondarie:** coseno sui soli geni che K562 non misura (U) e sui soli geni che misura (M).
- **Incertezza:** bootstrap appaiato sui bersagli, 10.000 ricampionamenti, seme 0.

## 6. Regola, fissata ora

- **Cancello tecnico:**
  - almeno 100 bersagli di test nella piega R;
  - nessun NaN nelle previsioni;
  - coseno di validazione di `adapter` sopra quello di `k562` sulle linee d'addestramento. Se fallisce, il modello non
    ha imparato e la piega di test non si legge.
- **Un modello appreso passa** se nella piega R `modello − k562` ≥ **+0,02**, con il limite inferiore dell'IC 95% sopra
  0, e nelle pieghe T e H la media di `modello − k562` è positiva.
- **Scelta del candidato:**
  - se passano entrambi, `adapter` solo se `adapter − ridge` ha l'IC sopra 0 nella piega R, altrimenti `ridge`, che è
    più semplice;
  - se ne passa uno solo, quello.
- **`adapter_swap` non decide.** Se `adapter ≈ adapter_swap`, il guadagno non viene dal contesto: cambia la lettura,
  non l'uso.
- **Se un modello passa (fase 2, stanotte):**
  1. si addestra il modello scelto su tutte le linee e sui bersagli d'addestramento e di validazione;
  2. si esportano gli effetti per A, B, C con il basale dai loro controlli;
  3. si registra la previsione del t32 prima di generare: stessa regola d'ampiezza del t31 (norm-match sui bersagli
     coperti, `--effects-scale 2.0`) e stesso generatore, quindi un solo fattore cambiato contro il t31, cioè la
     direzione;
  4. stadi 45 e 48.

  **L'invio resta al proprietario.**
- **Se nessuno passa:** nessun candidato, e l'esito si scrive.

## 7. Previsioni, prima di ogni numero

| Quantità (piega R) | Atteso | Fiducia |
|---|---|---|
| `adapter − k562` | da 0,00 a +0,06, centro +0,02 | — |
| `ridge − k562` | da −0,01 a +0,04 | — |
| Un modello passa la regola | — | 0,45 |
| `adapter − adapter_swap` | da −0,005 a +0,02 | — |

## 8. Limiti

- RPE1 è uno schermo su geni essenziali, e gli altri pannelli sono mirati: i bersagli non sono quelli ufficiali.
- La verità è rumorosa: per HipSci 83 cellule per bersaglio in mediana, per RPE1 72.
- Le linee del banco non sono A, B, C né D, E, F. Un coseno non è un punteggio VCC (CP-0027, CP-0058).
- Il contesto si legge solo dal basale medio, perché in locale non ci sono cellule di controllo delle linee pubbliche.
- Gli schermi d'uscita HipSci sono 19 donatori molto simili: la varietà di contesti in addestramento è bassa.
