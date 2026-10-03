# R-LEAD — imparare risposte trasferibili a contesti nuovi

- **Mandato:** prevedere come rispondono linee mai viste perturbate partendo dai soli controlli, e scegliere il modello
  con prove C/J su linee escluse intere; unico percorso operativo di R-COMP (D-052). **Mandato non negoziabile del
  proprietario (D-053):** tutte le linee e i contesti idonei nel percorso principale, secondo
  [GENERALIZZAZIONE §2.1](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile); i pilot ridotti
  restano dichiarati e non lo sostituiscono.
- **Direzione adottata (D-054, 3/10 sera):** la rete ancorata al transfer, adattamento dell'idea di X (secondo
  classificato 2025): basale dai controlli + effetto trasferito dalle altre linee (l'ancora, dagli aggregati) +
  correzione appresa sulle singole cellule. Il transfer t22/t25 resta il riferimento di produzione e una componente;
  ESM2 è un confronto successivo, a parità di dati. Fonti: [proposta Codex](../../reports/analisi/candidato_ibrido_2026-10-03/README.md),
  [lezioni 2025](../../reports/analisi/lezioni_vcc2025_2026-10-03/README.md),
  [revisione delle ancore](../../reports/analisi/revisione_ancorata_codex_2026-10-03/README.md),
  [diagnosi dei training v3](../../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md).
- **Stato (3/10, 23:15 CEST):** in corso su due binari. Lo stato scritto qui non prova che un job sia vivo: si rilegge
  su Kaggle prima di agire (PIANI §3).
  - **Modello, pilot v4** ([protocollo](../../reports/modelli/rete_ancorata_v4_2026-10-03/PROTOCOLLO.md), congelato a
    `ec580c6`, emendamento §10 a `953eb1e`, entrambi prima dei training): batch bilanciati a ogni passo, gemelli
    compatti degli shard, budget separati, ancore a medie J da tutti gli aggregati del cubo. Training
    `rcell-v4-train-h1-r1` e `rcell-v4-train-hepg2-r1` in esecuzione dalle 23:06
    ([lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_r1.json)); RPE1 quando una delle due
    sessioni GPU si libera. La v3 r1 è un pilot incompleto (H1 tecnicamente non accettabile), non una bocciatura.
  - **Dati, integrazione di tutti i contesti (D-053), indipendente dall'esito del pilot:** esecuzione in
    [R-LAB](piano-giorno-2026-09-30.md) (le quattro parti Orion che completano HCT116 e HEK293T in corsa dalle 23:08,
    [log di lancio](../../reports/sorgenti/ingestione_completa_2026-10-03/kaggle_cpu/lancio_orion_r2.jsonl));
    inventario riconciliato del catalogo, aggregati mancanti e campioni annidati in [R-DATI](dati-affidabilita.md).
- **Assegnazione:** Claude Code, sessione «Integrazione Codex e piano operativo» (`5eacdf`), macchina
  `LAPTOP-DLG1LHV1`, dal 3/10 21:47 CEST (commit di partenza `8f43310`), su richiesta del proprietario in chat, con
  l'autorizzazione dei job necessari al piano su Colab e Kaggle entro quota. Perimetro: questa scheda, PIANI,
  PROGETTO §0, AMBITI, REGISTRO, `reports/modelli/rete_ancorata_v4_2026-10-03/`, dati in
  `processed/rete_ancorata_v4_2026-10-03/`, regia dei job del binario dati che il piano richiede. Fuori perimetro:
  `adattatori_codex/` e i file non tracciati di altre sessioni. Le sessioni `22d21f` e `c7c07a` risultano inattive.
  **Subentro, 3/10 23:34 CEST:** Claude Code, sessione `d0100a`, stessa macchina, commit di partenza `c86f6ed`, su
  richiesta del proprietario in chat («Continua il compito dell'agente precedente», con il messaggio di passaggio della
  `5eacdf`, chiusa). Stesso perimetro e stesse destinazioni degli output; job riletti su Kaggle alle 23:32 prima di
  agire (cinque in corsa, `vcc-orion-hek293t-p2of8-r3` concluso), quota GPU 12,14 h residue alle 23:34.
- **Prossimo passo:**
  1. Leggere le ricevute tecniche dei training H1 e HepG2 con `fetch_outputs.py`, senza file di valutazione, e
     l'accettazione del §5 del protocollo; lanciare RPE1 con il comando del lancio.
  2. Per ogni linea accettata: generazione delle cellule (`kaggle_gen.py`, CPU), corsia A (`bench_effects.py`) e
     corsia B (`lane_b.py`); poi `decide_anchored.py`, che applica la regola del §7 e il requisito di promozione del
     §10.4 (battere anche `transfer_prod_J`).
  3. Binario dati: verifica di linea di HCT116 e HEK293T a parti finite (`build_orion_verify.py`), poi le parti CD4;
     inventario riconciliato del catalogo e aggregati per le voci senza tabella (R-DATI); campioni annidati
     32/64/128 con perdita d'informazione misurata contro i riassunti completi, letti dai gemelli.
  4. Qualunque sia l'esito del pilot, il corpus ampliato (prima CD4T, HCT116, HEK293T con cellule verificate) entra nel
     protocollo successivo; ESM2 dopo, a parità di dati e di campione.
- **Stato della sessione `d0100a` (4/10, 00:09 CEST; i job si rileggono su Kaggle prima di agire):**
  - In corsa: i due training GPU (dalle 23:06 del 3/10); su CPU `vcc-orion-hct116-verify-r1` (23:59),
    `vcc-cd4-d1-rest-verify-r1` (00:04), `vcc-cd4-d1-stim8hr-p{0,1}of2-r1` (23:35) e lo studio dei campioni annidati
    `rcell-v4-nested-h1-r1` (23:52, [protocollo](../../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md)
    con la regola congelata prima dei numeri, [lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_nested_r1.json)).
  - Chiusa: HEK293T, 223 shard e 4.534.299 cellule come attese, sha256 riletti da un altro kernel
    ([ricevute](../../reports/sorgenti/ingestione_completa_2026-10-03/orion/esito_verifica_hek293t_r1/line_complete.json)).
  - Pronto e non ancora spinto: gemelli compatti degli shard lasciati negli output dei kernel (`kaggle_fast_units.py`,
    3 test), da lanciare a sessione CPU libera per HEK293T (due kernel da quattro parti), HCT116 dopo la sua verifica
    e KOLF pan-genome; poi le 20 parti CD4 rimaste con `fill_sessions.py`.
  - [Inventario riconciliato](../../reports/sorgenti/inventario_riconciliato_2026-10-04/README.md): cellule di 8 gruppi
    su 21 nel pilot, aggregati di 10 nelle ancore, lacuna e lavoro per ogni altra voce.
  - Quota GPU letta il 3/10 alle 23:58: 11,32 h residue su `davideferrante11` (in consumo), 30 h intere su ciascuno
    degli altri due account; gli input dei training sono kernel e dataset privati di `davideferrante11`.
  - Scostamenti dalla proposta di Codex, detti al proprietario in chat: batch e fonti delle ancore cambiati insieme
    nella v4; Kaggle CPU al posto di Colab CPU per gemelli, campioni e generazione; riassunti delle cellule ammesse
    (R-DATI passo 2) non iniziati.
  - **Aggiornamento delle 00:30.** Chiuse e verificate anche HCT116 (109 shard, 3.409.169 cellule) e CD4 `D1_Rest`
    (154 shard, 1.750.820 cellule idonee su 3.074.496 righe), ricevute in `orion/esito_verifica_hct116_r1/` e
    `cd4/esito_verifica_d1_rest_r1/` dell'ingestione. Gemelli in corsa: `rcell-v4-fast-hek293t-{a,b}-r1` (00:12,
    00:14), `rcell-v4-fast-hct116-a-r1` (00:23); restano HCT116 parti 2–3, KOLF pan-genome, la terza ondata scPerturb.
    Correzione di Codex inoltrata dal proprietario (00:13): la scelta dei campioni è per fold e legge solo le cellule
    di training; lo studio r1 resta esplorativo ([emendamento §10](../../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md),
    test di invarianza). Da lanciare a sessione libera: `kaggle_nested.py` con `--dispersion` e slug
    `rcell-v4-nested-fold-<linea>-r1`, uno per fold.
  - **Aggiornamento delle 00:53, binario del modello.** H1 concluso alle 00:39 e **tecnicamente accettato** (§5:
    uscita 0, 365 gemelli verificati, nessuna cellula non di training, quote esatte in 60 finestre su 60, salute e
    valutazione complete, ancore a regime J; 2,0 epoche in 4.878 s, 1.579 cellule al secondo, attesa dei dati 0,565;
    [ricevute](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/train_h1_r1/)). RPE1 spinto alle 00:42
    ([lancio](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_rpe1_r1.json)); HepG2 ancora in corsa.
    Cellule di H1 generate (`rcell-v4-gen-h1-r1`). **Corsia A di H1 letta (misurato, 72 righe C, una linea su tre):**
    `ancorata` PDS 0,547 contro 0,965 di `transfer_all_J` e 0,963 di `ancora_sola`; coseno −0,031 contro 0,162;
    coseno specifico 0,145 contro 0,183; rapporto MSE 13,9 contro 2,6 (`laneA_h1_r1/summary.json` nella radice dati).
    Con −0,42 su H1 la guardia del §7 (media delle tre linee ≥ −0,02) è aritmeticamente quasi irraggiungibile. La
    corsia B di H1 gira sul portatile dalle 00:50 (PID 28200, `laneB_h1_r1` nella radice dati). Dopo: ricevute,
    generazione e corsie di HepG2 e RPE1, poi `decide_anchored.py` sulle tre linee e il checkpoint.
  - **Indicazione del proprietario in chat, 4/10 01:06:** Alfredo riferisce un modello a «quasi 0,08»; si può
    aspettare che lo pubblichi, seguirlo e migliorarlo «se non c'è nulla di meglio». Non verificato qui: scala e
    provenienza di quel numero (chiesto al proprietario; sul punteggio ufficiale la ricetta t22/t24 vale 0,142, il t28
    0,1448 e l'unica rete inviata, t29, −0,030). Non cambia il piano scritto: il pilot v4 si chiude sulle tre linee
    con la sua regola, il binario dati prosegue; il modello di Alfredo, quando arriva, si mette sul banco C/J a sei
    membri contro il transfer con una regola scritta prima dei numeri. Le 30 ore GPU intere di ciascuno degli altri due
    account restano libere per questo. HepG2 concluso alle 01:01 e tecnicamente accettato
    ([ricevute](../../reports/modelli/rete_ancorata_v4_2026-10-03/esito/train_hepg2_r1/)); la sua generazione attende
    una sessione CPU libera.
  - **Corpus ampliato, percorso critico (non iniziato):** protocollo con i gruppi adottati; pre-passo sui 365 shard
    del pilot più HCT116, HEK293T e KOLF pan-genome (16,2 milioni di cellule). Stima, non misura: il pre-passo del
    pilot ha impiegato 10.200 s per 5,6 milioni di cellule con 4 processi, quindi circa 8 ore per fold a parità di
    processi; ma gli shard Orion hanno 130–160 milioni di valori l'uno e quattro processi insieme hanno già esaurito
    la memoria nella costruzione dei gemelli (E-20261004-001). Con due processi il tempo supera le 12 ore di un kernel.
    Da decidere prima di lanciare, con il picco di memoria che i kernel dei gemelli ora registrano: pacchetto a
    tetto fisso scelto dai soli metadati prima del pre-passo, lettura a blocchi di righe, oppure pre-passo per
    sorgente con unione. `kaggle_train.py` costruisce l'elenco degli shard solo dai dataset con `files.json`: va
    esteso agli output dei kernel. Le chiavi dei bersagli del pilot (19.814 simboli, dall'inventario P0 che comprende
    Orion e KOLF) coprono già queste sorgenti. Poi campioni per fold e ancore per fold.
- **Riprendere da qui (passaggio ad altro account, 3/10 23:30 CEST; job verificati alle 23:27, tutti RUNNING):**
  - GPU: `rcell-v4-train-h1-r1`, `rcell-v4-train-hepg2-r1` (dalle 23:06). CPU: `vcc-orion-hct116-p3of4-r3`,
    `vcc-orion-hek293t-p{0,1,2}of8-r3` (dalle 23:08). Pronti: dataset `davideferrante11/rcell-v4-code-r1` (training),
    `rcell-v4-gen-r1` (generazione, bersagli r3), kernel `rcell-v4-anchors-r1` e `rcell-v4-fast-{a,b,c}-r1`.
  - Ricevute a training finito, senza i file di valutazione: `python fetch_outputs.py --config-dir
    ~/.kaggle-davideferrante11 --slug rcell-v4-train-<linea>-r1 --pattern "train/*.json" --pattern "train.log"
    --pattern "*kernel_done.json" --exclude "*eval*" --out esito/train_<linea>_r1` nella cartella v4; accettazione
    del §5 (`exposure.json`, `coverage.json` con `timing`, `verify.json`, `health.json`).
  - RPE1: il comando di [lancio_train_r1.json](../../reports/modelli/rete_ancorata_v4_2026-10-03/lancio_train_r1.json)
    con `--anchors-line RPE1 --anchors-dir anchors_RPE1_all --prepass-from rcell-prepass-rpe1-r1`, slug
    `rcell-v4-train-rpe1-r1`, appena una sessione GPU è libera; poi `kaggle quota`.
  - Generazione per linea: `python kaggle_gen.py kernel --config-dir <dir> --owner davideferrante11 --stage <nuova>
    --held-group <LINEA> --train-kernel rcell-v4-train-<linea>-r1 --prepass-kernel rcell-prepass-<linea>-r1
    --anchors-kernel rcell-v4-anchors-r1 --anchors-dir anchors_<LINEA>_all --slug rcell-v4-gen-<linea>-r1`.
    Corsie A/B e regola: comandi nei docstring di `bench_effects.py`, `lane_b.py`, `decide_anchored.py` (cellule vere e
    bersagli da `out_gen_h1_r3`, `out_gen_hepg2_r3b`, `out_gen_rpe1_r3b`; `--splits` da `out_prepass_<linea>_r1`).
  - Binario dati: `nested_samples.py` (studio dei campioni annidati) è scritto e testato, il suo launcher Kaggle no
    (input: gemelli, i dataset `rlab-*` per le colonne obs, `rcell-prepass-h1-r1`). Inventario riconciliato di
    R-DATI non iniziato. Verifiche di linea Orion a parti finite (R-LAB).
  - Da riferire al proprietario: un processo Python bloccato da una sessione chiusa (PID 2288, `C:\\Python314\\python.exe -`,
    padre bash PID 17800, dalle 16:19) occupa circa un core del portatile; terminarlo è stato negato dal controllo dei
    permessi, va fatto a mano.
- **Dipendenze:** [R-LAB](piano-giorno-2026-09-30.md) e [R-DATI](dati-affidabilita.md) per i dati,
  [GENERALIZZAZIONE](../GENERALIZZAZIONE.md), D-050, D-052, D-053, D-054; PROCEDURE §3 ed ERRORI per ogni job.
- **Chiusura:** scelta motivata con prove riproducibili e pipeline finale verificata, oppure esito negativo o
  inconclusivo con il transfer conservato e il limite identificato.
- **Dove stanno gli esiti precedenti:** P3, P4, pilot v2 (r3), miscele, v3 e v4 in
  [AMBITI §5](../AMBITI.md#5-modelli-appresi-e-generalizzazione); le note datate di questa scheda fino al 3/10 sera
  nello [storico del consolidamento](../storico/consolidamento_2026-10-03/INDICE.md).

## 1. Domanda scientifica e perimetro

**Ipotesi da verificare:** a parità di dati e generatore, una correzione della risposta dipendente dai controlli del contesto nuovo migliora il trasferimento degli effetti. Non basta ricostruire il basale, ridurre la loss o riconoscere un'identità di linea.

Il [confronto ufficiale Arc del 1 ottobre](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026) distingue esempi perturbati nella linea destinataria nel 2025 e soli controlli nelle sei linee del 2026. Il bersaglio può essere già noto in altre linee. Quindi **C e J** sono i regimi rilevanti; T è diagnostico e non promuove un modello per contesti nuovi. La figura chiarisce il compito, non dimostra la causa dei fallimenti locali.

Transfer e cellnet tentano già il trasferimento fra contesti. Ciò che manca è una prova robusta del beneficio appreso dal contesto: l'[audit](../../reports/analisi/lead_audit_2026-10-01/REVISIONE.md) trova r2 inferiore al transfer su HepG2 C in una misura esplorativa. HepG2 già esaminata resta sviluppo. Il [t29](../checkpoints/0055-t29-rete-cellulare-punteggio.md) richiede prima di un altro invio neurale un banco locale a sei membri almeno al livello del transfer. Il collasso `ident` di r3 non identifica la causa del t29, che usa r2 `desc`.

**Cambio rispetto al piano precedente:** costruire prima la prova di trasferimento e il confronto semplice; recuperare la rete solo come candidato motivato. Non si richiede che il bilineare vinca per poter provare una rete: un esito negativo può motivare un'ipotesi non lineare, ma occorrono dati identificabili e un contrasto che possa smentirla.

## 2. Sequenza e contratti di consegna

Gli identificativi P0–P6 sotto hanno questo significato dal 2 ottobre; la [versione precedente](../storico/R-LEAD_pre_contesti_2026-10-02.md) è storia, non una seconda coda.

| Passo | Output minimo | Condizione per avanzare |
|---|---|---|
| P0 — dati e fattibilità | `preflight.json`, `input_manifest.json`, `context_target_study.csv`, `feasibility.md` | Supporto, confondimenti e input disponibili espliciti |
| P1 — esposizione e split | `exposure_manifest.json`, `split_manifest.json`, `reserve_manifest.json` | C/J effettivi, esclusioni globali e storia delle riserve verificati |
| P2 — banco e regola | `PROTOCOLLO.md`, runner, fixture/test, `export_parity.json` | Regola fissata prima dei nuovi risultati; percorso fino allo scorer verificato |
| P3 — confronto semplice | codice, manifest dei fit, sei metriche, `context_ablation.json`, `decision.json` | Beneficio, assenza di beneficio o inconclusività attribuiti al confronto corretto |
| P4 — estensione motivata | `hypothesis.md`, nuova versione, `fix_matrix.json` se applicabile, misure appaiate | Una lacuna precisa motiva rete, dati o distribuzioni; stesso banco |
| P5 — conferma indipendente | candidato congelato, `confirmation.json`, `decision.json` | Regola rispettata su riserva appropriata o indipendenza insufficiente dichiarata |
| P6 — consegna finale | manifest della pipeline, prova a forma piena, verbale | Catena riproducibile e valida, anche se resta il transfer |

Nuovi output in `reports/analisi/generalizzazione_contesti_<data>/` e nuovo codice di ricerca in `reports/modelli/risposta_contesto_<data>/`, con suffisso se già occupati. Sono destinazioni proposte, non risultati esistenti. Indici e registro si aggiornano quando vengono create. Ogni run ha directory nuova, commit, comando, ambiente, input/hash, ruoli, parametri, seed e output/hash; dati e pesi pesanti restano fuori da Git. Distinguere **implementato, eseguito, misurato, adottato**.

## 3. P0 — quale trasferimento possiamo effettivamente imparare

1. Verificare Git, input leggibili, spazio, memoria, interpreter e scorer reale: `cell_eval2.config` e preset `vcc2026`. Per problemi di visibilità seguire [CP-0054](../checkpoints/0054-visibilita-scorer-e-consegna.md) prima di reinstallare. Su altra macchina usare [CONSEGNA_TEAMMATE](../CONSEGNA_TEAMMATE.md).
2. Costruire dal corpus presente una matrice con linea/donatore/stimolo, studio, assay, modalità CRISPRi/a/KO, bersaglio, guide/repliche, controlli, numerosità, geni misurati, unità e disponibilità di cellule o sole DE. Distinguere identità biologiche e alias. Per ogni confronto indicare gli input e il codice che producono le stime.
3. Contare perturbazioni osservate in più contesti, variazione fra contesti e confondimento linea/studio/assay. Se linea e studio coincidono, il confronto non separa le loro cause. Donatori della stessa linea non diventano automaticamente nuove linee indipendenti. Descrivere qualità delle etichette e riproducibilità fra guide/repliche quando misurabili.
4. Riportare efficacia del knockdown, profondità, numerosità e assay come metadati/strati quando disponibili. L'80% di riduzione dichiarato da Arc per la propria curazione non autorizza a filtrare retroattivamente la nostra validazione per efficacia osservata. Valori mancanti restano mancanti. CRISPRi, KO e attivazione hanno ruoli distinti.
5. Dichiarare quali linee permettono training, sviluppo e conferma separati, prima di sceglierle per i punteggi. Priorità ai collegamenti fra contesti, non al conteggio totale di cellule. Sorgenti senza overlap col pannello restano ammesse secondo D-044.

**Esito utile:** una mappa di ciò che è identificabile. Se mancano controlli, repliche o collegamenti, indicare file, locatore, byte e confronto reso possibile; R-DATI colma quella lacuna. L'annuncio dei dati Arc non significa che le risposte della gara siano training scaricabile. Nessun download o job cloud è implicito in questo piano.

## 4. P1 — simulare il 2026 senza cambiare gli split dopo i numeri

- **C:** bersaglio visto, linea nuova. **J:** bersaglio e linea nuovi. **T:** bersaglio nuovo, linea vista, solo diagnosi. Il cambio di pannello non implica automaticamente J.
- Escludere la linea destinataria perturbata da tutti gli studi, stimoli, cache, prior e derivati del fit. In J escludere anche le risposte dei bersagli da tutte le sorgenti, riconciliando alias, guide e repliche. Registrare provenienza del pretraining.
- Usare controlli della linea esclusa soltanto come input al percorso di inferenza preregistrato. Nessuna sua risposta perturbata in preprocessing, selezione di geni, fit, early stopping o tuning. Specificare separazione/incrocio delle librerie dei controlli usati per input basale e contrasto di valutazione.
- Costruire fold di sviluppo con linee intere escluse, ripetuti su più linee se possibile; scegliere iperparametri su ulteriori contesti interni esclusi. Tenere distinta una riserva finale mai consultata. Se il corpus non consente questa separazione, dichiarare il banco esplorativo e cosa manca; non fabbricare indipendenza con split di cellule.
- R2/r3 hanno esposizioni e split diversi: ricostruirli prima di ogni confronto. K562 già nel loro training non è un holdout neurale. Un nuovo fit può escluderla, ma risultati già noti non rendono il contesto una conferma finale intatta. H1 train/val sono nel corpus, H1 test resta chiusa: un test H1 dopo fit H1 non prova C/J.

**Accettazione eseguibile:** fixture con alias e la stessa linea in studi diversi; aggiunta/riordino di shard e QC non cambiano ruoli congelati. Gruppi persi dopo QC sono riportati, non riassegnati. Il controllo di esclusione vale per ogni braccio, compreso il transfer. Un unico contesto escluso o il bootstrap dei suoi target non misura incertezza fra contesti. Il manifest delle riserve registra anche valutazioni e tuning già effettuati.

## 5. P2 — un banco comune e una regola prima dei risultati

Congelare protocollo, bracci, supporti, fold, metrica primaria, aggregazione, miglioramento pratico richiesto, regressioni ammesse, confronti multipli e regola C/J. Motivare le soglie con pilot di sviluppo o informazione indipendente; se si usano risultati per progettarle, quelle osservazioni non sono conferma. Nessuna soglia numerica è inventata da questo piano.

Il runner usa verità, controlli, target, geni misurati, numerosità e seed comuni. Conservare copertura e gruppi esclusi; niente selezione silenziosa dei gruppi più numerosi. Normalizzatori, PCA e rappresentazioni si stimano sul fit ammesso. Un gene non misurato resta mascherato.

Ricostruire t22/t24 dai manifest per la replica; mantenere la correzione dello stimatore t25 nel riferimento corretto, distinguendo l'emissione t28. Fissare riferimento e generatore prima del confronto. Controllare ordine dei geni, log/CPM, maschere, scala, cis, clipping e fallback con una prova piccola di parità effetto → export → generazione; documentare tolleranze. La replica r2 serve se quel checkpoint entra nel banco, non blocca i confronti semplici.

Misurare **PDS, MSE, NMAE, FID, reach e Jaccard**, con scorer e aggregazioni effettivi, per contesto/regime/seed; mantenere numeratori/denominatori della MSE. Macro per contesto e media operativa restano separate. Non convertire le ancore aggregate in uno score VCC esatto. Senza ancore locali indipendenti usare grezzi e una regola esplicita sui sei membri. Coseno top-200, likelihood e metriche sugli effetti servono alla diagnosi, non alla promozione. Sole DE permettono una prova sugli effetti, non il banco completo sulle cellule.

Prevedere almeno tre seed dei finalisti e incertezza appaiata per unità indipendenti, distinguendo variabilità di generazione, fit, target e contesto. Tre seed non sostituiscono nuove linee. D-050 permette adozione nel ramo C con protezione preregistrata di J; per affermare generalizzazione congiunta serve J. Resta il vincolo t29 per nuovi invii neurali.

## 6. P3 — primo esperimento: il contesto migliora la risposta?

Implementare un'interfaccia comune: `fit(train, validation, manifest)` e `predict(target_descriptor, control_context, measured_mask)` → effetto, supporto, fallback. È un contratto proposto, da adattare alle API esistenti senza duplicare il generatore.

| Braccio | Scopo |
|---|---|
| Nullo | Riferimento di nessun effetto |
| Generico addestrato senza identità del bersaglio | Misurare quanto spiega una risposta comune; unknown non addestrato non lo sostituisce |
| Transfer dello stesso bersaglio | Riferimento C; in J nessuna risposta vietata, fallback esplicito |
| Modello del bersaglio senza contesto | Stessi descrittori leciti del candidato; confronto per l'utilità del contesto |
| Modello semplice condizionato | Effetto condiviso del bersaglio più correzione bilineare regolarizzata dai controlli |

Partire da descrittori basali su geni misurati e descrittori trasferibili del target; trasformazioni, rango, shrinkage e ampiezza si scelgono nei fold interni. Il target-ID può essere un confronto C, non la soluzione per J. Per il modello condizionato, il riferimento condiviso può essere il transfer C o il modello senza memoria J: le due strade sono esplicite, con fallback appreso e supporto registrato. Non si impone una nuova famiglia di embedding senza un'ablation che ne motivi l'informazione aggiuntiva.

Se si apprende un residuo rispetto al transfer, calcolare riferimento e residui di training out-of-fold per contesto: togliere ogni linea destinataria anche dalla media di transfer. In J rispettare inoltre le esclusioni globali dei target. Pesi di affidabilità e blending si stimano fuori campione; niente scelta per target del vincitore osservato nel test.

**Prova dell'uso del contesto:** confrontare il modello con contesto corretto, con contesto ignorato (braccio riaddestrato) e con descrittori scambiati secondo permutazioni fissate nel protocollo. Nello scambio mantenere i veri controlli destinatari per basale e generatore, e fissi target, supporto, calibrazione e seed: cambia soltanto il condizionamento dell'effetto. Se codice ed encoder intrecciano basale ed effetto, separare i due percorsi prima del test. Lo scambio da solo può produrre input fuori distribuzione: non dimostra causalità né basta senza il confronto riaddestrato. Permutare anche il target per diagnosticare la specificità.

**Decisione:** distinguere miglioramento della catena e prova del contributo del contesto. Una calibrazione utile ma insensibile al contesto può essere valutata per la produzione senza chiamarla apprendimento della risposta contestuale. Se il candidato perde, salvare la matrice degli errori; il risultato chiude quel confronto, non tutte le reti.

## 7. P4 — rete, dati o distribuzioni solo per un limite identificato

Prima di implementare l'estensione scrivere ipotesi, contrasto, output atteso e regola che la smentisce. Esempi: interazione non lineare non catturata dal bilineare; dati senza collegamenti; verità instabile; perdita introdotta dal generatore a pari effetto medio. Un esito inconclusivo per scarso supporto non motiva automaticamente una rete più grande.

Se si riusa cellnet, copiare il codice in una destinazione nuova; preservare originali e report importati. Usare [NOTA_TRAINING](../../reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md) e [AGGIORNAMENTO_R3](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md) per registrare ogni difetto come riprodotto, già corretto, non applicabile o non verificabile.

| Verifica necessaria per il codice riusato | Accettazione |
|---|---|
| Split e prepass | Esclusioni e stabilità P1 anche dopo QC |
| Sampler e pesi globali | Coefficienti aggregati corretti nel replay; niente rinormalizzazione nel batch che annulli i pesi |
| Controlli | Reservoir riproducibile per libreria, nessuna perturbata, fixture con librerie tardive e ordine variato |
| Miscela e gradienti | Log-pesi stabili, gradienti finiti e recupero nel controesempio; monitor per studio |
| Export e resume | Parità, seed ripristinati, smoke e pilot prima del job completo |

`--pi-floor` esiste già: non ricrearlo né scambiarlo per apprendimento dimostrato. Il quarto training datato mescola floor e dati: non riparte automaticamente. Una rete nuova si confronta con P3 sugli stessi fold e input; nessuna promozione da T o dalla likelihood.

Per i dati, ablation annidate a split fisso separano contesti, cellule, qualità e assay; non cambiare corpus e architettura insieme per attribuire il beneficio. R-DATI può aprirsi già da P0/P1 se manca l'informazione per costruire il banco. Per R-SWITCH occorre un limite di popolazione misurato a pari effetto medio e guide/repliche indipendenti; niente coppie cellulari inventate o bistabilità dedotta dalla sola bimodalità.

## 8. P5 — conferma e scelta

Congelare candidato, preprocessore, supporto C/J, adattamento dai controlli, fallback, calibrazione e regola prima di aprire la riserva appropriata di P1. Aprirla una volta; una bocciatura non si sana cambiando la soglia. H1 test non è automaticamente quella riserva. Se non esiste una conferma indipendente al livello di contesto, dichiarare il limite: non rinominare una rivalutazione del banco. Non sostenere generalizzazione robusta da un solo contesto o da target bootstrap sullo stesso contesto.

Conservare il transfer se nessun candidato passa. Un esito negativo produce una scelta del prossimo contrasto motivata da ciò che è misurato, senza espansione automatica del corpus né training senza domanda. La prova finale della pipeline procede comunque.

## 9. P6 — consegna D/E/F

La [prova generale a forma piena](revisione-critica.md) è necessaria anche col transfer: risorse attuali, inferenza completa, nuovi target, assi, maschere, controlli e packaging bitwise. Portare in produzione soltanto componenti adottati con test di parità. Al rilascio del 22 ottobre usare solo input leciti e adattamento preregistrato; registrare supporto C/J e fallback per target. [S-INVII](invii-finale.md) presidia la consegna entro il 5 novembre secondo le autorizzazioni della sessione, senza promessa di punteggio.

## 10. Handoff e lavoro indipendente

Claude consegna commit locali, codice/test/log, manifest, protocollo, misure e decisione; aggiorna scheda, indici e registro. Nessuna misura nasce dalla sola stesura di questo piano. Se manca un input, completare fixture, runner e verifiche indipendenti, poi indicare il minimo necessario per il passo impedito. Non ricreare tutto il disco della macchina origine. Download, cloud, nuovi agenti, invii e push seguono CLAUDE.md e le autorizzazioni della chat. Il piano non assegna tempi né limiti preventivi al lavoro.
