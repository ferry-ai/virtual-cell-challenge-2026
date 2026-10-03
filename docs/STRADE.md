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
| S-006 | Rete ancorata v4: ancora dal transfer più correzione appresa sulle cellule | peggiora la propria ancora su H1 e HepG2; RPE1 in corso | ipotizzato | 2026-10-04 |
| S-007 | Correzioni del transfer dai controlli medi (guadagni per gene, bilineare, rete sul pseudobulk) | nessun beneficio | ignoto | 2026-10-04 |
| S-008 | Modelli appresi precedenti (encoder, cancelli, rete dei contesti, relazionale, rete sulle sorgenti, Stack A e B) | nessuno ha passato la sua regola | ignoto | 2026-10-04 |

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
- **Prova:** [protocollo v4](../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md); misure in
  `reports/modelli/rete_ancorata_v4_2026-10-03/esito/` (`laneA_h1_r1/summary.json`, `laneA_hepg2_r1/summary.json`,
  `laneB_h1_r1/bench/scaled_local.csv`); ricevute dei training nella stessa cartella. Stato al 4/10 alle 01:43: due
  linee lette su tre, RPE1 in training; la decisione sulle tre linee e il checkpoint aggiornano questa voce.
- **Sintomo:** i training sono tecnicamente accettati (quote esatte, 2 epoche, valutazione completa). Corsia A, PDS
  delle righe C: 0,547 contro 0,965 dell'ancora su H1 e 0,639 contro 0,886 su HepG2; rapporto MSE 13,9 contro 2,6 su
  H1. Corsia B di H1, media dei sei membri: 0,057 contro 0,272. L'ancora da sola passata per la rete riproduce il
  transfer (0,963 e 0,883): il danno viene dalla correzione appresa. I geni chiamati per bersaglio dalle cellule
  generate sono circa 1.800 contro 160 dell'ancora e 400 delle cellule vere.
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
- **Segnale precoce:** al controllo di salute, il PDS dello spostamento previsto sui bersagli nascosti delle linee
  di training contro quello dell'ancora sola, e il rapporto fra l'ampiezza della correzione e quella dell'ancora
  (nel log: `shift_minus_anchor_rms` 0,23 contro `anchor_rms` 0,13 a fine corsa). Avrebbe fermato i training dopo
  dieci minuti invece di novanta.
- **Guardia eseguibile:** nessuna: il controllo di salute della v4 guarda solo il guadagno di verosimiglianza. Il
  prossimo trainer deve fermarsi sul segnale precoce.

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
