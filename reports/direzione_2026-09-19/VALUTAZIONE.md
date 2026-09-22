# Direzione scientifica dopo t07 — 19 settembre 2026

**Tipo:** audit retrospettivo e proposta del lead scientist. Nessun nuovo candidato addestrato o inviato; nessuna strategia dichiarata vincente. Revisione umana: non ancora effettuata.

## 1. La raccomandazione

Ripartire dal trasferimento **dello stesso bersaglio**, conservando trial-01 come riferimento da battere, e costruire un trasferimento da più sorgenti con controllo esplicito della componente comune e delle quantità statistiche realizzate dalle cellule generate. La prima prova deve separare questi fattori: cambiare contemporaneamente sorgenti, generatore e predittore renderebbe il prossimo risultato poco interpretabile.

Non propongo un'altra rete condizionata. Non propongo neppure di spendere la giornata cercando una nuova conversione del banco HepG2 in un voto ufficiale. Il prodotto utile è un candidato confrontato con il nostro migliore, con una spiegazione verificabile del suo eventuale vantaggio.

Questa è una **proposta**, non una modifica delle decisioni storiche. La missione di questa sessione è la valutazione e la scelta della direzione; il ciclo di implementazione non è stato avviato.

## 2. Evidenza che cambia la scelta

**Misurato negli artefatti ufficiali:** trial-01 = +0,045929; t03 = +0,019692; t07 = −0,016004. I record originali e i relativi membri sono elencati in `audit.json` in questa cartella. Il progresso nell'infrastruttura non si è tradotto in progresso nella gara.

**Misurato nel verdetto locale**, `reports/conditioned_2026-09-18/verdict/verdict.json`: il lineare C poi scelto per t07 è sotto t03 di 0,008912, IC95 [−0,035695; +0,017442]. Il confronto non dimostra superiorità. La rete è `DISCARD`; il controllo con il contesto sostituito non mostra un vantaggio del contesto corretto. La riproducibilità del lineare risolveva un problema operativo, non costituiva una ragione scientifica per aspettarsi un punteggio migliore.

**Misurato**, `reports/prediction_t07_2026-09-19/comparison.json`: previsione +0,010135, risultato −0,016004, errore −0,026139. Un rapporto ufficiale/banco ricavato da una ricetta non è una calibrazione validata per qualunque candidato. Un solo nuovo punto non separa effetto della famiglia, ampiezza, supporto e differenza dei contesti. Non basta quindi prescrivere una calibrazione «per famiglia» per risolvere il problema.

**Misurato**, `reports/common_component_2026-09-18/c001/verdict.json`: l'aggiunta della componente comune RPE1 è stata scartata. Questo non è una prova contro la *sottrazione* della risposta comune della sorgente, né contro il trasferimento degli stessi bersagli da altre sorgenti.

**Interpretazione:** abbiamo selezionato e interpretato modelli su un banco informativo ma diverso dal problema finale, e promosso alcuni risultati intermedi oltre quanto consentissero le misure. Il t07 non prova che tutto il trasferimento sia fallito: prova il fallimento di quel candidato ufficiale.

## 3. Che cosa insegnano davvero le sei note

Le descrizioni sono state fornite dal proprietario. La loro presenza non equivale a disponibilità del codice, e un buon punteggio non dimostra causalmente quale componente funzioni.

| Nota | Informazione utilizzabile | Cosa non sappiamo |
|---|---|---|
| 1 | Ricetta congelata, quattro semi, correzione rispetto a un nullo e controllo del rischio direzionale | Significato preciso di B32, PRE, JOINT, risk-pool e della perdita |
| 2 | Calibrazione in due direzioni, controllo aritmetico, prior distributivo e riparazione dei conteggi | Equazioni, stima dei parametri, eventuale vantaggio isolato di ciascun passaggio |
| 3 | Checkpoint congelato, direzione separata dalla norma, vincoli su supporto e conteggi; distingue refit locale e modello ufficiale | Il guard locale non passa: non è una ricetta localmente validata da copiare |
| 4 | Consenso, centratura, trasformazioni dell'ordinamento e rifinitura intera | Definizione di consA, oggetto permutato, ablation e generalizzazione |
| 5 | Più sorgenti, affidabilità n/(n+100), risposta comune attenuata, due ampiezze | Accessi esatti, indipendenza delle tre K562, modalità di stima e ruolo di ciascuna sorgente |
| 6 | Trasferimento ancorato ai controlli del destinatario, media CPM e profilo aggregato trattati separatamente | Algoritmo che realizza simultaneamente le due quantità nei conteggi interi |

