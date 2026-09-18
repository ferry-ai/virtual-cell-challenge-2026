# CP-0020 — Pipeline a singola cellula: effetto cis trasferibile, DE esatto e veloce, md5 del K562 gia verificato

- **Data:** 2026-09-17
- **Tipo:** cambio-di-strategia
- **Redatto da:** agente (Claude Opus 5), lead scientist su mandato del proprietario
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il 17 settembre il proprietario ha chiesto di lasciare le pipeline periferiche e puntare
a un modello sopra 0,1, lavorando **su cellule singole** con i grezzi già su Drive
(Colab o Kaggle) invece che sul solo pseudobulk. Prima di addestrare qualcosa servivano
tre risposte:

1. Nel codice dello scorer, che cosa decide le quattro metriche costruite sul DE, e che
   cosa ne segue per il generatore di cellule?
2. L'effetto cis della CRISPRi sui geni vicini al bersaglio (I-4 del
   [piano del 16](../PIANO_IMPLEMENTATIVO_2026-09-16.md)) è abbastanza forte e
   abbastanza trasferibile da entrare nel predittore?
3. I grezzi su Drive sono usabili da un runtime remoto, e come si valutano centinaia di
   bersagli con lo scorer in tempi utili?

## 2. Cosa è stato fatto

- **Lettura dello scorer** installato, `cell_eval2` 0.16.0: `metrics/direction.py`
  (fidelity e reach), `metrics/de.py` (NMAE e Jaccard), `metrics/delta.py` (MSE),
  `metrics/discrimination.py` (PDS), `baseline.py` (il punto 0), `de_compute.py` e
  `scanpy/tools/_rank_genes_groups.py` (il DE su CPU).
- **Codice nuovo:**
  - `src/vcc2026/sc_stream.py`: lettura a flusso di una X densa e contigua, con md5 nella
    stessa passata e un accumulatore numba per somme, frazioni, quadrati e rilevazioni per
    bersaglio.
  - `src/vcc2026/generator.py`: `ControlModel`, generatore appreso dai controlli di un
    contesto.
  - `src/vcc2026/de_tools.py`: il DE dello scorer, sia nella forma ufficiale sia in quella
    veloce (`ReferencePool`, `fast_scorer_de`).
  - `src/vcc2026/sc_effects.py`, `src/vcc2026/predictor_sc.py`: effetti da cellule con
    shrinkage empirical Bayes, modello cis, composizione del log fold change.
  - `src/vcc2026/bench.py`: banco a sei metriche con ancore locali.
  - Script da 71 a 79.
  - 8 test in `tests/test_sc_pipeline.py`, tutti verdi.
- **Annotazione genomica.** BioMart ha risposto «Service unavailable» e l'API REST di
  Ensembl HTTP 500, quindi le coordinate vengono da `gencode.v50.basic.annotation.gtf.gz`,
  con md5 `11e77cf1…` uguale a quello del file `MD5SUMS` della release. Lo script 74 le
  riporta sui 18.533 simboli ufficiali, con manifest nella radice dati.
- **Esecuzioni locali**, tutte senza sottomissioni:

  ```bash
  python scripts/77_cis_effect_report.py --out reports/cis_2026-09-17
  python scripts/78_coexpression_predictor_test.py --out reports/coexpression_2026-09-17
  python scripts/79_fast_de_parity.py --out reports/fast_de_2026-09-17
  python scripts/72_generator_null.py --out reports/generator_null_smoke_2026-09-17 \
      --contexts A --n-pseudo 4 --cells 100 --max-cells 3000 --knn 15
  ```

- **Runtime remoto.** `notebooks/colab_sc_training.ipynb` avvia un dispatcher che esegue
  i file depositati da Drive per desktop in `MyDrive/vcc2026/runs/queue/`: estrazione K562
  (71), calibrazione nulla su A/B/C (72), banco K562 del pannello (73) e banco di
  trasferimento K562 → HepG2 (75). **Al momento della scrittura nessuno dei quattro è
  partito**: il notebook non era ancora stato avviato. Un banco ridotto K562 → HepG2 in
  locale è stato fermato dopo 1 h 45 min perché la macchina, con 0,5 GB liberi, stava
  andando in swap. Non ha prodotto risultati.

