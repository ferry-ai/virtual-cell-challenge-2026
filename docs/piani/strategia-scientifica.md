# R-LEAD — imparare risposte trasferibili a contesti nuovi

- **Stato:** aperto; nuovo piano richiesto dal proprietario il 2 ottobre 2026, implementazione non iniziata.
- **Mandato:** verificare se i controlli di una linea mai vista perturbata permettono di migliorare il transfer; scegliere il modello in base a questa prova. Unico percorso di R-COMP.
- **Assegnazione:** destinatario Claude nella sessione scelta dal proprietario; Claude e teammate confermati fermi durante il rinnovo. Alla presa in carico registrare sessione, macchina, commit, file e output secondo [PIANI §3](../PIANI.md#3-lavorare-in-una-cartella-condivisa).
- **Prossimo passo:** P0/P1, protocollo e runner P2, primo confronto semplice P3 sugli input disponibili. La riparazione completa di cellnet non è un prerequisito di questo confronto.
- **Prima consegna:** matrice contesto × bersaglio × studio, split verificati, protocollo congelato, codice del banco e dei confronti semplici con test; misure se gli input lo consentono, altrimenti il file minimo mancante e il passo impedito. Non un altro piano.
- **Dipendenze:** [R-LAB](piano-giorno-2026-09-30.md), [GENERALIZZAZIONE](../GENERALIZZAZIONE.md), D-050 e D-052; procedure e preflight del lavoro effettivamente eseguito.
- **Chiusura:** scelta motivata con prove riproducibili e pipeline finale verificata, oppure esito negativo/inconclusivo con transfer conservato e limite identificato.

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