**Verifica web diretta:** nella [classifica pubblica](https://virtualcellchallenge.org/leaderboard), durante questa sessione, la ricerca «Atlas» mostra Jessy Liu, `AtlasShift rel100 cd4 0.5 BC 2:2:1 cpm1.2`, rango 80 e 0,1778; NiuLai, `AtlasShift rank77 ABC 20260917`, rango 87 e 0,1737. Sono osservazioni della pagina, arrotondate e soggette a cambiamento. Le descrizioni complete 5–6 restano attribuite al testo del proprietario: il pulsante informativo non le ha rese leggibili nella consultazione. Non è stata effettuata una revisione esaustiva di 100 progetti. La ricerca web generica non ha identificato un repository scientifico AtlasShift verificabile.

La riga di Jessy Liu mostra, in scala: PDS 0,694; MSE 0,080; Jaccard 0,001; NMAE 0,174; FID −0,010; reach 0,128. Rispetto a trial-01, il vantaggio complessivo di circa 0,132 si distribuisce indicativamente in +0,047 PDS, +0,029 FID, +0,025 NMAE, +0,018 reach, +0,013 MSE e +0,001 Jaccard. Calcolo descrittivo su valori arrotondati, non attribuzione causale; le versioni delle ancore dei concorrenti non sono note.

**Interpretazione:** una FID quasi nulla in scala può coesistere con un risultato competitivo. Ottimizzare soprattutto FID sacrificando PDS e accuratezza dell'espressione non segue l'esempio osservato. La [documentazione ufficiale](https://vcc-cli-wiki.virtualcellchallenge.org/) conferma che il totale è la media dei sei membri e che si consegnano 400 cellule per perturbazione.

## 4. Ipotesi concreta e differenza dal lavoro già fatto

Per ogni sorgente s e bersaglio t, scomporre la risposta in una componente comune m_s e un residuo specifico. Una prima famiglia da provare è `d'_s,t = d_s,t − gamma*m_s`, con gamma in {0, 0,75}; non assumere che 0,75 sia ottimale perché compare in una nota. Calcolare m_s su bersagli di sviluppo predefiniti, senza etichette del contesto di test. Registrare esattamente se si centra in lnFC, log2FC o un altro spazio: sono ricette diverse.

Solo dopo la prova a sorgente fissa, combinare sorgenti con pesi normalizzati sulle osservazioni effettivamente disponibili per ciascun bersaglio e gene. `n/(n+100)` è un'ipotesi iniziale di affidabilità, non una legge statistica. Evitare di contare mirror o repliche tecniche come contesti indipendenti; registrare maschere di disponibilità. Non usare assenza di misura come voto di effetto nullo.

La generazione deve distinguere `mean_i(X_ig/L_i)` da `sum_i(X_ig)/sum_i(L_i)`: la seconda pesa maggiormente le cellule profonde. Non sono in generale uguali. Nel codice attuale `generator.py` espone entrambe le letture, ma corregge una media dei conteggi stimata Monte Carlo, poi sceglie la dispersione anche in funzione degli zeri. Non garantisce per costruzione entrambe le quantità a 400 cellule. Questo è un **rischio da misurare**, non la diagnosi dimostrata della perdita di t07.

L'idea delle note 5–6 è quindi più precisa di «prendere più dati»: conservare la risposta specifica e controllare quale effetto il generatore realizza nelle due letture. Un vincolo su un momento può danneggiare l'altro: va verificato sui conteggi interi finali.

## 5. Primo passo eseguibile e criterio di arresto

**Proposta per una sessione locale di massimo 90 minuti:** produrre un confronto limitato a sorgente K562 fissa, con centratura disattivata/0,75, e una verifica delle due quantità sui conteggi. Nessun nuovo training neurale. Prima ripristinare lo scorer della versione fissata nel lock, oppure usare un ambiente già verificato; non aggiornare alla versione più recente alla cieca.

Il foglio di implementazione dovrà fissare prima del run:

1. Hash degli input e degli effetti; universo genico; unità; 400 cellule; semi appaiati; budget RAM. Pilot su pochi bersagli e controlli locali per verificare il procedimento, esplicitamente insufficiente a promuovere il candidato.
2. Quattro bracci fattoriali: trasferimento attuale; sola centratura; sola correzione delle quantità realizzate; entrambe. Se la correzione simultanea non è fattibile, riportare l'incompatibilità e non falsificare la distribuzione per ottenere una media desiderata.
3. Riferimenti obbligatori: trial-01 ricostruito nel banco, t03, nullo e trasferimento con identità dei bersagli permutata. Congelare il generatore quando si valuta la centratura. Controllare zeri, varianza, profondità e DE spurio su controlli disgiunti; non basta far tornare la media.
4. Sei metriche grezze e differenze appaiate; anche numero di chiamate, precisione dei segni e correlazione centrata. Le ancore ufficiali possono fornire una lettura indicativa, non una previsione certificata del voto.
5. Per la conferma successiva: bersagli disgiunti da quelli usati per scegliere parametri, più semi, confronto su contesto tenuto fuori e su pannello di regime pertinente. Gli split già consultati ripetutamente sono sviluppo; non chiamarli nuovo test indipendente. Una vittoria solo su HepG2 non basta. Un intervallo compatibile con zero dà «inconcludente», non «promosso».

Per promuovere una prova di efficacia, fissare una regola prima dei risultati: vantaggio appaiato positivo sul criterio primario dichiarato, intervallo bootstrap che escluda zero e margini di non inferiorità per PDS e NMAE definiti prima del run. Il bootstrap sui bersagli non copre l'incertezza di contesto. Nessuna ricerca a posteriori della metrica che rende vincente il candidato. Il pilot termina con fattibilità/errore misurato e costo della conferma, non con una sottomissione.

**Distinzione essenziale:** per i bersagli già perturbati nelle sorgenti esterne, la prova principale è trasferire a un contesto nuovo. Uno split che nasconde anche tutte le perturbazioni del bersaglio misura invece il problema dei bersagli nuovi. Serve per il fallback e per il pannello finale, ma non deve cancellare l'informazione esterna legittimamente disponibile per i bersagli noti.

**Sorgenti successive:** CD4 e HCT116 hanno interesse per copertura, da riconfermare sui dati utilizzabili e sulle repliche; H1 e HEK293T sono candidati per diversità e consenso, non automaticamente per corrispondenza del lignaggio. Le source-card del 15 settembre rinviavano CD4/H1: sono una fotografia precedente, non una dimostrazione che non servano. Prima dell'acquisizione servono manifest, licenza, meccanismo, controlli e copertura effettiva. Nessun atlante completo sul portatile.

## 6. Revisione della pulizia

Confronto effettuato su `main` a0ab5fb e `refactor/pulizia` 51a9c60. Il riepilogo allegato della precedente code-review riguardava il commit t07, non questa differenza. Il nuovo conteggio da oggetti Git è in `audit.json`; il perimetro è quello dei file Python tracciati sotto src, scripts e tests.

**Rilievo prioritario — flusso attivo rimosso.** Il branch elimina `scripts/32_daily_cycle.py`, mentre AGENTS e le skill continuano a prescriverlo. Il comando di stato eseguito su main vede un guardiano attivo, PID 6612. Il branch non è integrabile come semplice pulizia senza ripristinare il percorso operativo o deliberarne esplicitamente la sostituzione.

**Rilievo prioritario — ingestione rimasta senza dipendenze.** Il notebook `notebooks/remote_ingest_hepg2.ipynb` importa `vcc2026.remote_catalog` e `vcc2026.remote_ingest`, rimossi dal branch. L'analisi degli import dei soli script conservati non copre gli ingressi da notebook.

**Rilievo scientifico — riferimento migliore archiviato.** Scompaiono la pipeline di trial-01 e la funzione `predicted_profile` in `inference.py`, che applica la correzione composizionale. Il tag ne conserva la storia, ma il confronto col migliore diventa meno immediato proprio mentre occorre rifarlo. Ripristinare un percorso minimo riproducibile per trial-01 prima dell'integrazione, non necessariamente tutti i vecchi moduli.

La deduplicazione di lettori e lo spostamento di Adam appaiono coerenti con l'intento. Non ho però rieseguito le quattro riproduzioni su dati reali: il resoconto della pulizia le dichiara, gli script temporanei non sono versionati. Non dichiaro equivalenza numerica indipendentemente verificata.

I checker documentali passano su entrambi i checkout, ma nel branch accettano 134 percorsi dichiarati archiviati. Il verde documentale non garantisce che una procedura ancora prescritta sia eseguibile. Il tag archivio è locale secondo il resoconto: prima di trattarlo come conservazione durevole occorre includerlo nel normale backup/versionamento autorizzato.

## 7. Correzioni e verifiche della sessione

- Confermato nel log `reports/trial_2026-09-19/t07/job_043.log`: 6.477 geni sull'asse ufficiale per A/B/C, quindi 12.056 senza effetto esplicito del modello. Questo non garantisce effetto realizzato esattamente zero dopo generazione e normalizzazione. Il numero pubblico 11.698 non va riscritto nei record verbatim.
- L'affermazione di identità a 1e-7 su A/B/C non è dimostrata dagli artefatti qui esaminati. Non ho confrontato due checkpoint ufficiali indipendenti.
- Lo scarto massimo delle ancore di 0,003829 riguarda i membri controllati, non certifica la MSE né tutte le configurazioni. Nessuna soglia nuova scelta dopo aver visto lo scarto.
- Suite main: 581 test, un errore e un saltato. Errore: `test_components_reproduce_the_scored_fidelity`, import `cell_eval2.config` assente. Lo stesso import fallisce in processi isolati in entrambi i checkout: problema dell'ambiente condiviso, non regressione attribuita alla pulizia.
- La suite del branch è stata rilanciata con il suo wrapper, dopo una prima invocazione dal wrapper di main; l'esito definitivo è in `VERIFICHE.md`.
- Nessun file storico, checkpoint, dataset o previsione è stato sovrascritto. Nessun merge o invio effettuato. La proposta non assegna probabilità di successo né promette 0,1: definisce un passo capace di produrre evidenza utile senza ripetere la selezione di un candidato già non superiore.
