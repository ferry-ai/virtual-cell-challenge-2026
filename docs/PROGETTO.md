# Mappa del progetto — VCC 2026

**Questo è il punto di ingresso.** Se leggi una cosa sola, leggi questa pagina.
Aggiornata il 2026-09-16.

**Pianificazione del 16 settembre:** due workflow paralleli, entrambi proposte da
approvare. [Implementazione](PIANO_IMPLEMENTATIVO_2026-09-16.md): incarichi, scadenze e
regole di accettazione per arrivare a un candidato competitivo.
[Comprensione](PIANO_COMPRENSIONE_2026-09-16.md): stato, esperimenti, criticità e
studio, per i ricercatori. Si appoggiano sulla fotografia della classifica in
`reports/leaderboard_2026-09-16/`. Dal 17 settembre i due piani si preparano ogni
mattina alle 8 con la skill di progetto `piano-mattutino` (`/piano-mattutino`), che
parte da un'attività pianificata dell'app Claude e produce solo pianificazione.

**La catena di cicli (dal 16 settembre sera, [CP-0019](checkpoints/0019-catena-cicli-guardiano.md)).**
Il piano sigillato apre il ciclo 01. In ogni ciclo:
- Codex scrive il foglio e i test di collaudo;
- Claude implementa su un branch locale;
- Grok controlla, e può chiedere fino a tre campagne DeepSeek-Kimi;
- un resoconto chiude il ciclo.

