# Confronto con Alfredo: critica e divisione del lavoro

3 ottobre 2026, Codex. **Revisione e proposta**, non nuovo esperimento biologico. Richiesta del proprietario: leggere criticamente il resoconto di Alfredo, aggiornarlo su ingestion e training dei due Claude e proporre lavoro complementare. Nessun messaggio inviato ad Alfredo, nessun nuovo job di training o invio ufficiale.

Da inoltrare: [MESSAGGIO_ALFREDO.md](MESSAGGIO_ALFREDO.md). Approfondimento: questo file. I [calcoli analitici](calcoli_analitici.json), prodotti da [questo script](calcoli_analitici.py), sono controesempi matematici, non score. Le revisioni esterne e la loro verifica sono in [AGENTI.md](AGENTI.md).

## 1. Provenienza e limiti

- **Riferito da Alfredo:** collasso del suo `rlead-training-r1` v2, Strada A negativa, confronto scorer 0.16/0.18, Strada B bloccata sulle cache, protocollo e lancio Strada C. Le cartelle da lui citate non sono presenti/registrate in questo checkout; non ho letto i suoi log o il suo codice e non certifico il loro contenuto.
- **Verificato nei file locali:** protocollo, decisione JSON e tabelle del pilot `rete_cellulare_2026-10-03`; letture P3/P4; stato documentato dell'ingestione. Base iniziale `b12db62`, poi aggiornamento concorrente fino a `db2a706`, letto il 3/10 alle 14:24 CEST. Gli artefatti correnti sono più avanzati della scheda R-LEAD e di PROGETTO §0: non uso i loro vecchi «prossimi passi» come coda operativa.
- **Verificato su fonti primarie online il 3/10:** [regole VCC](https://virtualcellchallenge.org/rules), [descrizione Arc](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026), [changelog dello scorer](https://github.com/ArcInstitute/cell-eval2/blob/main/CHANGELOG.md), [definizione delle metriche](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics.md). Le regole sono state lette nel browser: il lettore web restituiva solo la schermata di caricamento.

## 2. Che cosa stiamo facendo noi

**Ingestione, Claude `096065`.** L'[inventario e piano](../../sorgenti/archivio_cloud_2026-10-02/INGESTIONE.md) separa acquisito, integrato nel banco e usato nel training. Jurkat Nadig, H1 train/validation e Tian sono già acquisiti; le loro somme sono entrate nel banco esteso. Fra gli ampliamenti documentati: cellule CD4/Orion con campionamento dichiarato, KOLF pan-genome, completamento Southard, Jiang/Mixscale (un'unica sorgente, non due), VIPerturb. Sono priorità/proposte o dati parziali secondo quella tabella: non sostengo che tutti i nuovi download o job siano partiti. H1 test resta chiuso. Il flusso previsto è sorgente → Colab CPU → shard e ricevute → Drive/Kaggle verificati.

**Training, Claude `22d21f`.** I confronti semplici e la rete sul pseudobulk a dieci gruppi danno `no_benefit` secondo le [regole congelate](../generalizzazione_contesti_2026-10-02/p4_decision_nn_r2/LETTURA.md). Il transfer resta primo anche nel [banco P3 sui sei membri, HepG2](../generalizzazione_contesti_2026-10-02/p3_six_member_r2/LETTURA.md). Questo chiude quei confronti, non ogni possibile uso del contesto.

Nel nuovo pilot **cellulare** r3, dopo aver tolto la miscela, tutti e tre i training passano l'accettazione tecnica. La [decisione](../../modelli/rete_cellulare_2026-10-03/esito/decision_r3/decision.json) riporta, sul PDS degli effetti in C:

| Contrasto | Differenza media tra linee | Linee positive | Lettura |
|---|---:|---:|---|
| Cellule contro media dei controlli, Q1 | +0,01384 | 2/3 | passa il criterio del pilot |
| Cellule contro transfer a informazione comparabile, Q2 | −0,32339 | 0/3 | fallisce |
| Cellule contro generico addestrato, Q3 | +0,06993 | 3/3 | passa |

Q1 confronta due rappresentazioni dei controlli: **non è** un confronto con un modello privo di ogni contesto. Tre linee di sviluppo e un seme non sono conferma indipendente. Nei sei membri locali già calcolati, `cells_shift` contro `transfer_cells` vale 0,21172 contro 0,24701 su [HepG2](../../modelli/rete_cellulare_2026-10-03/esito/laneB_hepg2_r3/scaled_local.csv) e 0,03407 contro 0,22321 su [RPE1](../../modelli/rete_cellulare_2026-10-03/esito/laneB_rpe1_r3/scaled_local.csv); l'emissione diretta `cells_cells` peggiora ulteriormente. Sono scale locali, non score VCC. Le note delle due cartelle identificano la generazione corretta `r3b` con π=1; la prima generazione usava erroneamente la testa del gate non addestrata.

