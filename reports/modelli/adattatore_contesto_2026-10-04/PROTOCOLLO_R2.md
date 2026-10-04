# Adattatore di contesto r2: il modello solo dove K562 non misura

4 ottobre 2026, notte. Ora esatta: il commit che aggiunge questo file. Viene **dopo** l'[esito r1](ESITO_R1.md),
quindi l'idea è nata guardando quei numeri. Per questo si prova su **bersagli di test nuovi**: la divisione dei
bersagli usa il seme 1 invece del seme 0. Le linee, le pieghe e i dati sono quelli del
[protocollo r1](PROTOCOLLO.md). Nessun numero della r2 è stato calcolato.

## 1. Domanda

Nella r1 i modelli prevedono con coseno positivo i geni che K562 non misura (U), ma peggiorano quelli che misura (M).
Se si tiene la copia di K562 sui geni M e si usa il modello appreso **solo** sui geni U, la direzione su una linea
nuova migliora rispetto alla copia?

## 2. Bracci

| Braccio | Geni M | Geni U |
|---|---|---|
| `k562` | copia K562 | 0 |
| `hyb_adapter` | copia K562 | β × uscita di `adapter`, addestrato come nella r1 |
| `hyb_adapterU` | copia K562 | β × uscita di un `adapter` addestrato con la perdita sui soli geni U |
| `hyb_ridge` | copia K562 | β × uscita di `ridge` |

- **β:** si sceglie per ciascun braccio sulla griglia {0; 0,25; 0,5; 1; 2; 4}, massimizzando il coseno medio sulle
  coppie di validazione (linee d'addestramento, bersagli di validazione). Con β = 0 il braccio coincide con `k562`.
- **Il resto è come nella r1:** iperparametri, arresto anticipato (`adapterU` lo fa sul coseno di validazione dei soli
  geni U) e misure.

## 3. Regola, fissata ora

- **Cancello tecnico:** come nella r1, ma sulla nuova divisione. Almeno 100 bersagli di test nella piega R; nessun NaN.
- **Un braccio ibrido passa** se nella piega R `braccio − k562` ≥ **+0,01**, con il limite inferiore dell'IC 95% sopra
  0, e nelle pieghe T e H la media è positiva.
  - La soglia è più bassa della r1 (+0,02) perché il braccio ibrido può solo aggiungere la parte U.
  - È fissata ora, prima dei numeri della r2.
- **Scelta:** fra i bracci che passano, il più alto nella piega R. In caso di IC sovrapposti vince il più semplice,
  nell'ordine `hyb_ridge`, `hyb_adapter`, `hyb_adapterU`.
- **Se un braccio passa (fase 2):**
  1. si registra la previsione del t32: geni M **identici al t31**, geni U dal modello scelto riaddestrato su tutte le
     linee con i bersagli d'addestramento e di validazione, β come scelto, lo stesso generatore e
     `--effects-scale 2.0`;
  2. stadi 45 e 48.

  **L'invio resta al proprietario.**
- **Se nessuno passa:** la strada dell'adattatore si ferma, e l'esito si scrive.

## 4. Previsioni, prima di ogni numero

| Quantità (piega R) | Atteso | Fiducia |
|---|---|---|
| Miglior braccio ibrido − `k562` | da 0,00 a +0,03, centro +0,01 | — |
| Un braccio passa | — | 0,45 |
| β scelto per `hyb_adapter` | da 0,5 a 2 | — |

## 5. Limiti in più rispetto alla r1

- Il disegno dei bracci viene dai numeri della r1. I bersagli di test sono nuovi, ma le linee di test sono le stesse.
- β e l'arresto anticipato si scelgono sulle linee d'addestramento: nella r1 la validazione sovrastimava il guadagno
  su una linea nuova.