I cicli successivi li avvia ChatGPT (l'app Codex) alla fine di un dialogo con il
proprietario, quante volte si vuole; nessuno li avvia a mano. È implementato e provato
solo con agenti simulati: nessun ciclo è ancora girato dal vivo
([CICLO_GIORNALIERO.md](CICLO_GIORNALIERO.md)).

**Dati grezzi pesanti, 16 settembre pomeriggio:** il proprietario dichiara che
`K562_gwps_raw_singlecell_01.h5ad` e `NadigOConner2024_hepg2.h5ad` sono già sul suo
Google Drive (5 TB). Da ora quei due file **si collegano dal runtime remoto, non si
scaricano**, e il portatile resta fuori dal percorso come prima (D-005). Le dimensioni
dichiarate tornano con il catalogo, ma md5 e percorso delle copie non sono verificati.
Attenzione: con le impostazioni predefinite il notebook remoto passerebbe a scaricare il
blocco successivo ([CP-0018](checkpoints/0018-drive-storage-confermato.md)).

**Pianificazione del 15 settembre:** [piano operativo](PIANO_OPERATIVO_2026-09-15.md)
con priorità giornaliere, incarichi e verifiche per dati, remoto e modello. È una
proposta fondata sugli artefatti esistenti, non un nuovo risultato sperimentale.
Il suo §8 segnala disallineamenti ancora presenti nei riepiloghi storici.

**Mandato aggiornato:** l'utente approva il piano e concentra oggi tutte le attività
possibili, avviando agenti contemporanei e supervisionandoli personalmente. Solo il
training può continuare oltre oggi. La [regia parallela](REGIA_PARALLELA_2026-09-15.md)
prevale sulla precedente scansione settimanale e sui limiti di filoni aperti.

Le altre pagine del sistema: [checkpoint](checkpoints/INDICE.md) (cosa è successo e
quando), [decisioni](DECISIONI.md) (cosa abbiamo scelto e quando va riaperto),
[registro](REGISTRO.md) (di quali documenti e dati ci si può fidare).

## 1. Il problema

Bisogna prevedere come cambia l'espressione genica di una cellula quando si spegne uno
di 300 geni, in tre tipi cellulari (A, B, C) mai visti prima. Della gara riceviamo solo
le cellule **non perturbate** dei tre contesti: 18.400 cellule ciascuno. Nessun esempio
di perturbazione, in nessuno dei tre. Si chiama previsione *zero-shot*: bisogna
imparare altrove e trasferire qui.

La classifica finale dipende solo dal set finale, su tre contesti diversi (D, E, F) e
300 perturbazioni nuove, rilasciato il 22 ottobre 2026. Le sottomissioni chiudono il
5 novembre 2026. Formato, metriche e setup: `README.md`.

## 2. Dove siamo

| Fase | Stato |
|---|---|
| Ambiente, CLI, dati di controllo, writer di sottomissione verificato | fatto |
| Identificazione dei contesti e del contratto di punteggio | fatto |
| Audit delle sorgenti esterne candidate | fatto |
| Registry versionato delle sorgenti, con livelli di verifica | fatto |
| Pipeline verticale: registry → firme con incertezza → baseline → valutazione | fatto, su scala ridotta |
| Baseline di trasferimento calibrate e valutate fuori campione | fatto (spazio pseudobulk) |
| Scorer ufficiale eseguito end-to-end su un bundle a singola cellula | fatto, su un **nullo** |
| Contratto di sottomissione verificato sulle fonti ufficiali e sulla CLI | fatto ([SOTTOMISSIONE.md](SOTTOMISSIONE.md)) |
| Calibrazione annidata dell'ampiezza, selezione separata dal riporto | fatto ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.2) |
| Inferenza per A/B/C e due previsioni complete 300 × 400 × 3 | fatto, verificate sul file scritto |
| Packaging `.vcc` di trial-01 | fatto in locale, 0,52 GiB di picco ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)) |
| **Banco di prova predittivo (punteggio VCC su effetti veri)** | **HepG2 Nadig è locale** (metodologico, 0/300 pannello, metriche grezze senza ancore ufficiali). Manca un bundle con ancore stabili e copertura del pannello |
| Prima sottomissione valutata | fatto: 0,045929, rango 446/920 ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)) |
| Ensemble, miglioramento del punteggio | non iniziato |
| Orchestratore locale per consultare più modelli su una domanda | canali DeepSeek/Kimi verificati; campagna Jiang **avviata** il 15 settembre, non conclusa ([ORCHESTRATORE.md](ORCHESTRATORE.md), [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md)) |
| Modalità di ricerca scientifica a tre fasi nell'orchestratore | implementata, provata solo a secco ([RICERCA_SCIENTIFICA.md](RICERCA_SCIENTIFICA.md), [CP-0010](checkpoints/0010-modalita-ricerca-scientifica.md)) |
| Primo confronto modulare contro rete unica e ShrunkTransfer | fatto, in spazio **proxy** pseudobulk su K562/RPE1; esito **inconcludente** per l'adozione ([CP-0011](checkpoints/0011-primo-benchmark-modulare.md), [BENCHMARK_MODULARE.md](BENCHMARK_MODULARE.md)) |
| Specifica degli input degli encoder per bersagli mai perturbati | fatta, descrittori verificati su file; GO slim proposta, non misurata predittivamente ([CP-0012](checkpoints/0012-encoder-inputs-unseen-target.md), [ENCODER_INPUTS.md](ENCODER_INPUTS.md)) |
| Terzo contesto perturbato acquisito (HepG2 Nadig) e benchmark a tre contesti | fatto: md5 verificato, 2.346 firme, tre fold esterni. Il descrittore di contesto e ora misurabile e **non aiuta in modo sistematico**; il segnale favorevole alla base congelata di CP-0011 **non si ripresenta** ([CP-0013](checkpoints/0013-hepg2-terzo-contesto.md), [BENCHMARK_TRE_CONTESTI.md](BENCHMARK_TRE_CONTESTI.md)) |
| Generatore contro predittore sulle sei metriche VCC, su cellule reali | fatto su HepG2 tenuto fuori, metriche **grezze senza ancore**: i due fattori muovono metriche diverse e talvolta in direzioni opposte ([CP-0013](checkpoints/0013-hepg2-terzo-contesto.md), D-027) |
| Pilot dei descrittori GO slim per bersagli mai perturbati | fatto: l'estensione e **scartata** dalla regola fissata prima, e il braccio con l'annotazione permutata va come quello vero ([CP-0014](checkpoints/0014-go-slim-e-gpu.md), D-028) |
| Verifica che il codice possa usare una GPU | fatta e **negativa**: ogni decoder e numpy scritto a mano, `torch` non e una dipendenza, e al formato attuale l'aritmetica e 1,3 s su 223. Il collo di bottiglia e algoritmico, non hardware ([CP-0014](checkpoints/0014-go-slim-e-gpu.md), D-029, [CONSEGNA_GPU.md](CONSEGNA_GPU.md)) |
| SVD randomizzata contro esatta, e confronto di rango 16/32/64/128 | fatta: la randomizzata **non** supera la banda prefissata sulle predizioni (4 fold su 48); il rango >16 scelto internamente **peggiora** il lowrank sul test. Default invariato: SVD esatta, griglia {8, 16} ([CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md), D-029, D-030, [SVD_E_RANGO.md](SVD_E_RANGO.md)) |
| Gate di espressione scritto a mano (G1 simmetrico, G2 asimmetrico, G3 sul bersaglio) con i due controlli obbligatori | fatto: **non promosso** dalla regola fissata prima del run. La selezione interna sceglie «non fare niente» in 30 righe su 54, e dove un gate aiuta, quello costruito sulla **sorgente** aiuta quanto o più di quello costruito sulla destinazione ([CP-0017](checkpoints/0017-gate-espressione-destinazione.md), D-033) |
| Catena di cicli: guardiano, collaudo scritto da Codex prima di Claude, controllo di Grok con campagne dell'orchestratore | implementata e provata con agenti simulati (42 test); **nessun ciclo dal vivo**. Guardiano registrato all'accesso e attivo dal 16 settembre, 23:54. Mancano `claude auth login` e la fase di integrazione ([CP-0019](checkpoints/0019-catena-cicli-guardiano.md), D-021 aggiornata) |
| Grezzi pesanti (K562 genome-wide a singola cellula, HepG2) sul Google Drive del proprietario | **dichiarato** il 16 settembre, non ancora verificato da un run: si collegano dal runtime remoto, non si scaricano. Dimensioni coerenti con il catalogo; md5 e percorso delle copie da verificare. Nessun dataset è adottato per questo ([CP-0018](checkpoints/0018-drive-storage-confermato.md)) |

**Il 13 settembre 2026 è stata inviata la prima sottomissione, ed è stata valutata:
punteggio 0,045929, posizione 446 su 920 squadre**
([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)). È il primo numero del
progetto sulla scala della gara. Fino a quel momento la riga qui sopra diceva «nessuna
sottomissione è stata inviata e non esiste alcun punteggio di leaderboard»: era vera
fino alle 01:12Z del 13 settembre.
Dal 12 settembre esistono però baseline misurate: trasferimento con ampiezza calibrata
su bersagli tenuti fuori ([CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md),
raffinata da [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md)).
Sono in spazio pseudobulk log2FC, **non** sono punteggi VCC, e la distinzione va tenuta:
lo scorer vuole conteggi a singola cellula contro controlli reali.

