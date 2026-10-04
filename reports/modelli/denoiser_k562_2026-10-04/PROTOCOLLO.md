# Denoiser degli effetti K562: protocollo registrato prima di ogni numero

4 ottobre 2026, notte. Ora esatta: il commit che aggiunge questo file. Viene dopo l'[adattatore di
contesto](../adattatore_contesto_2026-10-04/ESITO_R2.md), che si è fermato. Usa gli stessi dati, le stesse pieghe e le
stesse misure, con una divisione dei bersagli nuova (seme 2). Nessun numero di questa domanda è stato calcolato.

## 1. Domanda

Ogni effetto K562 gwps è stimato da circa cento cellule, quindi contiene rumore. Un modello appreso sull'insieme dei
9.510 effetti K562 può proiettare ogni effetto sui programmi genici comuni (media più prime k componenti). Rende la
direzione più vicina a quella vera **in una linea diversa**, senza perdere la capacità di distinguere un bersaglio
dall'altro?

Se sì, migliora la fonte di direzione di tutti i nostri invii: il t31 su 260 bersagli e la ricetta per la sua parte
K562.

## 2. Modello

- **Dati:** gli effetti K562 gwps nello spazio bulk-lognorm a 50.000, sui 7.681 geni che K562 misura (matrice
  9.510 × 7.681).
- **Stima:** si stimano la media μ (la risposta comune a tutte le perturbazioni) e le direzioni principali `V` di
  `X − μ`, con un SVD.
- **Previsione:** `x̂ = μ + V_k V_kᵀ (x − μ)`.
- **Bersagli usati:** il modello usa gli effetti K562 di tutti i bersagli, anche quelli di test. È lecito: nella gara
  l'effetto K562 dei bersagli ufficiali è noto. Non vede mai la verità delle altre linee.
- **k:** sulla griglia {8, 16, 32, 64, 128, 256, 512, 1.024}, scelto sul coseno medio delle coppie di validazione
  (linee d'addestramento, bersagli di validazione).

## 3. Bracci

| Braccio | Che cos'è |
|---|---|
| `k562` | la copia (la forma del t31) |
| `pca` | il denoiser con il k scelto |
| `mean_only` | solo μ, uguale per tutti i bersagli: controllo. Se va bene come `pca`, il guadagno è la sola risposta comune, che non distingue i bersagli |

## 4. Misure

- **Primaria:** come nell'adattatore. Media sulle coppie di test del coseno con l'effetto vero, sui geni non NaN della
  linea; bootstrap appaiato sui bersagli, 10.000 ricampionamenti, seme 0.
- **Discriminazione (secondaria):** per linea e bersaglio t, la quota degli altri bersagli di test s per cui
  cos(previsto_t, vero_t) > cos(previsto_t, vero_s). È un analogo del PDS.
  - Si calcola sui geni misurati della linea, con i NaN della verità a 0.
  - Si fa la media su t.

## 5. Regola, fissata ora

- **Cancello tecnico:** almeno 100 bersagli di test nella piega R; nessun NaN.
- **Passa** se tutte e tre le condizioni valgono:
  1. nella piega R, `pca − k562` ≥ **+0,01** di coseno, con il limite inferiore dell'IC 95% sopra 0;
  2. nelle pieghe T e H, `pca − k562` ha media positiva;
  3. nella piega R la discriminazione di `pca` non scende di più di 0,01 sotto quella di `k562`.
- **Se passa (fase 2):**
  1. si registra la previsione del t32: il t31 con gli effetti K562 sostituiti da quelli ripuliti sui geni misurati.
     Per bersaglio, si tiene la stessa norma del t31, quindi cambia solo la direzione. Stesso generatore,
     `--effects-scale 2.0`;
  2. stadi 45 e 48.

  **L'invio resta al proprietario.**
- **Se non passa:** nessun candidato, e l'esito si scrive.

## 6. Previsioni, prima di ogni numero

| Quantità (piega R) | Atteso | Fiducia |
|---|---|---|
| `pca − k562` | da −0,005 a +0,04, centro +0,015 | — |
| k scelto | da 32 a 256 | — |
| `mean_only − k562` | da −0,08 a +0,02 | — |
| Discriminazione `pca − k562` | da −0,03 a +0,02 | — |
| Passa | — | 0,4 |

## 7. Limiti

- Le linee di test non sono A, B, C né D, E, F.
- Il coseno non è lo scorer, e la discriminazione locale non è il PDS ufficiale.
- La verità è rumorosa: la piega T ha circa 40 bersagli.
- RPE1 copre geni essenziali, non i bersagli ufficiali.