## 3. Cosa si è osservato

### 3.1 Il K562 su Drive ha già un md5 verificato (misura)

`reports/drive_evidence_2026-09-17/` contiene le copie dei due sidecar `.fetch.json` e
del `catalog_run.json` del run Colab `catalog_2026-09-15T145842Z`. I file li ha
**scaricati quel run**, il 15 settembre, direttamente nei percorsi attesi
(`MyDrive/vcc2026/data/raw/replogle/` e `…/nadig_hepg2/`):

| File | Byte ricevuti | md5 | Uguale al catalogo |
|---|---:|---|---|
| `K562_gwps_raw_singlecell_01.h5ad` | 65.830.941.948 | `887e3e6a…` | sì |
| `NadigOConner2024_hepg2.h5ad` | 850.590.740 | `af2be47f…` | sì |

Nello stesso run il blocco K562 risulta `failed`. L'errore è
`TypeError: Argument 'path' must not be None` nella fase QC, con `md5_ok: true`: è un
errore di codice, non del file. Il contenuto del K562 quindi non è mai stato letto.

### 3.2 Che cosa decide le metriche DE (lettura del codice, 0.16.0)

- **FID** (`direction_fidelity_yield_raw`) vale `k / max(n_pred, N_conf)`. Qui `n_pred`
  sono i geni che la previsione chiama significativi, `N_conf` quelli significativi nel
  riferimento (bersaglio escluso), `k` le chiamate con il segno del log2FC reale. Chi
  **non chiama nulla** prende 0 su ogni bersaglio con `N_conf > 0`. Con le ancore stimate
  il 16 settembre (b = 0,5124, r = 0,8111, `reports/leaderboard_2026-09-16/snapshot.md`),
  quello 0 vale −1,71 in scala, cioè circa −0,29 sul punteggio complessivo.
- **REACH** ordina i soli geni significativi nel riferimento secondo i p-value **della
  previsione**, e misura la profondità massima alla quale la purezza di segno resta ≥ 0,9.
- **NMAE** si calcola sui geni significativi nel riferimento, per i bersagli che ne hanno
  almeno 10.
- **La baseline** (punto 0) ricampiona le cellule di controllo reali e moltiplica ogni
  gene per il rapporto tra risposta media del contesto e controllo
  (`_emit_scaled_resample`).
- **Il DE su CPU** è `rank_genes_groups` di scanpy: Wilcoxon con correzione per i
  pareggi, su log1p del CPM ottenuto come `x / (libreria / 1e6)`. Poi vengono il filtro a
  5 CPM calcolato sul solo riferimento e BH per bersaglio.
- Dalle docstring (misure degli organizzatori sui pannelli `val`, non nostre):
  - NMAE restituisce 272 / 229 / 218 bersagli su 300 in A / B / C, cioè quelli con
    almeno 10 geni nel gate;
  - con la soglia di purezza 0,9, tra il 12% e il 30% dei bersagli non ha nessuna
    profondità che tolleri un errore, quindi ha `N_conf` < 10;
  - esistono bersagli con più di 500 geni significativi.

### 3.3 Il generatore di trial-01 inventa chiamate (misura, prova ridotta)

Contesto A, 1.500 controlli per addestrare e 1.500 come riferimento, 4 pseudo-bersagli da
100 cellule, **nessun effetto previsto**
(`reports/generator_null_smoke_2026-09-17/context_A.json`):

| Braccio | Geni significativi per bersaglio | Di cui «in su» | Geni rilevati per cellula |
|---|---:|---:|---:|
| cellule reali | 0,0 | — | 5.912 (riferimento 5.925) |
| generatore di trial-01 (Poisson sul profilo medio) | 93,0 | 89% | 6.302 |
| `ControlModel`, stati da GMM | 0,2 | — | 6.001 |
| `ControlModel`, stati da KDE | 0,0 | — | 5.926 |

