# CP-0011 — Primo benchmark modulare su pseudobulk K562/RPE1

- **Data:** 2026-09-14
- **Tipo:** esperimento
- **Redatto da:** agente (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Una decomposizione in base condivisa più un piccolo predittore di coefficienti
batte, a budget comparabile e senza leakage, una MLP unica e il trasferimento
calibrato, sui dati perturbati che abbiamo in locale? Non si assume che la
modularità vinca. Con due soli contesti perturbati, un test che ne esclude uno
è un test di trasferimento, non una dimostrazione di apprendimento della
dipendenza dal contesto.

## 2. Cosa è stato fatto

Inventario delle sorgenti realmente sul disco, poi un pilot su firme
pseudobulk già costruite (e001), senza scaricare atlanti e senza sottomissioni.

```bash
.\scripts\py.cmd scripts/50_inventory_data.py --out reports/benchmark_2026-09-14
.\scripts\py.cmd scripts/51_run_modular_pilot.py --run-id m001 --allow-overwrite
.\scripts\py.cmd -m unittest tests.test_modular_benchmark
```

Configurazione fissata prima dei run in `configs/benchmark.yaml`: metrica
primaria `pooled_mse_vs_null`; margine di non inferiorità `null`; universo
genico = intersezione dei geni misurati; alpha 0,1974 vietato; 160 bersagli
estratti a caso dai 2350 condivisi, non filtrati per effetto (D-011); due seed
(2026, 2027); due direzioni; due protocolli (bersaglio già visto / mai visto).

Bracci: ShrunkTransfer; lineare a basso rango; MLP unica; base congelata + MLP
sui coefficienti; stessa architettura con affinamento congiunto. I modelli
condizionati hanno anche la variante senza descrittore di contesto. I NTC del
contesto di test sono usati da tutti i bracci. Le risposte perturbate di quel
contesto no.

Artefatti pesanti in `C:/Users/ferra/vcc2026-data/artifacts/m001`. Copia
leggera in `reports/benchmark_2026-09-14/`. Documentazione:
`docs/BENCHMARK_MODULARE.md`.

## 3. Cosa si è osservato

Tutti i numeri di questa sezione stanno in
`reports/benchmark_2026-09-14/` oppure in `artifacts/m001`.

**Inventario** (`inventory.json`): due contesti perturbati locali (K562, RPE1);
2390 bersagli condivisi k562_gwps ∩ rpe1_essential a livello di file grezzo,
2350 nelle firme e001 già filtrate a `min_cells=10`; 6714 geni sull'asse
ufficiale in comune fra k562_gwps e rpe1; pannello 2026 coperto 272/300 in
k562_gwps e 0/300 in rpe1 essential; nessun conteggio perturbato a singola
cellula in locale; esperimento generator × predittore sulle sei metriche
**bloccato**.

**Universo genico** (`gene_universe.json`): 6700/18533 geni tenuti quando entra
anche k562_essential (36,2%), 6714/18533 senza. I 11.833 (o 11.819) esclusi
sono non misurati, non invariati. `zero_fill_missing` è falso.

**Pilot, 72 righe** (`comparison_table.md`, `summary.json`, 223 s, picco RSS
505.606.144 byte ≈ 0,47 GiB, VRAM non misurata). 160 bersagli, stesso split
per tutti i bracci.

K562 → RPE1, bersaglio già visto, `pooled_mse_vs_null` (più basso è meglio):

| modello | seed 2026 | seed 2027 |
|---|---:|---:|
| shrunk_transfer | 0,9942 | 0,9955 |
| lowrank_linear | 0,9906 | 0,9906 |
| compact_mlp | 0,9974 | 0,9883 |
| modular_frozen | 0,9763 | 0,9737 |
| modular_joint | 0,9797 | 0,9939 |

Differenza appaiata per bersaglio, modular_frozen − shrunk_transfer, stessa
direzione: media −0,0127 e −0,0110, IC95 che **non** contiene zero su entrambi
i seed (`summary.json`, `paired_differences`). La MLP unica a seed 2026 è
**peggio** di ShrunkTransfer (media +0,036, IC che esclude zero); a seed 2027
l'intervallo contiene zero.

RPE1 → K562, bersaglio già visto, alpha prefissato 1,0 (nessuna coppia interna,
non 0,1974): shrunk_transfer 4,30 volte il nullo; modular_frozen 2,64–2,65;
tutti i bracci **sopra** 1. Predeterminato, non calibrazione cross-context.

Bersaglio mai visto, K562 → RPE1: ShrunkTransfer copertura 0 e MSE/nullo = 1
(non può predire); gli altri bracci circa 0,98 con Pearson mediana 0,20–0,27.
RPE1 → K562, bersaglio mai visto: tutti i bracci appresi **sopra** 1
(1,63–2,51); ShrunkTransfer resta il nullo.

Low-rank con e senza descrittore di contesto: MSE identica a quattro decimali
sulla stessa direzione. Il vettore di contesto non varia in training
(`context_dependence_identifiable: false` in ogni split).

Nessuna riga ha `eleggibile sul test: sì`. `winner_declared` è falso.
`non_inferiority_margin` è null.

**Generator × predittore:** non eseguito.
`missing_generator_bundle.json` elenca campi, coperture, ~0,85 GB (HepG2) o
~1,24 GB (RPE1 single-cell) compressi, lettura a blocchi, 0/300 del pannello.

24 test in `tests/test_modular_benchmark.py` (maschere, leakage, alpha 0,1974,
salvataggio/caricamento, identità delle predizioni).

## 4. Interpretazione e incertezza

**Misura.** Su questo proxy, su 160 bersagli casuali, nella sola direzione
K562 → RPE1 con bersaglio già visto, la base congelata ha un MSE/nullo più
basso di ShrunkTransfer, con IC che esclude zero su due seed. Nella direzione
inversa, senza compressione d'ampiezza, **tutti** i modelli fanno peggio del
nullo. Il descrittore di contesto non è identificabile. Le sei metriche VCC
non sono state calcolate.

**Interpretazione.** Non è un verdetto sulla modularità, e non è un punteggio
di gara. Il guadagno K562 → RPE1 è dell'ordine di due punti percentuali di
MSE/nullo su un sottoinsieme, in spazio log2FC. La direzione inversa conferma
CP-0003: trasferire a piena ampiezza è peggio che non prevedere nulla. Alpha 1
era la regola prefissata, non un errore di codice.

**Ipotesi, non misura.** Che lo stesso ordine resista sui 2350 bersagli, sui
contesti A/B/C, o sulle sei metriche; che un terzo contesto perturbato renda
`z_c` utile; che un generatore migliore cambi il confronto.

Se si dovesse riassumere in una parola il confronto architetturale: **inconcludente**
per l'adozione. I numeri esistono; non bastano a scegliere un modello.

## 5. Spiegazione semplice

Abbiamo due linee cellulari con perturbazioni già misurate, K562 e RPE1, e
nessuna cellula perturbata vera dei tre contesti della gara. Abbiamo chiesto:
se spezzo la previsione in «programmi condivisi» più «un piccolo adattamento»,
faccio meglio di una rete sola, o del vecchio trasferimento rimpicciolito?

È come chiedere se un dizionario di frasi fatte più un adattatore batte sia
un copincolla rimpicciolito sia una rete che scrive tutta la frase da sola —
ma con un solo dizionario di partenza. Con una sola lingua di allenamento non
puoi dire di aver imparato a cambiare lingua. Per questo il test che tiene
fuori RPE1 non è una prova generale, e per questo la casella «contesto
identificabile» è no.

## 6. Conseguenze

- D-024: per questo confronto l'universo genico è l'intersezione misurata, non
  il riempimento a zero. Riaperto se una fattorizzazione mascherata recupera i
  geni esclusi senza inventare evidenza.
- D-025: metrica primaria `pooled_mse_vs_null` in spazio proxy; non inferiorità
  non dichiarata; leave-one-context-out con due contesti = trasferimento, non
  apprendimento generale del contesto.
- D-003 resta bloccata: manca il bundle a singola cellula.
- D-006/D-012: l'alpha 0,1974 non entra nei fold che tengono fuori K562 o RPE1;
  confermato in codice (`reject_forbidden_alpha`).
- Il prossimo passo che riduce di più l'incertezza resta R-1 della roadmap: un
  bundle di conteggi perturbati reali più NTC, sulle sei metriche, con
  predittore e generatore fatti variare uno alla volta.

## 7. Cosa corregge

Nessuna conclusione precedente è sostituita. Si **opera** tre avvertenze che
erano già scritte e che il rapporto dei worker del 14 settembre aveva
segnalato come rischi:

1. LowRankRidge riempie i mancanti a zero prima della SVD (`src/vcc2026/models.py`);
   questo checkpoint non lo riusa fra pannelli diversi.
2. Alpha 0,1974 non è una costante da usare in un fold che esclude K562 o RPE1.
3. Due contesti perturbati non identificano una dipendenza generale dal contesto.

Il prospetto `docs/PROSPETTO_MODELLO_2026-09-14.md` resta una proposta. Questo
checkpoint non lo promuove a architettura adottata.

## 8. Domanda di comprensione

Perché un MSE/nullo 0,97 di una rete modulare su K562 → RPE1, in spazio
pseudobulk, non autorizza a dire che la modularità conviene per la gara?
