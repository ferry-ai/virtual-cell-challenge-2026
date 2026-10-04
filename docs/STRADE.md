# Strade già provate: che cosa è fallito, perché, e che cosa lo riaprirebbe

**Perimetro:** gli approcci provati dal progetto (modelli, correzioni, strategie sui dati) che non hanno passato la
loro regola o si sono fermati per un difetto, uno per riga. **Fonti:** i checkpoint, i protocolli e le misure citati
in ogni voce: questa pagina riassume e instrada, non è evidenza. **Si aggiorna:** ogni volta che si legge l'esito di
una regola, nello stesso commit del checkpoint. Chiesta dal proprietario il 4 ottobre 2026 (D-055): prima il progetto
registrava bene gli esiti, ma niente obbligava chi progetta il passo dopo a fare i conti con il meccanismo dei
fallimenti precedenti; il 4/10 una rete ha finito per la terza volta con la stessa incapacità di distinguere i
bersagli (S-001, S-002, S-006).

## Il ciclo, e che cosa lo fa rispettare

1. **Prima di progettare** un modello, una correzione o un esperimento si legge la tabella qui sotto e le voci
   pertinenti ([CLAUDE.md](../CLAUDE.md), tabella dei compiti).
2. **Ogni protocollo nuovo** (`reports/<categoria>/<cartella>_<data>/PROTOCOLLO*.md`, cartelle dal 4/10/2026) ha una
   sezione `## … Precedenti` che cita le voci pertinenti con il loro ID, dice in che cosa il disegno è diverso rispetto
   al meccanismo di ciascuna e, alla riga `**Segnale precoce e arresto:**`, quale misura a basso costo fermerà il
   lavoro se lo stesso guasto si ripresenta. Chi non trova precedenti scrive `Nessun precedente pertinente:` e il
   motivo. Lo verifica `scripts/31_check_docs.py`.
3. **Ogni esito letto** (regola passata, non passata, confronto incompleto) produce un checkpoint e una voce nuova o
   aggiornata qui. Un checkpoint di tipo `esperimento` dal numero 0061 in poi porta la riga `- **Strade:**` con gli ID
   delle voci (che devono citarlo a loro volta) oppure `nessuna:` e il motivo. Lo verifica lo stesso controllo.
4. **Dalla lezione alla guardia.** Quando il guasto si può riconoscere con un controllo eseguibile (una ricevuta, un
   test, un arresto nel trainer), la voce nomina il file che lo fa; se non c'è, lo dice. Una lezione senza guardia
   dipende dal fatto che qualcuno la legga.

Il meccanismo ha sempre un'etichetta: **accertato** (c'è una prova che lo isola), **ipotizzato** (spiegazione
compatibile con le misure, non isolata), **ignoto** (non ricostruito). Non si promuove un'ipotesi ad accertata
riassumendo. Il controllo verifica struttura, ID, percorsi ed etichette; non verifica che una voce dica il vero.

## Elenco

