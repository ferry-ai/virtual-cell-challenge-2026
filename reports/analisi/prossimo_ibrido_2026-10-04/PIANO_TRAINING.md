# Piano del prossimo ibrido: copertura, fedeltà della catena e informazione utile

4 ottobre 2026, Codex. **Proposta operativa, non protocollo congelato né autorizzazione di lancio.**
Mandato del proprietario in questa chat: audit del prepasso, piano del training successivo, rivalutazione delle scelte precedenti e approfondimento dei vincitori 2025. R-LEAD resta la sede operativa. Commit di partenza `13099149ed49c86af3e8d1faa95ca2e887f3ecea`, macchina `LAPTOP-DLG1LHV1`.

## 1. Stato dell'evidenza e divisione del lavoro

**Risultato ufficiale verificato:** T30 = **0,135248601985599**, delta t25 = **−0,00498945892923655**, ramo b della regola, nessuna promozione. Il PDS è il principale contributo negativo (−0,04223697 sul membro scalato), in parte compensato da fedeltà e Jaccard. [Ricalcolo indipendente](score_audit_r1.json). Priorità della diagnosi: capire perché la correzione perde specificità dopo il passaggio alla catena inviata; misurare quota comune, direzione/ampiezza, selettore e differenza d'ancora prima di intervenire sulla sola dispersione. Nessuna di queste cause è ancora identificata dal solo score aggregato. La soglia di perdita era 0,13523806091483554: l'arrotondamento a 0,1352 nasconde il ramo esatto della regola.

- **Claude1:** chiusura ufficiale del t30 e diagnosi banco/export, secondo [consegna](PROMPT_CLAUDE1.md); regia dei propri job già autorizzati.
- **Codex:** [audit del prepasso](AUDIT_PREPASSO.md), disegno dati/training e [approfondimento 2025](VINCITORI_2025.md), in questa cartella nuova.
- **Autore del prepasso diviso:** implementazione della suddivisione con merge e parità. Questo piano aggiunge requisiti informativi, senza sostituire o modificare il suo codice.

Inventario, fixture, contratto di inferenza e progettazione dei campioni possono procedere durante la diagnosi. La scelta finale della nuova loss, del generatore e delle guardie dipende dalle sei metriche e dai difetti riprodotti da Claude1. Questi campi si congelano prima dei nuovi esiti.

## 2. Precedenti e che cosa cambia

| Precedente | Evidenza/limite | Differenza proposta e controllo precoce |
|---|---|---|
| S-001/S-002: rete sostitutiva e pilot r3 | Discriminazione insufficiente o transfer migliore; lo stato può aiutare senza battere il riferimento | Transfer esplicito e invariato a residuo nullo; controllo di specificità dei target e confronto con rete senza contesto |
| S-006: correzione v4 | Correzione dannosa, risposta comune ipotizzata | Conservare guardie su ampiezza, risposta comune e specificità; verificarle su linee interne escluse, non soltanto coppie interne delle linee viste |
| S-007: reti/bilineari sui controlli medi | Quei confronti sono negativi; meccanismo non isolato | Non ripetere la stessa media come novità: pseudobulk stratificati con incertezza, supervisione media accanto alle cellule, eventuali descrittori aggiuntivi in ablation separata |
| S-009: D-056 v1 | Banco positivo, t30 riportato negativo; baseline del banco diversa da quella corretta in export | Un solo contratto di baseline/residuo in fit, banco ed export; prova completa con residuo nullo e stessi generatori |
| S-010: fonti del transfer | Più aggregati aiutano localmente, non provano un miglioramento ufficiale | Confrontare transfer ampliato e di produzione prima di attribuire il guadagno alla rete |

Fonti: [STRADE](../../../docs/STRADE.md), [CP-0062](../../../docs/checkpoints/0062-d056-ibrido-selettivo-esito-banco.md), [previsione t30](../../invii/prediction_t30_2026-10-04/prediction.json). Nessun esito precedente viene riscritto. L'approfondimento 2025 suggerisce contrasti, non riabilita automaticamente una strada negativa.

## 3. Dati: tutti i contesti, tre rappresentazioni con funzioni diverse

