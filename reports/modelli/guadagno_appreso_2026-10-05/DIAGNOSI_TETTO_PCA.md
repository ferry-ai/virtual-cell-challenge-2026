# Tetto: quanto alza l'allineamento del profilo aggregato una proiezione sulla base delle sorgenti?

6 ottobre 2026. Claude Code per Alfredo, che ha chiesto in chat di procedere per milestone («andiamo»).

**Registrato prima di ogni numero.** È una misura del **tetto** (M2 del piano), non un modello né un candidato.

## Perché (M1, calibrazione dai nostri invii)

- **Che cosa è la MSE.** La MSE ufficiale (`expr_mse_unbiased_capped_norm`, cell_eval2 0.16.0) è calcolata in
  `bulk_lognorm` con TS = 5e4: log1p della composizione del pseudobulk. È lo stesso spazio Δ del cubo
  (x = 0,05 · CPM).
- **Energia prevista S, ricalcolata dagli effetti.** Il calcolo da `predicted_profile` riproduce entro il 2% quella
  misurata sulle cellule generate del t35 (30.979 contro 30.388 sul contesto A).
- **Invii sul sito:**

  | Invio | S per contesto | MSE grezza |
  |---|---|---|
  | t32 (nostro t30 del 3/10) | ≈ 156 | 1,038 |
  | t34 | ≈ 29.500 | 7,649 |

  Il t32 ha quasi la stessa direzione del t34 (coseno 0,79–0,81), con l'ampiezza ridotta.
- **Modello.** Si scrive grezza = 1 + (S − 2A + U)/E, dove:
  - E è l'energia vera;
  - A è il prodotto scalare fra previsione e verità;
  - U è il rumore del generatore che la correzione non toglie.
- **Che cosa ne segue, con U ≥ 0 e A del t32 trascurabile:**
  - E ≈ 4.100–4.450 per contesto;
  - U ≈ 0: il generatore non è la causa;
  - l'allineamento della direzione K562×2 è c ≤ 0,10.
- **Che cosa serve.** All'ampiezza ottima la grezza vale 1 − c². Per avere la MSE scalata > 0 (zero a 0,986) serve
  c > 0,12. Per 0,1 scalato serve c ≈ 0,33.
- **Unica leva:** alzare l'allineamento c del profilo aggregato. Le entrate che dichiarano MSE scalata 0,2–0,4
  (ranghi 16, 21, 154) parlano di restringimento, smussamento PCA ed energia per accordo.

## Misura (cubo r2, 5 linee tenute fuori, aggregazioni ufficiali come in `modo_comune_alfa_ros.py`)

- **Base.** Per ogni linea L, la base V_k è data dalle prime k direzioni singolari degli effetti dei gruppi sorgente:
  - si prendono le medie di gruppo, con la stessa regola del transfer `all`, su un campione fino a 1.500 chiavi per
    gruppo, L esclusa;
  - k ∈ {5, 10, 20, 50, 100, 200}, più la proiezione assente.
- **Previsione:** P = λ · T_all V_k V_kᵀ, con λ ∈ {0,1, 0,2, 0,3, 0,5, 0,75, 1, 1,576, 2,4}.
- **Si riportano:**
  - la MSE (rapporto di somme, verità senza rumore);
  - la PDS (1 − rango/n);
  - il coseno aggregato c = Σ⟨Δp, Δy⟩ / √(ΣΔp² · Σ‖Δy‖²_senza rumore).
- **Scelta onesta.** Per ogni L, (k, λ) è scelto minimizzando la MSE media sulle **altre quattro** linee, e si riporta
  su L.

## Lettura (fissata ora)

- **Passa a M3** (smussatore appreso) se la scelta onesta dà:
  - MSE ≤ 0,95 su almeno 3 linee su 5;
  - PDS non peggiore di −0,01 contro `all` all'ampiezza di produzione, su almeno 4 linee su 5.
- **Se nessun k batte la proiezione assente** di almeno 0,02 di MSE su almeno 3 linee: la PCA non è la leva.
  Resta solo la scelta dell'ampiezza, il cui tetto si stima con 1 − c² a k assente.
- **Avvertenza.** Il cubo ha effetti più forti di A/B/C: si confronta c, non la MSE assoluta, per stimare il sito.

## Previsione (soggettiva)

- **c a k assente:** 0,2–0,3.
- **Miglior k:** 20–50, con c +0,03…+0,10.
- **MSE della scelta onesta:** 0,88–0,95.
