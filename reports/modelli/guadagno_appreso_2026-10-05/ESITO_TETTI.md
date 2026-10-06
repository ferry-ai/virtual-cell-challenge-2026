# Esito di M1, M2 e M2b (6 ottobre 2026)

Letti con le regole registrate prima dei numeri: [DIAGNOSI_TETTO_PCA.md](DIAGNOSI_TETTO_PCA.md) (commit `0d12d29`) e
[DIAGNOSI_TETTO_DE.md](DIAGNOSI_TETTO_DE.md) (commit `2dd4cd8`). Sono misure di **tetto** sul cubo r2, non punteggi VCC.

**Uscite** (fuori dal repository, cartella `vcc2026-data/processed/guadagno_appreso_2026-10-05/`):
- `tetto_pca_r1.json` e `.log`;
- `tetto_de_r1.json` e `.log`;
- calibrazione dai nostri invii: `decomp_t35.json` ed `expected_r1.json`, prodotti da script nel blocco note della
  sessione e riassunti qui.

## M1 — calibrazione della MSE sul sito (misurato e interpretato)

- **Lo spazio della MSE.** La MSE ufficiale è in `bulk_lognorm` (TS = 5e4), lo stesso spazio Δ del cubo.
- **L'energia prevista S si ricalcola dagli effetti.** Il calcolo da `predicted_profile` riproduce entro il 2% quella
  misurata sulle cellule del t35 (A: 30.979 contro 30.388). La quota comune è circa l'1%.
- **Due invii con la stessa direzione** (coseno 0,79–0,81 fra le due previsioni):

  | Invio | S per contesto | MSE grezza |
  |---|---|---|
  | t32 | ≈ 156 | 1,038 |
  | t34 | ≈ 29.500 | 7,649 |

- **Che cosa se ne ricava** (interpretazione: modello a due punti, A del t32 trascurabile):
  - l'energia vera è E ≈ 4.100–4.450 per contesto;
  - il residuo del generatore è U ≈ 0;
  - l'allineamento della direzione K562×2 è c ≤ 0,10.
- **Che cosa serve.** All'ampiezza ottima la grezza è 1 − c²: per superare lo zero scalato serve c > 0,12.

## M2 — proiezione PCA sulla base delle sorgenti: **non passa**

**Scelta onesta** (k e λ scelti sulle altre quattro linee):

| Linea | Scelta | MSE | PDS contro `all` a 1,576 | c |
|---|---|---|---|---|
| H1 | k100, λ 0,75 | 0,979 | −0,136 | 0,158 |
| HepG2 | k200, λ 0,5 | 0,890 | −0,033 | 0,423 |
| RPE1 | k100, λ 0,75 | 0,924 | −0,061 | 0,308 |
| Jurkat | k100, λ 0,75 | 0,906 | −0,060 | 0,315 |
| K562 | k200, λ 0,75 | 0,904 | −0,040 | 0,331 |

- **Regola:** la MSE è ≤ 0,95 su 4/5 linee, ma il PDS non perde più di 0,01 su **0/5**. Non si passa a M3.
- **La sola ampiezza** (`all` a λ = 0,5, scelta onesta) dà una MSE da 0,897 a 0,958 col PDS invariato, e c da 0,21 a
  0,36.
- **Stima sul sito** (interpretazione): con c da 0,2 a 0,3 vale +0,005…+0,013 sulla media, prima di quello che si
  perde sui membri DE abbassando l'ampiezza. È sotto la soglia d'impatto.

## M2b — chiamare solo i primi N geni: **non passa**

| Linea | \|R\| medio | Jaccard di «tutti» | Scelta onesta | Jaccard | Segno su P∩R | Rapporto |
|---|---|---|---|---|---|---|
| H1 | 2.494 | 0,190 | `det`, N 1000 | 0,098 | 0,64 | 0,51 |
| HepG2 | 495 | 0,057 | `det`, N 2000 | 0,089 | 0,69 | 1,57 |
| RPE1 | 613 | 0,077 | `det`, N 2000 | 0,115 | 0,64 | 1,50 |
| Jurkat | 283 | 0,035 | `det`, N 2000 | 0,056 | 0,70 | 1,60 |
| K562 | 312 | 0,037 | `det`, N 2000 | 0,056 | 0,66 | 1,50 |

- **Regola:** il rapporto è ≥ 3 su **0/5** linee; il Jaccard medio è 0,083.
- **Il limite è l'accuratezza del segno del transfer:**
  - 0,58–0,62 su tutti i geni;
  - 0,64–0,73 anche fra i più sicuri;
  - il reach proxy, con l'ordinamento migliore (`z`), è solo 0,03–0,26.
- **Spegnere i geni fuori dai primi N costa al profilo aggregato:** con N = 200 il coseno scende da 0,27–0,36 a
  0,12–0,18.
- **Avvertenza.** Il proxy della chiamata del cubo (|y| ≥ 3·se nel pseudobulk) dà insiemi veri molto più grandi delle
  chiamate per cellula dei banchi (N_conf con mediana da 2 a 39). Il regime del sito non è riprodotto, e la regola
  si legge per quello che misura.

## Che cosa ne segue (interpretazione)

1. **Il fattore che limita è la qualità del transfer per il contesto nuovo,** non l'emissione. Lo mostrano tre cose:
   - l'allineamento del profilo aggregato è 0,2–0,36 sul cubo e ≤ 0,10 sul sito per K562×2;
   - il segno sui geni DE è giusto solo per il 60–70%;
   - ampiezza, PCA e selezione delle chiamate spostano al più circa +0,01.
2. **La leva con l'effetto più grande misurato resta più dati e più linee sorgente.** La curva dello stadio 1 dà circa
   +0,01 di coseno per linea, senza saturazione a 8, ed è la strada della banca estesa di Davide. Aiutarlo a chiudere
   il rifit esteso vale più di altre correzioni dell'emissione.
3. **Lo spostamento dei conteggi con la rete L1 (t35, +0,0126 misurato sul sito)** resta l'unico guadagno
   dell'emissione già dimostrato. Si applica sopra qualunque profilo aggregato, anche al candidato di Davide.
