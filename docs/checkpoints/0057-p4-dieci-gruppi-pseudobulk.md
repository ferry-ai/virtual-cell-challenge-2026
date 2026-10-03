# CP-0057 — R-LEAD P4: dieci gruppi e una rete non lineare sul pseudobulk non danno beneficio dal contesto; sui sei membri vince il transfer

- **Data:** 2026-10-03
- **Corse:** notte fra il 2 e il 3 ottobre; letture dalle 03:26 alle 06:05 CEST (`written_utc` delle decisioni, orari dei commit)
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione `22d21f`
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

P3 ([CP-0056](0056-banco-contesto-c-j.md)) non ha trovato beneficio dai controlli della linea nuova. Due ipotesi registrate
in [p4/hypothesis.md](../../reports/analisi/generalizzazione_contesti_2026-10-02/p4/hypothesis.md):
- il limite sono le linee collegate, quindi con più linee il beneficio dovrebbe comparire;
- il limite è la forma del modello, quindi una correzione non lineare dovrebbe trovarlo.

Il banco a sei membri sui bracci di P3 doveva inoltre confermare con lo scorer ufficiale la lettura del limite della
primaria.

## 2. Cosa è stato fatto

- **Dieci gruppi.** Jurkat (Nadig), H1 train/val (gara 2025) e neuroni Tian 2021 sono stati aggiunti al cubo
  (`cube_r2`) con somme calcolate su Kaggle CPU. Il cubo è stato letto da due kernel di `davideferrante11`:
  - CPU `rlead-bench-cpu-r1`: bracci semplici, C e J, regola di P3;
  - GPU `rlead-bench-nn-r1`: rete del [protocollo P4](../../reports/analisi/generalizzazione_contesti_2026-10-02/p4/PROTOCOLLO_NN.json).
- **Sette gruppi, in locale:** la stessa rete (`p4_nn_r1`, 17.400 s).
- **Regole applicate con `decide.py`:** [p4_decision_nn_r1](../../reports/analisi/generalizzazione_contesti_2026-10-02/p4_decision_nn_r1/LETTURA.md),
  [p4_decision_nn_r2](../../reports/analisi/generalizzazione_contesti_2026-10-02/p4_decision_nn_r2/LETTURA.md) e le
  decisioni del kernel CPU copiate in `p4_decision_c_r3/` e `p4_decision_cj_r3/`.
- **Sei membri su HepG2:** `six_member_hepg2.py` sui bracci di P3, 150 bersagli, 2.048 controlli (deviazione dichiarata
  per memoria), in [p3_six_member_r2](../../reports/analisi/generalizzazione_contesti_2026-10-02/p3_six_member_r2/LETTURA.md).

## 3. Cosa si è osservato

Misurato, su linee di sviluppo. Indici sugli effetti, salvo i sei membri in scala locale; nessuno è un punteggio VCC.

- **Bracci semplici, dieci gruppi:** `no_benefit` in C e in J.
  - `m1` − `tm0` = 0,0000 (6/10), `m2` − `m2_0` = −0,0005 (4/10), con il miglior nullo a +0,0068.
  - `jm1` − `jm1_0` = +0,0010 (6/10).
- **Rete sul pseudobulk:** `no_benefit` su sette e su dieci gruppi.
  - Sette gruppi: `nn` − `nn0` = −0,0019 (4/7).
  - Dieci gruppi: `nn` − `nn0` = −0,0037 (2/10), bootstrap −0,0069…−0,0004, nulli fra −0,0058 e −0,0034.
  - Nessuna variante batte il transfer sul PDS (fino a −0,18).
- **Sei membri su HepG2, media locale:**
  - transfer 0,232, il migliore;
  - `m2` 0,184, `m2_0` 0,176;
  - `tm0` −0,014 e `m1` −0,002, che crollano in PDS (0,44–0,45 contro 0,95) e nelle chiamate (8–9 per bersaglio contro
    101);
  - generico −0,093, nullo −0,106.
- Parità degli adattamenti 4,4e-16; esportazione e generatore identici bit per bit.

## 4. Interpretazione e incertezza

- **Interpretazione.** Con tre linee in più il beneficio dei controlli medi non compare; con una rete non lineare non
  compare, e anzi il contesto peggiora di poco. Le due ipotesi di P4, in questa forma, non trovano sostegno. Sui membri
  ufficiali la calibrazione verso la risposta comune è la scelta peggiore: conferma che il coseno degli effetti premiava
  ciò che la gara punisce.
- **Incertezza.** Le linee restano poche e confuse con studio e saggio. Le tre linee aggiunte non sono collegate da
  bersagli comuni quanto K562/RPE1/HepG2. Un solo seme. I sei membri valgono su una sola linea, già letta più volte, con
  controlli ridotti. Questi risultati non dicono che la media dei controlli sia il limite.
- **Ipotesi aperta.** Le cellule potrebbero portare un segnale che la media perde. È ciò che il pilot della rete cellulare
  v2 deve verificare ([protocollo](../../reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md)), con il gemello a
  profilo medio come controllo.

## 5. Spiegazione semplice

Abbiamo dato ai modelli più tipi cellulari e un modello più flessibile, ma guardando solo la media delle cellule di
controllo non riescono ancora a correggere la previsione per una cellula nuova. Con il punteggio vero della gara, il
semplice trasferimento della risposta da altre cellule resta il migliore.

## 6. Conseguenze

- Nessuna adozione: il transfer t22/t25 resta il riferimento.
- Il proprietario ha chiesto di non addestrare altre reti sul pseudobulk: questi numeri sono la baseline della rete
  cellulare.
- Il pilot cellulare r1 è fallito tecnicamente (collasso) e riparte con l'emendamento 2.1
  ([PROTOCOLLO §7–8](../../reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md)); incidente E-20261003-001 per i
  lanci doppi.

## 7. Cosa corregge

Non corregge checkpoint precedenti. Estende CP-0056 da sette a dieci gruppi, alla rete non lineare e ai sei membri.

## 8. Domanda di comprensione

Perché un braccio che migliora il coseno con la verità in dieci gruppi su dieci (`tm0`) può avere quasi lo stesso
punteggio a sei membri del braccio nullo?