Il corpus principale deve rispettare [D-053](../../../docs/GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile). Per ogni sorgente conservare linea, donatore, stato/stimolo/tempo, studio, libreria, modalità, guide e repliche quando disponibili. Il gruppo usato per escludere un'intera linea non deve cancellarne i sottocontesti.

1. **Archivio completo verificato**, immutabile, con provenienza e metadati. Non restringerlo al pannello della gara.
2. **Banca di aggregati stratificati** sulle cellule ammesse: conteggi e denominatori, somme di proporzioni e loro variabilità quando necessarie, frazioni di zeri, profili di controllo, numerosità, maschere, strati di guida/replica. Distinguere somma dei conteggi, media delle proporzioni e media dei log: non sono intercambiabili. Stimatori, shrinkage e statistiche derivate devono rispettare il fold.
3. **Campioni cellulari annidati/rotanti** per apprendere l'eterogeneità, con probabilità di inclusione e controllo dell'esposizione per contesto, target e strato. Tutti i contesti idonei devono avere un ruolo effettivo; una fonte di soli aggregati non conta come supervisione cellulare.

La [misura sui campioni H1](../../modelli/rete_ancorata_v4_2026-10-03/esito/nested_fold_h1_r1/decision.md) boccia il cap fisso 64 per ricostruire quei riassunti. **Non dimostra che ogni minibatch debba contenere 128–512 cellule per target, né che un training debba rileggerne l'89% a ogni esperimento.** Distinguiamo precisione della banca di effetti, campione fisso conservato e campionamento stocastico durante il training. I livelli non giudicabili non sono certificati sufficienti.

Prova proposta, sui soli dati di training del fold: banca di aggregati completa + diversi livelli di campione cellulare, mantenendo contesti e split. Misurare errore dei riassunti, stati rari, esposizione cumulativa e utilità predittiva sulle linee interne escluse. Per campioni sovrarappresentati, distinguere pesi per stimare la popolazione da pesi deliberati della loss: niente doppia ponderazione involontaria.

L'inventario precedente è uno snapshot, non una certificazione attuale: includere CD4 per tutti i donatori/stati idonei, Orion, KOLF e le sorgenti minori; ogni adattatore o controllo mancante resta una lacuna esplicita. L'integrazione non dipende dal successo del modello. Un confronto ridotto può essere una ablation dichiarata, mai il corpus completo.

## 4. Prepasso: prima conservazione dell'informazione, poi distribuzione del calcolo

Implementare un bilancio per unità biologica e tecnica: attese → presenti → riconosciute → QC → ammesse → ruolo nel fold → campionate → lette dal loader → contributo alla loss. Geni, target, guide e controlli hanno contatori separati. Un contesto idoneo con zero uso deve fermare l'accettazione o figurare come eccezione motivata e verificabile.

La soglia attuale di 30 controlli può togliere un intero contesto. Non abbassarla indiscriminatamente e non prendere controlli da un'altra linea per far passare un conteggio. Per ogni caso: verificare etichette/partizioni, distinguere assenza reale e mancata associazione, valutare controlli dello stesso esperimento biologicamente compatibili con provenienza esplicita; altrimenti mantenere un ruolo compatibile distinto o una lacuna, senza dichiararlo supervisione cellulare valida. Valutare una policy per contesti a basso supporto con incertezza e shrinkage soltanto su fold di sviluppo.