Esistono anche, dal 12 settembre, **due previsioni complete a forma di sottomissione**
per i contesti A/B/C — un ricampionamento dei controlli senza modello e il
trasferimento calibrato — generate in locale e verificate contro il contratto leggendo
il file scritto. Dal 13 settembre **`trial-01-transfer` è impacchettato**: un `.vcc` da
3,91 GiB, prodotto con un percorso che convalida e scrive senza materializzare la
matrice (0,52 GiB di picco contro i 33,5 del modello della CLI ufficiale), con tutte e
24 le convalide attive e il payload verificato bit a bit contro l'input
([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)).

**Il server lo ha accettato**, il 13 settembre: la sottomissione è arrivata a
`published`, con l'md5 verificato e nessun errore. Resta vero che una convalida di
formato non dice nulla sulla qualità predittiva — ora misurata, e bassa.
`trial-00-controls` non è impacchettato e non va inviato (D-017).

## 3. Cosa sappiamo, e cosa lo sostiene

La colonna "tipo" è la parte importante. Una **misura** è un numero che si può
ricalcolare. Un'**interpretazione** è una lettura di quel numero. Un'**ipotesi** non è
stata ancora messa alla prova.

| Cosa sappiamo | Tipo | Evidenza |
|---|---|---|
| I controlli ufficiali sono 18.400 × 18.533 per contesto, conteggi interi, UMI mediani 20.109 / 19.946 / 20.034 | misura | `reports/data_audit/audit.json` |
| Il pannello dei 300 bersagli è espresso in tutti e tre i contesti: 288/300 sopra 5 CPM, solo 3 sotto 1 CPM in almeno uno | misura | `reports/candidate_verification/coverage_summary.json`, `docs/revisione_analisi_2026-09-11.md` §2 |
| Nessuno dei 300 bersagli compare nei pannelli *essential* di K562 e RPE1 (0/300, per simbolo e per ENSG), dove il caso ne farebbe attendere una trentina | misura | come sopra |
| Selezionare sorgenti esterne per "perturbazioni forti" seleziona sull'esito: sovrarappresenta gli effetti facili e gonfia quello che il modello sembrerà saper fare | interpretazione | `docs/data_strategy_2026-09-11.md` §3 |
| A è di lignaggio linfoide T, B epiteliale-mesenchimale, C epiteliale squamoso | interpretazione (su marcatori misurati) | `reports/context_identity/markers.csv` |
| Nessuno dei tre contesti è eritroide o pluripotente: K562, H1, KOLF2.1J e HIPSCI sono tutti di lignaggio non corrispondente | interpretazione | come sopra |
| K562 genome-wide copre 272/300 bersagli, ma la risposta stimabile è povera: mediana 5 geni DE per riga, 37 righe a zero | misura | `docs/revisione_analisi_2026-09-11.md` §4 |
| Quattro delle sei metriche misurano direzione o ordinamento; la MSE normalizzata non scende sotto 0, la NMAE si ferma a −6 | misura, dal pacchetto installato | `reports/candidate_verification/scorer_clamp_check.json` |
| L'effetto predetto è misurato contro le cellule di controllo **reali** (`control_source: real`): una differenza sistematica fra cellule generate e NTC reali diventa DE fittizio in tutte e 300 le perturbazioni | misura (configurazione) + interpretazione | `reports/scorer/vcc2026_contract.json` |
| CD4 (GSE314342) ha 297/300 bersagli in libreria e 293 osservati, ma solo 239 con almeno 30 cellule e 147 con almeno 100 | misura | `reports/candidate_verification/panel_coverage.csv` |
| Orion HCT116 ha 300/300 in libreria e 168 osservati nel solo Batch1, tutti sotto le 30 cellule | misura | `reports/candidate_verification/coverage_summary.json` |
| H1 2025 condivide 25/300 bersagli, e localmente non c'è la matrice RNA: solo quattro CSV di metadati | misura | `C:/Users/ferra/vcc2026-data/external/vcc2025/` |
| La macchina ha 8,4 GB di RAM; il disco libero oscilla (28,1 GB l'11 settembre, 33,7 GB il 12): gli atlanti completi non ci stanno comunque | misura | `reports/candidate_verification/hardware.json`, `reports/grok_verification/hardware.json` |
| L'estrazione remota mirata funziona: 64 cellule CD4 estratte con 92 MB di traffico | misura | `reports/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json` |
| **Trasferire una risposta a piena ampiezza è peggio che non prevedere nulla**: MSE 1,162 volte quella del nullo da K562 a RPE1, 1,535 fra due esperimenti nella stessa linea K562 | misura | `reports/pipeline/transfer_experiment.json` |
| All'ampiezza calibrata su bersagli tenuti fuori (α = 0,25 fuori linea, 0,50 stessa linea) l'MSE scende a 0,990 e 0,922 del nullo: il guadagno c'è, ed è dell'1,0% e del 7,8% | misura | come sopra |
| L'α scelto in validazione incrociata coincide con l'α oracolo (0,25 vs 0,216; 0,50 vs 0,472): il protocollo di calibrazione funziona | misura | come sopra |
| La correlazione cross-lineage held-out è 0,0947 [0,0891–0,0997]; quella di stessa linea 0,1693 [0,1589–0,1816]. Il trasferimento fuori lignaggio conserva circa il 56% di un tetto già basso | misura (bootstrap su bersagli) | come sopra |
| L'accordo di segno sui geni con \|log2FC\|≥0,5 è 0,555 fuori lignaggio e 0,650 nella stessa linea | misura | come sopra |
| Nel pseudobulk gli effetti **non** sono piccoli: il 23,3% delle coppie bersaglio-gene in RPE1 supera 0,5 log2FC (8,1% in K562) | misura | [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.3 |
| In tutte e tre le fonti locali l'effetto mediano è **più piccolo del proprio errore standard** (\|Δ\|/SE fra 0,795 e 0,945) | misura | `reports/pipeline/signature_qc.json` |
| I file `*_raw_bulk_01.h5ad` contengono **medie per cellula**, non somme: `X × num_cells_filtered` torna intera. Leggerli come conteggi gonfia l'errore di Poisson di ~13× | misura | [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.1 |
| Su dati reali NTC-contro-NTC lo scorer non produce quasi falsi positivi: 5 perturbazioni su 6 escluse per "empty gate", Jaccard 0,000, PDS esattamente 0,500 | misura, scorer ufficiale | `reports/pipeline/null_calibration_A.json` |
| **Codice e pesi non si consegnano.** Solo i finalisti devono pubblicare una descrizione di alto livello del metodo. Le sottomissioni sono **due** al giorno, una sola in volo per squadra | misura (regolamento ufficiale, letto il 2026-09-12) | [SOTTOMISSIONE.md](SOTTOMISSIONE.md) §1 |
| L'α di trasferimento K562 → RPE1 è 0,1974, non 0,25: il valore precedente era il punto di griglia più vicino. MSE fuori campione 0,98991 del nullo, IC95 [0,98866, 0,99114]; a piena ampiezza 1,16228 | misura (CV annidata, 2.350 bersagli) | `reports/trial_2026-09-12/calibration_c002.json` |
| Lo **shrinkage per gene è quasi inattivo**: `prior_sd` = 4 batte «nessuno shrinkage» di 0,00003 in MSE cross-validata. La compressione utile è tutta nell'ampiezza globale | misura | come sopra |
| Una previsione completa a densità realistica pesa 2,08·10⁹ valori memorizzati, 5.789 per cellula: il **44% del tetto**, non il 90% che darebbe submettere il profilo medio | misura | `reports/trial_2026-09-12/resources.json` |
| `vcc prep` carica l'intera matrice in memoria: 8,60 byte per valore memorizzato misurati, 22,19 GiB di picco per trial-00 secondo il modello della CLI stessa, contro 7,81 GiB totali di macchina. **`prep_memory_warning` non scatta su Windows** perché dimensiona contro `os.sysconf` | misura | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.5 |
| Quel limite è di `vcc prep`, non del problema: convalidando e scrivendo a blocchi, trial-01 si impacchetta con **0,519 GiB di picco** contro i 33,49 del modello, sulla stessa macchina, con le stesse 24 convalide | misura | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §3.1 |
| Il payload del `.vcc` porta `X/data`, `X/indices` e `X/indptr` **identici bit a bit** all'input; l'unica trasformazione è l'indice di `obs`, sostituito con `'0'..'n-1'`, che è ciò che fa anche `vcc prep` | misura | come sopra, §3.3 |
| La regola ufficiale «nessuna perturbazione tutta a zero» è **globale, non per contesto**: `vcc prep` accetta un bersaglio azzerato in un solo contesto | misura, sul comportamento di `prep` | come sopra, §3.5 |
| Gli offset CSR di una sottomissione completa arrivano al 97% del tetto di int32: `SubmissionWriter` li scriveva in int32 e avrebbe avvolto in silenzio su una previsione un filo più densa | misura, difetto corretto | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.6 |
| Il generatore produce il 4–6% di geni rilevati in più dei controlli reali **anche a effetto previsto zero**, mentre i CV di libreria e di rilevazione coincidono. Il log2FC efficace mediano dopo calibrazione è 0,0246 (1,7%), il massimo su un gene 0,776 (1,71×) | misura | `reports/trial_2026-09-12/q01pilot_generation_diagnostics.json` |
| Un contesto scambiato è rilevabile: somiglianza col proprio basale 0,999999 contro 0,888–0,928 fra basali diversi. La convalida di formato non se ne accorgerebbe | misura | `reports/trial_2026-09-12/q00full_validation.json` |
| Su 160 bersagli casuali, K562 → RPE1, MSE/nullo di modular_frozen 0,976 e 0,974 contro 0,994 e 0,996 di ShrunkTransfer (due seed); RPE1 → K562 a α prefissato 1 tutti i bracci sopra 1; universo 6700/18533; picco RSS 0,47 GiB. Non è un punteggio VCC | misura | `reports/benchmark_2026-09-14/comparison_table.md`, [CP-0011](checkpoints/0011-primo-benchmark-modulare.md) |
| Con tre contesti (K562, RPE1, HepG2) la differenza appaiata modular_frozen − ShrunkTransfer e **positiva in tutti e tre i fold** (+0,441 / +0,082 / +0,295, IC95 senza zero): il segno misurato in CP-0011 su due contesti si inverte. Universo 6477/18533; 2.315 bersagli condivisi dai tre contesti (JSON della singola esecuzione) | misura | `reports/benchmark_3ctx_2026-09-14/summary.json`, [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) |
| Su cellule HepG2 reali, cambiare il **solo** generatore porta il Jaccard sui geni significativi da 0,003 a 0,120 su un predittore nullo, e azzera la direction fidelity; il predittore domina invece la PDS (0,738 contro 0,425). Metriche grezze, 25 bersagli, nessuna ancora | misura | `reports/hepg2_2026-09-14/generator_x_predictor.json`, [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) |
| Il braccio con le 140 colonne GO **permutate** fra i geni va come quello con l'annotazione vera (|differenza| <= 0,023 sulla base congelata): il legame gene-annotazione non porta segnale in questo disegno | misura | `reports/go_slim_2026-09-15/summary.json`, [CP-0014](checkpoints/0014-go-slim-e-gpu.md) |
| Su matrici di risposta reali una SVD randomizzata di rango 16 e 11,9x piu veloce a 320 righe e 42,2x a 1.280, con l'1,3-1,6% di errore sui valori singolari; il rango 16 cattura il 25-30% della varianza | misura | `reports/gpu_2026-09-15/gpu_readiness.json`, [CP-0014](checkpoints/0014-go-slim-e-gpu.md) |
| Sulla matrice di training 320 × 6.477 del fold K562+RPE1 → HepG2, rango 16: randomizzata 9,74× sulla sola SVD, errore rel. sui valori singolari 1,05%, ma le due ricostruzioni di rango 16 differiscono del 18,5% (angolo max 39°); il rango 16 cattura il 50% della varianza di *questa* matrice | misura | `reports/svd_2026-09-15/factorization_comparison.json`, [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md) |
| Sostituzione randomizzata vs esatta sulle predizioni (48 righe, stessi split): 4 fold fuori dalla banda prefissata 0,01, tutti frozen con contesto, segni misti. Verdetto: non compatibile come drop-in. Orologio 331 s → 207 s; picco RSS ~456 MiB in entrambi | misura | `reports/svd_2026-09-15/prediction_comparison.json` |
| Griglia di rango {16,32,64,128}: il lowrank sceglie 64 su tutti i fold seen e perde 0,14–0,35 di MSE/nullo sul test contro {8,16}, IC senza zero nei tre contesti. Il frozen "sceglie" 128 su una griglia interna piatta | misura | `reports/rank_2026-09-15/rank_summary.json` |
| Il gate di espressione non passa la sua regola: «batte ShrunkTransfer in tutti i fold» vale in **1 split su 6** per tutte e tre le varianti. Il permutato batte il gate vero in 2 split su 6 (G1), e il gate costruito sulla sorgente lo batte in 4 su 6 (G1) | misura | `reports/expression_gate_2026-09-16/decision.json` |
| La scelta del gate non è stabile fra due seed che differiscono solo per i 32 bersagli di validazione interna: identità scelta in 23 righe su 27 con seed 2026 e in 7 su 27 con seed 2027 | misura | `reports/expression_gate_2026-09-16/gate_rows.json` |
| Nell'universo del banco (6.477 geni) i geni spenti non ci sono: 0–2 sotto 5 CPM per contesto, minimo 4,3–8,6 CPM. Nei contesti ufficiali è l'opposto: 8.409–8.923 geni su 18.533 sotto 5 CPM e 2.317–2.853 esattamente a zero | misura | `reports/expression_gate_2026-09-16/splits/`, `reports/expression_gate_2026-09-16/context_presence.json` |
| Un gene a 1 CPM è contato 368–389 volte nei controlli di un contesto ufficiale (3,68–3,89·10⁸ molecole su 18.400 cellule): su quella scala uno zero è quasi sempre biologia, non strumento | misura | `reports/expression_gate_2026-09-16/context_presence.json` |
| Le 54 righe dei nove bracci originali del run `x001` sono identiche a quelle di `m002`, differenza assoluta massima 0,0: stesso protocollo, stessi split, stessa metrica | misura | `reports/expression_gate_2026-09-16/decision.json`, campo `reproduction` |
| Il file K562 genome-wide a singola cellula pesa 65.830.941.948 byte, cioè **61,31 GiB** (65,83 GB). Il «61,3 GB» del profilo è la stessa dimensione in GiB, come il 9,9 e l'8,1 degli altri due file Replogle a singola cellula. L'etichetta «65,8 GiB» usata in alcuni documenti è un errore di unità | misura (aritmetica sui byte) | `src/vcc2026/external.py`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.3, [R-013](REGISTRO.md#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| Le copie su Drive mostrano 61,31 GB e 811,2 MB: coerenti con i byte del catalogo letti in unità binarie. Nessun md5 è stato calcolato su di esse | dichiarazione del proprietario (non misurata dal progetto) + misura (aritmetica) | `configs/remote_catalog.yaml`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.2 |
| Un run remoto vede i file solo sotto `<VCC2026_DATA_ROOT>/raw/`. `skip_complete` ricalcola l'md5 dell'intero file a ogni esecuzione, e con `FETCH_BLOCKS = None` la selezione salta i file presenti e scarica il blocco successivo | interpretazione (codice letto, non eseguito) | `src/vcc2026/remote_catalog.py`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.4–3.6 |

## 4. Cosa non sappiamo

Queste sono le incertezze che contano. Nessuna è stata risolta.

1. **Quanto vale un punto.** Le ancore di replicato `r` restano ignote a noi, ma dal
   13 settembre c'è una strada che non richiede un bundle di valutazione: la classifica
   pubblica mostra, per ogni squadra e metrica, **il grezzo e lo scalato**, e due righe
   con grezzi diversi determinano `b` e `r` di `(u − b) / (r − b)`. Derivazione
   preliminare su due righe per `mse`: `b ≈ 0,996`, `r ≈ 0,022`, che riproduce il nostro
   1,231 → 0. **Non è ancora una misura**: va rifatta su molte righe e per tutte e sei
   le metriche ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5).
   Il 16 settembre la stima è stata estesa alle sei metriche su undici righe
   (`reports/leaderboard_2026-09-16/snapshot.md`): resta un'interpretazione, con i
   limiti scritti lì, finché non viene rifatta su più righe e per contesto.
2. ~~**Se comprimere l'ampiezza convenga davvero**~~ — **parzialmente risolta il
   2026-09-12.** Misurato: a piena ampiezza il trasferimento è peggio del nullo, e
   l'ottimo sta intorno a un quarto dell'ampiezza fuori lignaggio
   ([CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §3.4,
   D-006, D-012). **Resta aperto** il pezzo che conta davvero: la misura è in spazio
   pseudobulk log2FC su K562 e RPE1, non sulle sei metriche VCC e non sui contesti
   A/B/C. Trasferibile è il metodo di calibrazione, non il valore, che rimisurato
   con selezione continua e validazione annidata è **0,1974** e non 0,25
   ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.2).
3. **Quanto sono grandi gli effetti da prevedere.** Non lo sappiamo. Che i 300
   bersagli non compaiano in due pannelli *essential* è una misura; dedurne che siano
   non essenziali nei contesti della gara è un passaggio non verificato, e dedurne che
   le risposte siano piccole ne è un secondo. L'essenzialità riguarda la sopravvivenza
   della cellula, non l'ampiezza del cambiamento di espressione: un gene non essenziale
   può muovere molti geni. La mediana di 5 geni DE per riga misurata in K562 dice
   quanto segnale riusciamo a **stimare lì**, con 168 cellule mediane per riga, non
   quanto ce ne sia in A, B o C. Scheda
   [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
4. **Se l'asse genico ufficiale sia ricostruibile in identificatori Ensembl.** Due
   documenti dicono il contrario: contraddizione aperta, scheda
   [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
5. **Se il CD4 primario trasferisca ad A**, che è un contesto T ma con marcatori
   immaturi (DNTT, RAG1). Ipotesi, non misura.
6. **Se la co-espressione nei controlli predica la direzione della risposta.** È il
   modello a costo zero più attraente, ed è anche quello contestato: la correlazione
   non è causalità, e il segno può venire da regolatori comuni o dalla normalizzazione.
7. **Se esista Perturb-seq CRISPRi pubblico in linea T matura o squamosa.** La ricerca
   non è conclusa; la pista più vicina per C, GSE281860, espone conteggi di guide e non
   la matrice RNA. Dal 14 settembre esiste un incarico di ricerca pronto su questa
   domanda, `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml`, **non
   ancora avviato**: serve l'autorizzazione del proprietario
   ([RICERCA_SCIENTIFICA.md](RICERCA_SCIENTIFICA.md) §11).
8. **L'efficienza di knockdown nei tre contesti ufficiali**, che non è disponibile.
9. **Se la licenza CC-BY-NC-SA-4.0 di Orion** sia compatibile con le regole della gara.
   Registrata, non verificata.
10. **Quale backend DE useremo davvero.** `cell-eval2` sceglie gpudge (con CUDA), poi
    pdex, poi scanpy, e avverte che i numeri differiscono fra engine. Su questa
    macchina si risolve a `scanpy`. Quattro delle sei metriche ne dipendono, quindi la
    scelta va fatta una volta e dichiarata prima di confrontare una serie di run
    (D-014). Non è ancora stata misurata l'entità dello scarto fra engine.
11. **Se l'α calibrato su K562/RPE1 valga per CD4.** L'α misurato è una proprietà della
    coppia sorgente-destinazione; una sorgente di lignaggio vicino potrebbe darne uno
    molto diverso, ed è il primo controllo da fare quando CD4 sarà ingerito.
12. **Se l'artefatto del generatore superi il segnale che iniettiamo.** Misurato: le
    cellule generate rilevano il 4–6% di geni in più dei controlli reali anche a
    effetto previsto zero, e il log2FC efficace mediano dopo calibrazione è 1,7%.
    Sono quantità diverse e dello stesso ordine; quale domini le quattro metriche DE
    dipende da come lo scorer aggrega, e non è stato misurato. È la ragione principale
    per cui il punteggio di `trial-01-transfer` non è prevedibile da ciò che sappiamo
    ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8).
13. **Se un ricampionamento dei controlli sia ammesso dalle regole.** Le regole dicono
    che i controlli scaricati sono soltanto input del modello e che le previsioni
    devono essere generate soltanto da modelli di machine learning. `trial-00-controls`
    passa la convalida di formato ma non è la previsione di un modello. Registrata in
    D-017, **non risolta**: serve un chiarimento da help@virtualcellchallenge.org o una
    decisione esplicita del proprietario.
14. **Quanto costi davvero `vcc prep` su una macchina adeguata.** Il picco di 22–33 GiB
    viene dal modello di dimensionamento della CLI, non da un'esecuzione nostra: la
    misura che abbiamo è il costo di lettura di anndata, 8,60 byte per valore
    memorizzato. Il numero va confermato la prima volta che `prep` gira per davvero.
15. **Se la decomposizione modulare convenga.** Misurato un proxy su 160 bersagli
    K562/RPE1 ([CP-0011](checkpoints/0011-primo-benchmark-modulare.md)): nella sola
    direzione K562 → RPE1 la base congelata ha un MSE/nullo un po' più basso di
    ShrunkTransfer, con IC che esclude zero su due seed; nella direzione inversa,
    a ampiezza prefissata 1, tutti i bracci perdono contro il nullo. Due contesti
    non identificano `z_c`. Non è un punteggio VCC. Resta **inconcludente**.
16. ~~**Se lo slim GO aggiunga qualcosa al solo basale sui bersagli mai visti.**~~
    **Risolta il 2026-09-15 in senso negativo** ([CP-0014](checkpoints/0014-go-slim-e-gpu.md), D-028):
    B1 non batte B0 e B3 (permutato) va come B1.
17. **Se `n_iter` > 2 della SVD randomizzata basti a rientrare nella banda
    sulle predizioni del frozen.** Misurato solo `n_iter=2`. Non adottata.
18. **Se 2.315 bersagli invece di 160 cambino la selezione di rango.** Il
    disaccordo inner/outer a 160 è già grande; non eseguito.
19. **Se una regola di presenza aiuti dove i geni spenti esistono davvero.** Nel banco
    a tre contesti l'universo non ne contiene (0–2 geni sotto 5 CPM per contesto),
    quindi il gate è stato misurato dove poteva esserlo, non dove servirebbe. Nei
    contesti ufficiali ce ne sono migliaia, ma lì non esistono risposte perturbate con
    cui misurare, e lo scorer dichiara comunque un filtro a 5 CPM
    ([CP-0017](checkpoints/0017-gate-espressione-destinazione.md)).
20. **Se le copie su Drive siano integre e leggibili in tempi utili.** Il proprietario
    dichiara che il K562 genome-wide a singola cellula e HepG2 sono su Drive, e le
    dimensioni tornano. Ma nessun md5 è stato calcolato, il percorso delle copie non è
    noto, e il tempo per leggere 61,31 GiB attraverso il mount di Colab non è misurato.
    Lo dirà il primo run che le collega
    ([CP-0018](checkpoints/0018-drive-storage-confermato.md)).

## 5. Il prossimo passo

Il punto 1 e il punto 4 dell'elenco sotto sono **stati eseguiti** il 12 settembre
(CP-0003): le baseline elementari girano, sono calibrate su bersagli tenuti fuori e
hanno prodotto numeri. Restano i punti 2 e 3, che sono acquisizioni.

1. ~~Scegliere i bersagli supportati con `panel_coverage.csv`~~ — fatto; la selezione
   vive ora in `configs/sources.yaml` e nello stadio 1 della pipeline.
2. ~~Acquisire da CD4~~ — **ordine aggiornato (D-031):** prima audit Jiang (RDS
   su runtime remoto: TGFB 2,64 GB non sta sotto il pavimento da 10 GiB di questa
   macchina) e Jurkat come quarto contesto (mirror 1,29 GB). CD4 resta la pista
   di copertura, rinviata. [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md).
3. HepG2 Nadig è già un bundle metodologico a singola cellula. Restano ancore
   locali stabili sulle sei metriche e, per la copertura del pannello, una
   sorgente diversa. Il seed di conferma 4242 non è stato aperto (D-032).
4. ~~Far girare le baseline elementari~~ — fatto: nullo, trasferimento con shrinkage,
   trasferimento pesato e ridge a basso rango sono implementati in
   `src/vcc2026/models.py`; i primi due sono misurati in
   `reports/pipeline/transfer_experiment.json`.

Dal 14 settembre esiste anche un **confronto modulare eseguito** (CP-0011): codice,
split, test e un pilot su 160 bersagli. Non sblocca i passi 2 e 3, e non adotta
un'architettura. Il passo che riduce di più l'incertezza resta il bundle a
singola cellula.

**I passi 2 e 3 non sono lo stesso passo, ed è l'errore da non fare.** Il pseudobulk
aggrega molte cellule in una riga: serve a stimare l'effetto medio di un bersaglio, ma
ha perso la distribuzione fra cellule. Ricostruire somme intere di conteggi non
ricostruisce le cellule che le hanno prodotte. Lo scorer vuole conteggi a singola
cellula (`input_type: counts`), misura contro le cellule di controllo **reali**, e la
sua correzione del rumore di campionamento sulla MSE dipende dalla dispersione fra le
cellule previste. Con il solo pseudobulk si ottengono diagnostiche sulla media — utili,
ma da non chiamare punteggio VCC. Un'acquisizione riuscita del solo passo 2
lascerebbe il collo di bottiglia esattamente dov'è.

HepG2 è la sede delle ancore metodologiche. Jurkat è il quarto contesto candidato
(D-031). CD4 resta la pista di copertura, non il prossimo download.

**Dal 16 settembre il K562 genome-wide a singola cellula e HepG2 non si scaricano
più.** Stanno sul Google Drive del proprietario, e il runtime remoto li collega montando
Drive. La procedura è in [CP-0018](checkpoints/0018-drive-storage-confermato.md) §6: le
copie vanno sotto `<VCC2026_DATA_ROOT>/raw/`, il notebook va lanciato con
`FETCH_BLOCKS = []`, e il `catalog_run.json` del primo run va conservato, perché è la
prima misura del loro md5. Avere il K562 a portata di mano non lo adotta: la sua scheda
resta `defer`, e resta vero che 61,31 GiB si leggono a blocchi, non in memoria.
Per gli altri blocchi del catalogo (Jurkat, Jiang, RPE1 a singola cellula) nessuna copia
su Drive è stata dichiarata: per loro vale ancora il download sul runtime remoto.

### Il passo operativo, che è diverso e indipendente

Il collo di bottiglia del packaging, aperto il 12 settembre, è **chiuso dal 13**:
`trial-01-transfer` è un `.vcc` da 3,91 GiB, prodotto qui con 0,52 GiB di picco
([CP-0005](checkpoints/0005-packaging-streaming-trial01.md)). Non serviva una macchina
più grande; serviva non caricare la matrice.

Restano due cose, e nessuna delle due è tecnica:

1. Il chiarimento sulle regole per `trial-00-controls` (D-017): un ricampionamento dei
   controlli reali non è la previsione di un modello, e le regole dicono che i
   controlli sono soltanto input. Fino ad allora quel trial non si impacchetta e non
   si invia.
2. L'autorizzazione a consumare quota. `docs/SOTTOMISSIONE.md` §3 ha i comandi esatti,
   §6 la lista di controllo; nessuno dei due è stato eseguito, e **nessun server ha
   accettato niente**: solo una sottomissione valutata lo dimostrerebbe.

Il piano ordinato, con ipotesi, criteri di successo e costi stimati, sta in
[ROADMAP.md](ROADMAP.md). L'architettura della pipeline è in [PIPELINE.md](PIPELINE.md);
come eseguirla su una macchina remota, con le stime di risorse, in
[ESECUZIONE_REMOTA.md](ESECUZIONE_REMOTA.md).

## 6. Percorso di lettura

Per capire il progetto, nell'ordine:

1. Questa pagina.
2. [CP-0001](checkpoints/0001-ricostruzione-stato-2026-09-12.md) — stato al
   12 settembre e tutte le correzioni avvenute finora.
2-bis. [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) — il primo trial
   locale: contratto di sottomissione verificato, calibrazione annidata, due previsioni
   complete, e il limite di memoria che blocca il packaging. Se devi capire *dove si è
   fermato il lavoro operativo*, è questo. I comandi stanno in
   [SOTTOMISSIONE.md](SOTTOMISSIONE.md).
3. `README.md` — compito, formato, metriche, setup. Leggi prima la sua scheda
   [R-001](REGISTRO.md#r-001--readmemd): alcune sue parti sono rimaste indietro.
4. `docs/candidate_adversarial_review_2026-09-12.md` — l'analisi più dettagliata sulle
   sorgenti candidate, su cui poggiano le decisioni attive.
5. `docs/revisione_grok_2026-09-12.md` — verifica di un inventario esterno, con cinque
   piste nuove. **Le sue conclusioni non sono ancora decisioni**: nessuno le ha ancora
   confrontate con D-004, e servirà un checkpoint per farlo.
6. [CP-0011](checkpoints/0011-primo-benchmark-modulare.md) e
   [BENCHMARK_MODULARE.md](BENCHMARK_MODULARE.md) — il primo confronto modulare, in
   spazio proxy, esito inconcludente per l'adozione.
7. [CP-0012](checkpoints/0012-encoder-inputs-unseen-target.md) e
   [ENCODER_INPUTS.md](ENCODER_INPUTS.md) — descrittori verificati per un gene mai
   perturbato nel training, e l'unica estensione proposta (GO slim).
8. [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) e
   [BENCHMARK_TRE_CONTESTI.md](BENCHMARK_TRE_CONTESTI.md) — il terzo contesto
   perturbato, che cosa cambia nel confronto modulare, e la prima misura sulle sei
   metriche con cellule reali. Correggono un punto di CP-0011.
9. [CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md) e
   [SVD_E_RANGO.md](SVD_E_RANGO.md) — la SVD randomizzata esiste e non è un
   drop-in; alzare il rango oltre 16, se scelto internamente, non trasferisce.

I due documenti più vecchi, `docs/data_strategy_2026-09-11.md` e
`docs/revisione_analisi_2026-09-11.md`, si leggono **dopo** e con il
[registro](REGISTRO.md) accanto: contengono materiale ancora valido e conclusioni già
corrette, e il registro dice quale è quale.

## 7. Come si tiene aggiornato questo sistema

Quattro regole, nient'altro.

1. **Un checkpoint quando succede qualcosa di significativo**, non a ogni modifica.
   Significativo vuol dire: un dataset adottato o scartato, un benchmark completato,
   un'ipotesi contraddetta, un cambio di strategia di modellazione o validazione.

   ```bash
   python scripts/30_new_checkpoint.py --slug benchmark-cd4 --title "Primo benchmark su CD4"
   ```

   Lo script numera da sé, non sovrascrive nulla e aggiorna l'indice. Poi si compila il
   file seguendo le otto sezioni del modello.

2. **I checkpoint non si riscrivono.** Se una conclusione risulta sbagliata si scrive
   un checkpoint nuovo e si compila la colonna "Corretto da" nell'indice. Il
   disaccordo storico resta visibile: serve a capire perché si è cambiata idea.

3. **Questa mappa si aggiorna** quando cambiano lo stato, le incertezze o il prossimo
   passo. Non deve diventare un riassunto di tutto: qui stanno le conclusioni, con un
   link all'evidenza.

4. **Il registro si aggiorna** quando un documento o un dato cambia stato. Se un
   materiale viene contraddetto, si apre una scheda che elenca le affermazioni
   contestate, non si butta via il documento intero.

Controllo di coerenza prima di chiudere una sessione di lavoro:

```bash
python scripts/31_check_docs.py
```

Verifica che i percorsi citati esistano, che ogni checkpoint abbia le sue otto
sezioni, che l'indice corrisponda ai file, e che ogni voce del registro segnata
`da-verificare` o `superato` abbia una scheda compilata.
