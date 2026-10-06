# Tetto: quanto valgono i membri DE se si chiamano solo i primi N geni, ordinati per confidenza?

6 ottobre 2026. Claude Code per Alfredo, nel piano a milestone («andiamo»), dopo M2 ([DIAGNOSI_TETTO_PCA.md](DIAGNOSI_TETTO_PCA.md)).

**Registrato prima di ogni numero.** È una misura del **tetto** (M2b), non un modello né un candidato.

## Perché

- **Esito di M2** (`processed/guadagno_appreso_2026-10-05/tetto_pca_r1.json`):
  - la PCA abbassa la MSE su 4 linee su 5, ma fa perdere PDS su 5 su 5 (da −0,03 a −0,14), quindi non passa;
  - l'ampiezza da sola (`all` a λ = 0,5, scelta onesta) dà una MSE da 0,90 a 0,96 col PDS invariato, e un coseno
    c da 0,21 a 0,36 sul cubo;
  - sul sito, dove la direzione K562×2 ha c ≤ 0,10, vale circa +0,005…+0,013 sulla media: sotto la soglia
    d'impatto.
- **Tutti gli invii del team hanno il Jaccard DE grezzo a 0,022–0,036, cioè scalato ≈ 0.**
  - Vale per ogni ampiezza: anche il t32 con effetti quasi nulli è a 0,028.
  - Lo zero ufficiale è circa 0,033. Il replicato a metà dati sul contesto A è circa 0,38 (docstring di
    `de_sig_jaccard`, cell_eval2 0.16.0).
- **Sui banchi v2 di Davide**, con l'emissione del t28, le previsioni chiamano 900–3.600 geni per bersaglio. Il
  replicato ne chiama 24–400, la verità ha una mediana di N_conf da 2 a 39. Il Jaccard resta 0,01–0,05.
- **Che cosa leggono i membri DE ufficiali** (`metrics/de.py`, `metrics/direction.py`):
  - **Jaccard:** gli insiemi significativi, senza il gene bersaglio;
  - **fedeltà:** la purezza del segno fra le chiamate, corretta per il caso, per min(1, n_pred/N_conf);
  - **reach:** la profondità a cui l'ordinamento per |lfc| previsto resta puro di segno, divisa per N_conf.

  Tutti premiano poche chiamate col segno sicuro, ordinate per confidenza.

## Misura (cubo r2, 5 linee tenute fuori, bersagli e transfer `all` come in M2)

- **Insieme vero R** (proxy della chiamata):
  - |y| ≥ 3·se;
  - CPM di L ≥ 5;
  - i geni bersaglio del pannello sono esclusi.
- **Insieme previsto P_N:** i primi N geni secondo un punteggio, con N ∈ {10, 20, 50, 100, 200, 500, 1000, 2000};
  in più «tutti i geni con T ≠ 0», che è il comportamento attuale.
- **Punteggi, tutti dalle sole sorgenti:**
  - `mag` = |T|;
  - `z` = |T| / se_T;
  - `agree` = |T| · accordo fra gruppi;
  - `det` = |T| · √x, dove x è l'espressione dei controlli di L.
- **Per bersaglio, poi in media:**
  - Jaccard;
  - richiamo |P∩R|/|R|;
  - accuratezza del segno su P∩R;
  - reach proxy: la massima profondità dell'ordinamento per punteggio a cui la purezza del segno sui geni di R
    resta ≥ 0,9, divisa per |R|.
- **Effetto sul profilo aggregato.** PDS e MSE di λ · T ristretto a P_N, con λ ∈ {0,5, 1, 1,576}, per sapere quanto
  costa spegnere gli altri geni.
- **Scelta onesta.** (punteggio, N) è scelto sulle altre quattro linee massimizzando il Jaccard medio.

## Lettura (fissata ora)

- **La leva è confermata (passa a M3)** se la scelta onesta dà:
  - Jaccard ≥ 3× quello di «tutti i geni con T ≠ 0» su almeno 4 linee su 5;
  - un Jaccard assoluto ≥ 0,08 in media.
- **Il profilo aggregato si separa dalle chiamate (M4)** se il PDS di T ristretto a P_N perde più di 0,01 contro T
  intero su almeno 3 linee. In quel caso si tiene T intero per il profilo aggregato e si separano le chiamate.
- **Avvertenza.** Il proxy della chiamata è a livello di pseudobulk; il Jaccard ufficiale viene dal Wilcoxon sulle
  cellule. Si confrontano i rapporti, non i valori assoluti.

## Previsione (soggettiva)

- **Jaccard di «tutti»:** 0,01–0,04.
- **Miglior scelta onesta:** 0,08–0,20, con N ≈ 50–200 e il punteggio `det` o `z`.
- **Accuratezza del segno su P∩R:** 0,7–0,85.
