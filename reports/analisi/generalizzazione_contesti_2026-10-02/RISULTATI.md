# Risultati di R-LEAD P0–P3: i controlli di una linea nuova non migliorano il transfer in queste forme

Claude Code, sessione `22d21f`, 2 ottobre 2026. Regola: [PROTOCOLLO](PROTOCOLLO.md), congelata nel commit
`e60767c` (17:32:23) prima dei dati reali; correzioni d'implementazione prima dei risultati nel §10 del
protocollo. Codice: [risposta_contesto_2026-10-02](../../modelli/risposta_contesto_2026-10-02/README.md).
Tipi: **misurato** (con la fonte), **interpretazione**, **ipotesi**, **proposta**. Tutte le linee del banco
erano già state lette: ogni numero qui è **sviluppo**, nessuno è un punteggio VCC.

## 1. P0 — che cosa è identificabile sulla macchina (misurato, `p0_r1/`)

- **Ambiente.** Scorer `cell_eval2` 0.16.0 importabile con il preset `vcc2026` nel venv del progetto
  (Python 3.12.3), fuori dal sandbox come in CP-0054. Risorse alla partenza: 7,8 GB di RAM con 0,8 liberi,
  8 CPU, 18,8 GB liberi su C:.
- **Input.** 457 file, 17,5 GB, sha256 di tutti; 0 discrepanze con gli hash che gli universi avevano
  registrato. HepG2 ricostruita qui dalle cellule locali con lo stimatore del t25 (`min_expected` 1):
  2.346 bersagli con ≥ 10 cellule, 4.976 controlli, mediana 46 cellule; due metà indipendenti.
- **Sette gruppi di linea CRISPRi** con effetti e controlli locali (33 tabelle):

  | Gruppo | Tabelle (studi, stati, cloni) | Bersagli | Cellule mediane | Saggio |
  |---|---|---|---|---|
  | CD4T | 3 stati, 4 donatori (Marson 2025) | 36.301 | 523 | Flex |
  | HCT116 | 1 (Orion) | 16.438 | 164 | GEM-X 5′ (da verificare) |
  | HEK293T | 1 (Orion) | 17.270 | 211 | come HCT116 |
  | HepG2 | 1 (Nadig) | 2.346 | 46 | 3′ (da verificare) |
  | K562 | 3 (GWPS, essential, VIPerturb) | 18.537 | 121 | 3′ e Flex |
  | RPE1 | 1 (Replogle) | 2.393 | 72 | 3′ |
  | iPSC | KOLF2.1J + 19 linee HIPSCI | 18.885 | 81 | da verificare |

  Fuori dal banco, registrati: A549 (KO), Hs27 (CRISPRa), i due schermi HIPSCI genome-wide (36 e 12
  controlli). Assenti in locale: Jurkat, H1 2025, DLD-1 e Mixscale (solo DE), Tian/Norman, terza ondata.
- **Collegamenti.** 18.204 chiavi di bersaglio in ≥ 2 gruppi, 8.097 in ≥ 5, 1.144 in tutti e sette;
  tutti i 300 bersagli del pannello A/B/C in ≥ 2 gruppi. 251 gruppi di alias riconciliati per ID Ensembl.
- **Confondimenti.** HCT116 e HEK293T condividono studio e saggio; K562 ha due chimiche; HepG2, RPE1 e
  K562 GWPS/essential vengono dalla stessa famiglia di schermi 3′; iPSC sono 20 tabelle di un tipo
  cellulare. Linea, studio e saggio non si separano con questi dati.

## 2. P1 — split ed esposizioni (misurato, `p1_r1/`)

Fold per hash della chiave riconciliata: togliere sei tabelle e riordinare non cambia nessun ruolo di
training (prova di stabilità passata). Righe valutate in C dopo il QC: CD4T 8.987, HCT116 3.553,
HEK293T 3.746, HepG2 2.346, K562 7.174, RPE1 2.354, iPSC 8.433; le perdite (bersagli senza supporto dopo
il QC) sono elencate, non riassegnate. Le esposizioni di r2/r3 lette dai loro prepass riproducono le
liste nascoste instabili dell'audit (Jaccard 0,06). **Nessuna linea locale è una riserva intatta.**

## 3. P2 — banco e parità (misurato)

- Controllo sintetico (`test_p3_synthetic.py`): un guadagno di contesto piantato viene rilevato dalla
  regola, nessun contesto viene inventato senza; nessun adattamento legge il gruppo escluso; la selezione
  interna di M2 non vede mai il gruppo di validazione (audit registrato in `fits.json`).
- Tetto di riproducibilità della verità (`ceiling_r1/`): coseno pesato fra metà indipendenti, mediana
  0,134 su HepG2 (0,07 con ≤ 40 cellule, 0,30 con > 64) e 0,052 su VIPerturb K562 Flex.
- Parità sui dati reali (`six_member_r1/`): gli adattamenti di HepG2 ricalcolati riproducono gli indici
  della corsa (differenza massima 4,4e-16); lo stadio 45 e `trial01_cells` scrivono le stesse celle bit per
  bit dagli effetti esportati; `load_effects` rilegge gli stessi bit.

## 4. P3 — regime C (misurato; regola applicata da `decide.py`, `p3_decision_c_r1/`)

**Esito della regola: `no_benefit`.** 731.860 righe (bersaglio × braccio) su sette gruppi tenuti fuori.

