# Rete L1: il log2FC mediano condizionato al gene DE, separato dal bulk

4 ottobre 2026, sera. Scritto **prima** di addestrare, di generare e di inviare. Il commit che aggiunge questo file ne
fissa l'ora. Invio autorizzato dal proprietario in chat («traina e gradalo»), nel primo slot del 5/10 UTC.

## 1. Idea

- **Che cosa misura l'nMAE.** Il membro `de_lfc_nmae` vale, per ogni bersaglio, `mean|lfc_pred − lfc_real| /
  mean|lfc_real|`, calcolato sui soli geni DE nella verità (Wilcoxon, p_adj < 0,05, CPM di riferimento ≥ 5, gene
  bersaglio escluso). Il `lfc_pred` è `log2` del rapporto fra la **media per cellula dei CPM** delle cellule previste e
  quella dei controlli veri (`cell_eval2/metrics/de.py`, `de_compute.py`).
- **Stima L1-ottima.** Sotto perdita L1 la previsione ottima è la **mediana** della distribuzione predittiva. Sui geni
  DE vale `|y| ≥ soglia di rilevamento`: se la probabilità del segno è vicina a 0,5, l'ottimo non è copiare la
  magnitudine del transfer (un segno sbagliato costa il doppio), ma una magnitudine vicina alla soglia, con il segno
  più probabile.
  - t31 e t34 hanno nMAE grezzo 1,061 e 1,066: peggio della previsione nulla (1,0).
- **Rete L1.** È una rete (MLP) addestrata con perdita L1 pesata come l'nMAE (ogni bersaglio pesa `1/(n_gate ·
  mean|y|)`), solo sulle righe DE della linea di arrivo. Stima direttamente quella mediana condizionata.
  - **Ingressi per coppia (bersaglio, gene):**
    - log2FC K562 (`replogle_k562_gwps`), il suo modulo, un rapporto segnale/rumore da cellule ed espressione;
    - due priori del gene, calcolati su tutti i bersagli K562: log2FC medio e quota di risposte in su;
    - la forza del bersaglio in K562;
    - l'espressione del gene in K562 e nella linea di arrivo;
    - i flag coperto/misurato.
  - **Uscita:** il log2FC (mediana condizionata).
- **Separazione dal bulk (generatore).** Ogni blocco di cellule si genera come per il t34 (stesso seme, stessi
  effetti, stesso flusso casuale). Poi, gene per gene, si spostano conteggi fra cellule con profondità diversa: da
  cellule grandi a piccole per alzare la media dei CPM per cellula, al contrario per abbassarla.
  - **Vincoli:** il totale di ogni gene nel blocco non cambia, quindi il bulk e la PDS/MSE restano identici a quelli
    del t34. Si spostano solo fra cellule già non nulle, lasciando sempre almeno un conteggio alla cellula di
    partenza, quindi il disegno degli zeri resta uguale.
  - **Obiettivo:** il `lfc_pred` della media per cellula si porta sul valore della rete L1, per i geni con CPM ≥ 5 nei
    controlli del contesto, gene bersaglio escluso.
  - **Che cosa si muove:** il test di Wilcoxon (ranghi) cambia poco. Si misura su blocchi campione prima di generare,
    e si riporta.

## 2. Banco (prima del candidato)

- **Dati:**
  - sorgente `replogle_k562_gwps`;
  - linee di arrivo nei gruppi h1, kolf, rpe1, hepg2, jurkat, hipsci, tian (chiavi locali);
  - per ogni linea, i bersagli coperti da K562 e una parte dei non coperti (ingressi K562 a 0, flag coperto = 0).
- **Porta DE (proxy, lato verità):**
  - CPM della linea ≥ 5;
  - `|y_ln| ≥ 3 · se`, con `se = sqrt((1/n_bersaglio + 1/5000) / (CPM · 1,5e4 / 1e6))`;
  - gene bersaglio escluso;
  - almeno 10 geni nella porta, altrimenti il bersaglio esce.
- **Pieghe:**
  - un gruppo fuori per volta (7 pieghe);
  - il gruppo successivo nell'ordine fa da validazione interna per l'arresto (ogni 250 passi, pazienza 6, al massimo
    4.000 passi);
  - i passi, i gruppi e i bersagli sono bilanciati.
- **Bracci sul gruppo di test:**
  - `zero` (nMAE 1 per costruzione);
  - `copia1` (log2FC K562);
  - `copia2` (×2, l'ampiezza del t31 e del t34);
  - `rete`.
- **Metrica:** nMAE per bersaglio come lo scorer, media sui bersagli e poi macro sui gruppi; IC 95% bootstrap sui
  bersagli. Si riporta anche la quota di segni giusti.
- **Regola del banco:** il candidato si genera solo se la macro `rete` è ≤ **0,99**, cioè almeno 0,01 sotto la
  previsione nulla, con il limite superiore dell'IC < 1, **e** se la `rete` batte `copia2` in almeno 5 pieghe su 7.
  Altrimenti niente invio.

## 3. Candidato t35 (numero provvisorio, da concordare con Davide)

- **Modello finale:** rete L1 addestrata su tutti i gruppi, per il numero di passi mediano scelto nelle pieghe.
- **Obiettivi:** per A, B, C, i 300 bersagli e i geni con CPM ≥ 5 nei controlli del contesto, si salvano in
  `vcc2026-data/processed/l1_obiettivi_2026-10-04/`.
- **Generazione:**
  - effetti del t34 (`effects_t34_2026-10-04`), `--effects-scale 2.0`, stesso seme e stesso trial del t34;
  - si aggiunge **solo** lo spostamento dei conteggi;
  - poi stadio 48 come sempre.
- **Rispetto al t34 è un solo fattore.** Lo spostamento conserva i totali per gene, quindi i blocchi prima dello
  spostamento sono byte per byte quelli del t34.

## 4. Previsione e regola (registrate ora)

| Grandezza | Previsione |
|---|---|
| nMAE grezzo t35 | 0,96–1,02 (t34: 1,066) |
| `pds_cosine` grezzo | entro ±0,003 dal t34 (0,7424): il bulk è identico |
| Membri di direzione e Jaccard | entro ±0,01 scalato ciascuno |
| Media t35 − t34 | da +0,005 a +0,030, centro +0,013 |

- **Regola:**
  - t35 − t34 ≥ **+0,005**: lo spostamento resta nella ricetta;
  - |t35 − t34| < 0,005: non conclusivo;
  - t35 − t34 ≤ −0,005: lo spostamento danneggia i membri DE e non si ripete in questa forma.

## 5. Limiti dichiarati

- La porta DE del banco è un proxy: profondità e numero di controlli delle linee di arrivo sono ipotizzati.
- Il `y` del banco è l'effetto delle chiavi (log fold change dei pseudobulk), non la media dei CPM per cellula.
- Un seme.
- Lo spostamento dei conteggi sfrutta la differenza, documentata in `cell_eval2` (#286), fra la media per cellula dei
  CPM (nMAE) e il bulk aggregato (MSE e PDS). È una scelta del generatore, non biologia. La magnitudine e il segno che
  impone vengono dalla rete.