| ID | Strada | Esito | Meccanismo | Aggiornata |
|---|---|---|---|---|
| S-001 | Rete sulle singole cellule al posto degli effetti del transfer, inviata (t29) | sotto la banda: −0,030 ufficiale | ipotizzato | 2026-10-04 |
| S-002 | Rete sulle singole cellule, pilot a linee escluse intere (r3) | perde contro il transfer in 3 linee su 3 | ipotizzato | 2026-10-04 |
| S-003 | Miscele a posteriori fra transfer e rete (r3) | non promettenti | ignoto | 2026-10-04 |
| S-004 | Miscela con cancello fra «nessun effetto» ed «effetto» nella rete | collasso del cancello | accertato | 2026-10-04 |
| S-005 | Rete ancorata v3: campionatore a epoche, riserva di valutazione stimata, lettura gzip | pilot incompleto, non una bocciatura | accertato | 2026-10-04 |
| S-006 | Rete ancorata v4: ancora dal transfer più correzione appresa sulle cellule | peggiora la propria ancora su 3 linee su 3; regola non passata (CP-0061) | ipotizzato | 2026-10-04 |
| S-007 | Correzioni del transfer dai controlli medi (guadagni per gene, bilineare, rete sul pseudobulk) | nessun beneficio | ignoto | 2026-10-04 |
| S-008 | Modelli appresi precedenti (encoder, cancelli, rete dei contesti, relazionale, rete sulle sorgenti, Stack A e B) | nessuno ha passato la sua regola | ignoto | 2026-10-04 |
| S-009 | Ibrido selettivo D-056 v1: transfer congelato + correzione neurale regolarizzata + selettore fuori fold | regola di banco passata su 5 linee (CP-0062); sul sito t30 −0,005 contro il t25, non conclusivo e nessuna promozione (CP-0064): il banco non aveva valutato il candidato inviato | ipotizzato | 2026-10-04 |
| S-010 | Fonti del transfer: tabelle aggregate in più contro le fonti della ricetta t22/t25 | «più fonti meglio» su Jurkat e K562; nessun candidato di solo transfer ammesso (CP-0062) | ipotizzato | 2026-10-04 |

## Voci

### S-001 — Rete sulle singole cellule al posto degli effetti del transfer, inviata (t29)

- **Che cosa si è provato:** la rete R-LAB del secondo training, braccio `desc`, come fonte degli effetti al posto
  della ricetta, con il generatore del t22.
- **Prova:** [CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md); riga t29 dell'[indice degli invii](../reports/invii/README.md).
- **Sintomo:** punteggio ufficiale −0,029625 contro 0,142 della ricetta; PDS grezzo 0,50 contro 0,79 del t22: la
  rete distingue poco i bersagli.
- **Meccanismo:** ipotizzato. Risposta comune, calibrazione, apprendimento ed esportazione restano spiegazioni da
  separare (CP-0055). Lo stesso sintomo ricompare in S-002 e S-006, dove la parte comune è misurata.
- **Che cosa esclude e che cosa no:** esclude l'invio di quel checkpoint; non esclude le reti sulle cellule.
- **Che cosa la riaprirebbe:** un banco locale a sei membri in cui la rete sta almeno al livello del transfer, prima
  di un altro invio neurale (regola del CP-0055).
- **Segnale precoce:** il PDS dello spostamento previsto, su bersagli tenuti fuori, confrontato con quello del
  transfer sugli stessi bersagli.
- **Guardia eseguibile:** nessuna nel codice. La regola del CP-0055 è scritta; chi la applica è il protocollo.

### S-002 — Rete sulle singole cellule, pilot a linee escluse intere (r3)

- **Che cosa si è provato:** rete che legge lo stato delle cellule di controllo (`cells`), quello medio (`mean`) e un
  braccio generico, su H1, HepG2 e RPE1 escluse intere.
- **Prova:** [protocollo r3 §11–12](../reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md),
  `reports/modelli/rete_cellulare_2026-10-03/esito/decision_r3/decision.json`,
  [confronto del 3/10](../reports/analisi/confronto_alfredo_2026-10-03/README.md).
- **Sintomo:** sul PDS degli effetti in C la rete sta sotto il transfer di 0,323 in media, 0 linee su 3; sui sei
  membri locali 0,212 contro 0,247 (HepG2) e 0,034 contro 0,223 (RPE1). Lo stato delle cellule aiuta rispetto al
  profilo medio (+0,014), ma non basta.
- **Meccanismo:** ipotizzato: non fu scomposto allora; è lo stesso sintomo di S-006.
- **Che cosa esclude e che cosa no:** esclude l'espansione di quella rete così com'è (scelta del proprietario del
  3/10); non esclude che lo stato dei controlli porti informazione.
- **Che cosa la riaprirebbe:** una rete che sulle stesse righe non perda discriminazione rispetto al transfer.
- **Segnale precoce:** come S-001.
- **Guardia eseguibile:** nessuna.

### S-003 — Miscele a posteriori fra transfer e rete (r3)