Nello stesso file, la distanza media del pseudobulk dalla metà di riferimento vale
3,25·10⁻³ per le cellule reali e 3,70·10⁻³ per il KDE. Questa differenza non è ancora
spiegata.

### 3.4 Il DE veloce è identico a quello dello scorer (misura)

Otto bersagli HepG2 da 80 cellule contro 1.500 controlli
(`reports/fast_de_2026-09-17/parity.json`):
- 76.648 righe in entrambi i percorsi;
- differenza massima 0,0 sia nel log10 dei p-value sia nel log2FC, e 2,2·10⁻¹⁶ nel p
  aggiustato;
- 7.916 chiamate significative da una parte e dall'altra, nessun disaccordo;
- 12 s contro 88 s.

La parità è esatta solo con le chiavi complesse `gene + i·valore`. La prima versione
sommava a ogni gene un offset reale, e questo fondeva valori che scanpy tiene distinti di
un solo ulp: spostava i p-value fino a 4·10⁻⁴ in log10.

### 3.5 L'effetto cis è forte e si trasferisce (misura)

Dal file `reports/cis_2026-09-17/cis_effect.json`. Sul pseudobulk K562 genome-wide, il
log2FC mediano dei geni espressi scende a circa −0,5 entro 1 kb dal TSS del bersaglio e a
circa 0 oltre i 20 kb (tabella in `k562_distance_curve.csv`). Per i bersagli presenti sia
in K562 sia in HepG2:

| Distanza | Coppie | Mediana K562 | Mediana HepG2 | Pearson | Segno concorde (K562 \|log2FC\| > 0,5) |
|---|---:|---:|---:|---:|---|
| ≤ 1 kb | 250 | −0,46 | −0,82 | 0,57 | 97,5% (n = 122) |
| 1–5 kb | 73 | −0,17 | −0,35 | 0,72 | 100% (n = 23) |

Nel pannello, i bersagli con un vicino non del pannello espresso a ≥ 10 CPM nei controlli
ufficiali sono:

| Contesto | Vicino entro 1 kb | Vicino entro 5 kb | Vicini non misurati in K562 |
|---|---:|---:|---:|
| A | 36 | 56 | 12 |
| B | 37 | 52 | 12 |
| C | 34 | 49 | 10 |

### 3.6 La co-espressione nei controlli non predice il knockdown (misura)

Dal file `reports/coexpression_2026-09-17/summary.json`: 243 bersagli HepG2 e 2.000
cellule NTC. La correlazione tra la co-espressione del bersaglio con ogni gene e
l'effetto del knockdown su quel gene ha mediana:
- −0,042 sulla co-espressione grezza;
- **0,0015** dopo aver tolto 20 componenti principali;
- 0,0011 anche sui 200 bersagli con gli effetti più forti.

## 4. Interpretazione e incertezza

- **Interpretazione.** La FID di trial-01 (0,458) sta sotto la baseline (0,512) in modo
  coerente con molte chiamate spurie il cui segno non concorda con il reale: 93 geni
  significativi per pseudo-bersaglio da 100 cellule in 3.3, l'89% «in su». Il meccanismo proposto
  è un'**ipotesi**: sui geni a espressione esplosiva, la media di 400 cellule reali cade
  più spesso sotto quella dei controlli.
- **Conseguenza di 3.2, lettura del codice.** Un generatore pulito **da solo**
  peggiorerebbe la FID, perché senza chiamate vale 0. Il generatore nuovo si adotta
  quindi solo insieme a un predittore che produca abbastanza chiamate informative. Quante
  siano «abbastanza» in `val` non è misurato: le docstring indicano una mediana di
  `N_conf` dell'ordine delle decine, con code sopra 500.
- **Ipotesi.** La testa cis dovrebbe alzare PDS e REACH sui 34–56 bersagli con un vicino
  espresso. La transfer K562 → HepG2 è misurata su geni **essenziali**; i vicini dei
  bersagli del pannello potrebbero comportarsi diversamente, e il reagente CRISPRi dei
  dati `val` non è noto, per cui l'ampiezza potrebbe differire.
