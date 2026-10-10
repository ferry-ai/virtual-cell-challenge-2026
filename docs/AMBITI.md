# Ambiti: dove sta che cosa

**Perimetro:** una sezione per ogni area del progetto VCC, più un rimando per gli strumenti di
esecuzione, l'infrastruttura degli agenti e l'archivio. Ogni sezione dà lo stato in poche righe,
con il tipo di affermazione, i due o tre documenti da leggere prima, la scheda del piano e gli
errori da non ripetere. **Si legge solo la sezione del proprio compito.** **Fonti:** i checkpoint e
i report citati; questa pagina instrada e non è evidenza, e i numeri completi stanno nelle fonti.
**Si aggiorna** nello stesso commit dell'evidenza che cambia una sezione (D-048). Scritta il 30/09.

Lo stato generale e la direzione sono nel §0 di [PROGETTO](PROGETTO.md); le priorità in
[PIANI](PIANI.md). La revisione lead del 29–30/09 ha corretto premesse che reggevano molte scelte
(CD4 è già Flex; il plateau non è saturazione): le sue scoperte sono riportate nelle sezioni 1–5 e
indicizzate in [lead_scientist_2026-09-29](../reports/analisi/lead_scientist_2026-09-29/README.md).

## Progetto VCC

### 1. Gara e lettura dei punteggi

- **Misurato.** Il punteggio è la media dei sei membri scalati. Un invio si legge dai sei scalati
  pubblicati nello status: le ancore aggregate hanno errori misurati ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Misurato.** In tutti i nostri invii la `mse` scalata vale 0 (tosata); tutte le prime 100
  squadre l'hanno positiva ([PROGETTO §3](PROGETTO.md#3-che-cosa-sappiamo-e-guida-le-scelte)).
- **Regola.** A, B e C sono 10x Flex; le loro identità di linea sono ipotesi e non si scrivono
  mai accanto ai contesti nella repo (regola globale di [CLAUDE.md](../CLAUDE.md)).