Altri controlli: maschere per cellula (non usare l'intersezione globale come perdita di tutti i geni), geni d'ingresso oltre i soli più abbondanti, controllo dei fenotipi estremi salvati dal QC, pool per libreria e sottostati rari. Le cellule senza etichetta non sono controlli per default; possono avere un ruolo basale esplicito, senza etichette inventate.

Per il prepasso diviso:

**Prima profilare il costo centrale.** Il log HepG2 mostra 6.677 s fra ultima prima lettura e primo risultato della seconda ([audit](AUDIT_PREPASSO.md)); l'intervallo include anche l'attesa del worker. Il costo totale non è proporzionale agli shard per definizione. Misurare le singole fasi e valutare accelerazione della pianificazione globale insieme alla divisione per sorgente. La proposta distribuita non è già una soluzione dimostrata al limite di runtime.

- indice globale stabile di shard, assi, chiavi e identità **prima** delle prime letture: già queste usano le maschere globali per chiave;
- letture indipendenti salvate, piano globale per QC/dedup/split/ammissione/ingressi, seconde letture secondo quel piano, merge con manifest completo;
- cache per fold dove cambiano maschere, geni selezionati, quote, ruoli o statistiche: non dichiarare tutto il primo passaggio indipendente dal fold senza provarlo;
- rifiuto di parti mancanti, duplicate, di versioni diverse o con identità conflittuali; somma deterministica e ordine canonico;
- equivalenza del contenuto scientifico col prepasso unico; eccezioni soltanto per metadati di esecuzione dichiarati (path, timestamp, argomenti di staging), non per maschere o ammissioni. Tolleranze numeriche motivate e congelate;
- fixture con shard riordinati, stesso contesto su sorgenti diverse, collisioni, librerie tardive, 29/30 controlli, assi differenti; perturbare le risposte escluse deve lasciare invariati i derivati del fit, non necessariamente le statistiche riservate alla valutazione;
- modalità distinta e testata per il refit finale senza holdout fittizio, dopo la selezione. Il limite dell'API non deve decidere quale rete esportare.

La parità ingegneristica conserva anche i difetti: la modifica della policy informativa è un intervento separato, con proprie misure di sensibilità. La vecchia versione e le ricevute restano intatte.

## 5. Contratto dell'ibrido e banco comune

Formula proposta: **effetto = T + w R**. T è definito da una policy versionata di fonti, stimatore, supporti, unità e maschere. Nel training ogni residuo usa un'ancora costruita senza la linea destinataria e senza il fold esterno; in J sono rimossi globalmente anche i bersagli nascosti. La stessa policy costruisce la base in banco e in produzione: i dati leciti cambiano, la definizione no.

Confronti obbligatori: transfer di produzione adattato lecitamente a ogni fold, transfer ampliato, ciascuna base con la propria correzione coerente. Non riusare una R appresa contro T_all sopra T25 come candidato equivalente. R deve essere espresso nelle stesse unità dell'effetto esportato e confrontato anche dopo normalizzazione, maschere e generazione.

Due emissioni esplicite, fissate prima: impostazioni t25 e impostazioni t28. Ogni ibrido si confronta con la propria baseline emessa allo stesso modo; scala e dispersione non diventano un guadagno attribuito alla rete. T28 resta il massimo ufficiale osservato, t25 il riferimento per isolare la correzione. Una replica locale del confronto non è una conversione dello score ufficiale.

Selettore: pesi appresi su predizioni fuori fold per linea, con validazione annidata e possibilità effettiva di w=0; basare l'obiettivo sul beneficio misurabile della correzione, con controllo sui sei membri dopo generazione. Supporto, assay, ampiezza e incertezza sono informazioni candidate da ablation. Nessun peso scelto sulle risposte A/B/C o del fold finale. Per bersagli J senza supporto, fallback congelato e risultato J separato; descrittori trasferibili non dimostrano da soli generalizzazione J.

Il passaggio di Claude1 delle 12:30 riferisce esplorativamente una quota comune di R più alta in A/B/C che nelle righe del banco. Chiedere la ricevuta riproducibile, con stessa definizione, maschera e supporto dei target: qui il numero non è ricertificato. Un confronto con R centrata è una diagnosi motivata da S-006, da preregistrare sui contesti di sviluppo; non autorizza una correzione a posteriori del t30 né un invio automatico. Verificare anche la dipendenza della centratura dalla composizione del pannello e applicare l'eventuale nuova regola identicamente in banco ed export.

Parità: residuo nullo → stessi effetti → stesse cellule con seed fissato → stesse metriche. Verificare la stessa prova nell'esportatore di produzione, non soltanto nel banco. Hash/versioni di ogni componente nel manifest.

## 6. Sequenza dei training, senza cambiare tutto insieme

| Passo | Confronto e domanda | Condizione per procedere |
|---|---|---|
| E0, prima della GPU | Audit di Claude1 + prepasso + catena a residuo nullo | Supporti completi, parità e diagnosi documentate; nessuna causa presunta trasformata in fatto |
| E1, primo training ibrido proposto | Stessa architettura D-056 regolarizzata, corpus ampliato tracciato, baseline coerente ovunque; baseline senza rete valutata a fianco | Uso effettivo dei contesti, guardie e miglioramento appaiato sul banco corretto. Questo è un nuovo candidato complessivo; non attribuire il delta al solo numero di contesti |
| E1a, ablation dei dati | Stessa architettura/policy su sottoinsieme annidato del corpus, stesso test, esposizione documentata | Separare ampiezza del corpus da modifiche del modello; subset dichiarato, nessuna esclusione dal percorso principale |
| E2, supervisione | Su stessi dati, loss cellulare contro loss cellulare + errore sullo pseudobulk stratificato; baseline aggregata riaddestrata a fianco | Termine medio migliora la previsione dopo generazione senza cancellare specificità/stati. Coefficienti scelti nei fold interni |
| E3, informazione di contesto | Media dei controlli contro media + riassunti di eterogeneità o encoder di insiemi, riaddestrati | Beneficio misurabile; controllo con contesto scambiato mantenendo fisso il vero basale del generatore |
| E4, descrittori | Descrittori correnti contro aggiunta ESM2 congelata, stessa capacità confrontabile | Beneficio C/J separato e provenienza lecita; nessun download prima di piano/versione/licenza/accesso |
| E5, finalisti | Almeno tre semi di fit; distinguere semi del generatore e variabilità fra contesti | Stabilità, conferma appropriata, refit completo e nuovo protocollo di invio |

E2–E4 sono contrasti condizionati dalle misure, non una sequenza automatica di job. Una nuova testa generativa/flow si considera solo se la diagnosi mostra un errore di distribuzione a effetto medio comparabile. Il nuovo input pseudobulk non elimina le cellule o i sottocontesti; la baseline aggregata resta un controllo, non è promossa dal riferimento al 2025.

## 7. Criteri da congelare prima di leggere i nuovi risultati

- Split per linee intere, target C/J, riserve e versioni del corpus immutabili. Le cinque linee già lette sono sviluppo per questa iterazione; una riserva deve essere davvero nuova al processo di selezione. H1 test resta chiusa.
- Sei metriche con lo scorer effettivo, per contesto e regime, insieme a grezzi e supporti. Separare macro fra contesti, scala locale e score ufficiale; investigare JAC e MSE senza eliminarli perché scomodi.
- Decisione sul **delta appaiato contro la baseline coerente**, miglioramento pratico, regressioni ammesse e incertezza fra contesti. Le soglie quantitative e i normalizzatori vanno motivati e fissati nel protocollo dopo l'audit, prima delle misure nuove; nessuna adozione dal solo banco ≥0,100.
- Guardie tecniche con tolleranze esplicite: contesti mancanti, esposizione, leakage, non-finiti, pool, parità, hash; guardie scientifiche per specificità/ampiezza/risposta comune e beneficio su linee interne escluse.
- L'eventuale nuovo invio registra separatamente una previsione sullo score e il confronto con t25/t28. Nessuna promessa di aumento derivata dal delta locale.

## 8. Esecuzione e prossima decisione

Locale: codice, fixture e letture leggere. Colab CPU: banchi e preparazione pesante con input disponibili. Per gli shard privati presenti solo nell'account di ingestione, documentare il vincolo di accesso che motiva il prepasso distribuito su Kaggle CPU in quell'account; GPU Kaggle per training effettivo su CUDA. Misurare memoria/processi per stadio: il picco dell'encoding Orion non è automaticamente il picco del prepasso. Salvare ricevute per kernel e recupero delle parti.

Prima del lancio: integrare il resoconto di Claude1, completare il bilancio del corpus ampliato, scegliere baseline e primo contrasto e congelare protocollo/manifest. Se mancano ricevute, si possono completare implementazione e test, ma non dichiarare completo il training. Job, nuovi download, push e invii seguono le autorizzazioni della sessione; questo documento non ne avvia.
