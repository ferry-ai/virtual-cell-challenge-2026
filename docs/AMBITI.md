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

- **Misurato.** Massimo osservato: t28, +0,144845, contro il t25 +0,0046, non conclusivo per la sua
  regola; la ricetta di riferimento resta quella del t22 ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
  Tutti i punteggi: [invii](../reports/invii/README.md).
- **Misurato.** Il t28 alza fedeltà (+0,051 scalato) e reach (+0,055), perde NMAE (−0,069) e
  Jaccard (−0,008): l'intervento sull'emissione sposta i membri DE, con costi.
- **Ultimo esito, 1/10.** T29, rete cellulare r2 `desc` con generatore t22: ramo c negativo.
  PDS, NMAE, reach e Jaccard scalati peggiorano rispetto a t22; fedeltà sale, MSE scalata
  resta zero mentre la grezza peggiora. Nessun nuovo invio neurale senza il banco a sei
  membri almeno al livello del transfer ([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)).
- **Interpretazione.** Dal t16 i cambi della media sono piccoli, ma diversi membri si compensano
  ([audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md)).

Leggi prima: [che cosa lascia un invio](../reports/CLAUDE.md), [PROCEDURE §1–2](PROCEDURE.md#1-il-percorso-di-un-invio).
Piani: [R-COMP](piani/modello-competitivo.md), [S-INVII](piani/invii-finale.md).

### 3. Generatore e banchi con lo scorer vero

- **Misurato.** Sul banco HepG2 ampiezza e dispersione interagiscono (+0,0177 d'indice
  nello sviluppo); la conferma su 96 bersagli dà +0,0289, ma 95 erano già stati valutati
  ([CP-0047](checkpoints/0047-conferma-generatore-t28.md), [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)).
- **Interpretazione.** Il banco HepG2 ha preso il verso dei cambi ufficiali e ne ha sovrastimato
  l'entità ([errori di metodo](ERRORI.md#errori-di-metodo-già-commessi)).
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

- **Direzione confermata, 4/10: [D-056](DECISIONI.md#d-056--transfer-con-correzione-neurale-selettiva).**
  Transfer congelato con correzione neurale selettiva, pesata sul beneficio validato fuori fold. Il selettore
  può tornare al transfer; familiarità con bersagli o contesti non equivale a affidabilità dimostrata.
  Proposta da implementare e confermare in R-LEAD, con precedenti S-001–S-007; nessuna promozione acquisita.
- **In corso, 3/10 sera: pilot v4 della rete ancorata** (direzione D-054: basale dai controlli +
  ancora dal transfer degli aggregati + correzione appresa sulle cellule). Protocollo congelato prima
  dei training, con la regola contro la propria ancora e il requisito di promozione contro la ricetta
  di produzione ([protocollo](../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md),
  [lanci](../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_r1.json)). Nessun esito ancora.
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