Leggi prima: [PROCEDURE §2](PROCEDURE.md#2-le-regole-dellinvio), punto 7, per leggere un punteggio;
[credibilità degli score](../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md);
[gara](../reports/gara/README.md).

### 2. Invii e ricetta di produzione

- **Misurato, 9/10 sera ([CP-0074](checkpoints/0074-t38-crispri-piu-ko-punteggio-ufficiale.md)).** Massimo osservato td 38 **0,148922**, +0,001673 da td 36: T3, cioè T1 più cinque voti KO a peso 0,25 su 34 bersagli. Dentro la soglia ±0,005 registrata prima: non conclusivo, nessuna attribuzione a una fonte, un solo invio. Il [registro previsione → punteggio](../reports/analisi/validazione_banco_eace4d03_2026-10-09/invii/RAPPORTO_INVII_r1.md) confronta ogni previsione registrata di Davide con i sei membri ufficiali: 14 bande del punteggio su 17 contengono l'esito; le due previsioni puntuali di un banco su un delta (td 28, td 30) lo hanno sovrastimato; taratura numerica non sostenuta.
- **Misurato, 10/10: dopo il td 38 e sul branch di Alfredo.** td 39 (T3 più il ridge ESM2 sulle coppie mancanti) è caricato ed era in `scoring` all'ultima lettura salvata, senza punteggio. Gli invii di Alfredo, ta 30–ta 39 sul branch `codex/teammate-rlead`, sono tutti sotto td 36 e td 38: il più alto è ta 36, 0,141392. Entry, stato verificato, evidenze per commit e collisioni di nomi nella [mappa td/ta](../reports/invii/README.md#nomi-td-e-ta-mappa-dei-candidati).
- **Misurato, 6/10.** Massimo osservato td 36 **0,147249**, +0,002404 da td 28 sulla banca estesa parziale. Sei membri ufficiali verificati; PDS/NMAE salgono, reach/fedeltà/Jaccard scendono, MSE scalata 0. Confronto descrittivo senza soglia numerica preregistrata; nessuna stabilità dimostrata o promozione automatica ([CP-0067](checkpoints/0067-t36-banca-estesa-punteggio-ufficiale.md)). Tutti i punteggi: [invii](../reports/invii/README.md).
- **Misurato, 8/10 notte ([CP-0070](checkpoints/0070-t2-centratura-su-tutti-i-bersagli.md)).** T2, cioè T1 con ogni fonte centrata sulla media di tutti i suoi bersagli: valido e sfavorevole. Livello A `disc95` −0,0005 [−0,0030; +0,0020] contro td 36, con `sign50` e `nmae_conf` in lieve peggioramento risolto; sei membri −0,0087 ± 0,0045 sul fold K562 e +0,0023 ± 0,0125 sul fold iPSC. Il candidato consegnato ha gli stessi byte dello stimatore valutato. Punteggi locali di sviluppo, non VCC ([risultati](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RISULTATI_T2.md)).
- **Misurato, 8/10, a lignaggio escluso ([CP-0069](checkpoints/0069-validazione-indipendente-t1-e-ampliamento.md)).** T1, cioè r1 senza il voto RFK di Tian 2019, non si distingue da td 36: livello A `disc95` +0,0004 [−0,0005; +0,0013] su sei fold, sei membri −0,0003 ± 0,0014 su due; nessuna promozione. Sulle stesse tabelle td 36 perde PDS contro le quattro linee sul fold K562 (−0,10) e ne guadagna sul fold iPSC (+0,07): H1 aiuta, KOLF2.1J costa ai lignaggi non staminali. Punteggi locali di sviluppo, non VCC ([raccomandazione](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RACCOMANDAZIONE.md)).
- **Misurato.** Il td 28 alza fedeltà (+0,051 scalato) e reach (+0,055), perde NMAE (−0,069) e
  Jaccard (−0,008): l'intervento sull'emissione sposta i membri DE, con costi.
- **Esito del 4/10.** td 30, ibrido selettivo D-056 (effetti td 25 + w · R): 0,135249, −0,004989 contro il td 25, ramo b
  non conclusivo, nessuna promozione. PDS scalato −0,042, fedeltà +0,014, Jaccard +0,002, NMAE e reach −0,002
  ([CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)). Le cellule dei bersagli non corretti non sono quelle del td 25: il delta contiene anche un
  cambio di realizzazione del rumore ([catena](../reports/modelli/diagnosi_t30_2026-10-04/esito/chain_t30_r2.json)).
- **Esito del 1/10.** td 29, rete cellulare r2 `desc` con generatore td 22: ramo c negativo.
  PDS, NMAE, reach e Jaccard scalati peggiorano rispetto a td 22; fedeltà sale, MSE scalata
  resta zero mentre la grezza peggiora. Nessun nuovo invio neurale senza il banco a sei
  membri almeno al livello del transfer ([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)).
- **Interpretazione.** Dal td 16 i cambi della media sono piccoli, ma diversi membri si compensano
  ([audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)).

Leggi prima: [che cosa lascia un invio](../reports/CLAUDE.md), [PROCEDURE §1–2](PROCEDURE.md#1-il-percorso-di-un-invio).
Piani: [R-COMP](piani/modello-competitivo.md), [S-INVII](piani/invii-finale.md).

### 3. Generatore e banchi con lo scorer vero

- **Misurato, 9/10 sera: che cosa valuta il banco a lignaggio escluso, e con quali misure** ([contratto v3](../reports/analisi/validazione_banco_eace4d03_2026-10-09/PROTOCOLLO_v3.md), [inventario](../reports/analisi/validazione_banco_eace4d03_2026-10-09/inventario/INVENTARIO_r1.md), [validità delle misure](../reports/analisi/validazione_banco_eace4d03_2026-10-09/banco/VALIDITA_MISURE_r1.md)). Spazio degli effetti su sei lignaggi del pannello (K562, CD4T, HCT116, HEK293, iPSC, H1); sei membri con lo scorer vero solo su K562 e iPSC; in banca ci sono le cellule per CD4T, HCT116, HEK293 e per la libreria pan-genome di iPSC, da estrarre. `disc95`, `r_spec` e `sign50` distinguono il transfer dal suo scambio di bersagli su tutti e sei i fold; `reach` no su H1 e iPSC; `mse_ratio` dà il transfer **peggiore** della previsione nulla su ogni fold, per l'ampiezza scelta sul punteggio ufficiale: è una misura d'ampiezza, da leggere solo fra bracci con la stessa ampiezza e la stessa copertura. Bracci con copertura diversa si confrontano anche sul supporto definito dalla verità (CP-0075).
- **Misurato.** Sul banco HepG2 ampiezza e dispersione interagiscono (+0,0177 d'indice
  nello sviluppo); la conferma su 96 bersagli dà +0,0289, ma 95 erano già stati valutati
  ([CP-0047](checkpoints/0047-conferma-generatore-t28.md), [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Interpretazione.** Il banco HepG2 ha preso il verso dei cambi ufficiali e ne ha sovrastimato
  l'entità ([errori di metodo](ERRORI.md#errori-di-metodo-già-commessi)).
- **Strumento, 8/10.** Banco a lignaggio escluso sul pannello: lo stadio 100 di produzione su una cache senza le tabelle del lignaggio, misure per bersaglio (livello A) e `bench_v2` con cellule vere estratte per K562 e KOLF2.1J (livello B); contratto, manifest dei fold e regola di adozione in [contratto v2](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v2.md). Il controllo a bersagli scambiati mostra che sulla scala locale del fold iPSC NMAE, fedeltà e Jaccard quasi non dipendono dal bersaglio: un delta della media si legge con il PDS accanto ([livello B](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RISULTATI_LIVELLO_B.md), §1).
- **Protocollo e bracci disponibili.** Il banco K562 non ha un esito del job registrato
  ([protocollo](../reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md),
  azione 4 di [R-REV](piani/revisione-critica.md)). La ripresa richiede preflight e scelta
  del confronto; non è una coda automatica. K562 già visto da r2/r3 non ne prova la
  generalizzazione a un contesto nuovo.

Leggi prima: [generatore e banchi](../reports/generatore_e_banchi/README.md), la sezione
«Generatore e t28» dell'[indice lead](../reports/analisi/lead_scientist_2026-09-29/README.md),
[audit del generatore](../reports/analisi/lead_scientist_2026-09-29/AUDIT_GENERATORE.md). Per
cambiare il codice: `scripts/CLAUDE.md` e `src/vcc2026/CLAUDE.md`.

### 4. Dati e sorgenti

- **Mandato non negoziabile, 3/10 (D-053).** Tutte le linee e i contesti idonei nel percorso principale, con
  tre rappresentazioni collegate (archivio completo verificato, aggregati, campioni cellulari), inventario
  riconciliato col catalogo e uso effettivo verificato ([GENERALIZZAZIONE §2.1](GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile)).
  L'integrazione prosegue qualunque sia l'esito del pilot v4.
- **Misurato, 3/10 sera.** Corpus cellulare del pilot: 8 gruppi, 365 shard, 5.603.629 cellule, 53,3 GB; i loro
  gemelli compatti, verificati per decodifica, occupano 21,25 GB
  ([manifest](../reports/modelli/rete_ancorata_v4_2026-10-03/esito/)). Aggregati nel cubo del banco r2 per 10
  gruppi, fra cui CD4T (tre stati), HCT116, HEK293T e K562 VIPerturb, già usati come fonti delle ancore v4.
  Ingestione completa ([README](../reports/sorgenti/ingestione_completa_2026-10-03/README.md),
  [consegna](../reports/sorgenti/ingestione_completa_2026-10-03/HANDOFF_CLAUDE2.md)): KOLF pan-genome chiuso e
  verificato; Orion HCT116 e HEK293T con le ultime quattro parti in corsa dal 3/10 23:08; CD4 due parti su 24; DLD-1,
  Mixscale, VIPerturb in cellule, microglia e PerturbFate ancora da convertire.
- **Aggiornamento CD4 misurato, 4/10 19:36.** Ingestione verificata per tutte le 12 unità:
  ricevute indipendenti positive, SHA degli shard riletti e conteggi riconciliati alla specifica.
  21.980.517 cellule idonee su 33.610.471 righe originali
  ([copertura](../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/copertura_cd4_r2.json)).
  Gemelli compatti, integrazione e uso effettivo nel training restano da verificare;
  [stato e seguito](../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/STATO_1936.md).
- **Mandato del proprietario, 3/10.** Acquisizione completa delle cellule CD4 idonee:
  capacità Drive dichiarata 5 TB, occupazione da misurare; il campione iniziale non è
  un tetto definitivo. Revisione locale della consegna Claude2 e passaggio della regia
  a Claude1 nella [revisione ingestion](../reports/sorgenti/revisione_ingestion_2026-10-03/README.md).
  Codice e fixture non attestano una nuova acquisizione remota.
- **Verificato.** CD4 è Flex e K562 Replogle è 3'. Per Orion le schede indicano GEM-X 5′, da
  riverificare sul protocollo primario ([audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
- **Misurato.** I profili basali sono normalizzati su supporti genici diversi: riscalarli non
  ricrea i geni mancanti (K562 ne misura 7.681 nel basale) ([audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), §4).
  Il ricalcolo dell'azione 5 di R-REV ha il protocollo ma non ancora i risultati
  ([basali sull'asse](../reports/sorgenti/basali_asse_2026-09-29/RISULTATI.md)).
- **Aggiornamento 1/10.** La produzione di riferimento usa quattro sorgenti; il nuovo training
  cellulare r2 include HIPSCI. L'audit trova pesi effettivi e controlli diversi dal disegno,
  e misura la riproducibilità degli effetti HepG2
  ([revisione](../reports/analisi/lead_audit_2026-10-01/REVISIONE.md), §2–3). La copertura del
  [29/09](../reports/analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md) descrive la rete precedente.
- **Regola.** Una sorgente non si scarta per scarsa sovrapposizione con i 300 bersagli (D-044); un
  gene non misurato resta mascherato, non vale zero (D-009).

Leggi prima: [GENERALIZZAZIONE §2.1](GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile),
[sorgenti](../reports/sorgenti/README.md), [strategia dati inoltrata dal proprietario](../reports/sorgenti/ingestione_completa_2026-10-03/STRATEGIA_DATI_TRAINING.md).
Piano operativo: il binario dati di [R-LEAD](piani/strategia-scientifica.md); l'esecuzione (ingestione, archivio,
verifiche, gemelli) in [R-LAB](piani/piano-giorno-2026-09-30.md); inventario riconciliato, aggregati mancanti e
campioni annidati in [R-DATI](piani/dati-affidabilita.md).

### 5. Modelli appresi e generalizzazione

- **Misurato, 9/10 sera ([CP-0075](checkpoints/0075-fallback-esm2-supporto-e-vista-del-generatore.md), [CP-0076](checkpoints/0076-ammi-none-contro-ancora-annidata.md)).** Ridge ESM2 a lignaggio escluso: perde contro il transfer su K562 (`disc95` −0,239) e, tolto iPSC dal training, il suo segnale su iPSC scende di 0,10. Usato come riempimento delle coppie che il transfer non prevede aggiunge copertura e una risposta comune debole, senza specificità del bersaglio; il delta di `disc95` pubblicato non poteva vederlo. Sei membri in corsa a quattro bracci: esito del §8 ancora **inconcludente**. AMMI `none` (seme 17): non si distingue dalla propria ancora annidata su K562 e iPSC; i fit `cells` si leggono contro quell'ancora, non contro T0 ([fallback](../reports/analisi/validazione_banco_eace4d03_2026-10-09/RISULTATI_ESM2_FALLBACK.md), [AMMI](../reports/analisi/validazione_banco_eace4d03_2026-10-09/RISULTATI_AMMI_NONE.md)).
- **Misurato, 9/10 ([CP-0072](checkpoints/0072-esm2-ridge-regime-t.md)): ridge ESM2 senza contesto, regime T.** Sui 66 bersagli nascosti del pannello un segnale specifico del bersaglio è riconoscibile solo contro la verità iPSC (`disc95` 0,627, contrasti risolti); su CD4T, HCT116, HEK293 e K562 il ridge sta a 0,51–0,53, come con le previsioni scambiate, e sotto la testa cis del transfer. Lettura descrittiva di sviluppo, non VCC; nulla sui contesti nuovi ([risultati](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RISULTATI_ESM2_T.md), [S-013](STRADE.md#s-013--ridge-sugli-embedding-esm2-del-bersaglio-senza-contesto-regime-t)).
- **Direzione confermata, 4/10: [D-056](DECISIONI.md#d-056--transfer-con-correzione-neurale-selettiva).**
  Transfer congelato con correzione neurale selettiva, pesata sul beneficio validato fuori fold. Il selettore
  può tornare al transfer; familiarità con bersagli o contesti non equivale a affidabilità dimostrata.
- **Misurato, ibrido selettivo D-056 v1 (4/10): passa sviluppo e conferma**
  ([CP-0062](checkpoints/0062-d056-ibrido-selettivo-esito-banco.md),
  [S-009](STRADE.md#s-009--ibrido-selettivo-d-056-v1-transfer-congelato--correzione-neurale-regolarizzata--selettore-fuori-fold)).
  - Il protocollo v1 è stato congelato prima dei training
    ([protocollo](../reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md)): testa comune esclusa dalla
    previsione, guadagno fisso, penalità, guardie interne, selettore fuori fold.
  - Corsia B, `ibrido_selettivo − transfer` sui sei membri locali:
    - sviluppo +0,006, +0,063, +0,040 (H1, HepG2, RPE1, selettore leave-one-line-out);
    - conferma +0,037 e +0,074 (Jurkat e K562, sistema congelato).
  - Punteggio di banco del §9: 0,134 contro 0,090 del transfer.
  - Limiti: un seme, corpus pilot a 8 gruppi, scala locale; lo stato delle cellule (`ibrido − ibrido_mean`) non dà un
    contributo coerente.
  - **Sul sito il guadagno non è comparso (misurato, 4/10):** t30 −0,004989 contro il t25, non conclusivo
    ([CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)). Misurato nella [diagnosi](../reports/modelli/diagnosi_t30_2026-10-04/README.md): il candidato inviato non era un
    braccio del banco (R definita contro `transfer_all_J`, sommata al t25); all'esportazione la quota comune di R è
    0,62–0,69 contro 0,07–0,24 delle righe e l'ampiezza 0,71–0,96 contro 0,24–0,42; sul fold esportato il banco
    perdeva PDS (−0,093) e la media lo copriva; il JAC locale di K562 porta il 77 % del suo guadagno.
    La stessa procedura di esportazione sui controlli di HepG2 (non di gara) dà quota comune 0,61: non servono i controlli di gara; i bersagli del pannello non erano fra quelli del banco su tre linee su cinque.
    La causa della perdita sul sito resta un'ipotesi. Le cinque linee lette sono sviluppo.
  - **Confronti e rumore del banco (misurato, 4/10 sera, [CP-0065](checkpoints/0065-d056-confronti-e-rumore-del-banco.md)):** il guadagno a un seme e 32 cellule
    ha deviazione standard 0,007–0,045, quanto i guadagni letti; su 5 semi e 400 cellule è +0,004…+0,031, risolto in
    tre linee su cinque. Il fold esportato (HepG2) perde PDS, −0,129 ± 0,005. La procedura dell'invio è fedele al
    banco; sulla baseline di produzione il guadagno resta ([esito](../reports/modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md)).
  - **Banco v2 t28 concluso (4/10, [CP-0066](checkpoints/0066-banco-v2-t28-cinque-linee.md)):** 400 cellule × 5 semi;
    regola con guardia PDS favorevole in 4/5 linee su all, solo Jurkat su prod. HepG2 perde PDS su entrambe,
    RPE1 su prod. Rumore del generatore a fit/verità fissi; pilot a otto gruppi, nessuna promozione.
    [Esito verificato](../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/ESITO_BANCO_V2.md).
- **Misurato, pilot v4 della rete ancorata (4/10): non passa** ([CP-0061](checkpoints/0061-pilot-v4-esito-tre-linee.md)).
  Tre training tecnicamente accettati; la correzione appresa peggiora la propria ancora su tre linee su tre (corsia
  B, media dei sei membri: −0,214, −0,050 e −0,131; guardia della corsia A −0,307). Non è soddisfatto nemmeno il
  requisito di promozione contro la ricetta di produzione. Meccanismo ipotizzato: uno spostamento comune ai
  bersagli ([S-006](STRADE.md#s-006--rete-ancorata-v4-ancora-dal-transfer-più-correzione-appresa-sulle-cellule)).
- **Misurato, v3 r1 (3/10):** pilot incompleto. H1 non soddisfa il bilanciamento: il campionatore a
  epoche, rigiocato sullo stato reale, riproduce esattamente le estrazioni della corsa e non carica mai
  gli shard dei neuroni CRISPRi; la riserva di valutazione ha tolto circa 88 minuti di training; la GPU
  aspettava la decompressione gzip. Risultati scientifici non aperti; non è una bocciatura
  ([diagnosi](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md),
  [ricevute Codex](../reports/analisi/candidato_ibrido_2026-10-03/README.md)).
- **Misurato, pilot v2 r3 (3/10):** lo stato delle cellule di controllo aggiunge informazione al loro
  profilo medio (Q1 passa), la rete non supera il transfer (Q2 no) in entrambe le corsie; le miscele a
  posteriori non sono promettenti ([protocollo r3 §11–12](../reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md),
  [miscele](../reports/modelli/rete_cellulare_2026-10-03/esito/miscele_r3/LETTURA.md)).
- **Misurato, P3 (2/10) e P4 (3/10):** C e J `no_benefit`: i controlli medi della linea esclusa non
  migliorano il transfer né come guadagni per gene né come correzione bilineare, né con dieci gruppi né con
  una rete non lineare sul pseudobulk; sui sei membri di HepG2 vince il transfer (0,232 contro 0,184 del
  migliore braccio) ([CP-0056](checkpoints/0056-banco-contesto-c-j.md), [CP-0057](checkpoints/0057-p4-dieci-gruppi-pseudobulk.md)).
  Per indicazione del proprietario quelle reti sul pseudobulk valgono come baseline, non come candidati.
- **Scoring 1/10.** T29 non promuove la sostituzione del transfer con la rete r2 `desc`
  ([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)). La scarsa discriminazione
  dei bersagli è misurata dal PDS; risposta comune, calibrazione, apprendimento ed esportazione
  restano spiegazioni da separare. Il collasso identity di r3 è un altro braccio e un altro
  training: non dimostra la causa dello score t29.
- **Audit 1/10.** La rete cellulare r2 perde in media contro transfer su HepG2 C, ma mostra
  complementarità esplorativa. Split r2/r3 diversi impediscono un'attribuzione ai soli dati
  aggiunti; unknown non è una baseline generica addestrata. Evidenza e correzioni nella
  [revisione lead](../reports/analisi/lead_audit_2026-10-01/README.md); direzione in
  [R-LEAD](piani/strategia-scientifica.md), criteri C/J precisati da D-050.
  R3 concluso: identity collassato e controesempio del gradiente sotto clamp
  nell'[aggiornamento](../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md).

- **Misurato.** Nessun modello appreso ha passato la sua regola: encoder, modello a cancelli, rete
  dei contesti, rete relazionale ([CP-0043](checkpoints/0043-misura-decisiva-relazioni.md)), rete
  sulle sorgenti (+0,0022 e +0,0025 contro la soglia +0,01), Stack A e B
  ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md), [CP-0051](checkpoints/0051-stack-ab-negativi.md)).
- **Interpretazione.** Il contesto letto dai controlli non ha dato finora un beneficio robusto;
  questo non dimostra che nessuna rete possa funzionare ([CP-0049](checkpoints/0049-rete-sorgenti-replica.md)).
- **Regola proposta.** Una rete nuova si prova sui sei membri, con una riserva mai valutata
  ([audit del prescreen](../reports/analisi/lead_scientist_2026-09-29/neural/NN_PRESCREEN_AUDIT.md)).

Leggi prima: il [protocollo v4](../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md) e la
[diagnosi](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md); le analisi Codex del 3/10
([candidato ibrido](../reports/analisi/candidato_ibrido_2026-10-03/README.md),
[lezioni 2025](../reports/analisi/lezioni_vcc2025_2026-10-03/README.md)); [GENERALIZZAZIONE](GENERALIZZAZIONE.md);
[modelli](../reports/modelli/README.md). Piano operativo: [R-LEAD](piani/strategia-scientifica.md), con il
binario del modello e quello dei dati (D-053, D-054). T non promuove per contesti nuovi.
[R-COMP](piani/modello-competitivo.md) mantiene l'obiettivo, [R-V2](piani/modello-v2.md) le alternative.

### 6. Set finale D, E, F

- **Fatto.** La classifica finale dipende solo da D/E/F, rilasciati il 22 ottobre; gli invii
  chiudono il 5 novembre.
- **Misurato.** La prova generale in forma ridotta produce un `.vcc` valido
  ([CP-0044](checkpoints/0044-prova-generale-22-ottobre.md)); D1–D5 e D9–D11 sono corretti con i
  loro test. La stima della forma piena era circa 17 GB liberi; spazio e risorse disponibili
  vanno misurati alla ripresa, senza usare come blocco attuale la fotografia del 30/09.
- **Dichiarato dagli organizzatori, 1/10.** Il protocollo è identico nelle sei linee: stesse
  sgRNA, MOI, tempo di raccolta e pipeline. I bersagli della gara hanno un silenziamento
  mediano di almeno l'80% (ln 1,61) e 400 cellule ciascuno. *Ipotesi:* almeno una delle sei
  linee è immortalizzata non tumorale. Conseguenze e cautele nel
  [post di Arc](../reports/gara/dati_arc_2026-10-02/RISULTATI.md).

Leggi prima: [PROCEDURE §7](PROCEDURE.md#7-il-set-finale-22-ottobre), [la prova generale](../reports/invii/prova_generale_2026-09-28/RISULTATI.md).
Piano: azione 3 di [R-REV](piani/revisione-critica.md).

## Strumenti di esecuzione

### 7. Calcolo, job, disco

Le procedure stanno in [PROCEDURE](PROCEDURE.md): §1–2 per generare, impacchettare e inviare, §3 per i
job su Colab e Kaggle, §7 per il set finale. Ogni job nuovo supera il preflight di
[ERRORI](ERRORI.md), dove sono anche le [trappole operative](ERRORI.md#lezioni-operative-da-non-ripetere)
già incontrate. Chi autorizza la quota, i download e i push: [CLAUDE.md](../CLAUDE.md).

- **Archivio cloud, dal 2/10.** La radice dati si copia su Drive a percorsi invariati
  (`MyDrive/vcc2026/data/<rel>`, la radice dei job Colab); le copie valgono solo dopo la lettura da Colab
  (job 130–131). Kaggle: 557/557 shard del corpus verificati sul server, dataset tutti privati. Nessuna copia
  locale si cancella senza prova remota e senza il via del proprietario
  ([archivio cloud](../reports/sorgenti/archivio_cloud_2026-10-02/README.md)).
- **Pulizia locale del 3/10:** rimosse copie delle matrici delle vecchie reti sui contesti r1/r2
  per 14,517 GiB, con hash locali ricalcolati contro la prova indipendente Kaggle e ricevute per file;
  metadati e dipendenze attive conservati. Il resto attende le verifiche Colab
  ([ricevute e ripristino](../reports/sorgenti/libera_spazio_2026-10-03/README.md)).

## Infrastruttura degli agenti

La base di lancio `agent-hub` (fuori dalla repo), l'orchestratore e la catena di cicli ritirati il
23/09 e il coordinamento fra sessioni stanno in [AGENTI](AGENTI.md). Chi lavora su dati, modelli o
invii non ne ha bisogno.

## Archivio e storia

### 8. Metodo, evidenza e memoria del progetto

La sede di ogni tipo di informazione è in [docs/CLAUDE.md](CLAUDE.md). Per ricostruire una decisione
o un risultato: la tabella in cima a [DECISIONI](DECISIONI.md), poi la sua sezione; il checkpoint che
cita, dall'[indice](checkpoints/INDICE.md) con la colonna «Corretto da»; lo stato di un documento con
`python scripts/31_check_docs.py --status <percorso>`. Il codice ritirato e come riportarlo:
[ARCHIVIO](ARCHIVIO.md). I due riordini della repo del 30/09:
[notte](../reports/analisi/riordino_repo_2026-09-30/RIORDINO.md) e
[pomeriggio](../reports/analisi/ingresso_agenti_2026-09-30/RIORDINO.md).

Una previsione si registra prima dell'invio, con la regola di lettura
([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)); un numero locale non diventa un punteggio VCC.