**Decisione corrente:** benché Q1 permetta l'espansione secondo la regola registrata, il proprietario ha scelto di non espandere questa rete e passare a una rete cellulare che corregga il transfer, preceduta dal controllo descrittivo delle miscele transfer/rete sui sei membri. Fonte: [protocollo §11](../../modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md), commit `713a7ba`, e controllo delle miscele registrato in `db2a706`. Alfredo non deve duplicare né questa analisi né il nuovo training.

## 3. Il collasso: diagnosi plausibile, rimedio non garantito

È corretto distinguere il codice d'uscita 0 dal successo tecnico/scientifico e non leggere Q1–Q4 del run bocciato. Tuttavia il gradiente della log-verosimiglianza della miscela rispetto alla log-verosimiglianza della componente perturbata è moltiplicato dalla **responsabilità a posteriori**, non soltanto da π:

`r = π exp(ℓ1) / [π exp(ℓ1) + (1−π) exp(ℓ0)]`.

Con π=0,05 e ℓ1−ℓ0=−100, r≈1,96×10⁻⁴⁵; con π=0,5 è ancora ≈3,72×10⁻⁴⁴. Un floor non garantisce un gradiente utile; «50.000 volte» può descrivere uno specifico controesempio, non una garanzia generale. Inoltre, nel gate `f+(1−2f)sigmoid(z)`, la derivata rispetto a z continua a saturare. Fonte di implementazione: [cellnet.py, gate_logs e mixture_loglik](../../modelli/rete_cellulare_2026-10-03/cellnet.py).

Le nostre prove rendono il problema concreto: [protocollo §7–9](../../modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md), collasso con floor 0,01 e poi responsabilità nulla anche con π fissato a 0,5. π=1 ha rimosso questa specifica via di collasso, cambiando però il modello e l'emissione; non è una prova di maggiore efficacia biologica né l'unica soluzione concepibile.

Per un futuro protocollo: responsabilità, differenza di likelihood, norma degli spostamenti e gradienti per braccio e studio; finestre persistenti anziché un singolo batch; controlli durante tutto il training. Un controllo solo nei primi 1.000 passi perderebbe il nostro collasso a circa 3.700. Un criterio `pi < floor` è irraggiungibile. Salvare checkpoint a passi iniziali e conservare uno stato sano separato dalla rotazione degli ultimi checkpoint. Sono proposte, non nuovi criteri applicati retroattivamente ad Alfredo.

## 4. MSE: che cosa si può concludere

Per l'errore quadratico ordinario, stesso supporto e stessa metrica, indicando con q il rapporto delle norme previsione/verità e con c il coseno:

`errore relativo = 1 + q² − 2qc`.

Se c≈0, aumentare solo l'ampiezza peggiora. Con scala non negativa ottimizzata, il minimo è `1−max(c,0)²`. Un coseno 0,12 consente al massimo 0,0144 di riduzione in questo modello semplificato. Questo spiega la debole leva dell'ampiezza, **non dimostra una soglia universale 0,12**. Il valore 4786 e le soglie devono restare legati al pannello, supporto, normalizzazione e ancore da cui sono stati ricavati.

La MSE ufficiale usa un rapporto di somme con correzioni jackknife e limiti alla correzione della previsione, anche a livello di pannello. L'invarianza della media non implica invarianza della metrica a cambiamenti della distribuzione cellulare. Ma dedurre dalle classifiche che «gran parte dei punteggi alti è un exploit» richiederebbe artefatti o una riproduzione, oggi assenti in questa revisione. La [specifica ufficiale](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics.md) documenta i limiti introdotti proprio su questi contributi.