- **Che cosa si è provato:** combinare dopo il training le previsioni della rete r3 e quelle del transfer.
- **Prova:** [lettura delle miscele](../reports/modelli/rete_cellulare_2026-10-03/esito/miscele_r3/LETTURA.md).
- **Sintomo:** nessuna miscela promettente sui sei membri.
- **Meccanismo:** ignoto: non ricostruito in questa stesura.
- **Che cosa esclude e che cosa no:** non è lo stesso esperimento di una rete addestrata sul residuo del transfer
  (S-006), che è stata provata a parte.
- **Che cosa la riaprirebbe:** una rete i cui punti di forza per membro siano diversi da quelli del transfer; va
  mostrato prima membro per membro.
- **Segnale precoce:** il confronto dei sei membri uno per uno fra i due componenti, prima di mescolare.
- **Guardia eseguibile:** nessuna.

### S-004 — Miscela con cancello fra «nessun effetto» ed «effetto» nella rete

- **Che cosa si è provato:** una verosimiglianza a miscela con un cancello appreso (π) fra la componente senza effetto
  e quella perturbata, con e senza pavimento per π.
- **Prova:** [aggiornamento r3 dell'audit](../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md);
  [protocollo r3 §7–9](../reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md);
  [confronto del 3/10, §3](../reports/analisi/confronto_alfredo_2026-10-03/README.md).
- **Sintomo:** il cancello collassa: la componente perturbata smette di ricevere gradiente, con pavimento 0,01 e anche
  con π fissato a 0,5.
- **Meccanismo:** accertato: il gradiente della componente perturbata è moltiplicato dalla responsabilità a
  posteriori, non da π; quando la componente perturbata è molto meno verosimile la responsabilità è numericamente
  nulla, e un pavimento su π non la rialza.
- **Che cosa esclude e che cosa no:** esclude il cancello così formulato; π = 1 toglie questa via di collasso ma
  cambia modello ed emissione, e non è una prova di efficacia.
- **Che cosa la riaprirebbe:** una formulazione in cui la componente perturbata riceva gradiente anche quando perde,
  provata prima su un controesempio.
- **Segnale precoce:** responsabilità media e π ai primi passi, già nel log del trainer.
- **Guardia eseguibile:** `--gate-mode off` e il controllo di salute al passo 5.000 in
  `reports/modelli/rete_ancorata_v4_2026-10-03/train_cellnet.py`.

### S-005 — Rete ancorata v3: campionatore a epoche, riserva di valutazione stimata, lettura gzip

- **Che cosa si è provato:** il primo training della rete ancorata (v3 r1) su H1 e HepG2.
- **Prova:** [diagnosi](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md);
  [CP-0060](checkpoints/0060-direzione-x-transfer-pilot-v4.md).
- **Sintomo:** H1 fermo a 0,714 epoche senza leggere `tian2021_crispri` (neuroni allo 0,7% della loss invece del
  14,3%); circa 88 minuti di training tolti da una riserva di valutazione sovrastimata; GPU in attesa dei dati per
  l'81–84% del tempo.
- **Meccanismo:** accertato: il campionatore rigiocato sullo stato reale riproduce le estrazioni della corsa; la
  decompressione gzip è il collo di bottiglia misurato.
- **Che cosa esclude e che cosa no:** non dice niente sul valore scientifico della rete: è un difetto tecnico.
- **Che cosa la riaprirebbe:** niente da riaprire: corretto nella v4 (S-006 è la lettura scientifica).
- **Segnale precoce:** quote per gruppo in ogni finestra di 500 passi e unità mai estratte.
- **Guardia eseguibile:** la ricevuta `exposure.json` e i batch bilanciati,
  `reports/modelli/rete_ancorata_v4_2026-10-03/test_balanced.py` e
  `reports/modelli/rete_ancorata_v4_2026-10-03/test_train_v4.py`.

### S-006 — Rete ancorata v4: ancora dal transfer più correzione appresa sulle cellule

- **Che cosa si è provato:** logit = basale dai controlli + guadagno × ancora (il transfer da tutti gli aggregati
  delle altre linee, medie del regime J) + correzione appresa sulle singole cellule; H1, HepG2 e RPE1 escluse intere.
- **Prova:** [CP-0061](checkpoints/0061-pilot-v4-esito-tre-linee.md), regola del §7 applicata alle tre linee
  ([decision.json](../reports/modelli/rete_ancorata_v4_2026-10-03/esito/decision_r1/decision.json));
  [protocollo v4](../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md); misure in
  `reports/modelli/rete_ancorata_v4_2026-10-03/esito/` (`laneA_h1_r1/summary.json`, `laneA_hepg2_r1/summary.json`,
  `laneB_h1_r1/bench/scaled_local.csv`, `lanes_rpe1_r1_kaggle/`); ricevute dei training nella stessa cartella.
- **Sintomo:** i training sono tecnicamente accettati su tre linee su tre (quote esatte, 2 epoche, valutazione
  completa). Corsia A, PDS delle righe C: 0,547 contro 0,965 dell'ancora su H1 e 0,639 contro 0,886 su HepG2; rapporto
  MSE 13,9 contro 2,6 su H1. Corsia B, media dei sei membri, `ancorata_shift − transfer_all_J`: −0,214 (H1), −0,050
  (HepG2), −0,131 (RPE1), macro −0,132; guardia della corsia A −0,307; requisito di promozione non soddisfatto. L'ancora
  da sola passata per la rete riproduce il transfer (corsia B: 0,275, 0,216 e 0,191 contro 0,272, 0,212 e 0,192): il
  danno viene dalla correzione appresa. I geni chiamati per bersaglio dalle cellule generate sono circa 1.800 contro 160
  dell'ancora e 400 delle cellule vere (H1).
- **Meccanismo:** ipotizzato: la correzione impara uno spostamento comune a tutti i bersagli, tipico delle linee di
  training, che sulla linea nuova copre il segnale specifico. Indizio esplorativo, su linee già lette
  (`esito/esplorativo_centrato_h1_r1/summary.json`, `esito/esplorativo_centrato_hepg2_r1/summary.json`): togliendo
  dalla previsione la media sui bersagli il PDS risale a 0,852 (H1) e 0,822 (HepG2), ancora sotto l'ancora; il
  coseno specifico è 0,145 contro 0,184 su H1 e 0,201 contro 0,203 su HepG2. Quindi la parte comune spiega gran
  parte del danno, e la correzione specifica non aggiunge. Non è isolato perché la parte comune non trasferisca.
- **Che cosa esclude e che cosa no:** esclude questo disegno con questa loss (verosimiglianza per cellula, guadagno e
  correzione liberi); non esclude l'ancora, che funziona, né una correzione vincolata.
- **Che cosa la riaprirebbe:** un disegno in cui la correzione non possa spostare la media sui bersagli, o sia
  penalizzata per allontanarsi dall'ancora con una forza scelta su linee interne escluse, e che sul segnale precoce
  qui sotto non perda discriminazione. Serve un protocollo nuovo e linee non ancora lette (H1, HepG2 e RPE1 lo sono).
  Il primo tentativo è il protocollo D-056 v1 (`reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md`): testa
  comune esclusa dalla previsione, guadagno fisso, penalità, guardie interne, selettore fuori fold, conferma su Jurkat e
  K562. Esito, 4/10: regola di banco passata su cinque linee, comprese le tre di questa voce
  ([CP-0062](checkpoints/0062-d056-ibrido-selettivo-esito-banco.md), S-009).
- **Segnale precoce:** al controllo di salute, il PDS dello spostamento previsto sui bersagli nascosti delle linee
  di training contro quello dell'ancora sola, e il rapporto fra l'ampiezza della correzione e quella dell'ancora
  (nel log: `shift_minus_anchor_rms` 0,23 contro `anchor_rms` 0,13 a fine corsa). Avrebbe fermato i training dopo
  dieci minuti invece di novanta.
- **Guardia eseguibile:** nella v4 nessuna: il controllo di salute guarda solo il guadagno di verosimiglianza. Dal 4/10
  il trainer v5 si ferma sul segnale precoce: `reports/modelli/ibrido_selettivo_2026-10-04/guards.py` misura
  discriminazione, ampiezza e componente comune su coppie di validazione interne, e `train_cellnet.py` si arresta su
  due violazioni consecutive (test in `test_guards.py` e `test_hybrid_train.py`).

### S-007 — Correzioni del transfer dai controlli medi (guadagni per gene, bilineare, rete sul pseudobulk)

- **Che cosa si è provato:** correggere il transfer con i controlli medi della linea esclusa: guadagni per gene,
  correzione bilineare, dieci gruppi, una rete non lineare sul pseudobulk.
- **Prova:** [CP-0056](checkpoints/0056-banco-contesto-c-j.md), [CP-0057](checkpoints/0057-p4-dieci-gruppi-pseudobulk.md).
- **Sintomo:** C e J `no_benefit`; sui sei membri di HepG2 vince il transfer (0,232 contro 0,184 del migliore
  braccio).
- **Meccanismo:** ignoto: non ricostruito in questa stesura.
- **Che cosa esclude e che cosa no:** esclude quei confronti; per indicazione del proprietario le reti sul pseudobulk
  valgono come baseline, non come candidati. Non esclude ogni uso del contesto.
- **Che cosa la riaprirebbe:** un'informazione di contesto diversa dalla media dei controlli, con un contrasto che
  possa smentirla.
- **Segnale precoce:** il confronto con il braccio riaddestrato senza contesto, sulle stesse righe.
- **Guardia eseguibile:** nessuna.

### S-008 — Modelli appresi precedenti (encoder, cancelli, rete dei contesti, relazionale, rete sulle sorgenti, Stack A e B)

- **Che cosa si è provato:** sei famiglie di modelli appresi, elencate in AMBITI §5; le date sono nei checkpoint.
- **Prova:** [CP-0043](checkpoints/0043-misura-decisiva-relazioni.md), [CP-0049](checkpoints/0049-rete-sorgenti-replica.md),
  [CP-0051](checkpoints/0051-stack-ab-negativi.md); elenco in [AMBITI §5](AMBITI.md#5-modelli-appresi-e-generalizzazione).
- **Sintomo:** nessuno ha passato la sua regola; la rete sulle sorgenti ha dato +0,0022 e +0,0025 contro una soglia
  di +0,01.
- **Meccanismo:** ignoto: questa voce raccoglie più strade e non ne ricostruisce i meccanismi. Chi ne riprende una
  apre una voce propria dopo aver letto il suo checkpoint.
- **Che cosa esclude e che cosa no:** il contesto letto dai controlli non ha dato finora un beneficio robusto; non
  dimostra che nessuna rete possa funzionare (CP-0049).
- **Che cosa la riaprirebbe:** dipende dalla famiglia: va scritto nella voce propria.
- **Segnale precoce:** non definito per l'insieme.
- **Guardia eseguibile:** nessuna.

### S-009 — Ibrido selettivo D-056 v1: transfer congelato + correzione neurale regolarizzata + selettore fuori fold

- **Che cosa si è provato:** `ibrido = T + w · R`. T è `transfer_all_J`; R = s(N) − s(A) è la correzione della rete v5
  sulle singole cellule:
  - guadagno fisso a 1 sull'ancora;
  - testa comune nella sola verosimiglianza;
  - penalità L2 0,05 sulla correzione;
  - coppie di validazione interne a peso zero e guardie con arresto.
  w viene da un selettore logistico a cinque ingressi, stimato fuori fold. Corpus pilot a 8 gruppi; sviluppo H1, HepG2
  e RPE1, conferma Jurkat e K562.
- **Prova:** [CP-0062](checkpoints/0062-d056-ibrido-selettivo-esito-banco.md);
  [protocollo](../reports/modelli/ibrido_selettivo_2026-10-04/PROTOCOLLO.md) con gli emendamenti §12–§14;
  [decision.json](../reports/modelli/ibrido_selettivo_2026-10-04/esito/decision_full_r1/decision.json).
- **Sintomo:** è un esito positivo, non un guasto. Corsia B, `ibrido_selettivo − transfer` sui sei membri locali:
  - sviluppo +0,006, +0,063, +0,040;
  - conferma +0,037 (Jurkat), +0,074 (K562);
  - guardia della corsia A ≥ −0,02 ovunque;
  - punteggio di banco del §9: 0,134 contro 0,090 del transfer.
  Il guadagno fuori fold del selettore sull'errore quadratico pesato delle righe è piccolo (−1,8…+0,4 %), e lo stato
  delle cellule (`ibrido − ibrido_mean`) non dà un contributo coerente.
- **Meccanismo:** ipotizzato: separare la risposta comune dalla correzione e pesare la correzione fuori fold toglie lo
  spostamento comune che in S-006 copriva il segnale specifico. Lo indicano la quota comune di R nelle guardie interne
  (0,12–0,20) e la tenuta del PDS delle righe C. Non è isolato: le quattro differenze di disegno cambiano insieme.
- **Che cosa esclude e che cosa no:** esclude che una correzione neurale debba per forza peggiorare il transfer su
  linee nuove (S-001, S-002, S-006). Non dimostra che il guadagno passi al sito né al corpus completo D-053; un seme,
  8 gruppi.
- **Esito ufficiale, 4/10 ([CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)):** t30 = 0,135249, −0,004989 contro il t25, ramo b della
  regola registrata: non conclusivo, nessuna promozione. Il PDS scalato perde 0,042; fedeltà +0,014, Jaccard +0,002.
- **Che cosa del banco non si è trasferito (misurato, [diagnosi](../reports/modelli/diagnosi_t30_2026-10-04/README.md)):**
  - il candidato inviato non era un braccio del banco: R definita contro `transfer_all_J` è stata sommata al t25
    (coseno mediano fra le due baseline 0,71), con uno stimatore di R mai passato per il banco;
  - all'esportazione la quota comune di R è 0,62–0,69 contro 0,07–0,24 delle righe, oltre la soglia 0,5 della
    guardia del trainer, che lì non era applicata; l'ampiezza relativa è 0,71–0,96 contro 0,24–0,42 e l'ingresso di
    ampiezza del selettore è fuori dal suo intervallo di stima per il 45 % dei bersagli di B e C;
  - sul fold esportato (HepG2) il banco perdeva già PDS (corsia B −0,093, corsia A −0,039) e la media lo copriva con
    membri DE che sul sito non si sono mossi; il +0,074 di K562 viene per il 77 % dal JAC locale (denominatore 0,047);
  - `t30 − t25` contiene anche un cambio di realizzazione del rumore: lo stadio 45 usa un solo flusso casuale e le
    cellule dei bersagli non corretti non sono quelle del t25 (1 blocco su 210).
  Controllo locale (R4, lettura scritta prima): la stessa procedura sui controlli di HepG2, linea non di gara esclusa dal training, dà quota comune 0,61 e ampiezza 0,88 (0,23 e 0,42 sul banco della stessa linea); sulle linee di training H1 e RPE1 0,30 e 0,32. Esito registrato: non distinto sulla quota comune, «procedura o bersagli del pannello» sull'ampiezza. I 300 bersagli del pannello non sono fra quelli del banco su HepG2, RPE1 e Jurkat (0), 15 su H1, 72 su K562.
  Quale di queste differenze abbia prodotto la perdita **non è isolato**: meccanismo ipotizzato.
- **Che cosa la riaprirebbe:** un ibrido in cui il candidato inviato è esattamente un braccio valutato (una sola
  baseline in fit, banco ed esportazione), con le guardie del trainer applicate all'esportazione, una guardia sul PDS
  per linea e una correzione che non sposta la media sui bersagli; i confronti che separano le cause sul banco sono
  in `reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md`, congelati e non eseguiti. Poi il refit su
  tutti i gruppi e il corpus completo. Le cinque linee lette sono ormai sviluppo.
- **Segnale precoce:** le guardie interne del trainer v5 (discriminazione, ampiezza, quota comune) e la parità
  `ibrido_w0`. Sul candidato A/B/C, il rapporto RMS(R)/RMS(T) dell'esportazione confrontato con quello delle righe di
  sviluppo: su A vale circa e^−0,35 ≈ 0,70 contro 0,24–0,42 delle righe (`export_abc_r2`, targets_A.csv); su B e C
  0,96. Dal 4/10: la quota comune della correzione all'esportazione (> 0,5 avrebbe fermato il t30) e il PDS della
  corsia B del fold che si esporta (`reports/modelli/diagnosi_t30_2026-10-04/export_vs_rows.py`, `bench_members.py`).
- **Guardia eseguibile:** `reports/modelli/ibrido_selettivo_2026-10-04/guards.py` e l'arresto in `train_cellnet.py`; la
  parità in `hybrid_lanes.py laneB` (fallisce la corsia) e in `export_abc.py` (rifiuta l'esportazione se w = 0 non dà
  gli effetti del t25); test in `test_guards.py`, `test_hybrid_train.py` e `test_export_abc.py`. **Manca** un rifiuto
  dell'esportazione su quota comune, ampiezza e ingressi del selettore: oggi li misura solo, a posteriori,
  `reports/modelli/diagnosi_t30_2026-10-04/export_vs_rows.py`.

### S-010 — Fonti del transfer: tabelle aggregate in più contro le fonti della ricetta t22/t25

- **Che cosa si è provato:** tre regole di fonti dello stesso transfer, con medie J e ampiezza t25:
  - `production`: le tabelle della ricetta inviata, senza la linea esclusa;
  - `cells`: i gruppi con cellule del corpus pilot;
  - `all`: tutte le tabelle del cubo r2.
  Il confronto usa le stesse cellule, gli stessi bersagli e lo stesso generatore su Jurkat e K562.
- **Prova:** [CP-0062](checkpoints/0062-d056-ibrido-selettivo-esito-banco.md) §3;
  [protocollo](../reports/trasferimento/fonti_transfer_2026-10-04/PROTOCOLLO.md); corsie B in
  `reports/modelli/ibrido_selettivo_2026-10-04/esito/lanes_jurkat_r1/laneB/bench/scaled_local.csv` e
  `reports/modelli/ibrido_selettivo_2026-10-04/esito/lanes_k562_r1/laneB/bench/scaled_local.csv`.
- **Sintomo:** è un esito positivo della regola primaria:
  - `cells_J − prod_J` vale +0,113 e +0,105;
  - `all_J − prod_J` vale +0,073 e +0,142;
  - il punteggio di banco su Jurkat e K562 resta sotto 0,100 per tutti i bracci (−0,11, per il JAC di K562), quindi
    nessun candidato di solo transfer è ammesso.
  Sulle tre linee dell'indizio (H1, HepG2, RPE1) il segno era lo stesso.
- **Meccanismo:** ipotizzato: più gruppi di linea mediano via le particolarità di ciascuna sorgente; le tabelle della
  ricetta sono poche e due di loro, K562 e CD4T, sono molto diverse dalle linee nuove. Non è isolato.
- **Che cosa esclude e che cosa no:** non esclude la ricetta t25 come riferimento ufficiale (nessun invio con più
  fonti finora); indica che per D/E/F le fonti vanno scelte su linee escluse, non per abitudine.
- **Che cosa la riaprirebbe:** voce aperta: un candidato con più fonti per A/B/C richiede un punteggio di banco ≥ 0,100
  sulle linee del suo protocollo e la prova di parità della catena (§4 del protocollo).
- **Segnale precoce:** la differenza contro `transfer_prod_J` sulla prima linea completata (arresto del §5 del
  protocollo).
- **Guardia eseguibile:** nessuna nel codice; la regola è nel protocollo.
