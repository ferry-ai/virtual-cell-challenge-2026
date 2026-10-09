# Rete ponte (JEPA + SIGReg) sul transfer `all`: protocollo

9 ottobre 2026, 17:45 CEST. Claude Code per Alfredo, che ha chiesto in chat una rete addestrata per la VCC,
provata sul banco, con i risultati pushati a Davide, «così poi capiamo se gradare la rete oppure no». Le decisioni
sono state lasciate a me.

**Registrato prima di ogni numero di questa rete.** Le soglie non si spostano dopo i risultati.

## Domanda

Una rete appresa sulle 34 tabelle del cubo r2 predice la risposta di una linea **mai vista** meglio della media a pesi
uguali dei gruppi sorgente (`all`, la base del t36/t37)?

## Il banco (lo stesso dello stadio 1, [guadagno.py](../guadagno_appreso_2026-10-05/guadagno.py))

- **Cubo:** `kaggle_in/cube_r2_layout`, manifest sha256 `c7fb7662…`, 13.425 geni, 10 gruppi.
- **Linee tenute fuori:** H1, HepG2, RPE1, Jurkat, K562, una alla volta (piega L).
- **Bersagli valutati:** quelli di `guadagno.eval_keys`, con almeno 30 cellule vere e supporto, al massimo 400. Sono
  gli stessi bersagli dello stadio 1.
- **Misure:** `guadagno.measures`, importata senza modifiche:
  - coseno debiasato con la verità di L nello spazio Δ (log1p dei conteggi a 5e4);
  - indice PDS;
  - MSE alla norma della ricetta.
  
  Bootstrap appaiato sui bersagli con `guadagno.boot_diff`.
- **Parità:** il `T_all` ricostruito dalla cache della rete deve coincidere con `guadagno.transfer` (atol 1e-4) su
  tutti i bersagli valutati, altrimenti la corsa si ferma.

## La rete

L'uscita è `P = media pesata delle sorgenti + U·r`, nello spazio ln fc dello stimatore.
- **Pesi delle sorgenti:** un'attenzione su (contesto della linea, contesto della sorgente, codifica dell'effetto
  della sorgente).
- **Residuo:** `U` è una base di 64 geni-carichi appresa, inizializzata a zero; `r` esce dal predittore latente.
- **All'inizializzazione `P = T_all` esattamente:** pesi uniformi, residuo nullo.

**Pezzi:**
- **encoder E** (lineare 13.425 → 256) degli effetti di gruppo;
- **encoder di contesto B** (lineare sui basali, centrato);
- **attenzione** sulle sorgenti disponibili;
- **predittore** del latente della linea.

**Perdita, per batch di bersagli di una stessa linea di addestramento h:**
- **coseno:** 1 − coseno fra P e la verità raw di h, pesati per x/(1+x) (lo spazio Δ al primo ordine), con il gene
  bersaglio escluso;
- **InfoNCE fra i bersagli del batch** (τ = 0,1): la previsione di k deve somigliare alla verità di k più che a quella
  degli altri. È il PDS reso differenziabile; peso 0,5;
- **JEPA (peso 0,1):** il latente predetto deve avvicinarsi a `sg(E(verità di h))`. **SIGReg di LeJEPA**
  (Epps–Pulley, 256 direzioni) sui latenti delle sorgenti, mischiato 0,95/0,05 come nel paper, impedisce il collasso
  di E senza EMA.

**Addestramento della piega L:**
- **bersagli:** tutti i gruppi h ≠ L con almeno 50 chiavi, fino a 1.500 chiavi per gruppo (ordine per hash);
- **sorgenti:** i gruppi ∉ {L, h}. **Il gruppo L non è mai letto per l'addestramento**, né come sorgente né come verità;
- **arresto anticipato:** sul 15% delle chiavi di ogni gruppo di addestramento (hash), pazienza 4, al massimo 30
  epoche;
- **un seme (0)**, AdamW con lr 1e-3 e weight decay 1e-2, batch di 128 bersagli.

## Bracci misurati

| Braccio | Che cosa è |
|---|---|
| `all` | T_all, come nello stadio 1 |
| `rete` | P completo |
| `rete_pesi` | solo i pesi dell'attenzione, senza residuo (diagnostico) |

## Regola

**La rete passa** se valgono tutte e tre:
1. la media su 5 linee di `rete − all` nel coseno è ≥ **+0,015**;
2. almeno 3 linee hanno la differenza di coseno con il limite inferiore dell'IC 90% sopra 0;
3. il PDS non peggiora: media di `rete − all` ≥ 0, e nessuna linea sotto −0,02.

**Se passa:** si esportano gli effetti per A/B/C sui controlli ufficiali e si propone l'invio (decide Alfredo).
**Se non passa:** la rete non va al sito in questa forma.

## Previsione (soggettiva, registrata ora)

| Grandezza | Previsione |
|---|---|
| `rete − all`, coseno | media fra +0,000 e +0,025, centro +0,008 |
| `rete − all`, PDS | fra −0,02 e +0,03 |
| Probabilità che la regola passi | 0,25 |

**Perché bassa:**
- i pesi oracolo valgono solo +0,004…+0,013;
- il guadagno appreso ha dato +0,013 (stadio 1);
- l'informazione per coppia è il limite.

Il residuo a basso rango e l'InfoNCE sono le due cose che lo stadio 1 non aveva.

## Limiti

- È un indice sugli effetti del cubo, non lo scorer VCC né i membri DE sulle cellule.
- È un solo seme.
- Il passaggio ad A/B/C cambia la tecnologia e i controlli.