Il [changelog 0.18](https://github.com/ArcInstitute/cell-eval2/blob/main/CHANGELOG.md) conferma `rule_version=3` e digest competitivo invariato rispetto a 0.16: la conclusione di equivalenza delle regole è sostenuta. Non ho ripetuto il confronto numerico di Alfredo. Per riprodurre un risultato conservare anche configurazione, backend, bundle e digest; il solo numero di versione è insufficiente.

## 5. Strada C: finirla, senza estendere il suo verdetto

Leggere la corsa in atto con la regola già registrata. Le osservazioni seguenti qualificano ciò che dimostra; modifiche al disegno richiedono una corsa distinta preregistrata.

1. **Definire `same`.** Stesso tipo ampio ma linea distinta può verificare trasferimento fra linee affini. Stessa linea in altro studio verifica trasferimento fra studi e non C/J rigoroso. H1 e iPSC non sono sinonimi. I gruppi locali riuniscono KOLF/HIPSCI in iPSC: un disegno che li separi deve dichiararlo e verificare alias, cloni e donatori, senza chiamarlo replica dello stesso holdout.
2. **Confronto appaiato.** Stessi target, geni misurati, controlli, generatore e seed. Riportare copertura oltre al risultato sull'intersezione; un braccio senza sorgenti ammissibili è non valutabile, non zero. Controllare numero di sorgenti, numerosità, qualità e studio/assay. Il contrasto pratico con tutti i dati e quello a supporto comparabile rispondono a domande diverse.
3. **Specificità e incertezza.** `same > same_shuf` controlla l'associazione al bersaglio, non prova l'utilità del tipo cellulare. La permutazione deve mantenere struttura di disponibilità e supporto. Bootstrap appaiato per target quantifica incertezza entro quella linea; non sostituisce altre linee. Ricampionare numeratori/denominatori insieme e ricalcolare il rapporto; se il contributo di correzione è dipendente dal pannello, distinguere bootstrap dei contributi congelati da uno scorer ricalcolato sul pannello ricampionato. Denominatori instabili o non positivi vanno segnalati, non filtrati dopo i risultati.
4. **Regola debole su KOLF.** Media ≥0 non dimostra equivalenza o non inferiorità: manca un margine e un intervallo coerente. Non cambio la sua soglia; un eventuale pass resta un segnale per quella regola di sviluppo. Per MSE grezza, che è da minimizzare, esplicitare il segno del contrasto; il testo «same−cross >0» non identifica da solo una metrica orientata correttamente.
5. **Finale.** Nessuna fonte verificata qui giustifica una scommessa esclusiva su contesti staminali D/E/F. Congelare anche un fallback per contesti lontani e bersagli senza supporto.

## 6. Divisione proposta, con consegne concrete

| Responsabile | Domanda e consegna | Confine |
|---|---|---|
| Claude ingestion | Colmare le lacune cellulari; manifest, QC, ruoli e disponibilità reale | Non confondere acquisizione con beneficio |
| Claude training | Rete cellulare ancorata al transfer; prova preliminare delle miscele già registrata | Candidato di ricerca, nessuna promozione acquisita |
| Alfredo, primo pacchetto | Concludere Strada C; matrice sorgente×destinazione con tipo, studio, supporto, qualità e controlli scambiati | Leggere il protocollo originale; nuove analisi solo descrittive o nuova versione |
| Alfredo, secondo pacchetto | Strada B e affidabilità del transfer: pesi di sorgente e cis come contrasti separati sui sei membri | Non ripetere reti sui pesi, correttori neurali o miscele già in corso |

**Secondo pacchetto, proposta operativa:** fissare il transfer corretto t25 come confronto e tenere invariato il generatore. Prima `uniform` contro `alloc` contro `normrest`, con cis invariato; poi cis attuale contro 50 kb, a pesi fissati in anticipo. Se si vuole studiare l'interazione, preregistrare un fattoriale: non leggere il cambiamento simultaneo come effetto di una sola leva. Definizioni di alloc/normrest e cache effettivamente richieste vanno lette dal suo codice, oggi non disponibile qui.

L'estensione informativa è verificare se la **riproducibilità fra guide/librerie** e il disaccordo fra sorgenti predicono gli errori fuori contesto: stime solo nelle sorgenti e nei fold interni, mai dalla verità della linea esclusa. Confrontare una regola congelata di affidabilità/shrinkage con uniforme e con `same`; se non aggiunge valore sui sei membri, conservarla solo come diagnosi. Non serve un'altra rete sui pesi: le precedenti varianti hanno già avuto esiti negativi. Se mancano repliche indipendenti, dichiarare che la separazione rumore/biologia non è identificata; uno split casuale di cellule fornisce una prova più debole.

**Sblocco dati concreto:** ho verificato per metadati la presenza locale dei nove `.npz` di `processed/multisource_2026-09-27_r9`: K562, CD4 mix/Rest/Stim8hr/Stim48hr/halfA/halfB, HCT116, HEK293T (28–43 MB ciascuno). Non sono stati trasferiti. La lista visibile non contiene `manifest.json`: prima di consegnarli va ricostruita/verificata la provenienza dagli artefatti della corsa, senza inventare un manifest storico. Chiedere ad Alfredo i nomi richiesti dal loader e fornire solo cache/assi/maschere/coordinate necessarie, con hash; non ricostruire l'intero disco e non usare le cache del pseudoconteggio superato. Pannello attuale e universi per bersagli finali restano distinti.

Output attesi da Alfredo: commit e protocollo; manifest degli input e degli split; tabella per target e contesto; sei membri grezzi e scalati con ancore locali dichiarate; numeratori e denominatori MSE; decisione secondo la regola congelata; copertura e fallback. Un mancato pass conserva il riferimento; un pass su H1/KOLF motiva una conferma su contesti appropriati, non una previsione sul finale.

## 7. Regole della gara: la distinzione corretta

Le [regole del 16 settembre](https://virtualcellchallenge.org/rules) consentono dati sperimentali/pubblicati per addestramento o fine tuning; vietano di inserirne i risultati nell'invio o usarli per revisionare le previsioni del modello. Non è un divieto generale di dati della stessa linea. È però scorretto dedurne che basti chiamare «modello» la copia di un effetto noto. La verifica riguarda anche le altre forme di transfer basate su effetti sperimentali, non solo `same-line`; un eventuale chiarimento agli organizzatori dovrebbe descrivere l'algoritmo concreto. Questa revisione non certifica l'ammissibilità di una ricetta e non contatta gli organizzatori.

Separatamente dalle regole, addestrare su perturbazioni della stessa linea significa rinunciare alla dichiarazione scientifica di linea mai vista perturbata. Il banco può tenerlo come confronto con più informazione, etichettato chiaramente, senza farlo passare per C/J.