- **Limite.** La co-espressione è negativa in un solo contesto e su bersagli essenziali.
  Resta non provata sui bersagli non essenziali.
- **Nessuna affermazione sul punteggio di trial-02**: i banchi che devono sceglierne le
  ampiezze non sono ancora girati.

## 5. Spiegazione semplice

Lo scorer controlla, gene per gene, se le cellule che inventiamo sono «diverse» da quelle
di controllo. Le cellule di trial-01 lo erano in centinaia di geni anche dove non
prevedevamo alcun effetto: erano troppo regolari, tutte copie della stessa cellula media.
Il nuovo generatore impara com'è fatta la popolazione di controllo e, a effetto zero, non
si distingue dal reale.

C'è però un tranello. Una delle sei metriche premia chi indica i geni che cambiano *e*
la loro direzione, e chi non ne indica nessuno prende zero. Una previsione pulita ma muta
andrebbe peggio di una sporca. Servono quindi geni da indicare con buona sicurezza.

Il primo candidato è sicuro. Quando la CRISPRi spegne il promotore di un gene, spegne un
po' anche quello del gene accanto. In K562 e in HepG2 succede nello stesso modo: se in
K562 il vicino scende, in HepG2 scende anch'esso nel 97,5% dei casi. Nel pannello della
gara una cinquantina di bersagli ha un vicino così.

Il secondo candidato, «i geni che nei controlli variano insieme al bersaglio», invece non
funziona. Nei dati HepG2 non dice nulla su cosa succede quando il bersaglio viene spento.

## 6. Conseguenze

- **`docs/DECISIONI.md`, voci proposte:**
  - **D-034**, il generatore delle sottomissioni: `ControlModel`, cellule nuove, i
    controlli usati solo come input;
  - **D-035**, nessun invio con un budget di chiamate molto sotto `N_conf`;
  - **D-036**, termine cis nel predittore, co-espressione esclusa;
  - **D-037**, il DE dei banchi è quello veloce, verificato identico.
- **Regola di I-2 del piano del 16 incompleta.** «Vince il generatore più vicino al
  reale-contro-reale» non basta da sola: va letta insieme a D-035.
- **Il passo successivo è far girare la coda Colab.** Le ampiezze di trial-02 si scelgono
  dai banchi 73 e 75, poi vengono generazione (76), packaging (48) e verifica. L'invio
  avviene solo con l'autorizzazione del proprietario.
- **`docs/PROGETTO.md`:**
  - lo stato si aggiorna con la pipeline implementata e non ancora eseguita in remoto,
    il cis misurato, la co-espressione negativa e l'md5 verificato;
  - l'incertezza 6 riceve una prima misura contraria;
  - l'incertezza 20 si chiude per integrità e percorso, e resta aperta per i tempi di
    lettura dal mount.

## 7. Cosa corregge

- **[CP-0018](0018-drive-storage-confermato.md) §3.1 e §4.** Quelle sezioni presentano le
  copie su Drive come una dichiarazione del proprietario, con md5 e percorso non
  verificati. In realtà le copie le ha scaricate il run Colab del 15 settembre nei
  percorsi attesi, e il loro md5 al download coincide con il catalogo (§3.1 qui sopra).
  Resta vero che nessun run ne ha letto il contenuto (CP-0018 §3.7), e che il tempo di
  lettura attraverso il mount non è misurato.
- Non corregge altri checkpoint. Completa, senza smentirla, la regola di I-2 del piano
  del 16 settembre (vedi §6).

## 8. Domanda di comprensione

Un collega propone di inviare trial-01 con il solo generatore nuovo, «così togliamo gli
artefatti e vediamo quanto sale». Quale formula di 3.2 gli mostri per spiegargli perché la
FID potrebbe scendere invece di salire, e che cosa andrebbe aggiunto alla previsione
perché la proposta abbia senso?