| Braccio (macro su 7 gruppi) | cos | pds | cos_spec | sign_sig | mse_ratio |
|---|---|---|---|---|---|
| generico addestrato | 0,109 | 0,500 | −0,001 | 0,537 | 1,127 |
| transfer (t25) | 0,080 | **0,759** | 0,105 | 0,556 | 1,415 |
| tm0, senza contesto | 0,137 | 0,641 | 0,114 | 0,576 | 1,000 |
| m1, guadagni dai controlli | 0,138 | 0,638 | 0,115 | 0,573 | 1,000 |
| m1 con controlli scambiati | 0,137 | 0,637 | 0,114 | 0,576 | 1,003 |
| m1 con bersagli permutati | 0,075 | 0,499 | 0,004 | 0,516 | 1,032 |
| m2_0, bilineare senza contesto | 0,090 | 0,753 | 0,087 | 0,559 | 1,327 |
| m2, bilineare con contesto | 0,094 | 0,748 | 0,091 | 0,564 | 1,331 |

- **Contesto, m1:** Δcos +0,0010 (bootstrap sui gruppi −0,0015…+0,0045), positivo in 2 gruppi su 7;
  scambio +0,0010, positivo in 4 su 7. Falliscono le condizioni 2, 3 e 4.
- **Contesto, m2:** Δcos +0,0037, positivo in 3 gruppi su 7; un nullo con controlli permutati fa
  meglio (+0,0095). Falliscono le condizioni 1, 2 e 4.
- **Catena:** tm0 e m1 alzano il coseno in 7 gruppi su 7 (+0,057 e +0,058) e portano l'MSE relativo al
  livello del nullo, ma il PDS scende di 0,12: falliscono la non regressione. m2_0 e m2: +0,011 e +0,014,
  positivi in 5 gruppi su 7, PDS −0,006 e −0,011.
- **Specificità:** permutare i bersagli toglie a m1 +0,14 di PDS e +0,11 di cos_spec: il transfer porta
  un segnale specifico del bersaglio vero.

**Interpretazione.** I controlli della linea tenuta fuori non aggiungono nulla di misurabile a una
correzione per gene o di programma, a parità di righe, descrittori e capacità: sette linee, gemelli
riaddestrati, scambi e nulli dicono la stessa cosa. La calibrazione senza contesto migliora coseno e MSE
spostando le previsioni verso la risposta comune, e paga in discriminazione: è lo schema di CP-0026, ora
misurato su sette linee. L'unico segno descrittivo di contesto (m2 +0,026 su HepG2 e RPE1, negativo su
CD4T, HCT116, HEK293T e iPSC) cade sui due schermi essenziali della stessa famiglia 3′ di K562:
laboratorio e chimica non si separano dalla biologia (ipotesi, non misura).

**Che cosa è escluso** a questa scala di dati: guadagni per gene letti dall'espressione basale e
interazioni bilineari a basso rango con le coordinate principali dei controlli, come correzione del
transfer. **Non è escluso:** un contesto utile con molte più linee, o con descrittori diversi
dall'espressione basale media, o nelle metriche ufficiali dove l'ampiezza conta in altro modo (§5).

## 5. P3 — regime J (misurato; `p3_decision_cj_r1/`, regola applicata a C e J insieme)

**Esito della regola: `no_benefit`.** Bersaglio e linea nuovi; cinque fold per hash su sette gruppi.

| Braccio (macro su 7 gruppi) | cos | pds | cos_spec | mse_ratio |
|---|---|---|---|---|
| generico addestrato | 0,109 | 0,500 | 0,000 | 1,128 |
| `embed`, senza memoria | 0,110 | 0,508 | 0,040 | 1,114 |
| jm1_0, guadagni senza contesto | 0,115 | 0,503 | 0,041 | 1,008 |
| jm1, guadagni dai controlli | 0,116 | 0,502 | 0,041 | 1,008 |

- Il riferimento senza memoria discrimina appena sopra il caso: PDS +0,0075 sul generico, positivo in 6
  gruppi su 7 (soglia di viabilità del protocollo superata). La sua parte specifica (cos_spec 0,040) è un
  terzo di quella del transfer in C.
- Contesto: jm1 − jm1_0 = +0,0017 di coseno, positivo in 5 gruppi su 7 (ne servono 6); lo scambio
  dei controlli non peggiora in modo coerente. Non passa.
- **Protezione J:** nessuna correzione è adottata in C, quindi i bersagli senza memoria restano al ripiego
  senza contesto.

## 6. Decisione

**C: nessun beneficio. J: nessun beneficio. Nessuna adozione; il transfer t22/t25 resta il riferimento.**
Distinzione richiesta da R-LEAD:
- **Beneficio del contesto:** non dimostrato in nessun regime (né in M1 né in M2).
- **Miglioramento della catena:** non dimostrato; la calibrazione senza contesto migliora coseno e MSE
  degli effetti ma perde discriminazione (PDS −0,12), e la regola la boccia. Sulla sola parte
  specifica migliora il transfer in 7 gruppi su 7 (+0,009, lettura post hoc, non regola): un confronto
  da registrare prima, se serve alla produzione.

**Limite della metrica primaria (dichiarato dopo i risultati, regola invariata):** il transfer della
ricetta toglie la risposta comune, la verità la contiene; il coseno premia quindi per costruzione i bracci
che la reintroducono. Il PDS come vincolo ha impedito di promuoverli; un protocollo futuro dovrebbe usare
come primaria la parte specifica o il PDS.

Prossimo contrasto giustificato e richieste: [p4/hypothesis.md](p4/hypothesis.md).
