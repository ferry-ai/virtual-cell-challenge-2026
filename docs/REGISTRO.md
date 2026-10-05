# Registro del ciclo di vita di documenti e dati

A che serve: dire, per ogni materiale del progetto, **se ci si può ancora contare**.
**Per un solo percorso non serve leggere questo file:** `python scripts/31_check_docs.py --status
<percorso>` stampa le voci che lo coprono, la scheda da leggere, le correzioni dell'indice dei
checkpoint e il giudizio dell'indice della cartella, quando c'è (D-049).
Un documento non diventa falso tutto insieme: di solito resta valido in gran parte e
sbaglia in due punti. Qui si segna lo stato del documento e, quando serve, si apre una
scheda che elenca le singole affermazioni in discussione.

Il rinnovo richiesto il 1 ottobre e completato nelle verifiche del 2 ottobre riallinea
le guide a t29: R-LEAD è il piano operativo unico; le code datate restano evidenza storica.
Le revisioni aperte sotto conservano numeri e ancore. La cronologia del registro si recupera
in Git; [rapporto del rinnovo](../reports/analisi/rinnovo_repo_2026-10-01/README.md).

## Stati

| Stato | Significato | Cosa deve fare chi legge |
|---|---|---|
| `attuale` | È la guida valida adesso | Seguilo |
| `da-verificare` | Contiene almeno un'affermazione in dubbio, ma il resto regge | Usalo leggendo prima la sua scheda |
| `superato` | Le sue conclusioni sono state sostituite da un materiale successivo, indicato per nome | Non usarlo come guida; leggilo per capire la storia |
| `storico` | Non è una guida: è una registrazione datata, o evidenza grezza | Usalo come prova di ciò che si vedeva allora, non come indicazione |

Tre regole che rendono il registro affidabile:

1. **`da-verificare` non diventa `superato` in silenzio.** Serve un materiale nuovo,
   citato per nome nella colonna "Sostituito da", e una riga nel checkpoint che lo
   stabilisce.
2. **Un documento più recente non è automaticamente più corretto.** Quando due
   documenti sono in disaccordo e nessuno dei due ha misure decisive, si registra la
   contraddizione come aperta (vedi [R-004](#r-004--docsrevisione_analisi_2026-09-11md)).
3. **Niente cancellazioni, e niente sovrascritture dell'evidenza.** Il registro cambia
   stato e aggiunge avvisi; non elimina documenti, report o dataset. Una nuova
   esecuzione di una sonda va in una destinazione distinta (`--out`), non sopra il
   risultato precedente: anche un tentativo fallito documenta che cosa si vedeva a
   quella data. Vedi [Revisione periodica](#revisione-periodica-e-pulizia).

### Che cosa copre una voce

Il controllo automatico usa questa convenzione, quindi conviene rispettarla:

| Forma della voce | Copre |
|---|---|
| `docs/PROGETTO.md` | esattamente quel file |
| `reports/storico/data_audit/` (con `/` finale) | quella cartella e tutto ciò che contiene, sottocartelle comprese |
| `reports/storico/candidate_verification/*.json` | i file che corrispondono al modello, senza scendere nelle sottocartelle |

Ogni file sotto `docs/` e `reports/` deve essere coperto da almeno una voce, a qualunque
profondità. Registrare una cartella intera copre anche i file che ci finiranno domani:
farlo solo quando il contenuto è omogeneo, per esempio una serie di sonde con lo stesso
manifest. Materiale di natura diversa merita una voce propria.

## Documenti, report e artefatti di codice

| Percorso | Stato | Sostituito da | Cosa resta utile / nota | Scheda |
|---|---|---|---|---|
| `reports/analisi/riconciliazione_banca_2026-10-05/` | attuale | — | Verifica metadata, versioni/hash/mount, ledger storico recuperato, byte Git e limiti del consumo; nessuna certificazione di corpus completo | [R-LEAD](piani/strategia-scientifica.md) |
| `docs/storico/consolidamento_banca_2026-10-05/` | storico | `docs/piani/strategia-scientifica.md` | Quattro guide complete e byte-identiche prima del consolidamento; manifest dei file originali | — |
| `reports/modelli/percorso_riusabile_2026-10-05/DATI_DISPONIBILI_r2.md` | da-verificare | — | Dimensioni datate utili; note su training non avviato superate, GB storage non uso del fit | [R-024](#r-024--identità-della-banca-ledger-congelati-e-stato-del-rifit) |
| `reports/modelli/percorso_riusabile_2026-10-05/TRAINER_r1.md` | storico | `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r2.md` | Reader neurali e fixture, non launcher lineare corrente; divieti e stato datati non operativi | — |
| `reports/modelli/percorso_riusabile_2026-10-05/TRANSFER_IDENTICO_r1.md` | da-verificare | — | Identità t25/t28 valida; no-VCC superato dal mandato umano INVIO_DIRETTO, senza cambiare ricetta | [R-024](#r-024--identità-della-banca-ledger-congelati-e-stato-del-rifit) |
| `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r1.md` | superato | `reports/modelli/percorso_riusabile_2026-10-05/RIUSO_r2.md` | Procedura utile, vecchio inventario vincola un ledger operativo mutato; r2 usa la copia storica byte-identica | [R-024](#r-024--identità-della-banca-ledger-congelati-e-stato-del-rifit) |
| `reports/modelli/percorso_riusabile_2026-10-05/training_coverage_r1/expected.json` | superato | `reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r2.json` | Inventario originale preservato; r2 conserva copertura e corregge soltanto il riferimento al ledger congelato | [R-024](#r-024--identità-della-banca-ledger-congelati-e-stato-del-rifit) |
| `reports/analisi/pezzi_adottabili_2026-10-05/` | attuale | — | Catalogo del 5/10 dei pezzi copiabili nel residuo ancorato: equazioni riaperte in stesura, correzioni ai rapporti Antigravity (l'arXiv 2007.02747 non è PLE), testi integrali in agenti/. Nessun innesto, training o score | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/analisi/gears_nella_rete_2026-10-04/` | attuale | — | GEARS a commit fisso: studio di fonti primarie, audit della loss e del flusso dei dati; prototipo a grafo condizionato dal contesto collegato su fixture alla CellNet D-056. Nessun training o beneficio biologico misurato | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/analisi/prossimo_ibrido_2026-10-04/` | attuale | — | Codex: consegna Claude1 e piano proposto post-t30, audit leggero dei QC del pilot, esclusione di contesto sotto 30 controlli riprodotta su fixture, ricalcolo dello score dagli status, fonti primarie 2025. Nessun nuovo training né modifica al prepasso; corpus ampliato ancora da certificare | [R-LEAD](piani/strategia-scientifica.md) |
| `docs/checkpoints/0065-d056-confronti-e-rumore-del-banco.md` | attuale | — | Confronti controllati e taratura del rumore del banco D-056: guadagni a un seme rumorosi quanto il loro valore, +0,013 di media su 5 semi e 400 cellule, PDS in perdita netta sul fold esportato, procedura dell'invio fedele; corregge CP-0062 e CP-0064 | — |
| `docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md` | attuale | — | t30 ufficiale 0,135249, −0,004989 contro il t25, ramo b non conclusivo; che cosa del banco D-056 non si è trasferito (baseline, quota comune e ampiezza all'esportazione, PDS del fold esportato, JAC locale, flusso casuale unico, bersagli del pannello assenti dal banco); delimita CP-0062; causa non isolata. Corretto in parte da CP-0065 (0065): la procedura dell'invio è fedele al banco | — |
| `docs/checkpoints/0060-direzione-x-transfer-pilot-v4.md` | attuale | — | D-054: rete ancorata al transfer come candidato operativo; diagnosi misurata dei training v3 (ricostruzione esatta del campionatore, riserva di valutazione, decompressione); pilot v4 congelato e lanciato; binario dati D-053 indipendente dall'esito. Nessun risultato scientifico v4 | [R-LEAD](piani/strategia-scientifica.md) |
| `docs/checkpoints/0058-copertura-integrale-contesti.md` | attuale | — | Mandato del proprietario D-053: tutte le linee e i contesti idonei, campioni senza omissioni di contesti, ruoli e uso effettivo verificabili; nessun nuovo training o beneficio biologico misurato | — |
| `reports/analisi/candidato_ibrido_2026-10-03/` | attuale | — | Proposta Codex di adattamento di X alla rete ancorata, ruoli di aggregati e campioni, riconto 8/21 gruppi. Nuove ricevute tecniche v3: H1 non passa il bilanciamento preregistrato, attesa dei batch 81–84%; nessuna metrica scientifica aperta o nuova corsa. Raccordo dei piani proposto, pausa mantenuta | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/analisi/lezioni_vcc2025_2026-10-03/` | attuale | — | Analisi Codex dei vincitori 2025 con fonti primarie e catalogo PRiMeFlow/ESM2; riconti riproducibili su metadati del pilot e del banco, limiti inferiori dei campioni e proposte per modelli/dati. Nessun nuovo training, download di dataset o score; R-LEAD resta la sede operativa | — |
| `reports/sorgenti/inventario_riconciliato_2026-10-04/` | attuale | — | Inventario riconciliato del catalogo per gruppo di linea (sessione d0100a, D-053): fonti, cellule acquisite, aggregati nel cubo, uso nel pilot v4, lacuna e lavoro per ogni voce; esclusioni con motivo. Sintesi di manifest citati, non adozione di gruppi o ruoli; lo stato dei job è quello della notte fra il 3 e il 4/10 | [R-DATI](piani/dati-affidabilita.md) |
| `reports/sorgenti/ingestione_completa_2026-10-03/` | attuale | — | Ingestione completa per mandato del proprietario del 3/10 (sessione 22d21f): sorgenti con stato e assegnazione, vincoli di parallelismo misurati, verificatore dell'archivio che riprende da ricevute precedenti con test, job 133–134 | [R-LAB](piani/piano-giorno-2026-09-30.md) |
| `reports/analisi/revisione_ancorata_codex_2026-10-03/` | attuale | — | Revisione Codex richiesta prima del training v3: fixture della dipendenza delle ancore da target nascosti, allineamento del riferimento B e pacchetto di generazione; nessuna modifica del codice attivo né job avviato | — |
| `reports/sorgenti/prepasso_ampliato_2026-10-04/` | attuale | — | Decisione delegata dal proprietario (sessione 2b35612c): il pre-passo del corpus ampliato su shard campionati dai soli metadati (livello 64, tutti i controlli), con le misure di tempo, memoria e inventario che la motivano e le alternative scartate | [R-DATI](piani/dati-affidabilita.md) |
| `reports/gara/scorer_0_18_2026-10-04/` | attuale | — | Confronto di cell-eval2 0.18.0 con la 0.16.0 dei banchi (sessione 2b35612c): fonti PyPI, differenze dei pacchetti, venv uguale alla ruota ufficiale 0.16.0, suite della repo con il venv; parità numerica non eseguita | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/trasferimento/fonti_transfer_2026-10-04/` | attuale | — | Confronto delle fonti del transfer (sessione 2b35612c): `transfer_cells_J` e `transfer_all_J` contro `transfer_prod_J` sui sei membri di Jurkat e K562, linee che non hanno dato l'indizio di H1 e HepG2; regola e condizioni di un invio di solo transfer congelate prima delle uscite | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/generatore_e_banchi/banco_v2_2026-10-04/` | attuale | — | Banco v2 (sessione ba9b8bcb): strumento per differenze appaiate su più semi con la numerosità dell'invio e flusso casuale per blocco, emissione t25 o t28; test senza scorer passati, nessuna esecuzione su dati veri e nessun risultato | — |
| `reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/` | attuale | — | Subentro Codex: CD4 12/12 verificata; cinque banchi CPU t28 completati e ricevute verificate. ESITO_BANCO_V2 e decisione_r1: favorevoli 4/5 su all, solo Jurkat su prod; PDS negativo HepG2 su entrambe e RPE1 su prod. Pilot diagnostico, nessuna promozione | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/modelli/percorso_riusabile_2026-10-05/` | attuale | — | Storage r11 e producer persistenti; rifit/generazione parziale conclusi, candidato formato PASS. ESECUZIONE_r17 e R-LEAD seguono trasferimento/invio t36; corpus completo e valutazione ancora aperti | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/modelli/ibrido_esecuzione_2026-10-04/` | attuale | — | Banca CD4 e preparazione di tre fold CPU su tre account; catena del primo fit GPU. Campagna in corso, primo cohort aggregato non completo; nessuna promozione | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/modelli/ibrido_pseudobulk_2026-10-04/` | attuale | — | Mandato e componenti dell'ibrido semplice. Esecuzione successiva in ibrido_esecuzione_2026-10-04; integrazione del corpus completo ancora aperta | [R-LEAD](piani/strategia-scientifica.md) |
| `docs/checkpoints/0066-banco-v2-t28-cinque-linee.md` | attuale | — | Esito preregistrato banco v2 t28: 4/5 favorevoli su all, 1/5 su prod; Jurkat unica su entrambe, rumore del generatore a fit e verità fissi | — |
| `reports/modelli/diagnosi_t30_2026-10-04/` | attuale | — | Diagnosi dopo il t30 (sessione ba9b8bcb): ricevute riproducibili della catena dell'invio, dei membri del banco D-056 e del confronto fra esportazione A/B/C e righe di sviluppo; tabella training → banco → export → generazione; difetti riprodotti, controlli passati e ipotesi aperte tenuti distinti; protocollo dei confronti controllati congelato prima delle uscite, non ancora eseguito | — |
| `reports/modelli/ibrido_selettivo_2026-10-04/` | attuale | — | Ibrido selettivo D-056 versione 1 (sessione 2b35612c): protocollo congelato prima dei training (transfer congelato, rete con testa comune esclusa dalla previsione, guadagno fisso, penalità sulla correzione, guardie su coppie di validazione interne, selettore a sei parametri fuori fold con leave-one-line-out su H1/HepG2/RPE1, conferma su Jurkat), codice, lanci ed esiti | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/modelli/rete_ancorata_v4_2026-10-03/` | attuale | — | Rete ancorata v4 (sessione 5eacdf): modello della v3 con batch bilanciati a ogni passo (peso 1 per cellula), gemelli compatti degli shard verificati per decodifica, budget separati, ricevuta `exposure.json`, ancore a medie J da tutti gli aggregati del cubo; diagnosi dei training v3 r1 senza aprire i loro risultati; protocollo del pilot dichiarato (D-053) congelato prima dei training; 35 test | [R-LEAD](piani/strategia-scientifica.md) |
| `reports/modelli/rete_ancorata_2026-10-03/` | superato | `reports/modelli/rete_ancorata_v4_2026-10-03/` | Rete cellulare versione 3 (sessione 22d21f): ancora del transfer nei logit, guadagno e correzione appresi; protocollo congelato a `4cb61d4` con emendamento §9. Training H1 e HepG2 r1 conclusi: H1 non tecnicamente accettabile (bilanciamento), RPE1 mai lanciato; pilot incompleto, risultati non aperti. Resta l'evidenza dei lanci e il codice v3; la v4 ne corregge percorso dei batch, budget e ancore ([diagnosi](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md)) | [R-023](#r-023--rete-ancorata-v3-pilot-incompleto-percorso-dei-dati-e-ancore-sostituiti) |
| `reports/sorgenti/revisione_ingestion_2026-10-03/` | attuale | — | Revisione della consegna Claude2 con originale preservato, correzioni e fixture locali; mandato CD4 completo dopo dichiarazione di capacità Drive 5 TB, campioni distinti dall'archivio. Passaggio della regia a Claude1, monitor Codex sospeso, fotografia dei job 130–131; nessuna nuova ingestion o rimozione certificata | — |
| `reports/analisi/confronto_alfredo_2026-10-03/` | attuale | — | Revisione Codex del resoconto di Alfredo con rapporti integrali di Grok e Antigravity, verifica sul pilot corrente e fonti ufficiali; messaggio proposto e divisione ingestion/training/transfer, controesempi analitici. Risultati del teammate riferiti, non replicati; nessun nuovo training, invio o messaggio esterno | — |
| `reports/sorgenti/libera_spazio_2026-10-04/` | attuale | — | Pulizia locale autorizzata il 4/10: ricevute Colab r1/r2, piano chiuso di copie archiviate, SHA256 locale ricontrollato sotto lock prima di ogni rimozione; dipendenze attive, dati unici e copie cloud conservati | — |
| `reports/sorgenti/libera_spazio_2026-10-03/` | attuale | — | Pulizia autorizzata delle sole copie locali archiviate delle vecchie matrici r1/r2: SHA256 locali ricalcolati contro prova Kaggle indipendente, hard link, lista chiusa e ricevute; nessuna cancellazione remota né modifica alla ricerca attiva | — |
| `reports/analisi/revisione_pilot_cellulare_2026-10-03/` | attuale | — | Audit Codex del pilot al commit 05504a1: guardie su due revisioni, salute mancante corretta e confronto incompleto ancora promuovibile; supporto per bersaglio e modalità, limiti della conclusione causale sul numero di contesti. Nessun nuovo training | — |
| `reports/analisi/generalizzazione_contesti_2026-10-02/` | attuale | — | R-LEAD P0–P3 (sessione 22d21f): preflight, manifest degli input con hash, matrice contesto × bersaglio × studio, split per gruppi di linea stabili, esposizioni e storia delle riserve, protocollo congelato prima dei risultati; misure e decisione aggiunte nelle sottocartelle delle corse. Banco di sviluppo, indici sugli effetti non punteggi VCC | — |
| `reports/modelli/rete_cellulare_2026-10-03/` | attuale | — | Rete cellulare versione 2 (sessione 22d21f): copie corrette di cellnet (pesi gerarchici con denominatore fisso, serbatoio per libreria a hash, gruppi di linea interi e fold a hash del banco, classi dopo il QC, braccio generico addestrato, gemello a profilo medio, gate in log-sigmoid) con test; protocollo del pilot congelato prima di ogni training. Nessun risultato al commit del protocollo | — |
| `reports/modelli/risposta_contesto_2026-10-02/` | attuale | — | Codice di ricerca di R-LEAD P0–P3 con test: universo HepG2, inventario, cubo del banco, split, bracci (transfer t25, generico, guadagno per gene, bilineare a basso rango, gemelli senza contesto, scambi, nulli permutati), metriche, regola. Controllo positivo/negativo sintetico; nessuna adozione in produzione | — |
| `reports/gara/dati_arc_2026-10-02/` | attuale | — | Parafrasi del post di Arc del 1/10 sulla produzione dei dati 2026 (dichiarazioni degli organizzatori, non misure nostre), confronto con NTC e profondità misurati su A/B/C, conseguenze etichettate e catalogo delle sorgenti citate. Nessun download, job o invio | — |
| `docs/PROMPT_CLAUDE.md` | attuale | — | Prompt unico per R-LEAD: prova C/J, confronto semplice del contesto e verifiche; dal 3/10 richiama il mandato D-053 di copertura integrale e uso effettivo dei contesti | — |
| `docs/storico/consolidamento_2026-10-03/` | storico | `docs/PIANI.md`, `docs/piani/strategia-scientifica.md` | Copie identiche al byte (sha256 nell'indice) di PROGETTO, PIANI, AMBITI, R-LEAD, R-DATI e R-LAB al commit `36cea0a`, prima del consolidamento della sera del 3/10 (sessione 5eacdf): istruzioni datate della v3, stato dell'ingestione delle 16:00, chiusura di R-DATI precedente a D-053. Non è una coda da riprendere | — |
| `docs/storico/R-LEAD_pre_contesti_2026-10-02.md` | storico | `docs/piani/strategia-scientifica.md` | Copia invariata del piano al commit 0b491b3 prima di D-052; gli ID P0–P6 avevano un significato diverso. Non è una seconda coda di esecuzione | — |
| `docs/storico/rinnovo_2026-10-01/` | storico | `docs/PIANI.md`, `docs/piani/strategia-scientifica.md` | Copie di 18 documenti prima del rinnovo, prose invariate salvo link relativi e fine riga; manifest con hash e commit 3de6cd0. Nessuna coda o assegnazione vigente si ricava dalle copie | — |
| `reports/analisi/rinnovo_repo_2026-10-01/` | attuale | — | Rinnovo richiesto dal proprietario dopo t29: inventario dei depistaggi corretti, script applicati, snapshot/hash e verifiche. Nessun nuovo risultato biologico o training | — |
| `docs/CONSEGNA_TEAMMATE.md` | attuale | — | Addendum portabile: Git, runtime, input esterni e accessi sulla macchina del teammate. Strategia e sequenza soltanto in R-LEAD; t29 concluso | — |
| `docs/PROMPT_CLAUDE_TEAMMATE.md` | attuale | — | Rimando al prompt unico PROMPT_CLAUDE.md con addendum per macchina esterna; vecchio prompt integrale nello storico del rinnovo | — |
| `reports/analisi/handoff_teammate_2026-10-01/` | attuale | — | Inventario portabile della consegna e verifiche sulla macchina di origine; il destinatario deve eseguire i propri check. Nessuna nuova prova del modello | — |
| `docs/checkpoints/0054-visibilita-scorer-e-consegna.md` | attuale | — | Consegna portabile al teammate e correzione della diagnosi ambientale citata da CP-0053: stesso Python, scorer visibile e 287 test passati fuori dal sandbox. Nessuna nuova misura del modello | — |
| `docs/checkpoints/0053-audit-cellnet-e-strategia.md` | attuale | — | Audit riproducibile cellnet e HepG2; D-050 precisa C/J e R-LEAD delinea il programma. CP-0054 precisa soltanto la diagnosi ambientale delle verifiche citate; misure e soglie scientifiche invariate | — |
| `docs/storico/PROGETTO_direzione_2026-09-30.md` | storico | — | Apertura della direzione generale del 30/09, sostituita il 1/10 con D-050/CP-0053; testo conservato salvo i link | — |
| `reports/analisi/lead_audit_2026-10-01/` | attuale | — | Revisione lead con nuove misure riproducibili: split r5/r7, replay di 50.172 batch r2, controesempi unknown/basale/ruoli pre-QC, controlli per libreria e lettura integrale HepG2. Consegna tecnica e D-050; post hoc, nessuna conferma VCC né modifica al training concorrente | — |
| `reports/analisi/lead_audit_2026-10-01/VERIFICHE.md` | storico | — | Fotografia dei check nel sandbox: errori di import osservati confermati, ma non provano che il pacchetto sia assente dalla macchina. CP-0054 e la scheda collegata documentano 287 test passati nello stesso Python fuori dal sandbox | [Correzione scorer](../reports/analisi/handoff_teammate_2026-10-01/VERIFICHE.md#correzione-scorer) |
| `docs/piani/strategia-scientifica.md` | attuale | — | Coda unica del 5/10: banca persistente, rifit lineare t28 e invio diretto autorizzato; stati/PID precedenti conservati nello storico, nessun nuovo worker dichiarato | — |
| `reports/sorgenti/corpus_cellulare_2026-09-30/` | attuale | — | Inventari successivi, contratti, QC, shard, adattatori e job; sorgenti usate nei training cellulari r1–r3. Le vecchie code Colab sono fotografie datate; catalogo, presenza e uso dopo QC sono distinti. Leggere README e manifest della versione effettiva, disponibilità sul destinatario da verificare | — |
| `reports/sorgenti/archivio_cloud_2026-10-02/` | attuale | — | Migrazione dei dati pesanti al cloud del 2/10: inventario per file fisico, specchio su Drive con ricevute, verifiche lato Kaggle e su Colab, copie locali eliminabili solo col via del proprietario, piano d'ingestione. In corso alla prima scrittura; lo stato pesante sta in `processed/archivio_cloud_2026-10-02/` della radice dati | — |
| `reports/modelli/cellnet_terza_ondata_2026-10-01/` | attuale | — | Protocollo tecnico del quarto training, terza ondata e floor pi. Nessun esito registrato; il prossimo job si decide tramite R-LEAD dopo t29, non automaticamente alla riapertura della quota. Non contiene il banco a sei membri richiesto per un altro invio neurale | — |
| `reports/modelli/cellnet_completo_2026-10-01/` | attuale | — | R3: protocollo, lanci ed ESITO.md con misure tecniche/esplorative; identity collassato, diagnosi AGGIORNAMENTO_R3 nell'audit del 1/10. Split diversi da r2; nessuna promozione scientifica | — |
| `reports/modelli/cellnet_esteso_2026-10-01/` | attuale | — | R2: training e parte tecnica misurati, ESITO.md e ricevute; braccio desc usato in t29, non promosso (CP-0055). Correzioni del disegno in NOTA_TRAINING; non confondere il completamento con il successo competitivo | — |
| `reports/modelli/cellnet_tecnico_2026-10-01/` | attuale | — | R1: primo training reale, protocollo/lanci/esiti conservati. ESITO.md: parte A non interamente passata, incidente E-20261001-001. Misura tecnica, nessuna promozione | — |
| `reports/modelli/risposta_biologica_2026-09-30/` | attuale | — | Codice originale cellnet, prepass, descrittori, export e registri usati dai training r1–r3; non più solo una miniatura. H1 train/val ammesse al fit, test riserva chiusa. Diagnosi in lead_audit_2026-10-01: split, controlli, pesi, baseline e gate; nuove correzioni in copie distinte, nessuna promozione implicita | — |
| `reports/analisi/test_orientamento_2026-09-30/` | attuale | — | Protocollo dei test di orientamento degli agenti, scritto prima di qualunque esecuzione: nove compiti, 46 domande con risposta attesa e fonte (`chiave.json`, verificata da `orientamento.py check`), misure, soglia di successo, due versioni con i costi stimati. Non ancora eseguito: aspetta il via del proprietario | — |
| `reports/analisi/pulizia_struttura_2026-09-30/` | attuale | — | La pulizia della struttura del 30/09 sera, a tappe: inventario misurato di worktree, branch e stash con la proposta scritta prima di agire (`inventario_worktree.json`), poi l'esito di ogni tappa | — |
| `docs/AGENTI.md` | attuale | — | Dal 30/09 (D-049): la pagina dell'infrastruttura degli agenti. L'interfaccia con la base di lancio `agent-hub`, che sta fuori dalla repo (autorizzazione, regole del worker, rapporti in `agenti/`); lo stato dei sistemi ritirati il 23/09, con le due attività pianificate di Windows ancora registrate (misurato il 30/09); il coordinamento fra sessioni nella stessa cartella e le lezioni della base di lancio. Instrada, non è evidenza | — |
| `docs/storico/PROGETTO_sezioni_0_6_7_2026-09-30.md` | storico | — | Il preambolo, il §0, il §6 e il §7 di PROGETTO com'erano al commit `1212e2f` (30/09 mattina), tolti con il riordino dell'ingresso (D-049) senza cambiare il testo salvo i percorsi dei link: la cronaca del t28, della rete sulle sorgenti e di Stack, la tabella dei punteggi, il vecchio percorso di lettura. I punteggi stanno ora in `reports/invii/README.md` | — |
| `reports/analisi/ingresso_agenti_2026-09-30/` | attuale | — | Il riordino dell'ingresso degli agenti del 30/09 pomeriggio (D-049): che cosa si leggeva prima e che cosa si legge ora, le sedi canoniche, le duplicazioni tolte, le verifiche dei sei percorsi e i problemi rimasti | — |
| `CLAUDE.md` | attuale | — | Accordo di lavoro, perimetri, letture per compito e regole globali; dal 3/10 riquadro non negoziabile D-053 sulla copertura dei contesti con rinvio alla sede canonica. Niente punteggi o assegnazioni | — |
| `AGENTS.md` | attuale | — | Rimando per Codex a CLAUDE e alle guide di cartella; dal 3/10 richiamo esplicito al vincolo D-053 di copertura integrale. La versione della catena di cicli è nella riga delle skill archiviate | — |
| `docs/AMBITI.md` | attuale | — | Dal 30/09 (D-048): la mappa per ambiti, una sezione per area con stato, letture prime, evidenza e scheda del piano. È un instradamento scritto da un agente dalle fonti che cita: la fonte resta il checkpoint o il report citato | — |
| `reports/analisi/riordino_repo_2026-09-30/` | attuale | — | Il riordino della notte del 30/09: che cosa è stato committato per conto di chi, che cosa è uscito dall'albero e dove sta, con gli hash; che cosa aspetta il proprietario | — |
| `docs/checkpoints/0050-credibilita-score-e-riserva.md` | attuale | — | Correzione: ancore aggregate non esatte su t03/t25; 95/96 target della conferma già valutati storicamente. Aritmetica locale e soglie confermate, nessuna previsione ufficiale dimostrata | [R-022](#r-022--ancore-aggregate-e-indipendenza-della-conferma) |
| `docs/ERRORI.md` | attuale | — | Dal 29/09: guasti operativi trasformati in incidenti immutabili, test di regressione e preflight riusabile dei job; verifica locale distinta da quella remota. Usa le autorizzazioni già presenti, non crea orchestratore o nuove approvazioni. Dal 30/09 (D-048) anche gli errori di metodo già commessi, con fonte, e le trappole operative | — |
| `docs/STRADE.md` | attuale | — | Dal 4/10 (D-055): registro degli approcci provati e non riusciti, una voce per strada con sintomo, meccanismo etichettato (accertato, ipotizzato, ignoto), che cosa la riaprirebbe e segnale precoce; cancello «Precedenti» nei protocolli nuovi e riga «Strade» nei checkpoint di esperimento, verificati da `scripts/31_check_docs.py`. Sintesi scritta da un agente dalle fonti citate: dove il meccanismo non era stato ricostruito è segnato ignoto | — |
| `reports/analisi/lead_scientist_2026-09-29/learning/` | attuale | — | Registro append-only EID con causa/fix/test/evidenza di verifica; indice derivabile, validatore di manifest locali/remoti e test. Gli stati dei cinque incidenti iniziali sono attestazioni circoscritte, non risultati scientifici o autorizzazioni | — |
| `reports/analisi/lead_scientist_2026-09-29/` | attuale | — | Audit e prove Codex: banco generatore su 96 bersagli/3 semi supera la regola registrata, ma 95/96 erano già presenti nei report storici; pendenze globali non sono conversione esatta in VCC (CP-0050). Rete a sorgenti separate sotto soglia in entrambi i semi (CP-0048/0049). Stack A/B negativi, selettore congelato completato dopo ricontrollo numerico 085, nessuna conferma (CP-0051). ERRORI: ledger append-only e preflight applicato localmente/remotamente. Diagnostiche post hoc e limiti espliciti; non risultati VCC | — |
| `reports/invii/prediction_t36_2026-10-06/` | attuale | — | Record runtime congelato prima stage100, copia dopo generazione; nome t36 richiesto dall'utente, nessuna banda numerica inventata e nessun miglioramento presunto | — |
| `reports/invii/trial_2026-10-06/` | attuale | — | Candidato e packaging verificati; testi t36 e output CLI dell'invio quando disponibile. Non dichiarato score | — |
| `reports/invii/prediction_t31_2026-10-06/` | storico | `reports/invii/prediction_t36_2026-10-06/` | Bozza locale mai inviata, conservata; correzione del solo nome richiesta dal proprietario prima upload | — |
| `reports/invii/prediction_t30_2026-10-04/` | attuale | — | Registrazione del t30 (ibrido selettivo D-056: effetti t25 + w · R della rete del fold HepG2, selettore congelato), scritta alle 08:14 UTC prima della lettura degli effetti ibridi e della generazione; banda 0,125–0,160, regola a ±0,005 contro il t25; confronto ufficiale: 0,135249, −0,004989 contro il t25, ramo b non conclusivo, nessuna promozione (CP-0064) | — |
| `reports/invii/trial_2026-10-04/` | attuale | — | Testi del t30 scritti prima della generazione; manifesti dell'esportazione e degli stadi 45 e 48, output di `vcc` salvato così com'è, status pubblicato del t30 (0,135249); catena riletta in `reports/modelli/diagnosi_t30_2026-10-04/esito/chain_t30_r2.json` | — |
| `reports/invii/prediction_t29_2026-10-01/` | attuale | — | Registrazione del t29 (rete R-LAB r2, braccio `desc`, generatore del t22), scritta alle 12:06 UTC prima dell'esportazione degli effetti e della generazione; confronto ufficiale: −0,029625, ramo c della regola (CP-0055) | — |
| `reports/invii/prediction_t28_2026-09-29/` | attuale | — | Registrazione immutata e confronto ufficiale: 0,144845205, delta t25 +0,004607144. Nuovo massimo osservato, non conclusivo rispetto alla soglia +0,005. Sei membri pubblicati verificati; nessuna promozione. Il delta locale +0,028918 non era calibrato; 95/96 target già valutati | — |
| `docs/checkpoints/0052-t28-punteggio-ufficiale.md` | attuale | — | T28 pubblicato: nuovo massimo osservato ma sotto la soglia prefissata; compensazioni fra membri e MSE grezza peggiorata. Conclude il seguito ufficiale senza nuovi invii; piano R-COMP dal passo 2 | — |
| `reports/sorgenti/basali_asse_2026-09-29/` | attuale | — | Azione 5 di R-REV, assegnata a Claude: protocollo del 29/09 per ricalcolare i profili basali sull'asse comune, controllarli dal grezzo e verificare l'impatto sui lettori e sulle quote t23/t27. Registrato durante il lavoro condiviso; non implica che i calcoli siano conclusi | — |
| `reports/README.md`, `reports/*/README.md` | attuale | — | Gli indici dell'evidenza (D-046): che cosa leggere per primo, le otto categorie, il codice di ricerca che altri banchi importano; per ogni categoria una riga per cartella con data, nocciolo, validità e peso. Riassunti scritti da un agente il 28/09 dalle righe di questo registro e dai report: la fonte resta il report citato | — |
| `reports/analisi/revisione_criticita_2026-09-28/` | attuale | — | Revisione critica del 28/09 (Claude, sessione cloud, su richiesta del proprietario): bias di valutazione (proxy di due membri su sei, verità rumorose, molteplicità, rumore ufficiale su una coppia), piattaforma e normalizzazione, evidenza mancante, codice di ricerca non testato, proposte in ordine; e `ALFREDO_VCC_MINI.md`, la valutazione punto per punto delle critiche di Alfredo al suo banco. **Revisione, non misura**: i soli calcoli nuovi sono quelli sul rumore dei punteggi ufficiali | [R-020](#r-020--evidenza-citata-ma-assente-dal-repository) |
| `reports/analisi/sintesi_stato_2026-09-24/` | storico | — | Il report che stava nella radice (`REPORT_2026-09-24_stato_e_interpretazioni.md`), spostato qui il 28/09 senza modifiche: sintesi del 24/09 scritta prima dei punteggi di t16 e t17. Come stato è superato dal §0 di PROGETTO (dice che il migliore è il t15); le interpretazioni dei §3–4 vanno lette con CP-0034 | — |
| `docs/storico/README.md` | attuale | — | Indice di `docs/storico/` (D-046): per ogni documento spostato, data, nocciolo e che cosa vale ancora | — |
| `docs/storico/PROGETTO_sezioni_3_4_2026-09-28.md` | storico | — | Il §3 (misure del 12–17/09) e il §4 (21 incertezze numerate) di PROGETTO com'erano fino al 28/09, spostati senza cambiare il testo salvo i percorsi. Lo stato di ciascuna incertezza al 28/09 è nel nuovo §4 di PROGETTO | — |
| `docs/storico/README_2026-09-11_13.md` | storico | — | Le sezioni del README in inglese dell'11–13/09 (piano per fasi, revisioni, audit dei candidati), spostate il 28/09 senza cambiare il testo salvo i link. Contengono le sei affermazioni contestate della scheda R-001 | [R-001](#r-001--readmemd) |
| `reports/analisi/audit_piani_dati_2026-09-26/` | attuale | — | Audit Codex: riconciliazione di piani e sorgenti, inventario locale e menzioni di accessioni, HIPSCI distinto da KOLF, revisione biologica e controesempio sintetico di contaminazione tramite centratura nel banco appreso r2/r3. Nessun training o score nuovo | — |
| `reports/analisi/biologia_architetture_2026-09-25/` | attuale | — | Ricerca esplorativa CP-0040: riesecuzione con hash degli input, STAT2 su supporto appaiato, geometria con segno, MCF7/TNF, confidenza e riproducibilità CD4; architetture e dati candidati distinti dalle misure. Riconciliazione del proxy MSE con R-018. Nessun training, acquisizione o punteggio VCC | — |
| `docs/checkpoints/0040-biologia-contesti-donatori.md` | attuale | — | Pattern di contesto e limiti della confidenza fra donatori; proposte di ricerca, non modelli promossi. Precisa l'inferenza da MSE proxy a score ufficiale senza modificare r10 | — |
| `docs/PIANI.md` | attuale | — | Indice operativo introdotto il 24 settembre su richiesta del proprietario: piani aperti, dipendenze, coordinamento nella cartella condivisa e rimandi agli esiti passati. Non avvia lavori o automazioni | — |
| `docs/piani/piano-giorno-2026-09-30.md` | attuale | — | R-LAB: inventario corrente di corpus, codice e r1–r3; in attesa del nuovo protocollo R-LEAD per un training. Quarto training storico non in coda automatica; cronologia conservata nello storico | — |
| `docs/piani/` | attuale | — | Schede correnti e guida: R-LEAD unico percorso eseguibile; R-COMP scopo, R-LAB mezzi, R-REV/S-INVII requisiti; R-DATI/R-SWITCH/R-V2 in attesa di una motivazione. R-MODELLI chiusa dal 30/09. Versioni precedenti nel rinnovo storico, agenti confermati fermi dal proprietario | — |
| `reports/analisi/ipotesi_trasferimento_2026-09-24/` | attuale | — | Ipotesi e proposte su programmi, stato cellulare, switch genes, intensità, affidabilità e dati ponte; fonti primarie verificate e confronto STAT2 IFNB/IFNG dalle misure esistenti. Nessun modello addestrato, dataset adottato o protocollo congelato **Vale in parte:** H1 (programmi) e H6 (pesi per somiglianza) sono state provate e sono cadute (`reports/trasferimento/programmi_2026-09-26/`, `reports/trasferimento/contesti_2026-09-26/`); le altre restano aperte. | — |
| `reports/trasferimento/banco_varianti_2026-09-25/` | attuale | — | Banco a sorgente esclusa sulle varianti della ricetta del t15, con proxy di PDS e della fedeltà ricavati dalle note dello scorer. Le esecuzioni r2, r4, r5 e r6 hanno un difetto sull'SE di `cd4_mix`; `CORREZIONE.md`, r7 e r8 danno i numeri corretti: gli effetti ristretti alzano il PDS proxy di +0,01…+0,04 e, a parità di geni rilevabili, battono il t16 nel modello del generatore; γ e consenso non contano; il filtro dei bersagli difficili è respinto. Revisioni di claude2 e grok in `revisioni/`. r10: ampiezza ottima oracolare sul proxy 0,02–0,16, guadagno sul nulla sotto lo 0,11%; l'estensione alla MSE ufficiale e alla sua causa esclusiva è non dimostrata, vedi R-018 e CP-0040. Proxy su sorgenti pubbliche, non punteggi VCC (CP-0039) | — |
| `reports/trasferimento/banco_varianti_2026-09-25/MSE.md` | da-verificare | — | Conservare misure r10 e distinzione modello/calibrazione; qualificare estrapolazione allo score ufficiale, ottimo oracolare, norme dei vettori e confronti di ampiezza | [R-018](#r-018--mse-proxy-e-punteggio-ufficiale) |
| `reports/trasferimento/banco_varianti_2026-09-25/RISULTATI.md` | da-verificare | — | Scritto prima delle revisioni: le colonne ristrette delle tabelle 2 e 4 e la proposta di k 64 vengono da un calcolo difettoso; il resto regge. Leggerlo con `CORREZIONE.md` | [R-017](#r-017--banco-del-25-settembre-effetti-ristretti-ricalcolati-senza-se) |
| `reports/sorgenti/ricerca_sorgenti_2026-09-25/` | attuale | — | Ricerca multi-agente della notte del 25 settembre: provenienza dei log2FC Mixscale (per linea, dedotta dal codice), audit di microglia GSE335887 e dei dati K562 letti con Flex, catalogo completo delle nuove sorgenti (KOLF2.1J e GSE345058 verificati da Claude sulle API pubbliche). In `agenti/` i rapporti integrali; quello di antigravity contiene errori di metodo segnalati nel testo. Candidati, non adozioni | — |
| `reports/sorgenti/pattern_mixscale_2026-09-24/` | attuale | — | Rianalisi esplorativa dei 1.626 confronti Mixscale: eterogeneità per bersaglio/stimolo, differenze appaiate dal controllo, bootstrap per bersaglio e sensibilità senza i dieci maggiori vantaggi. Riusa le misure CP-0035, non i conteggi grezzi; nessun test J o punteggio VCC | — |
| `reports/sorgenti/dld1_ceiling_2026-09-24/` | attuale | — | Esplorativo, completa CP-0035: tetto di riproducibilità dentro DLD-1 (Low1 contro Low2, due metà per corsia) 0,070 di correlazione mediana per bersaglio, contro 0,014–0,027 verso le sorgenti della cache r5, con bootstrap. HCT116 non si distingue da K562 né da CD4. Chiarisce suffissi, righe, colonne e modello delle matrici DLD-1; la base del log resta da verificare. Non è un punteggio VCC | — |
| `reports/sorgenti/schede_sorgenti_2026-09-24/` | attuale | — | Schede di 17 sorgenti candidate nel formato di GENERALIZZAZIONE §2, scritte da un agente (claude2) sui report della ricerca multi-agente della sera, con la seconda verifica di un agente di un'altra famiglia (grok) e i file pubblici DepMap 24Q4. Ogni fatto porta la sua etichetta verificato/da verificare. Candidati, non sorgenti adottate | — |
| `docs/GENERALIZZAZIONE.md` | attuale | — | D-044, C/T/J e leakage; dal 3/10 §2.1 è la sede canonica di D-053: tutte le linee e i contesti idonei, inventario riconciliato, campioni stratificati ed esposizione effettiva obbligatori, pilot distinti. Regole richieste, non controlli runtime dichiarati implementati | — |
| `docs/checkpoints/0036-generalizzazione-bersagli-contesti.md` | attuale | — | CP-0036: cambio di strategia richiesto dal proprietario; J come prova principale per nuovi predittori, baseline dello stesso bersaglio mantenuta | — |
| `docs/checkpoints/0035-dld1-mixscale-audit.md` | attuale | — | CP-0035: copertura DLD-1 misurata e primo confronto descrittivo fra sei linee Mixscale. Nessuna sorgente adottata. Corretto da CP-0036, §7: la copertura dei bersagli attuali non è un criterio di ammissione alla ricerca, e il confronto fra linee è distinto dalla generalizzazione a bersagli nuovi | — |
| `reports/sorgenti/dld1_audit_2026-09-24/` | attuale | — | Audit esplorativo delle matrici Low1 DLD-1 già scaricate: manifest verificato, 67/300 bersagli, 2.587/18.533 geni ufficiali, confronto con K562 su 61 bersagli. Inventario Mixscale e piano per contesti nuovi. `r1/` contiene le misure; `source_inventory/` conserva la copertura DLD-1 prima di un errore di permessi sulla cartella dati, `source_inventory_r2/` il tentativo con accesso autorizzato. Non è una sorgente adottata né un punteggio VCC | — |
| `reports/analisi/analisi_2026-09-24/` | attuale | — | Analisi dello stato chiesta dal proprietario, scritta **prima** dei punteggi di t16 e t17. `ANALISI.md` legge il codice dello scorer 0.16.0 e i report esistenti; `calcoli.json` tiene i conti. **Interpretazioni, non misure nuove**: la MSE dei nostri effetti implica un coseno con la verità intorno a 0,04; l'artefatto del generatore di trial-01 (429–675 chiamate a effetto nullo) ha una precisione di segno stimata di 0,44 contro 0,53 delle chiamate da effetti; le previsioni per il t16 sono al §4. Propone correzioni a §0 della mappa e a D-042, non applicate **Vale in parte:** il confronto delle precisioni di segno va letto contro il controllo a bersagli scambiati, perché il 50 % non basta come riferimento (`reports/analisi/audit_stato_2026-09-24/ANALISI.md`, §1; CP-0034). | — |
| `reports/analisi/audit_stato_2026-09-24/` | attuale | — | Audit esplorativo riproducibile della cache r5: controlli dei segni a bersagli scambiati, confronto fra metà CD4, confronto delle ampiezze t17/t15 e proposte per il set finale. Include script, misure per bersaglio e limiti. Non è un punteggio VCC (CP-0034) | — |
| `docs/checkpoints/0034-audit-segni-e-ampiezza.md` | attuale | — | CP-0034: distingue specificità dei segni, prevalenza e rumore; precisa due interpretazioni di CP-0033 e la lettura causale del t17. Nessuna ricetta modificata | — |
| `reports/trasferimento/direzione_2026-09-24/` | attuale | — | Stadio 103 sulla cache r5. **Misura nello spazio degli effetti, non un punteggio**: tenendo fuori ogni sorgente come contesto nuovo, il segno della miscela delle altre coincide con il suo sui geni con l'effetto previsto più grande nel 51–56% dei casi (mediana per bersaglio, primi 25–500 geni); il consenso fra sorgenti porta al 52–56%; la centratura γ = 1 non aiuta e per HCT116 peggiora (0,48 contro 0,56). Scritto dopo CP-0032 | — |
| `reports/invii/trial_2026-09-24/` | attuale | — | Il t15 (il t11 con ampiezza 0,394): diagnostica e manifesti degli stadi 45 e 48, generati il 24 settembre alle 00:57–01:17Z. Convalida superata, payload identico bit per bit all'input, archivio sha256 `fb532e7a…cb27`. L'invio aspetta il via del proprietario. **Invio del t15** alle 10:28Z (`submit_U1K3SZuq7w5cef9lBKsn.json`, `status_U1K3SZuq7w5cef9lBKsn.json`, `submit_t15_*`): +0,107533, rango 436. `submission_texts.md`: testi di t16 e t17, scritti prima della loro generazione. t16 e t17 generati e impacchettati il 24 fra le 11:23 e le 12:34Z (`t16_*`, `t17_*`): convalida superata, payload identico bit per bit, archivi sha256 `467275ae…` e `6fdcb577…`. **Invii del 25 settembre** dalla catena `submit_chain.py` (`submit_t16_*`, `submit_t17_*`): t16 +0,137627, rango 336 (entry `qUV1D6QZh2tZ5Z9Vx185`); t17 +0,108774, rango 448 (`status_4su3dF6Up12QhdCfnNgE.json`). Lo stato del t16 non è leggibile: `vcc status` serviva solo l'ultimo invio (`status_qUV1D6QZh2tZ5Z9Vx185_tentativo1_errore.txt`). Intermedi di t16 e t17 nel Cestino il 25 alle 03:24 | — |
| `docs/PROCEDURE.md` | attuale | — | Documento operativo: pipeline, invii, Colab, stadi, dati e preflight. Fino al 30/09 si chiamava `docs/LAVORO.md`, nome che checkpoint e report continuano a citare (ARCHIVIO, «Nomi cambiati»). Corretto il 29/09 il §2: leggere i sei scalati pubblicati, le ancore aggregate non convertono esattamente i grezzi. Descrive procedure, non risultati | [R-022](#r-022--ancore-aggregate-e-indipendenza-della-conferma) |
| `docs/ARCHIVIO.md` | attuale | — | Che cosa la pulizia del 23 settembre ha tolto dall'albero (D-040): 244 file, 50.306 righe, in sei gruppi, con righe e prima riga del docstring di ogni file, il tag `archivio/pre-pulizia-2026-09-23` e il comando di recupero. Il controllo documentale accetta i percorsi elencati lì, e solo quelli. Dal 24 settembre ha una seconda sezione, la pulizia di D-043, con il tag `archivio/pre-pulizia-2026-09-24`, e una terza sui branch ritirati nell'unificazione su `main`. I tag sono anche su GitHub | — |
| `docs/CLAUDE.md` | attuale | — | Dal 30/09 (D-049) la mappa delle sedi canoniche: dove vive ogni tipo di informazione e come si scrive nei documenti. Prima: Guida della cartella per gli agenti, aggiunta il 24 settembre (D-043): i documenti che reggono il progetto, le analisi dell'11–15 settembre e le regole della cartella | — |
| `reports/CLAUDE.md` | attuale | — | Guida della cartella per gli agenti, aggiunta il 24 settembre (D-043): come si scrive e come si trova l'evidenza, e che cosa lascia un invio, con l'esempio del t15 | — |
| `src/vcc2026/CLAUDE.md`, `scripts/CLAUDE.md`, `configs/CLAUDE.md`, `tests/test_live_tree.py` | attuale | — | Aggiunti il 24 settembre (D-043). Le guide danno la mappa dei moduli, con gli stadi che importano ciascuno, gli stadi per ruolo e le regole di uno stadio e di una ricetta. Il test fallisce se le tabelle degli stadi (`docs/PROCEDURE.md` §4) e dei moduli, l'albero del repository in `CLAUDE.md` o l'indice di `reports/` non corrispondono all'albero, se una definizione di `src/vcc2026` non ha un chiamante vivo o se un file importa un nome che non usa. Una prova a mutazione su una copia dell'albero ha verificato che sei guasti diversi lo fanno fallire | — |
| `reports/sorgenti/multisource_2026-09-22/` | attuale | — | Script 98. `PRIMA_DEI_RISULTATI.md` fissa la regola della ricetta t08 **prima** che esista un numero su CD4, con due emendamenti datati. `transfer.json`/`coverage.json` alla radice sono il **primo run, difettoso** (effetti CD4 ridotti a zero da un pavimento sbagliato dell'errore standard; proxy di discriminazione bloccata a 0,5): restano come evidenza, non si usano. `r2/` è il run corretto; `r3/` lo riproduce e aggiunge la miscela CD4 grezza nella cache. **Misura (r3):** fra K562 e CD4 sui bersagli del pannello, discriminazione ~0,67–0,69, correlazione per gene ~0,02, accordo di segno 55,5% sui geni \|z\| > 3 di K562; mediare le sorgenti non alza la discriminazione. Proxy nello spazio degli effetti, non punteggi VCC | — |
| `reports/sorgenti/orion_2026-09-23/` | attuale | — | Script 102 (Orion HCT116/HEK293T, pseudobulk per lotto GEM, licenza CC-BY-NC-SA-4.0). `PRIMA_DEI_RISULTATI.md` fissa la regola del t11 (t08 + Orion, pesi uguali, criterio d'arresto) **prima** di qualunque numero su Orion. `manifest_HEK293T.json` (stadio 102, 05:19Z: 300 bersagli, 2.392 righe) e `r5/` (stadio 98 con HCT116 e HEK293T, 13:22Z) sono output registrati il 23 settembre **senza essere ancora stati letti** | — |
| `reports/invii/trial_2026-09-23/` | attuale | — | Il t10 (il t08 senza CD4): testi della sottomissione scritti prima dell'invio, manifesti, output verbatim di `vcc` (entry `JvksJS5r08YNOP6jfP4Q`, +0,0502, rango 570). Il t11: tre tentativi d'invio, **nessuna entry valutata** — `create_failed` alle 02:11Z, upload interrotto dal sonno del portatile e annullato, terzo tentativo uscito con `exit 1` alle 13:23:45Z senza output catturato (`submit_t11_*`); alle 14:29Z `vcc whoami` dà `can_submit: true` (`whoami_after_t11_attempt3.json`) **Aggiornamento, sera del 23:** il quarto tentativo (`vcc submit --resume` sulla stessa entry, autorizzato dal proprietario in chat) completa l'upload; md5 verificato dal server; **+0,070777, rango 560** (`submit_FEBhtilNLpSm2kGiHB71.json`, `status_FEBhtilNLpSm2kGiHB71.json`, `submit_t11_attempt4_*`). Il t12: testi della sottomissione scritti prima della generazione. `t14_generation.json`: diagnostica dello stadio 76 per il t14 (360.000 cellule, 2.086.386.939 valori, 35 minuti sul portatile). Il t14: testi scritti prima, manifesti dello stadio 48 (`t14_*`), invio alle 00:05Z del 24 (`submit_QiuBir8wNfqDnVdDxqTB.json`, `status_QiuBir8wNfqDnVdDxqTB.json`, `submit_t14_*`): +0,064892, rango 564 | — |
| `reports/invii/trial_2026-09-22/` | attuale | — | Il t08: testi della sottomissione scritti prima dell'invio, manifesti di generazione e di impacchettamento, autorizzazioni del proprietario, output verbatim di `vcc submit` e `vcc status` (entry `NNUXtdhV4ByiETbolCKJ`, +0,0604, rango 547) | — |
| `reports/generatore_e_banchi/dispersion_2026-09-23/` | attuale | — | Generatore di trial-01 con dispersione per gene (`sampling.fit_gene_dispersion`, stadio 45 `--gene-dispersion`). `PRIMA_DEI_RISULTATI.md` fissa la regola del t13 (controllo nullo con criterio d'arresto, scelta dell'ampiezza per chiamate) **prima** dei piloti. `RISULTATO_NULLO.md`: a effetto nullo 5 / 15 / 31 chiamate mediane in A / B / C, sopra la soglia di 10 in B e C, quindi il t13 **non si costruisce**. `PRIMA_T14.md`: regola del t14, scritta prima dei piloti. `T14_IN_LOCALE.md`: t09 e t14 sul portatile per scelta del proprietario, scritto prima dei piloti. `t14_pilots/`: **misura**, `ControlModel` fa 0 chiamate mediane a effetto nullo in A/B/C; 4,5/16,5/20 ad ampiezza 1, 140/235/261 a 2,5; la regola sceglie 2,5 | — |
| `reports/generatore_e_banchi/prediction_calls_2026-09-23/` | attuale | — | Stadio 83 sul file del t11 (generatore di trial-01), 20 bersagli per contesto, 9.200 controlli di riferimento. **Misura:** n_pred mediano 543 / 582 / 764 in A / B / C, l'83–85% «in su». Con n_conf mediano stimato a 30–50 (docstring dello scorer), la fedeltà di questa famiglia è la precisione delle chiamate spurie del generatore. `t14/`: stadio 83 sul file completo del t14 (`ControlModel`, effetti del t08 × 2,5): n_pred mediano 136,5 / 213 / 218 in A / B / C, il 43–52% «in su», coerente con i piloti. `t15/`: n_pred mediano 804 / 730 / 1.009 in A / B / C, l'81–86% «in su» | — |
| `reports/invii/prediction_t18_2026-09-25/` | storico | — | Previsione del t18 (il t16 con ampiezza 1,576, un solo fattore) registrata **prima** della generazione, il 25 settembre alle 01:30 UTC: banda +0,12…+0,17, regola di lettura contro il t16 (sale: 3,152; scende: 1,114; altrimenti si tiene 0,788) | — |
| `reports/invii/prediction_t19_2026-09-25/` | storico | — | Previsione del t19 (il t16 con lo `shrunk` della cache, k 4, all'ampiezza 1,576) registrata **prima** della generazione, il 25 settembre alle 01:37 UTC: banda +0,12…+0,165, regola di lettura contro il t16; t19 − t18 riportato solo come descrizione (CP-0039) | — |
| `reports/invii/trial_2026-09-25/` | storico | — | Testi di t18 e t19 scritti prima della loro generazione. t18 e t19 generati e impacchettati il 25 fra le 01:45 e le 03:05Z (`t18_*`, `t19_*`): convalida del contenitore superata, payload identico all'input, archivi sha256 `655f674a…a166` e `bc492e3a…b5e7`. L'invio aspetta il via del proprietario | — |
| `reports/trasferimento/modulo_cis_2026-09-26/` | attuale | — | Modulo cis CRISPRi: la repressione dei geni con il TSS vicino a quello del bersaglio, prior dal K562 genome-wide senza i bersagli del pannello, aggiunto al trasferimento. Su sorgenti tenute fuori, forma t19, due volte la mediana entro 5 kb: PDS proxy +0,0024…+0,0061 (r2) e +0,0012…+0,0048 col modello del generatore (r3), vicini mescolati a zero; sostituire il valore trasferito perde. Proxy, non punteggi VCC | — |
| `reports/trasferimento/programmi_2026-09-26/` | attuale | — | Proiezione dell'effetto trasferito sui programmi imparati dalle sorgenti predittrici (ipotesi H1, forma lineare): perde PDS proxy a ogni rango, −0,02…−0,22, con controllo a base casuale. Proxy, non punteggi VCC | — |
| `reports/trasferimento/bersagli_nuovi_2026-09-26/` | attuale | — | I 300 del pannello trattati da bersagli nuovi, esclusi da ogni addestramento: il modello lineare con embedding dei geni non discrimina nemmeno in campione (r2); cis da solo 0,555–0,579 di PDS proxy; 0,1 × STRING + cis +0,009…+0,035 (r3), confermato da r4 con la media dei partner corretta (gene proprio di ogni partner escluso); stesso bersaglio misurato in K562 0,711–0,755. r1 confronta bracci con e senza la risposta comune: i confronti puliti sono in r3. Proxy, non punteggi VCC | — |
| `reports/sorgenti/universo_2026-09-26/` | attuale | — | Cache di tutti i bersagli delle sorgenti genome-wide sull'asse ufficiale, con la stima dello stadio 98: K562 (9.866 bersagli, `r1/`) e CD4 genome-wide (`CD4.md`, `cd4_universe.py`, `r2/`: 12.238 bersagli, parità esatta con la cache del pannello sui 293 del pannello); Orion HCT116 e HEK293T (`ORION.md`, `orion_universe.py`, pilota su 4 file in `orion_pilot/` con parità esatta con gli stadi 102 e 98; HCT116 finalizzato il 26/09 alle 21:37: 16.438 bersagli con effetti su 18.293, parità esatta con la cache r5 sui 268 del pannello, `orion_hct116/`; HEK293T finalizzato il 27/09 alle 01:44: 17.270 bersagli con effetti su 18.311, parità esatta con la cache r5 sui 281 del pannello, `orion_hek293t/`; esito delle due linee in fondo a `ORION.md`); K562 essential (2.057 bersagli) e RPE1 (2.393) di Replogle, con lo stesso `k562_universe.py` e `--name` (`k562_essential/`, `rpe1/`), per il confronto descrittivo dell'atlante; script, indici e manifest, i blocchi stanno nella radice dati **Vale in parte:** gli universi di CD4 e delle due Orion sono sostituiti da quelli ricostruiti con lo stimatore corretto (`reports/sorgenti/universo_corretto_2026-09-27/`); K562, K562 essential e RPE1 valgono. | — |
| `reports/sorgenti/universo_corretto_2026-09-27/` | attuale | — | Script per ricostruire gli universi CD4, HCT116 e HEK293T con lo stimatore corretto (`min_expected`), dagli stessi ingressi e con gli script del 26/09 invariati; parità contro la cache r9. HCT116, HEK293T e CD4 fatti, parità esatta sui bersagli del pannello (`RISULTATI.md`) | — |
| `reports/sorgenti/universo_kolf_2026-09-27/` | attuale | — | Ingestione di KOLF2.1J (Figshare+ 27261219, CC BY 4.0, h5ad di 189 GB) senza scaricarlo: `kolf_sums.py` somma i conteggi grezzi per (bersaglio, gruppo di canali) leggendo per blocchi di geni a intervalli di byte, eseguibile in più sessioni (locale, Colab, Kaggle); scritto da codex con la base di lancio (note in `agenti/`), test in `tests/test_kolf_sums.py`. Eseguito: il passo `obs` (27/09, 14:44–14:58) dà 92.636 gruppi (11.688 bersagli per 8 gruppi di canali, 146.747 cellule di controllo) e 17.971 geni dell'asse, 80,9 GB da leggere; `run_blocks.py` li legge in 32 blocchi; `kolf_effects.py` (claude2; `--name` e `--context` di codex) ne fa l'universo con lo stimatore corretto. Fatto il 27/09 sera: 10.985 bersagli su 11.687 con effetti (`effetti_me1/`); il gene bersaglio scende (mediana −0,83, `effetti_me1/controllo_bersaglio.json`) | — |
| `reports/sorgenti/universo_hipsci_2026-09-27/` | attuale | — | Scaricamento dei record HIPSCI CRISPRi da Figshare (26819743 e 27989294, MIT, 17 GB) con verifica md5 file per file, col via del proprietario del 27/09; `hipsci_sums.py` e `hipsci_check.py` (codex, autoverifiche 10 e 4 su 4) portano i tre schermi nel formato delle somme, per linea nel mirato **Vale in parte** secondo l'indice di `reports/sorgenti/`: le linee con silenziamento debole vanno trattate a parte, e gli universi `_ua1`, che usano come controlli anche le cellule senza guida assegnata, possono tirare gli effetti verso zero (interpretazione). | — |
| `reports/sorgenti/universo_nuovi_2026-09-27/` | attuale | — | Ingestione generica di schermi a cellula singola scaricati (h5ad compresso, righe per cellula): `h5ad_sums.py` somma i conteggi grezzi per (bersaglio, gruppo di lotti) nel formato di `kolf_sums`, così lo stesso passo di stima (`../universo_kolf_2026-09-27/kolf_effects.py`) serve ogni sorgente; provato su dati sintetici. Usi: A549 (job 048), Southard Hs27 e RPE-1 (job 049 e 050); `on_target_check.py` e il controllo sul bersaglio di sei universi in `RISULTATI.md` | — |
| `reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/` | attuale | — | Azione 4 di R-REV: il banco con lo scorer vero sui bersagli del pannello (verità K562 dallo stadio 71, sorgenti senza K562), bracci che separano esclusione, pesatura e riscalatura del t23, la soglia del t26 e le ampiezze; controlli di validità contro i membri ufficiali di t23 e t26; protocollo e regola fissati alle 18:10 del 29/09 prima di scrivere il codice dei bracci | — |
| `reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/` | attuale | — | Input del banco HepG2 con lo scorer vero (stadio 75, job Colab `046_bench_hepg2_v2`): effetti di produzione in forma t16/t19/t20 solo-K562 per 300 bersagli HepG2, e il solo modulo cis. r1 del 27/09 (job 046): membri scalati e contrasti appaiati in `RISULTATI.md` e `r1/`, descrittivi (nessuna regola registrata) | — |
| `reports/invii/prediction_t20_2026-09-26/` | attuale | — | Previsione del t20 (t19 + modulo cis) registrata **prima** della generazione, il 25 settembre alle 22:04 UTC: banda +0,115…+0,17, regola di lettura contro il t19 (±0,005, lettura di non inferiorità nel caso intermedio). `comparison.json`: +0,139676, t20 − t16 = +0,0020, non conclusivo; il t19 non è stato inviato | — |
| `reports/invii/trial_2026-09-26/` | attuale | — | Testi del t20 scritti prima dell'invio, dopo la registrazione e durante la generazione. t20 generato e impacchettato il 25 fra le 22:05 e le 22:55Z (`t20_*`): convalida del contenitore superata, payload identico all'input, archivio sha256 `e80e135a…a16b`. Inviato il 26 alle 00:06Z con il via del proprietario (solo t20): +0,139676, rango 346 (`status_I8FX2yQabjKjPPDTYnaW.json`). t22 generato e impacchettato il 26 (`t22_*`, commit 3b67189), inviato il 26 alle 23:06Z con il via del proprietario e valutato alle 23:40Z: +0,141250, rango 337 (`submit_t22_*`, `status_hOy1AirAxJsFvpQAHH15.json`) | — |
| `reports/invii/trial_2026-09-27/` | attuale | — | Testi del t23 (27 settembre, 01:15, durante la generazione) e del t24 (02:02, prima della generazione), scritti dopo la registrazione e prima dell'invio. t23 generato e impacchettato il 27 fra le 01:14 e le 02:41 (`t23_*`): convalida del contenitore superata, payload identico all'input, archivio sha256 `2805aea8…3a07`. t24 (seme 20260927, effetti del t22) generato fra le 02:42 e le 03:22 e impacchettato alle 12:02 (`t24_*`; il portatile è stato in sospensione dalle 03:23 alle 11:43, da qui i 30.981 s dello stadio 48): convalida del contenitore superata, payload identico all'input, archivio sha256 `757fd597…1fec`. t25 impacchettato il 27 alle 14:57 (`t25_*`: convalida del contenitore superata, payload identico all'input, archivio sha256 `019ffd70…cbaf`), testo d'invio scritto alle 14:58. Gli invii aspettano il via del proprietario, che per ora li ha sospesi Invio del t23 il 28/09 alle 22:05–22:37 UTC con il via del proprietario (`submit_t23_*`, `status_JvKSI2yE5zdnw4Agghvy.json`) | — |
| `reports/trasferimento/rete_2026-09-26/` | attuale | — | Lisciamento del t20 con la risposta media dei partner fisici STRING (K562, bersaglio escluso) sui bersagli misurati: +0,0002…+0,003 di PDS proxy, solo CD4 a λ 0,1 con intervallo sopra zero; il braccio vero supera sempre il controllo mescolato; r2 rifà r1 con la media dei partner corretta, stesso esito. Proxy, non punteggi VCC | — |
| `reports/trasferimento/risposta_comune_2026-09-26/` | attuale | — | La risposta condivisa da tutti i knockdown (media sui bersagli) vale l'1–14 % dell'energia nelle sorgenti pubbliche tenute fuori e non si trasferisce fra linee (correlazione per gene 0,05–0,11); aggiungerla al t20like non abbassa l'errore quadratico (0,998–1,000 del nullo) e toglie PDS proxy (−0,008…−0,082). Proxy su previsioni del banco r5, non punteggi VCC r2: la `mse` ufficiale grezza dei sei invii col generatore del trial-01 segue 1 + E/4786, con E l'energia prevista nello spazio dello scorer (scarto massimo 0,048): le previsioni sono quasi ortogonali agli effetti reali. Analisi del membro di claude2 in `agenti/` | — |
| `reports/trasferimento/taratura_proxy_2026-09-28/` | attuale | — | Azione 2 di R-REV: il proxy dei banchi (0,36 ΔPDS_gen − 0,27 ΔnMAE_gen) contro il segno delle quattro differenze ufficiali sopra il rumore, con le ricette ricostruite esatte e HEK293T come verità; regola fissata alle 18:45 del 28/09 prima di girare. Esito (r1, 19:28): non passa, due coppie su quattro lette (CP-0041) | — |
| `reports/trasferimento/quattro_sorgenti_2026-09-26/` | attuale | — | Il t20 con HEK293T come quarta sorgente genome-scale: sulle sorgenti tenute fuori che lasciano entrambe le Orion come ingressi, 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen = +0,011 (+0,006…+0,016) con K562 fuori e +0,001 (−0,006…+0,009) con CD4 fuori; regola fissata alle 15:30 prima del banco, superata a pesi uguali, non a metà peso per studio. Origine del t22. Proxy, non punteggi VCC | — |
| `reports/trasferimento/atlante_2026-09-26/` | attuale | — | Banco dell'atlante: trasferimento provato su migliaia di bersagli fuori dal pannello per linea tenuta fuori, con gli universi genome-wide come ingressi (varianze del modello gerarchico e programmi di risposta stimati su migliaia di bersagli, accordo per bersaglio). Regola fissata alle 19:15 (aggiunta alle 19:19) prima di eseguirlo; `shared_response.py` descrive che cosa condividono due linee, per gene e per knockdown: su 8.423 bersagli K562×CD4 fuori dal pannello il coseno fra i profili ha mediana 0,009 (si trasferiscono Mediator, TFIID, Integrator, NMD; non ribosoma e proteasoma), e i geni condivisi sono in buona parte bersagli di ATF4 e trascritti mitocondriali (`condivisione_r1/`); `panel_strength.py`: i bersagli del pannello sono knockdown di forza tipica (percentile mediano 0,54 nel K562, 0,59 nel CD4; `forza_pannello/`); linea, laboratorio e stato sugli stessi 1.242 bersagli (`condivisione_r2/`, `condivisione_r3/`, `confronto_r1/`): coseno mediano 0,254 fra stati di CD4, 0,160 fra due esperimenti K562, circa 0,07 fra RPE1 e K562, 0,019 fra K562 e CD4 a riposo a parità di cellule. **r1** (27/09, K562, CD4 e HCT116 tenuti fuori, 1.000 bersagli ciascuno): nessun braccio passa la regola; il più vicino è `share_atlas` (+0,008 e +0,009 con l'intervallo sopra zero con CD4 e HCT116 fuori, −0,0002 con K562 fuori); programmi e accordo per bersaglio perdono su tutte le linee. **r2** (27/09, con HEK293T, quattro linee tenute fuori): replica riportata, non decide; `share_atlas` +0,0055 e +0,009 con l'intervallo sopra zero con HCT116 e HEK293T fuori, nullo con K562 e CD4 fuori. Con CD4 fuori la quota stimata anche su HEK293T si appiattisce (mediana 0,991 contro 0,687 di r1), ma r2 cambia anche base e bersagli di prova e non separa le cause. Proxy e descrizioni, non punteggi VCC | — |
| `reports/trasferimento/quota_condivisa_2026-09-27/` | attuale | — | La quota condivisa per gene (il braccio più vicino dell'atlante r1) provata sui 300 bersagli del pannello, con le varianze stimate sugli universi senza la sorgente tenuta fuori; ipotesi nuova suggerita da r1, regola pubblicata alle 00:25 del 27/09 prima di eseguire. **Passa**: Δ +0,012 con CD4 fuori e +0,013 con HEK293T fuori (intervalli sopra zero), +0,005 con HCT116 fuori, −0,002 con K562 fuori; origine del candidato t23. `t23_share.py` e `t23/`: la quota della ricetta t23, stimata su K562, CD4 e HCT116 fuori dal pannello (8.247 geni a 0). Proxy, non punteggi VCC **Vale in parte:** l'ablazione del t23 attribuisce il guadagno all'esclusione dei geni, non alla quota (`reports/trasferimento/ablazione_t23_2026-09-27/`). | — |
| `reports/sorgenti/pseudoconteggio_2026-09-27/` | attuale | — | L'artefatto del pseudoconteggio costante di `effects_from_pseudobulk`: un gene senza conteggi in entrambi i gruppi vale ln(L_c / L_t). In CD4 i sei geni Y delle donatrici risultavano indotti dal 99–100 % dei knockdown del pannello (5,3–5,5 % dell'energia pesata del t22 sui geni espressi in A e C); in HCT116 315 geni vicini a 1 CPM. Correzione tenuta: `min_expected` 1 (r9), che scarta per gene il donatore i cui controlli prevedono meno di un conteggio; tre alternative misurate e non usate (r6, r7, r8). Parità: default identico byte per byte (t22 e le nove cache di r5). Origine del t25. Rivisto da grok (`agenti/revisione_grok.md`): tre numeri corretti, prova dei byte uguali in `parita_sha256.txt`, distorsione residua calcolata (+0,17 a un conteggio atteso) e due punti aperti. Misure sugli effetti, non punteggi VCC | — |
| `reports/trasferimento/ablazione_t23_2026-09-27/` | attuale | — | Il t23 smontato sul pannello: esclusione dei geni non stimabili, pesatura per gene e riscalatura, ognuna contro le altre, con il codice del banco sul pannello. Regola fissata prima di eseguirlo; r1 sulla cache r5, r2 (replica) sulla cache r9. **r1:** l'esclusione dei geni non stimabili passa la regola (positiva sulle quattro sorgenti), la pesatura oltre l'esclusione no, e passa il contrario della riscalatura (riscalare peggiora il proxy, che però non vede i membri DE). Proxy, non punteggi VCC | — |
| `reports/sorgenti/profondita_silenziamento_2026-09-27/` | attuale | — | Esplorazione: la risposta a valle di un bersaglio cresce con la profondità del silenziamento del suo gene, da una linea all'altra? Pendenza e correlazione fra log-rapporti di energia e di profondità sui bersagli condivisi da coppie di universi (`depth_energy.py`); nessuna regola di decisione | — |
| `reports/analisi/revisione_codex_2026-09-27/` | attuale | — | Revisione di codex del 27/09 (girata dal proprietario), riassunta punto per punto con la risposta: sei punti accettati (atlante = regime C; t23 mescola esclusione, pesatura e riscalatura; «i modelli complessi hanno perso» troppo generale; coseni fra linee confusi; t24 con una coppia di semi è debole; HIPSCI = un solo tipo cellulare) e tre consegne con chi le fa. Revisione, non misura | — |
| `reports/trasferimento/trasferimento_gerarchico_2026-09-26/` | attuale | — | Trasferimento gerarchico con Bayes empirico (risposta condivisa + deviazione di linea + rumore, varianze per momenti, SE di CD4 gonfiato per i donatori): nessun braccio passa la regola fissata alle 15:20; con due o tre linee la varianza condivisa è piccola e mal stimata e le Orion perdono PDS (−0,015…−0,018). Revisione di codex in `agenti/` (nessuna perdita; conteggio dei bersagli nella fusione per fasce da correggere, corretto nel modulo). Proxy, non punteggi VCC | — |
| `reports/sorgenti/ricerca_sorgenti_2026-09-26/` | attuale | — | Catalogo: HIPSCI CRISPRi (Feng et al. 2025; 7.226 bersagli, 34 linee iPSC da 26 donatori; Figshare 26819743 e 27989294, MIT, 9,1 e 7,9 GB, verificati da Claude sull'API) e ciò che dicono le pagine pubbliche della gara (zero della `mse` 0,986–0,992 = risposta media del contesto). Rapporto integrale di grok in `agenti/`, nomi utente privati oscurati. Nessun download | — |
| `reports/sorgenti/ricerca_sorgenti_2026-09-27/` | attuale | — | Ricerca di dati con gli stessi geni perturbati in molti tipi cellulari: antigravity (solo risultati di ricerca) e verifica di grok sulle pagine primarie, rapporti integrali in `agenti/`; nessun dataset pubblico con cinque o più tipi cellulari (VIPerturb-seq genome-wide è solo K562; HyperMapDB sono previsioni). Struttura di KOLF2.1J letta a intervalli di byte (CSC per gene, senza compressione) e piano d'ingestione dei candidati autorizzati dal proprietario | — |
| `reports/modelli/modello_contesto_2026-09-27/` | attuale | — | Disegno di un modello bersaglio × contesto (claude2, base di lancio) con la letteratura verificata da grok sulle fonti primarie: un modello a cancelli sul trasferimento, con il contesto letto solo dai controlli, e la prova E1 + E2 che lo usa. Proposta e letteratura, nessuna misura | — |
| `reports/modelli/rete_contesti_2026-09-27/` | attuale | — | La rete su molti contesti (F10 di R-V2), disegno e codice di claude2 dalla base di lancio, scritti senza poter eseguire nulla: parte dal trasferimento calibrato e impara correzioni per bersaglio e contesto, il contesto letto solo dai controlli; controlli cieco, scambio, E2 e regime J; `DISEGNO.md` (proposta, con la regola da registrare), `data.py`, `pool.py`, `net.py`, `train.py` (autoverifica sintetica, da eseguire dove c'è torch), `score_pred.py`, `adapter_ctj.py` | — |
| `reports/invii/lezioni_invii_2026-09-28/` | attuale | — | Che cosa insegnano i nostri 13 invii valutati (raccolti dagli stati salvati: coppie a un fattore contro il rumore del seme misurato dal t24, bande registrate contro esiti) e la classifica pubblica in soli aggregati, senza nomi: il divario maggiore coi primi 100 è l'MSE **Vale in parte:** l'audit del 29/09 ne corregge il rumore stimato da una sola coppia di semi e il peso della risposta comune sull'MSE (`reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md`, §2.2 e §2.4). | — |
| `reports/sorgenti/corpus_basale_2026-09-28/` | attuale | — | Corpus di profili basali (solo controlli) sull'asse ufficiale per pre-addestrare l'encoder di contesto: controlli delle nostre sorgenti CRISPRi (con le 19 linee HIPSCI), A/B/C, DepMap e Tahoe DMSO; `SORGENTI.md` con la decisione per ciascuna sorgente (ruolo, sottoinsieme, integrazione, che cosa è girato, ostacolo) | — |
| `reports/modelli/encoder_contesto_2026-09-28/` | attuale | — | Encoder di contesto pre-addestrato a ricostruire geni mascherati da profili basali e innestato nella rete senza modificarne i file (claude2, codice scritto senza eseguirlo); autoverifica su Kaggle 17 su 17 (rete 14 su 14); regola della prima tornata registrata alle 03:10 del 28/09 in `RISULTATI.md`, prima di qualunque corsa sui dati veri | — |
| `reports/sorgenti/tahoe_dmso_2026-09-28/` | attuale | — | Controlli DMSO di Tahoe-100M: `extract_dmso.py` (codex, tutti i frammenti con piano preliminare, lanciato su Kaggle) e `extract_dmso_subset.py` (un frammento ogni k, letture parallele a intervalli di byte, verificato al bit su un frammento); `LAYOUT.md` con i contratti del dataset | — |
| `reports/modelli/tahoe_bracci_2026-09-28/` | attuale | — | I bracci farmacologici di Tahoe-100M come perturbazioni in molti contesti (codex, esecuzione `20260928-032819-v2-tahoe-arms`): estrattore per linea × piastra × farmaco × dose con il DMSO della stessa piastra, stima degli effetti con lo stimatore degli universi, selezione di 73 farmaci (bersaglio unico silenziato anche dagli schermi CRISPRi, più controlli positivi) e il disegno dei banchi T1 (differenze fra linee tenute fuori) e T2 (ponte con il knockdown). Autoverifiche sintetiche passate; proposta, nessun risultato | — |
| `reports/sorgenti/ponte_flex_2026-09-28/` | da-verificare | — | Gli stessi knockdown K562 letti con Flex (VIPerturb-seq) e con 3' (Replogle): coseno per bersaglio fra universi, su tutti i bersagli condivisi e sui forti, e pendenza per gene di Flex su 3'. Esplorativo, senza regola. r2 misura il tetto di rumore interno di VIPerturb-seq: metà dei pool contro l'altra metà 0,110 di coseno mediano, contro 0,030 di ciascuna metà verso il 3' sugli stessi bersagli. Le misure sulla coppia restano valide; è falsa la premessa che tutte le altre sorgenti siano in 3': CD4 è GEM-X Flex v1. Correzione nell'audit del 29/09; nessuna mappa predittiva su bersagli tenuti fuori è stata valutata da questo report | [R-021](#r-021--piattaforma-plateau-e-inferenze-causali-nelle-sintesi) |
| `reports/modelli/rete_contesti_r2_2026-09-28/` | attuale | — | La rete su più contesti: il registro r2 (K562 essenziale, VIPerturb-seq, RPE1 e i due schermi HIPSCI in più; famiglie per linea: `k562`, `ipsc`) e la regola della tornata r2 fissata alle 04:00 del 28/09 prima di addestrare (r2 contro r1 sugli stessi bersagli; l'encoder su r2); `varianti_r1/`: le varianti descrittive della rete su r1, tutte con il minimo della famiglia tenuta fuori entro i primi 100 passi | — |
| `reports/modelli/rete_r1_lettura_2026-09-28/` | attuale | — | `leggi_r1.py`: la lettura della regola di r1 (27/09, 22:03) sui punteggi di `score_pred.py` per le previsioni mediate sui tre semi, più il segno per seme dai `metrics.json`; scritto dalla sessione Claude `f4f38e58` prima della lettura. Esito (29/09): uso del contesto, candidato ed E2 non passano (la rete perde contro `excl` su tre linee); J passa | — |
| `reports/modelli/covariazione_2026-09-28/` | attuale | — | Azione 6 di R-REV, la misura decisiva per la rete relazionale: la covariazione fra geni è più conservata fra linee dell'effetto del singolo bersaglio, e serve a prevedere una linea nuova? Protocollo e regola fissati alle 19:56 del 28/09, prima di qualunque calcolo sugli effetti; codice e uscite `r1/`. Esito (29/09): inconclusivo per W1, «uso» no (CP-0043) | — |
| `reports/modelli/rete_relazionale_2026-09-28/` | attuale | — | La rete relazionale di R-V2: carte dei geni da tutti i knockdown visibili, vicini per carta, guadagni di modulo letti dai controlli, sopra il trasferimento calibrato di r1; `DISEGNO.md` (proposta) e la regola della prima tornata fissata alle 19:58 del 28/09, prima di scrivere il codice; parte solo se la misura decisiva lo consente. Codice con autoverifica 12 su 12; modifiche dichiarate alle 00:50 del 29/09; non parte (CP-0043) | — |
| `reports/invii/prova_generale_2026-09-28/` | attuale | — | Azione 3 di R-REV (F8 di R-V2): la prova generale del 22 ottobre su A/B/C trattati come nuovi, con 300 bersagli finti, fino al `.vcc` verificato e senza invio; protocollo, previsioni e difetti attesi fissati alle 20:00 del 28/09, prima di girare. Esito (29/09, forma ridotta): `.vcc` di D/E/F verificato; D4 e D9 da correggere (CP-0044) | — |
| `reports/invii/prediction_t27_2026-09-29/` | attuale | — | Previsione del t27 (il t25 con l'esclusione 0/1 dei geni a quota 0 del t23, senza pesatura né riscalatura; lista in `esclusione.csv`) registrata **prima** della generazione, il 29 settembre alle 15:45 UTC: banda +0,128…+0,150, t27 − t25 in −0,010…+0,008, regola di lettura a ±0,005 contro il t25 | — |
| `reports/invii/prediction_t26_2026-09-29/` | attuale | — | Previsione del t26 (il t25 con la soglia d'espressione dello stadio 100: effetto 0 sui geni sotto 5 CPM nei controlli del contesto) registrata **prima** della generazione, il 29 settembre alle 12:24 UTC: banda +0,134…+0,156, t26 − t25 in −0,006…+0,012, regola di lettura a ±0,005 contro il t25. Esito (`comparison.json`, 29/09): +0,138721, −0,0015, non conclusivo (CP-0045) | — |
| `reports/invii/trial_2026-10-01/` | attuale | — | Testi del t29 scritti prima della generazione; manifesti degli stadi 45 e 48, output di `vcc` salvato così com'è, status pubblicato del t29 (−0,029625) | — |
| `reports/invii/trial_2026-09-29/` | attuale | — | t26 pubblicato, t27 pronto. t28: ricevute originali, recupero locale con SHA completo, upload verificato 22:46 UTC; status finale published, score 0,144845205, entry ZvrYZ4UazadAyuq4AsDB. INVIO_T28.md resta la fotografia pre-score; confronto e CP-0052 chiudono il seguito. Rimozione autorizzata del solo intermedio t26, contenitore conservato; marker arresto keep-awake a conclusione | — |
| `reports/invii/prediction_t22_2026-09-26/` | attuale | — | Previsione del t22 (t20 + HEK293T a peso 1) registrata **prima** della generazione, il 26 settembre alle 13:34 UTC: banda +0,125…+0,152, t22 − t20 in −0,006…+0,006, regola di lettura a ±0,005. `comparison.json`: +0,141250, t22 − t20 = +0,0016, non conclusivo per la regola; tutti i membri grezzi dentro gli intervalli registrati (fedeltà al bordo) | — |
| `reports/invii/prediction_t23_2026-09-27/` | attuale | — | Previsione del t23 (t22 con la quota condivisa per gene) registrata **prima** della generazione, il 26 settembre alle 23:14 UTC: banda +0,120…+0,165, t23 − t22 in −0,010…+0,015, regola di lettura a ±0,005 contro il t22 (contro il t20 se il t22 non ha punteggio). Esito (`comparison.json`, 29/09): +0,141868, t23 − t22 = +0,0006, non conclusivo (CP-0042) | — |
| `reports/invii/prediction_t24_2026-09-27/` | attuale | — | Previsione del t24 (il t22 rigenerato con un altro seme del generatore, per misurare il rumore del generatore sul punteggio ufficiale) registrata **prima** della generazione, il 27 settembre alle 00:02 UTC: t24 − t22 in −0,004…+0,004; la regola fissa la soglia delle regole successive al massimo fra 0,005 e il triplo della differenza assoluta fra t24 e t22 | — |
| `reports/invii/prediction_t25_2026-09-27/` | attuale | — | Previsione del t25 (il t22 sulla cache r9, un solo fattore: lo stimatore senza l'artefatto del pseudoconteggio) registrata **prima** della generazione, il 27 settembre alle 11:41 UTC: banda +0,133…+0,152, t25 − t22 in −0,006…+0,008, regola di lettura a ±0,005 | — |
| `reports/trasferimento/contesti_2026-09-26/` | da-verificare | — | H6: numeri proxy conservati; somiglianza basale DepMap non predice il trasferimento in questa prova. Correzione: Mixscale è CRISPRi, non knockout; pannello degli interventi distinto dai geni di risposta. r2 p53 non aiuta coerentemente. Vedi audit del 26 settembre | [R-019](#r-019--audit-del-26-settembre) |
| `reports/trasferimento/trasferimento_appreso_2026-09-26/` | da-verificare | — | Trasferimento appreso: r1 non affidabile; r2/r3 correggono diversi difetti ma lasciano centri calcolati prima degli split e non costituiscono test J. Risultati proxy esplorativi conservati, incluse perdite PDS del modello diretto e vantaggi del reweighting; impatto numerico del leakage non misurato r3/r4: due canali (direzione del t20, profilo di magnitudine del modello), +0,008…+0,010 di PDS attraverso il modello del generatore. **r5, banco isolato come chiede R-019** (famiglia di prova esclusa da etichette, ingressi e centri; centri entro fold; arresto anticipato su bersagli interi; test di invarianza): sulle linee nuove +0,004…+0,008 con due intervalli su tre attraverso lo zero, nMAE proxy peggiore di +0,017…+0,051; per la regola fissata prima, **niente t21**, stadio 104 sperimentale | [R-019](#r-019--audit-del-26-settembre) |
| `reports/invii/prediction_t16_2026-09-24/` | attuale | — | Previsione del t16 (il t15 con ampiezza 0,788) registrata **prima** della generazione: banda +0,08…+0,14, regola di lettura contro il t15 (sale: si raddoppia ancora; scende: si prova il punto medio; altrimenti si tiene 0,394). `comparison.json`: esito **+0,137627**, rango 336, dentro la banda; per la regola la curva sale e il passo dopo è 1,576. Grezzi del t16 derivati dagli scalati con le ancore (errore ≤ 0,00076 sul t17), CP-0037 | — |
| `reports/invii/prediction_t17_2026-09-24/` | da-verificare | — | Previsione del t17 (il t15 + Orion HEK293T a pesi uguali, ampiezza 0,4285 perché il q99 mediano dell'effetto assoluto resti quello del t15) registrata **prima** della generazione: banda +0,095…+0,125, regola di lettura contro il t15. Preregistrazione invariata; la lettura causale a parità di ampiezza richiede il limite misurato in CP-0034. `comparison.json`: esito +0,108774, rango 448, dentro la banda; per la regola non conclusivo, CP-0038 | [R-016](#r-016--lettura-causale-del-t17) |
| `reports/invii/prediction_t15_2026-09-23/` | attuale | — | Previsione del t15 (il t11 con ampiezza 0,394 invece di 0,197, un solo fattore) registrata **prima** della generazione e dei punteggi di t12 e t14: banda +0,060…+0,095, regola di lettura contro il t11. Mette alla prova D-006 sul punteggio ufficiale: lo 0,197 minimizzava la MSE in pseudobulk, e lo scalato della `mse` è tosato a 0 in tutti gli invii. `comparison.json`: esito **+0,107533**, rango 436, **sopra** la banda (ogni membro dentro il suo intervallo); per la regola, D-006 si riapre (+0,0368 sul t11). Ancore riprodotte con scarto massimo 0,00095 (CP-0033) | — |
| `reports/invii/prediction_t14_2026-09-23/` | attuale | — | Previsione del t14 (`ControlModel` con gli effetti del t08 × 2,5, ampiezza scelta dai piloti) registrata dopo i piloti e **prima** della generazione completa: banda +0,02…+0,12, regola di lettura contro il t08 (stessi effetti; cambiano insieme generatore e ampiezza). Spiega perché, alla lettera del punto 2 della regola, gli effetti restano quelli del t08: il job è partito alle 18:00Z, il t11 è stato pubblicato alle 18:25Z. `comparison.json`: esito +0,064892, dentro la banda; per la regola **non attribuibile** (+0,0045 sul t08); fedeltà grezza 0,447, sotto l'intervallo previsto (CP-0032) | — |
| `reports/invii/prediction_t12_2026-09-23/` | storico | — | Previsione del t12 (il t11 più Orion HEK293T, quattro sorgenti a pesi uguali, cache dello stadio 98 run r5) registrata **prima** della generazione e prima del punteggio del t11: banda +0,050…+0,080, scarto dal t11 fra −0,005 e +0,010, regola di lettura fissata prima. La regola d'arresto di `reports/sorgenti/orion_2026-09-23/PRIMA_DEI_RISULTATI.md` non scatta (proxy HEK293T–K562 0,78, HEK293T–CD4 0,59–0,62) | — |
| `reports/invii/prediction_t11_2026-09-23/` | attuale | — | Previsione del t11 (t08 + Orion HCT116 a pesi uguali) registrata **prima** della generazione: banda +0,055…+0,075 e regola di lettura fissata prima. `comparison.json`: esito +0,070777, dentro la banda; per la regola, Orion aggiunge informazione (+0,0104 sul t08), ma i pesi di K562 e CD4 sono cambiati insieme (CP-0031); ancore riprodotte con scarto massimo 0,00026 | — |
| `reports/invii/prediction_t10_2026-09-23/` | attuale | — | Previsione del t10 (il t08 senza CD4) registrata **prima** della generazione: banda +0,040…+0,060 e regola di lettura fissata prima (≤ 0,050: CD4 porta almeno due terzi del guadagno del t08; ≥ 0,056: il guadagno viene soprattutto da stimatore e centratura). `comparison.json`: esito +0,0502, dentro la banda; per la regola, non attribuibile (0,0002 sopra la soglia); descrittivamente CD4 porta +0,0102 dei +0,0144 | — |
| `reports/invii/prediction_t08_2026-09-22/` | attuale | — | Previsione del t08 registrata **prima** dell'invio: banda del punteggio medio +0,03…+0,06 e direzione attesa di ogni membro rispetto a trial-01. Non viene dallo stadio 84, che non vale per una famiglia nuova (CP-0027), ma dalle misure di CP-0028. `comparison.json`: esito +0,0604, sul bordo superiore; tutti i grezzi nella direzione prevista | — |
| `reports/sorgenti/cd4_rows_2026-09-22/` | attuale | — | Script 97: righe pseudobulk CD4 (GSE314342) dei bersagli del pannello più 200 righe NTC per donatore × condizione, lette per intervalli di byte dal file pubblico su S3 (1,33 GiB). 297/300 bersagli, mediana 1.478 cellule per bersaglio; ogni riga verificata contro il proprio `total_counts`. La matrice sta sotto la radice dati (`external/cd4/`), non nel repository | — |
| `reports/gara/context_fingerprints_2026-09-22/` | attuale | — | Script 99. **Misura:** l'asse ufficiale è quello di un pannello di sonde (18.533 geni contro i 18.532 di Flex v1.0.1; 0 RPL/RPS, 0 HLA, niente XIST/MALAT1/NEAT1), coerente con il 10x Flex dichiarato da Arc. I profili NTC di A/B/C correlano fra loro più che con K562/RPE1 in 3'. Impronte genetiche: sesso, zeri omozigoti, spostamenti per braccio cromosomico. **Le identità di linea sono ipotesi**, non misure | — |
| `reports/analisi/direzione_2026-09-19/` | storico | — | Audit retrospettivo di main e refactor/pulizia, lettura delle sei note fornite dal proprietario e verifica di alcune righe AtlasShift della classifica. Proposta di trasferimento specifico del bersaglio con centratura e calibrazione delle quantità realizzate; nessun nuovo candidato o ciclo avviato. Suite rieseguite: errore comune di import cell_eval2.config; dettagli e limiti in VALUTAZIONE.md e VERIFICHE.md | — |
| `docs/checkpoints/0020-singola-cellula-cis-generatore.md` | attuale | — | Cambio di strategia verso le cellule singole su Colab. Misure: effetto cis trasferibile K562 → HepG2, co-espressione non predittiva, DE veloce identico allo scorer, generatore di trial-01 con 93 chiamate spurie per bersaglio a effetto zero. Corregge CP-0018 §3.1 e §4 (md5). **Nessun banco remoto e nessun invio eseguiti** | — |
| `reports/trasferimento/cis_2026-09-17/` | attuale | — | Script 77: curva effetto-distanza sul pseudobulk K562, coppie K562–HepG2 entro 5 kb, esposizione del pannello per contesto. Misura su bersagli HepG2 essenziali, non un punteggio | — |
| `reports/storico/coexpression_2026-09-17/` | attuale | — | Script 78: la co-espressione nei controlli HepG2 non predice l'effetto del knockdown (correlazione parziale mediana 0,0015 su 243 bersagli). Un contesto, bersagli essenziali | — |
| `reports/generatore_e_banchi/fast_de_2026-09-17/` | attuale | — | Script 79: `fast_scorer_de` contro il percorso scanpy di `cell_eval2` su cellule HepG2: righe, p-value, log2FC e chiamate identici | — |
| `reports/generatore_e_banchi/generator_null_smoke_2026-09-17/` | storico | `reports/generatore_e_banchi/generator_null_2026-09-17/` | Script 72 in versione ridotta (contesto A, 3.000 controlli, 4 pseudo-bersagli da 100 cellule): chiamate spurie a effetto zero per cellule reali, generatore di trial-01 e `ControlModel`. Prova ridotta, non la calibrazione a scala piena | — |
| `reports/generatore_e_banchi/generator_null_2026-09-17/` | attuale | — | Calibrazione a effetto zero su A, B e C (run `n003`, 9.200 controlli per addestrare e 9.200 come riferimento, 20 pseudo-bersagli da 400 cellule): il generatore di trial-01 dichiara 462 / 453 / 684 geni significativi per bersaglio (82% «in su»), le cellule reali 0,1 / 0,0 / 0,1 e `ControlModel` 0,5 / 0,5 / 1,2. Sostituisce la prova ridotta di `reports/generatore_e_banchi/generator_null_smoke_2026-09-17/` | — |
| `reports/generatore_e_banchi/bench_2026-09-17/` | storico | — | I due banchi a sei metriche del 17 settembre, girati su Colab: K562 del pannello (`b002`, 224 bersagli, mediana `N_conf` 3, oracolo dallo stesso bersaglio) e trasferimento K562 → HepG2 (`h002`, 300 bersagli, mediana `N_conf` 130). Scala **locale** (0 = baseline, 1 = replica del banco): confronta bracci, non è un punteggio VCC | — |
| `reports/invii/trial02_decision_2026-09-17/` | storico | — | Applicazione meccanica di `configs/trial02_rule.yaml` (script 81): scelto trasferimento ×2 + cis, riportato a ×1 dal tetto K562 → t02. `deviation_t03.json` documenta t03 (×2 + cis, senza tetto), deviazione a posteriori motivata dall'artefatto del Jaccard in K562 | — |
| `reports/sorgenti/k562_sc_2026-09-17/` | storico | — | Report e log dello stadio 71 (run `x002`, Colab, 17 settembre): prima lettura completa del K562 genome-wide a singola cellula, 1.989.578 cellule x 8.248 geni in 43 minuti (24,6 MiB/s dal mount Drive), md5 ricalcolato sui byte letti uguale al catalogo, 272 bersagli del pannello (28 assenti, elencati), 75.328 cellule NTC. Le uscite pesanti (parti, `group_stats.npz`) restano in `MyDrive/vcc2026/data/processed/k562_gwps_sc/x002/`. Il run `x001` e fallito all'avvio: la sua cartella contiene un `report.json` segnaposto che NON e un report | — |
| `reports/generatore_e_banchi/call_budget_2026-09-17/` | storico | — | Script 80 sul contesto A reale (20 bersagli del pannello, 400 cellule, 1.500 controlli di riferimento, sorgente K562 pseudobulk): chiamate significative per bersaglio al variare delle ampiezze. Mediana 1 con il solo cis, 9 con trasferimento EB x1, 216 con EB x2, 27 con raw x0,25. Conta le chiamate, non ne misura il segno | — |
| `reports/storico/drive_evidence_2026-09-17/` | storico | — | Copie dei sidecar `.fetch.json` e del `catalog_run.json` del run Colab del 15 settembre, più l'elenco dei file in `MyDrive/vcc2026` al 17 settembre: provano md5 e percorso delle copie su Drive | — |
| `src/vcc2026/sc_stream.py`, `src/vcc2026/generator.py`, `src/vcc2026/de_tools.py`, `src/vcc2026/sc_effects.py`, `src/vcc2026/predictor_sc.py`, `src/vcc2026/bench.py` | attuale | — | Pipeline a singola cellula: lettura a flusso con md5 e accumulatore numba; generatore appreso dai controlli; DE dello scorer in forma ufficiale e veloce; effetti con shrinkage EB; termine cis e composizione del log fold change; banco a sei metriche con ancore locali | — |
| `scripts/71_extract_k562_sc.py`, `scripts/72_generator_null.py`, `scripts/73_bench_k562_panel.py`, `scripts/74_fetch_gene_coordinates.py`, `scripts/75_bench_hepg2_transfer.py`, `scripts/76_generate_sc_prediction.py`, `scripts/77_cis_effect_report.py`, `scripts/78_coexpression_predictor_test.py`, `scripts/79_fast_de_parity.py`, `scripts/80_call_budget.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `scripts/78_coexpression_predictor_test.py`, `scripts/80_call_budget.py`. 71 e 73–76 provati solo su dati ridotti o finti in locale; 71, 72, 73 e 75 in coda su Colab e **non ancora eseguiti** a scala piena. 74 eseguito: coordinate GENCODE v50 per 18.447 dei 18.533 geni ufficiali. 77, 78, 79 e 80 eseguiti, con report | — |
| `notebooks/colab_sc_training.ipynb`, `notebooks/colab_jobs/` | attuale | — | Notebook Colab con dispatcher: esegue i job depositati in `MyDrive/vcc2026/runs/queue/` e scrive i log in `runs/jobs/`; `sync_to_drive.ps1` copia il codice su Drive. Mai eseguito su Colab al 17 settembre, 16:40. Dal 30/09 restano `common.sh`, `generate_trial.sh`, `queue_trial.sh` e `sync_to_drive.ps1`: gli script dei singoli job del 17–18/09 sono archiviati (ARCHIVIO) | — |
| `tests/test_sc_pipeline.py` | attuale | — | 8 test: flusso e accumulatore contro letture dirette, md5, rifiuto di X a blocchi, Mann-Whitney esatto con pareggi, BH, generatore senza copie e con conteggi interi, prior cis limitato alla distanza, shrinkage EB | — |
| `docs/checkpoints/0019-catena-cicli-guardiano.md` | attuale | — | Cambio di strategia: la catena diventa a cicli ripetibili, con guardiano, test di collaudo scritti da Codex prima di Claude e controllo di Grok con al massimo tre campagne dell'orchestratore. Implementato e provato con agenti simulati; **nessun ciclo eseguito dal vivo**. La catena è stata ritirata il 23/09 (D-040); il suo stato di oggi è in `docs/AGENTI.md` §2 | — |
| `reports/storico/catena_2026-09-16/` | storico | — | Le uniche prove sui servizi veri per la catena: trascrizione della chiamata di prova a Grok Build (formato della risposta, costo nominale), validazione con `orch brief` di un incarico nel formato generato, esiti delle verifiche del 16 settembre | — |
| `docs/checkpoints/0018-drive-storage-confermato.md` | da-verificare | — | Dichiarazione del proprietario: `K562_gwps_raw_singlecell_01.h5ad` e `NadigOConner2024_hepg2.h5ad` sono già su Google Drive. Dimensioni coerenti con il catalogo in unità binarie. **Corretto da CP-0020:** le copie le ha scaricate il run Colab del 15 settembre nei percorsi attesi, con md5 verificato al download. Resta vero che nessun run ne ha letto il contenuto. Non adotta nessun dataset | [R-014](#r-014--cp-0018-md5-e-provenienza-delle-copie-su-drive) |
| `docs/CICLO_GIORNALIERO.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Contratto della catena di cicli: piano, revisione, implementazione, controllo; guardiano, casella, collaudo, campagne, permessi, comandi e limiti. Riscritto il 16 settembre (la versione a un giro al giorno è nel commit `4272b3b`). Provato con agenti simulati; nessuna esecuzione dal vivo | — |
| `reports/storico/ciclo_giornaliero/` | storico | — | Registrazioni della catena, una cartella per giornata con `ciclo-NN/`: segnali JSON delle quattro fasi, revisione o dialogo, foglio, test di collaudo, esito di Claude, analisi e sintesi di Grok, campagne, resoconto. Documentano che cosa gli agenti hanno consegnato; non sono risultati scientifici. La cartella `2026-09-16` ha la forma piatta precedente, e il suo sigillo non corrisponde più ai piani modificati dopo ([CP-0018](checkpoints/0018-drive-storage-confermato.md)) | — |
| `scripts/32_daily_cycle.py`, `scripts/ciclo.cmd`, `configs/ciclo_giornaliero/`, `tests/test_daily_cycle.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). La catena (solo libreria standard): guardiano, coda, cicli dal dialogo, collaudo prima e dopo, fase di Grok e campagne con tetto; wrapper per l'Utilità di pianificazione, impostazioni, schemi e testi fissi. 42 test con agenti simulati (Codex, Claude, Grok, orchestratore) in un repository git temporaneo | — |
| `.agents/skills/avvia-ciclo/`, `.agents/skills/revisione-piano/`, `.claude/skills/piano-mattutino/` | storico | — | **Archiviati il 23 settembre** (D-040): le tre skill. `AGENTS.md` resta, riscritto come rimando a `CLAUDE.md` e al ritiro della catena. Com'era: Istruzioni degli agenti della catena: dialogo e avvio dei cicli in Codex, revisione del ciclo 01 con i test di collaudo, piano del mattino che legge i resoconti dei cicli, regole comuni per Codex e Grok | — |
| `docs/PIANO_IMPLEMENTATIVO_2026-09-16.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Workflow 1 del 16 settembre: dieci incarichi paralleli con scadenze, regole di accettazione scritte prima dei risultati, cinque decisioni del proprietario (O1–O5), obiettivi di spinta dichiarati come non previsioni. Proposta: non attesta l'avvio di alcun incarico. Aggiornato alle 16:49 con CP-0018: in I-5 e I-6 il K562 a singola cellula si collega da Drive e non si scarica | — |
| `docs/PIANO_COMPRENSIONE_2026-09-16.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Workflow 2 del 16 settembre, per i ricercatori: stato per area da verificare, criticità C1–C12, studio biologico e informatico, domande di comprensione e disallineamenti noti. Proposta: non attesta l'avvio di alcun incarico. Aggiornato alle 16:49 con CP-0018: C8 declassata per l'ingestione, unità del file K562 corretta | — |
| `reports/gara/leaderboard_2026-09-16/` | storico | — | Fotografia trascritta a mano della classifica pubblica alle 11:31Z: prime dieci righe e la nostra (rango 493), senza nomi di squadra. Contiene una **stima** delle ancore b/r per metrica da un adattamento lineare: interpretazione, non misura ufficiale | — |
| `docs/checkpoints/0017-gate-espressione-destinazione.md` | attuale | — | Gate di espressione G1/G2/G3 con controlli permutato e sorgente: implementato, eseguito e misurato. **Non promosso** dalla regola fissata prima del run. Non adotta niente | — |
| `configs/benchmark_expression_gate.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo del run `x001` e regola di decisione, scritti prima di qualunque risultato. `owner_confirmed: false`: la regola proposta nel brief non è stata confermata dal proprietario prima del run | — |
| `src/vcc2026/presence.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Presenza per gene dai controlli già letti (`inference.read_basal_profile`, `ControlProfile`) e peso logistico graduale; nessun secondo lettore di controlli. Un gene non misurato ha peso 1 (D-009) | — |
| `src/vcc2026/benchmark/gate.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). I bracci gate: G1/G2/G3, i controlli C1 (permutato) e C2 (sorgente), la selezione sulla coppia interna al training e la valutazione meccanica della regola di decisione. Spento se la configurazione non lo dichiara | — |
| `tests/test_expression_gate.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 53 test: presenza non misurata contro misurata a zero, peso graduale e non a scalino, permutazione che conserva i valori, selezione che non legge il contesto di test, base che deve coincidere con `shrunk_transfer`, regola che non promuove su un confronto mancante | — |
| `scripts/69_expression_gate_decision.py`, `scripts/70_context_presence_audit.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 69 applica la regola già scritta e non sceglie nulla; 70 conta quanti geni e quanti bersagli sono poco espressi nei controlli ufficiali A/B/C. Eseguiti il 2026-09-16 | — |
| `reports/storico/expression_gate_2026-09-16/` | attuale | — | Run `x001`: tabella comparativa, universo, riepilogo con i confronti appaiati, split con la distribuzione dei CPM, decisione applicata, righe dei gate, e l'audit di presenza dei contesti ufficiali. I pesi e `results.json` restano in `artifact_root` | — |
| `docs/RL/README.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Appunti RL rinviati su richiesta dell'utente: allocazione del calcolo, calibrazione e affinamento generativo; ipotesi e criteri di ripresa, nessuna adozione o esecuzione | — |
| `docs/checkpoints/0016-piano-operativo-audit-protocollo.md` | attuale | — | Audit Jiang/Jurkat, protocollo congelato, disco sotto soglia per TGFB, campagna orch avviata. Non adotta Jiang né Jurkat | — |
| `configs/eval_protocol.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo di valutazione congelato (D-032). Seed 4242 riservato. Non è un risultato | — |
| `src/vcc2026/eval_protocol.py`, `src/vcc2026/runtime.py`, `src/vcc2026/remote_job.py`, `src/vcc2026/source_card.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo, inventario runtime, fetch riprendibile, scheda sorgente | — |
| `scripts/61_probe_jiang.py`, `scripts/62_reconcile_nadig.py`, `scripts/63_runtime_preflight.py`, `scripts/64_source_cards.py`, `scripts/65_eval_protocol_pilot.py`, `scripts/66_primeflow_feasibility.py`, `scripts/67_remote_ingest.py`, `scripts/68_remote_catalog.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 67 = contratto HepG2; 68 = piano/catalogo multi-sorgente. 68 eseguito in locale **plan-only** (nessun file da 61,3 GiB sul portatile; la versione precedente di questa nota diceva «65,8 GiB», un errore di unità: [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb)) | — |
| `tests/test_eval_protocol.py`, `tests/test_remote_job.py`, `tests/test_remote_ingest.py`, `tests/test_remote_catalog.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Leakage, fetch, gate Jiang, catalogo byte/md5, persistenza Colab, checkpoint immutabile | — |
| `src/vcc2026/remote_ingest.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Job HepG2: parità, resume, gate TGFB | — |
| `src/vcc2026/remote_catalog.py`, `configs/remote_catalog.yaml` | da-verificare | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Catalogo blocchi con byte/md5 da evidenza: byte, md5, URL e `relpath` sono giusti, e il codice lavora in byte. **Non** è vero che il «61,3 GB» del profilo differisca dai 65.830.941.948 byte misurati: sono 61,31 GiB, la stessa dimensione. Errati `advertised_bytes`, `advertised_note` e l'etichetta «65,8 GiB» nelle docstring | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `notebooks/remote_ingest_hepg2.ipynb` | da-verificare | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Un solo notebook: preflight, selezione, fetch, QC, deriva. `FETCH_BLOCKS is None` auto-sceglie dopo il preflight (HepG2 se manca, poi K562 GW se Drive è montato). Vuoto `[]` resta plan-only. HepG2 si salta se size/md5 ok. Il run Colab `catalog_2026-09-15T143641Z` era plan-only per `FETCH_BLOCKS=[]`, non un fallimento del fetcher. **Dal 16 settembre** i due file sono già su Drive (CP-0018): per soltanto collegarli serve `FETCH_BLOCKS = []`, perché con `None` la selezione passa al blocco successivo e lo scarica | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/storico/remote_catalog_2026-09-15/` | storico | — | Piano locale. HepG2 complete (file già sul disco). Nessun download nuovo. Non è una prova Colab. Ripete `advertised_bytes` del catalogo, contestato in R-013 | — |
| `reports/storico/remote_2026-09-15/` | da-verificare | — | Parità HepG2 ok, resume ok, Jiang skip per disco: misure valide. Le istruzioni in `COME_APRIRE.md` usano «65,8 GiB» (sono 61,31 GiB) e consigliano `FETCH_BLOCKS = None`, che con i file già su Drive porta a un download non voluto | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/storico/jiang_2026-09-15/` | storico | — | Record Zenodo, HEAD, file piccoli, scheda, proposta TGFB. Copertura pannello missing | — |
| `reports/storico/nadig_reconcile_2026-09-15/` | attuale | — | HepG2 GEO=mirror per forma e NTC; Jurkat mirror 1,29 GB, 0/300 | — |
| `reports/storico/runtime_2026-09-15/` | storico | — | 7,81 GiB RAM, 11,3 GiB liberi; TGFB non sta sotto il pavimento da 10 GiB | — |
| `reports/storico/source_cards_2026-09-15/` | storico | — | Schede Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount. Nella scheda Replogle SC, `profile_declared_sc` converte in byte decimali cifre del profilo che sono GiB; decisioni e altri campi non ne dipendono | [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |
| `reports/storico/eval_protocol_2026-09-15/` | storico | — | 12 split, 0 fail, tutti sviluppo. Ancore HepG2: solo smoke su finestra, non un risultato | — |
| `reports/storico/primeflow_2026-09-15/` | storico | — | Fattibilità da preprint; codice/pesi missing; defer | — |
| `configs/orchestrator/briefs/vcc2026-jurkat-audit.yaml`, `configs/orchestrator/briefs/vcc2026-pharma-atlas-audit.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Incarichi preparati, non avviati: l'orchestratore serializza il browser | — |
| `docs/REGIA_PARALLELA_2026-09-15.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Mandato esplicito dell'utente: concentrare oggi tutti i filoni, solo training oltre oggi; otto incarichi, proprietà file, dipendenze e formato delle consegne. Avvio agenti a cura dell'utente | — |
| `docs/PIANO_OPERATIVO_2026-09-15.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Piano approvato: audit, elenco ufficiale, protocollo e incarichi. Jiang/Jurkat prioritari. La riga «nessun run dei worker» è superata da CP-0016 (campagna Jiang avviata). Nessun nuovo training | — |
| `configs/orchestrator/briefs/vcc2026-jiang-audit.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Audit Jiang; pannello allegato. Campagna live `20260915T115742Z-vcc2026-jiang-audit-v1-a81104`: DeepSeek 3 fasi, Kimi timeout ×2, fermata `service_unavailable`. Puntatore in `reports/storico/orchestrator/jiang-audit-20260915.md` | — |
| `configs/orchestrator/briefs/vcc2026-validation-review.yaml`, `configs/orchestrator/briefs/vcc2026-primeflow-audit.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Incarichi delimitati preparati per review metodologica e ricerca primaria; non avviati | — |
| `docs/storico/SVD_E_RANGO.md` | storico | — | SVD randomizzata configurabile e confronto di rango 16/32/64/128. Implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta la randomizzata né un rango >16 | — |
| `reports/storico/ricerca_dataset_20260915.md` | storico | — | Dossier di una campagna `scientific_research` dell'orchestratore (run `20260914T222203Z-campagna-dati-v1-037cbd`). Non è una misura di questo repository: i livelli di consultazione restano dichiarati (D-023). Non usato da CP-0015 | — |
| `docs/checkpoints/0015-svd-randomizzata-e-rango.md` | attuale | — | Misura della sostituzione esatta/randomizzata e del rango; regola di banda prefissata non soddisfatta | — |
| `reports/storico/svd_2026-09-15/` | attuale | — | Fattorizzazione isolata, confronto predittivo s001/s002, tabelle e split. I `results.json` restano in `artifact_root` | — |
| `reports/storico/rank_2026-09-15/` | attuale | — | Tabella, riepilogo, split e `rank_summary.json` del run r001 | — |
| `configs/benchmark_svd_exact.yaml`, `configs/benchmark_svd_randomized.yaml`, `configs/benchmark_rank.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocolli eseguiti: sostituzione SVD e confronto di rango. Non sono una proposta di default | — |
| `scripts/60_compare_factorization.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Confronto esatta/randomizzata su una matrice reale e, se dati due run, sulle predizioni | — |
| `tests/test_factorization.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Riproducibilità, forme, centratura, bootstrap pooled, aggregazioni di segno opposto | — |
| `src/vcc2026/benchmark/factorization.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Unico punto di SVD troncata del benchmark; `exact` predefinito | — |
| `docs/storico/ENCODER_INPUTS.md` | attuale | — | Specifica degli input di contesto e bersaglio per il modo B (gene mai perturbato). Descrittori verificati su file. **La sua unica estensione, il GO slim, è stata eseguita e scartata il 2026-09-15** ([CP-0014](checkpoints/0014-go-slim-e-gpu.md)): il resto della pagina resta valido come specifica e inventario | — |
| `reports/storico/encoder_inputs_2026-09-14/` | attuale | — | Probe isolato: HEAD, download, mapping HGNC, copertura GO/STRING. Cache pesante in `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/` | — |
| `scripts/56_probe_target_descriptors.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Probe dei descrittori di modo B. Eseguito il 2026-09-14; non modifica il benchmark. Numerato 56 perché 52–55 sono l'ingestione HepG2 in corso | — |
| `reports/storico/hepg2_2026-09-14/` | attuale | — | Acquisizione (URL, byte, md5 verificato), audit del contenuto, tabella contesto×bersaglio e confronto generatore×predittore di HepG2 Nadig. Non modificati da CP-0012 | — |
| `docs/storico/BENCHMARK_TRE_CONTESTI.md` | storico | — | Benchmark a tre contesti (K562, RPE1, HepG2): implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta un'architettura e non dichiara un vincitore | — |
| `reports/storico/benchmark_3ctx_2026-09-14/` | attuale | — | Tabella comparativa, universi genici, riepilogo e manifesti del run m002 a tre contesti. Pesi e `results.json` restano in `artifact_root` | — |
| `configs/benchmark_3ctx.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo del benchmark a tre contesti: tre fold esterni, alpha vietato, universo per intersezione, regola di combinazione delle sorgenti fissata prima dei run | — |
| `configs/benchmark_3ctx_hepg2_predictions.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Derivato dal precedente: stesso protocollo, solo il fold con HepG2 fuori e le predizioni salvate, per l'esperimento generatore×predittore | — |
| `scripts/52_audit_hepg2.py`, `scripts/53_build_hepg2_signatures.py`, `scripts/54_context_target_table.py`, `scripts/55_control_profile.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Acquisizione e ingestione HepG2: audit, firme con controlli appaiati per batch, censimento contesto×bersaglio, profilo basale. Eseguiti il 2026-09-14 | — |
| `scripts/57_generator_x_predictor.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Confronto generatore×predittore sulle sei metriche, cellule HepG2 reali. Numerato 57 perché 56 è la sonda dei descrittori | — |
| `reports/storico/go_slim_2026-09-15/` | attuale | — | Pilot dei descrittori GO slim (run g002): tabella comparativa, split, riepilogo con i confronti appaiati, e il riassunto della tabella congelata. Esito: estensione **scartata** dalla regola fissata prima ([CP-0014](checkpoints/0014-go-slim-e-gpu.md)) | — |
| `reports/storico/gpu_2026-09-15/` | storico | — | Audit di prontezza GPU: che cosa esegue ogni passo numerico, quanto costa alle forme reali, e lo scaling della SVD. Misure su questa macchina a carico scarico | — |
| `docs/CONSEGNA_GPU.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Pacchetto trasferibile per la macchina con GPU del compagno: file da copiare, dipendenze, comandi, e che cosa la GPU accelera davvero (il solo backend DE dello scorer) | — |
| `configs/benchmark_go_slim.yaml`, `requirements-gpu.txt` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo del pilot GO slim, con la regola decisionale e il braccio permutato; dipendenze aggiuntive per una macchina CUDA, deliberatamente senza torch | — |
| `scripts/58_build_go_slim_table.py`, `scripts/59_gpu_readiness.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Tabella congelata simbolo→140 bit GO con gli sha256 delle quattro fonti; audit GPU misurato. Eseguiti il 2026-09-15 | — |
| `docs/PROSPETTO_MODELLO_2026-09-14.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Proposta: ricostruzione trial, blocchi modulari, evidenze e protocollo comparativo. Nessun vantaggio misurato né architettura adottata. Il confronto è stato eseguito in [CP-0011](checkpoints/0011-primo-benchmark-modulare.md), esito inconcludente | — |
| `docs/storico/BENCHMARK_MODULARE.md` | storico | — | Primo confronto modulare: implementato / eseguito / misurato / ipotizzato tenuti distinti. Non adotta un'architettura | — |
| `reports/storico/benchmark_2026-09-14/` | attuale | — | Inventario, split riassunti, tabella comparativa, specifica del bundle mancante, manifesti del pilot m001. I pesi e `results.json` restano in `artifact_root` | — |
| `src/vcc2026/benchmark/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo comune, universo genico, modelli A–E, runner. Coperti da `tests/test_modular_benchmark.py` | — |
| `scripts/50_inventory_data.py`, `scripts/51_run_modular_pilot.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Inventario e pilot. Eseguiti il 2026-09-14; i risultati leggeri sono in `reports/storico/benchmark_2026-09-14/` | — |
| `tests/test_modular_benchmark.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Maschere, leakage, alpha 0,1974, salvataggio/caricamento, identità delle predizioni | — |
| `configs/benchmark.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Protocollo del pilot: metrica primaria, alpha vietato, universo, seed, budget. Non è un risultato | — |
| `docs/PROGETTO.md` | attuale | — | Stato e direzione (§0), il problema, che cosa sappiamo e non sappiamo, le criticità. Dal 30/09 (D-049) il §0 è corto: la cronaca è in `docs/storico/PROGETTO_sezioni_0_6_7_2026-09-30.md`, i punteggi in `reports/invii/README.md`, il percorso di lettura nella tabella dei compiti di `CLAUDE.md` | — |
| `docs/DECISIONI.md` | attuale | — | Decisioni attive e quando riaprirle | — |
| `docs/REGISTRO.md` | attuale | — | Questo file | — |
| `docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md` | da-verificare | — | Stato e correzioni al 12 settembre; ricostruzione retrospettiva dichiarata. Tre affermazioni corrette da CP-0002: resta leggibile com'era, come tutti i checkpoint | [R-009](#r-009--docscheckpoints0001-ricostruzione-stato-2026-09-12md) |
| `docs/checkpoints/0002-correzioni-dopo-revisione-umana.md` | attuale | — | Le sei correzioni chieste dalla prima revisione umana, e da dove veniva ciascuna | — |
| `docs/checkpoints/` | attuale | — | Modello, indice e checkpoint. I checkpoint non si riscrivono: le correzioni stanno in quello successivo e nella colonna "Corretto da" dell'indice | — |
| `docs/storico/revisione_grok_2026-09-12.md` | attuale | — | Verifica live di un inventario esterno fornito da Grok: correzioni di accessione e cinque piste nuove. Dichiara i propri limiti. **Le sue conclusioni non sono ancora entrate in `docs/DECISIONI.md`**: farlo richiede un checkpoint | — |
| `docs/storico/candidate_adversarial_review_2026-09-12.md` | attuale | — | Analisi più recente: coperture misurate, correzioni di accessione, piano di acquisizione. Non è stata rivista da un umano e il suo §2 è in disaccordo aperto con la revisione dell'11 settembre sull'asse genico | — |
| `README.md` | attuale | — | Compito, formato, metriche, layout, setup e autenticazione: la parte corretta del README (R-001). Dal 28/09 le sezioni storiche con le sei affermazioni contestate sono in `docs/storico/README_2026-09-11_13.md`, che porta la scheda | — |
| `reports/gara/scorer/vcc2026_contract.json` | superato | `reports/gara/scorer_2026-09-12/vcc2026_contract.json` | Il dump di `official_config` e i clamp per metrica sono verificati e invariati; solo il campo `floor_note` è sbagliato. Resta come evidenza storica di che cosa diceva l'estrattore prima della correzione | [R-002](#r-002--reportsscorervcc2026_contractjson) |
| `docs/storico/data_strategy_2026-09-11.md` | superato | `docs/storico/revisione_analisi_2026-09-11.md`, `docs/storico/candidate_adversarial_review_2026-09-12.md` | Il §4 (contratto di preprocessing) e il §1 (misure locali) restano validi e sono usati | [R-003](#r-003--docsdata_strategy_2026-09-11md) |
| `docs/storico/revisione_analisi_2026-09-11.md` | da-verificare | — | Identità dei contesti, povertà di segnale in K562, tabella dei clamp e disegno del pannello restano validi e riusati | [R-004](#r-004--docsrevisione_analisi_2026-09-11md) |
| `reports/storico/candidate_verification/cd4_readme.txt` | superato | `reports/storico/candidate_verification/expanded/cd4_readme.txt` | Nulla: è il corpo di una risposta 404 | [R-005](#r-005--i-due-stub-404-di-candidate_verification) |
| `reports/storico/candidate_verification/cd4_repo_tree.txt` | superato | `reports/storico/candidate_verification/expanded/cd4_repo_tree.txt` | Nulla: è il corpo di una risposta 404 | [R-005](#r-005--i-due-stub-404-di-candidate_verification) |
| `reports/storico/candidate_pdf_extracted.txt` | storico | — | Fonte esterna di affermazioni da verificare, non evidenza nostra: diverse sue tesi sono state smentite | [R-006](#r-006--reportscandidate_pdf_extractedtxt) |
| `reports/storico/transfer_ceiling/` | da-verificare | — | I numeri sono corretti e riusati; è il nome della cartella a suggerire una conclusione che non è stata dimostrata | [R-007](#r-007--reportstransfer_ceiling) |
| `configs/candidate_ingestion.json` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Manifesto di piano e configurazione. Non è la prova che un runner l'abbia consumato: nessun addestramento è partito | — |
| `reports/gara/context_identity/` | attuale | — | Marcatori e test di contrasto; le cautele sono scritte dentro `context_identity.json` **Vale in parte:** la lettura «occhio» di B è un'ipotesi debole (R-001, punto 3). | — |
| `reports/storico/data_audit/` | attuale | — | Audit dei controlli ufficiali e copertura HIPSCI: misure ancora valide anche se HIPSCI è stata spostata più in basso nelle priorità | — |
| `reports/storico/candidate_verification/coverage_summary.json` | attuale | — | Coperture per sorgente; ricontato il 2026-09-12 | — |
| `reports/storico/candidate_verification/panel_coverage.csv` | attuale | — | Tabella per bersaglio: il file su cui si sceglie cosa è supportato | — |
| `reports/gara/external_compat/` | attuale | — | Struttura delle guide NTC e contratto di compatibilità esterna | — |
| `reports/storico/candidate_verification/` | storico | — | Sonde remote del 11–12 settembre con manifest, byte e sha256: `expanded/`, `annotations/`, `context_c_lead/`, `pilot/` e i file di primo livello. Fotografie datate di endpoint pubblici, non conclusioni | — |
| `reports/storico/grok_verification/` | storico | — | Sonde e campioni prodotti da `scripts/27_verify_grok_leads.py` e `scripts/28_probe_grok_files.py`, spiegati da `docs/storico/revisione_grok_2026-09-12.md`. Contiene `multiome.zip`, che `.gitignore` esclude: è locale, non versionato | [R-008](#r-008--reportsgrok_verification) |
| `scripts/` (01–28, analisi) | attuale | — | Esistono e sono documentati come eseguiti; l'esistenza di uno script non è prova di esecuzione né di risultato | — |
| `scripts/30_new_checkpoint.py`, `scripts/31_check_docs.py`, `tests/test_doc_workflow.py` | attuale | — | Utilità di questo sistema: creano checkpoint numerati senza sovrascriverli e verificano la coerenza di registro, indice e riferimenti. Solo libreria standard | — |
| `notebooks/` | attuale | — | Il dispatcher Colab e i suoi job, che hanno una riga propria (`notebooks/colab_sc_training.ipynb`, `notebooks/colab_jobs/`). Era vuota fino al 13 settembre; i due notebook di allora sono archiviati dal 23 (D-040). *Riga corretta il 24 settembre: diceva «cartella vuota»; la correzione del 15 (`fa0b1c6`) non era mai stata unita* | — |
| `docs/checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md` | attuale | — | Prima pipeline verticale eseguita e prima calibrazione misurata dell'ampiezza di trasferimento; corregge due letture dei dati mai scritte prima | — |
| `docs/PIPELINE.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Architettura della pipeline, moduli, comandi e scelte di progetto. Descrive codice eseguito, non previsto | — |
| `docs/ROADMAP.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Passi ordinati per valore informativo diviso costo, con ipotesi, criterio di successo e artefatto atteso per ciascuno | — |
| `docs/ESECUZIONE_REMOTA.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Piano locale/remoto con tempi misurati e profili di risorse. **Non contiene prezzi**: il preventivo va costruito al momento della proposta | — |
| `configs/sources.yaml` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Registry versionato delle sorgenti con livelli di verifica ed evidenza. Fonte autorevole sullo stato di una sorgente (D-013); `src/vcc2026/registry.py` ne verifica la coerenza | — |
| `reports/storico/pipeline/` | storico | — | Risultati leggeri e manifesti dei tre stadi eseguiti il 2026-09-12: QC delle firme, esperimento di trasferimento, calibrazione del nullo con lo scorer ufficiale. Gli artefatti pesanti restano in `artifact_root` | [R-010](#r-010--reportspipeline) |
| `reports/storico/pipeline/transfer_experiment_e001_superseded.json` | superato | `reports/storico/pipeline/transfer_experiment.json` | Stessa esecuzione, ma con un campo di riepilogo a `null` per un errore di chiave nella funzione di aggregazione. I numeri di trasferimento sono identici; conservato perché una riesecuzione non sovrascrive un'evidenza | [R-010](#r-010--reportspipeline) |
| `reports/gara/scorer_2026-09-12/vcc2026_contract.json` | attuale | — | Riestrazione del contratto dallo stesso `cell-eval2` 0.16.0, con il `floor_note` corretto. Sostituisce funzionalmente `reports/gara/scorer/vcc2026_contract.json`, che resta come evidenza storica | [R-002](#r-002--reportsscorervcc2026_contractjson) |
| `src/vcc2026/` (genes, signatures, pseudobulk, models, splits, evaluation, registry, manifest) | attuale | — | Moduli aggiunti il 2026-09-12, coperti da 42 test nuovi. I moduli preesistenti non sono stati toccati; `config.py` è stato solo esteso. Di questi restano `genes` e `manifest`: `pseudobulk`, `splits` e `registry` sono archiviati dal 23 settembre (D-040), `signatures`, `models` ed `evaluation` dal 24 (D-043, [ARCHIVIO.md](ARCHIVIO.md)) | — |
| `scripts/40_build_signatures.py`, `41_transfer_experiment.py`, `42_null_calibration.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). I tre stadi della pipeline. Eseguiti il 2026-09-12; i loro manifesti sono in `reports/storico/pipeline/` | — |
| `docs/SOTTOMISSIONE.md` | da-verificare | — | Il contratto (§1–2, §4–5, §7) resta valido. **Il §3 e il punto 1 del §6 rimandano a stadi archiviati il 23 settembre** (D-040): i comandi vivi sono in `docs/PROCEDURE.md`. Contratto di sottomissione verificato il 2026-09-12 sulle fonti ufficiali e sulla CLI installata, comandi esatti per rigenerare, convalidare, inviare e leggere i punteggi, e la distinzione fra punteggi normalizzati e metriche locali. La sezione 4 è **compilata** dalla prima sottomissione del 2026-09-13 | [R-015](#r-015--docssottomissionemd-i-comandi-del-3-e-la-lista-del-6) |
| `reports/invii/trial_2026-09-12/` | attuale | — | Artefatti leggeri del primo trial locale: calibrazione annidata, confronto fuori campione, misure di risorse, convalide e log di `vcc prep`. Introdotti da [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md). Le previsioni pesanti restano in `artifact_root` | [R-011](#r-011--reportstrial_2026-09-12) |
| `reports/invii/trial_2026-09-12/calibration_c001_peak_memory_unrecorded.json` | superato | `reports/invii/trial_2026-09-12/calibration_c002.json` | Stessa esecuzione e numeri identici; il solo campo `peak_rss_bytes` è `null` perché il lettore di memoria di picco su Windows non era ancora corretto. Conservato perché una riesecuzione non sovrascrive un'evidenza | [R-011](#r-011--reportstrial_2026-09-12) |
| `configs/trials.yaml` | attuale | — | Il trial dello stadio 45 (`trial-ext-profile`) e i suoi valori predefiniti, seme 20260912 compreso. `src/vcc2026/trials.py` lo legge, così un run non può contraddire il trial che dichiara. Le definizioni di trial-00 e trial-01 sono archiviate dal 24 settembre (D-043, tag `archivio/pre-pulizia-2026-09-24`, [ARCHIVIO.md](ARCHIVIO.md)) | — |
| `src/vcc2026/inference.py`, `resources.py`, `trials.py` | attuale | — | Moduli aggiunti il 2026-09-12: trasformazione da log2FC a conteggi con vincolo compositivo (D-015), misura di RAM/disco e memoria di picco, definizione dei trial. Coperti da 33 test in `tests/test_trial_inference.py` (conteggio del 24 settembre) | — |
| `scripts/43_freeze_trial.py`, `44_calibrate_transfer.py`, `45_generate_prediction.py`, `46_validate_package.py`, `47_resource_report.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `scripts/43_freeze_trial.py`, `scripts/44_calibrate_transfer.py`, `scripts/46_validate_package.py`, `scripts/47_resource_report.py`. Gli stadi del trial: congelamento dello stato, calibrazione annidata, generazione, convalida e packaging, consolidamento delle risorse. Eseguiti il 2026-09-12; i risultati leggeri sono in `reports/invii/trial_2026-09-12/`. Lo stadio 45 resta: dal 24 settembre genera solo con `--effects` (D-043) | — |
| `tests/test_trial_inference.py` | attuale | — | 33 test (24 settembre) su vincolo compositivo, conservazione dell'identità dei contesti, generazione dei conteggi, ampiezza degli offset CSR, misura delle risorse e definizione del trial, seme compreso. I test di selezione annidata sono usciti il 23 settembre, quelli delle firme e di trial-00/01 il 24 | — |
| `reports/invii/trial_2026-09-13/` | attuale | — | Artefatti del packaging a memoria limitata di trial-01: report della corsa, manifesto, e `source_snapshot.tar.gz` — **il codice, non i suoi hash**: 66 file, 180 KB, verificato che ricostruisca i moduli byte per byte. Il `.vcc` (3,91 GiB) resta in `artifact_root`. Introdotti da [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) | [R-012](#r-012--reportstrial_2026-09-13) |
| `reports/invii/trial_2026-09-13/submit_PNn227rxP3bVByS37W41.json`, `status_PNn227rxP3bVByS37W41.json`, `submission_PNn227rxP3bVByS37W41.md` | attuale | — | La prima sottomissione valutata: output verbatim di `vcc submit` e `vcc status`, più la loro lettura ordinata. **Punteggio 0,045929, rango 446/920.** Non sovrascrivere: sono l'unica prova di che cosa il server ha risposto quel giorno | [R-012](#r-012--reportstrial_2026-09-13) |
| `reports/invii/trial_2026-09-17/submission_texts.md` | attuale | — | I testi di nome e descrizione delle sottomissioni t02 e t03, scritti prima di mandarle. Sezione «Correzioni» in fondo: ogni numero corretto dopo la generazione è annotato lì, con la fonte | — |
| `reports/invii/trial_2026-09-17/t02/` | attuale | — | Prove del file t02 prodotto su Colab il 2026-09-17 (job 011): `generation.json` (269/300 bersagli coperti, bin cis, diagnostica per contesto), `packaging.json` e manifesto (24 convalide PASS, X bit-identica all'ingresso), `prediction.vcc.sha256` e il log completo del job. Il `.vcc` (3,88 GiB) resta sul Drive, non nel repository | — |
| `reports/invii/trial_2026-09-17/t03/` | attuale | — | Prove del file t03 (ampiezza di trasferimento 2,0, job 014): stessa forma del t02. **Generato e verificato ma mai sottomesso**, vedi [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) §6 | — |
| `reports/invii/trial_2026-09-17/submit_49Gvtu504clN1mIu8T2V.json`, `reports/invii/trial_2026-09-17/status_49Gvtu504clN1mIu8T2V.json`, `reports/invii/trial_2026-09-17/submit_t02_raw.json` | attuale | — | La seconda sottomissione valutata (t02): output verbatim di `vcc submit` e `vcc status`, più la cattura grezza del comando. **Punteggio −0,092774, rango 764.** Contiene i valori **grezzi** di tutti e sei i membri, che sono ciò che ha reso risolvibili le ancore. Non sovrascrivere | — |
| `reports/gara/anchors_2026-09-17/anchors.json` | da-verificare | — | JSON storico immutato: trasformazioni affini di cinque membri ricavate da due invii; il claim interno di conversione esatta è smentito su t03/t25. Restano pesi riproducibili per gli indici locali congelati, non ancore per contesto identificate; MSE indeterminata. Leggere SCORE_CREDIBILITA e CP-0050 prima dell'uso | [R-022](#r-022--ancore-aggregate-e-indipendenza-della-conferma) |
| `reports/invii/prediction_t03_2026-09-17/prediction.json`, `scripts/84_predict_official.py` | attuale | — | Previsione **registrata prima** della sottomissione: dai grezzi del banco h002, dal punto di calibrazione t02 e dalle ancore ufficiali, media attesa +0,0338 per il t03. Calibrazione a un solo punto per membro, senza barra d'errore: è una previsione, non una misura. Non sovrascrivere, serve al confronto con il punteggio reale | — |
| `reports/invii/trial_2026-09-17/submit_0TbVAwhVTj6UYpaU2v9d.json`, `reports/invii/trial_2026-09-17/status_0TbVAwhVTj6UYpaU2v9d.json`, `reports/invii/trial_2026-09-17/submit_t03_raw.json` | attuale | — | Terzo invio valutato: **punteggio +0,019692, rango 576**, evidenza ufficiale immutata. Il confronto fuori campione non verifica l'esattezza delle ancore: scarto sulla media +0,0007302, misurato in CP-0050 | [R-022](#r-022--ancore-aggregate-e-indipendenza-della-conferma) |
| `reports/gara/anchors_2026-09-17/three_points/anchors.json` | da-verificare | — | Conserva la ricostruzione del terzo invio senza usarlo nel fit; i residui fino a circa 0,002 per membro smentiscono la pretesa esattezza. Non trattare questa verifica come identificazione delle ancore dei contesti | [R-022](#r-022--ancore-aggregate-e-indipendenza-della-conferma) |
| `reports/generatore_e_banchi/prediction_calls_2026-09-17/t02_r4000/` | attuale | — | Stadio 83 sul file t02 già sottomesso: quanti geni dichiara significativi sui contesti ufficiali (mediana 53/17/1 in A/B/C, media 288/231/95, su 4.000 controlli dei 18.400 — quindi un **limite inferiore**), e il controllo sul gene bersaglio, che risulta abbassato solo del 5-9% invece che dell'85%. Nessun `k` e nessun `n_conf`: richiedono i dati perturbati nascosti | — |
| `reports/gara/contexts_2026-09-17/`, `scripts/85_identify_contexts.py` | attuale | — | Che cosa sono i contesti ufficiali, dai marcatori di lignaggio nelle loro cellule di controllo. **Misurato:** A è un linfocita T (`CD3D` 943 CPM nel 100% delle cellule), B è cheratine+/E-caderina−/vimentina-alta, C è epiteliale coeso (`EPCAM` 312, `VIM` 2,0). Pluripotenza, marcatori eritroidi ed epatocitari **assenti in tutti e tre**: K562 e HepG2 non condividono il lignaggio con nessun bersaglio. I nomi di linea (Jurkat, HEK293) sono ipotesi, il lignaggio è misura | — |
| `reports/invii/trial_2026-09-17/t04/` | attuale | — | Prove del file t04 (`--max-calls 150`, mediana di geni mossi esattamente 150 per contesto). **Generato e mai sottomesso**: [CP-0022](checkpoints/0022-previsione-verificata-t03.md) misura che va nella direzione contraria ai dati. Resta come controllo | — |
| `reports/generatore_e_banchi/call_budget_2026-09-17/c001/` | storico | — | Stadio 80 sulle statistiche a singola cellula, contesti A/B/C, 20 bersagli, pool di riferimento da 1.500 cellule: quante chiamate producono le ampiezze 1,0 e 2,0. **Regime più piccolo di quello ufficiale** (18.400 controlli), quindi un limite inferiore | — |
| `reports/storico/source_coverage_2026-09-17/c001/`, `reports/storico/source_coverage_2026-09-17/c002/`, `scripts/86_source_panel_coverage.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `scripts/86_source_panel_coverage.py`. Quanto del pannello del banco HepG2 copre ciascuna sorgente di trasferimento, misurato prima di spendere Colab. **Misurato:** dei 1.061 bersagli HepG2 con almeno 50 cellule, RPE1 ne copre 1.061 e K562 genome-wide 1.059; RPE1 misura 7.733 dei 9.624 geni HepG2, K562 7.425. Mediana di cellule per bersaglio 101 (RPE1) contro 184 (K562), cellule NTC 11.485 contro 75.328: la copertura non e' il confondente, la profondita' lo e'. `shared_targets.txt` e' il pannello condiviso (1.059) che i due bracci devono usare per essere confrontabili: `c002` (stessa misura piu' il controllo di selezione) misura che **senza** `--targets-file` i due banchi condividerebbero solo **205 bersagli su 300**, e con esso 300 su 300 | — |
| `configs/source_lineage_rule.yaml`, `scripts/87_compare_source_benches.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Regola **pre-registrata** (scritta il 2026-09-18 ~00:15, prima che i job 018 e 019 producessero qualsiasi cosa) per leggere il confronto RPE1 contro K562 sul banco HepG2, e lo stadio che la applica meccanicamente. Contiene il cancello di validita: `replicate`, `baseline` e `null_new` non leggono la sorgente e devono coincidere, altrimenti i due banchi non condividono una verita e il confronto e nullo. `owner_confirmed: false` alla stesura; dal 18 intorno alle 13:00, prima dei risultati, `owner_confirmed: true` con `verdict_scope` (una vittoria merita un approfondimento, non un'adozione). Soglia e bracci invariati | — |
| `reports/storico/source_lineage_2026-09-18/` | attuale | — | Il confronto RPE1 contro K562 sul banco HepG2. `PRIMA_DEI_RISULTATI.md` è scritto **prima** che esistesse qualunque output: registra che i job 018 e 019 non hanno prodotto nulla (runtime perso il 17 intorno alle 22:10 UTC) e sono stati rimessi in coda come 020 e 021 con output `_r2`, e dichiara due letture secondarie che la regola non conteneva: la fedeltà a parità di chiamate (volume contro direzioni) e lo stato di TP53 come spiegazione alternativa al lignaggio. Non cambia la regola né la soglia. Il suo §4 registra la revisione del proprietario, sempre prima dei risultati, e la copertura dei bersagli ufficiali (RPE1 0/300). **Risultati** ([CP-0023](checkpoints/0023-rpe1-contro-k562-su-hepg2.md)): i due `bench.json` copiati da Drive; `c001/` è lo stadio 87 (verdetto `WINS_RPE1`, cancello passato); `c002/` è lo stadio 88 (vantaggio +0,056…+0,096 a parità di chiamate medie, pre-registrato; confronto appaiato esplorativo scelto dopo i risultati). **Controllo d'identità** ([CP-0024](checkpoints/0024-identita-del-bersaglio-su-hepg2.md)): `*_r3_bench.json` (job 022/023); `c003/` è lo stadio 89 (riproducibilità passata; K562 `MIXED`, RPE1 `SPECIFIC`, vantaggio di RPE1 `MAINLY_COMMON` alla coppia a ~100 chiamate); `c004/` è lo stadio 90, precisione per bersaglio, esplorativo | — |
| `reports/storico/conditioned_2026-09-18/`, `configs/conditioned_rule.yaml`, `scripts/92_train_conditioned.py`, `scripts/93_pick_amplitudes.py`, `scripts/94_conditioned_verdict.py`, `src/vcc2026/conditioned.py`, `src/vcc2026/bench_score.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `configs/conditioned_rule.yaml`, `scripts/92_train_conditioned.py`, `scripts/93_pick_amplitudes.py`, `scripts/94_conditioned_verdict.py`, `src/vcc2026/conditioned.py`, `src/vcc2026/bench_score.py`. Primo predittore neurale condizionato su bersaglio e contesto (mandato del proprietario del 18 settembre). Rete in numpy (cancello di trasferimento per gene + termine bilineare bersaglio × gene; il contesto entra per gene come espressione basale nei controlli) contro un modello lineare con gli stessi input, il trasferimento semplice e la ricetta t03, con lo stesso generatore e gli stessi bersagli. Tre split: contesto nuovo (C), congiunto (J), bersagli nuovi (T). `panel/` fissa i bersagli prima del training; regola scritta prima di ogni training su dati reali, `owner_confirmed: false`. **Esito** ([CP-0026](checkpoints/0026-predittore-neurale-condizionato.md)): `DISCARD`, in `verdict/`. `benches/` contiene i quattro `bench.json` (validazione e test) e le scelte dello stadio 93; `effect_space/` le letture centrate dello stadio 95 (esplorative); `train*_manifest.json` i training; `PIANO_INVIO_t06.md` il piano di invio scritto prima dei risultati, con l'aggiunta che sostituisce il t06 con il t07. Job 028, 033, 034, 037 (ucciso per memoria), 038, 039 e 041 | — |
| `reports/storico/common_component_2026-09-18/`, `configs/common_component_rule.yaml`, `scripts/91_common_component_verdict.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `configs/common_component_rule.yaml`, `scripts/91_common_component_verdict.py`. Tenere o scartare la componente comune RPE1 (`common_from_bulk`, termini `common_aX` e `permcommon_aX` negli stadi 73 e 75, `--a-common` nello stadio 76). Disegno scelto dal proprietario: peso scelto su un insieme di bersagli e verdetto su un altro, disgiunto, in due banchi (HepG2 con la ricetta t03; bersagli ufficiali in K562); si tiene solo se passano entrambi. `panel/` contiene i file dei bersagli, fissati prima dei job 024-027. Regola scritta prima dei job, `owner_confirmed: false`. **Esito** ([CP-0025](checkpoints/0025-componente-comune-scartata.md)): `DISCARD`, in `c001/verdict.json`, con i quattro `bench.json` copiati accanto | — |
| `reports/invii/trial_2026-09-19/` | storico | — | File generati la notte del 19 settembre. `t06/`: la rete condizionata (job 040), generata e impacchettata ma **non inviata**, perché il modello rilanciato dal job 039 non è quello giudicato dai banchi (`reports/storico/conditioned_2026-09-18/PIANO_INVIO_t06.md`). `t07_job042/`: il log del primo tentativo di generare il t07, interrotto durante l'impacchettamento dalla perdita del runtime (circa 02:14 UTC); nessun file del t07 è arrivato su Drive. `t07/`: il t07 rigenerato dal job 043 e **inviato** il 19 alle 09:42:58 UTC (entry `BV1gqrIYuy2KMVZSGmN4`, punteggio −0,016004, rango 671), con i record di generazione e impacchettamento; accanto, l'output verbatim di `vcc submit` e `vcc status` e i testi della sottomissione ([CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)) | — |
| `reports/invii/prediction_t07_2026-09-19/`, `scripts/95_centered_effect_space.py` | attuale | — | **Archiviati il 23 settembre** (D-040): `scripts/95_centered_effect_space.py`. Previsione del punteggio ufficiale del t07 (stadio 84), registrata il 2026-09-19 alle 01:22 UTC prima dell'invio: +0,0101; ufficiale −0,0160 (`comparison.json`, [CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)). Lo stadio 95 misura la parte di una previsione specifica del bersaglio (correlazione centrata, accoppiamento, confronto con la media) | — |
| `configs/specificity_rule.yaml`, `scripts/88_matched_volume_reading.py`, `scripts/89_specificity_reading.py`, `scripts/90_per_target_precision.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 90: precisione dei segni `k/n_pred` per bersaglio dai `components_<braccio>.csv`, esplorativa. 88: la lettura di due banchi a parità di chiamate medie, più un confronto appaiato per bersaglio dichiarato come scelto dopo i risultati. 89 e la regola: il controllo d'identità del bersaglio (`shuffled_aX`) per i job 022 e 023. Regola scritta prima dei job; **versione 2** scritta dopo il loro avvio ma prima di ogni output, perché un test sintetico a risposta nota mostrava che la versione 1 chiamava `MIXED` una sorgente nulla. `owner_confirmed: false` | — |
| `scripts/82_solve_anchors.py`, `83_prediction_calls.py` | attuale | — | 82: risolve base e replica dal doppio output di `vcc status`. 83: conta quanti geni una previsione generata dichiara significativi contro le cellule di controllo ufficiali (`n_pred`) — non calcola `k` né `n_conf`, che richiedono i dati perturbati nascosti | — |
| `src/vcc2026/packaging.py` | attuale | — | Convalida e packaging `.vcc` senza materializzare la matrice. Le convalide sui metadati **sono** quelle ufficiali, importate e chiamate; quelle sulla matrice sono equivalenti a blocchi. Rifiuta esplicitamente i layout che non sa preservare | — |
| `scripts/48_package_prediction.py` | attuale | — | Lo stadio che convalida, impacchetta e verifica. Esce con codice diverso da zero se qualcosa fallisce, e non scrive nulla se la convalida non è pulita | — |
| `tests/test_packaging_parity.py` | attuale | — | 46 test di parità (la riga diceva 41; contati il 24 settembre) contro `vcc prep` 0.2.0 su fixture a forma ufficiale completa: stessa accettazione, stesso rifiuto, stesse codifiche HDF5. Circa 98 s | — |
| `notebooks/kaggle_package_trial01.ipynb` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Percorso remoto per la stessa implementazione su Kaggle CPU. **Non eseguito**: il run locale è riuscito. Resta pronto per il set finale D/E/F | — |
| `tests/test_pipeline_contracts.py` | attuale | — | Contratti che fallirebbero in silenzio. Al 24 settembre restano 7 test: manifesti che non si sovrascrivono e registrano ambiente e seme, impronte dei file, radice dei dati portabile. I test di split e registry sono usciti il 23 settembre, quelli di allineamento, firme, modelli e metriche in pseudobulk il 24, con il loro codice (D-043) | — |
| `docs/ORCHESTRATORE.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Architettura dell'orchestratore locale per le consultazioni multi-modello. Dichiara in testa che cosa e' stato eseguito e che cosa e' solo implementato: gli adattatori verso i servizi reali non sono mai stati usati | — |
| `src/orchestrator/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Il codice dell'orchestratore: motore, contratto di risposta, stato persistente, adattatori, rapporto, CLI. Solo libreria standard, tranne PyYAML per le configurazioni YAML e Playwright per gli adattatori web | — |
| `configs/orchestrator/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Configurazione operativa, profili dei servizi web, incarichi e risposte preparate a mano per le prove a secco. I profili di DeepSeek e Kimi sono `verified: true` dal 13 settembre, ciascuno citando l'invio reale che lo giustifica. **Solo DeepSeek dichiara un controllo di ricerca sul web** (`ricerca_intelligente`); su Kimi non ne è mai stato osservato uno | — |
| `scripts/orch.cmd` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Wrapper della console `orch`, come `py.cmd`: UTF-8 e `src/` sul PYTHONPATH. Usa `VCC2026_ORCH_PYTHON` se impostata, per tenere Playwright fuori dall'ambiente di analisi | — |
| `tests/test_orchestrator.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 95 test sui modi in cui l'orchestratore potrebbe sbagliare in silenzio: incarico modificato senza versione, materiale fuori perimetro, risposta che prova a cambiare le regole, doppio invio dopo un crash, accordo scambiato per verifica, servizio morto sostituito | — |
| `reports/storico/orchestrator/` | storico | — | Copie di esecuzioni dell'orchestratore tenute come evidenza. Le prove del 13 e del 14 settembre sono **a secco**. Puntatore alla campagna Jiang live del 15 settembre: `reports/storico/orchestrator/jiang-audit-20260915.md` (run in `VCC2026_DATA_ROOT`, fermata `service_unavailable`) | — |
| `docs/RICERCA_SCIENTIFICA.md` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). La modalità `scientific_research`: tre fasi, livelli di provenienza, deduplicazione delle fonti, regola delle piste, dossier. Dichiara in testa riga per riga che cosa è stato provato e che cosa no. Introdotta da [CP-0010](checkpoints/0010-modalita-ricerca-scientifica.md) | — |
| `src/orchestrator/research/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Il codice della modalità di ricerca: contratto, prompt delle tre fasi, scelta deterministica delle piste, dossier e rapporto, motore. Non importa `oracle` né alcun client HTTP, e c'è un test per entrambe le cose | — |
| `tests/test_orchestrator_research.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). 65 test sulle promozioni che non si annuncerebbero: una ricerca dichiarata che diventa osservata, un riferimento che diventa una fonte, una fonte solo elencata che diventa letta, un'opinione che diventa un risultato riferito dagli autori, due articoli che diventano uno | — |
| `reports/storico/orchestrator/prova-a-secco-ricerca-2026-09-14/` | storico | — | La campagna di ricerca di prova, per intero: dossier, piste, rapporto, eventi e cartelle dei passi. **I contenuti delle risposte sono inventati**, con DOI a prefisso `10.0000/finta-`. Dimostra il motore, non gli adattatori reali | — |
| `docs/oracle/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Contratto del prototipo di oracolo numerico pairwise sulla loss. Indipendente dall'orchestratore; non valuta ipotesi biologiche | — |
| `reports/storico/oracle/` | storico | — | Prima esecuzione della CLI sull'esempio a tre casi. Fixture sintetici, non dati della gara. Introdotti da [CP-0007](checkpoints/0007-oracle-pairwise-loss.md) | — |
| `src/oracle/` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Verificatore `oracle.pairwise_loss` 0.2.1, sola libreria standard, frazioni esatte. Non importa `orchestrator` né `vcc2026`. Correzioni in [CP-0008](checkpoints/0008-oracle-fraction-regression.md) e [CP-0009](checkpoints/0009-oracle-json-number-csv-error.md) | — |
| `tests/test_oracle_pairwise_loss.py` | storico | — | **Archiviato il 23 settembre** (D-040, tag `archivio/pre-pulizia-2026-09-23`, [ARCHIVIO.md](ARCHIVIO.md)). Test su fixture sintetici; i risultati attesi sono calcolati a mano, non generati dal verificatore | — |


## Dati

Nessun file di dati è stato spostato o copiato per compilare questo registro. I dati
pesanti stanno fuori dal repository, sotto `C:/Users/ferra/vcc2026-data`
(vedi `configs/config.yaml`). Dal 16 settembre due grezzi pesanti stanno anche sul
Google Drive del proprietario, secondo la sua dichiarazione
([CP-0018](checkpoints/0018-drive-storage-confermato.md)).

Tipi: `grezzo` (sorgente scaricata, da non modificare), `derivato` (prodotto da uno
script nostro), `campione` (piccolo estratto di verifica), `temporaneo` (cache o
dipendenza di runtime, ricreabile).

Alcune righe qui sotto indicano un percorso dentro `reports/` che **un clone non contiene**:
è un artefatto pesante che `.gitignore` tiene fuori (`*.h5ad`, `*.vcc`, …), e ne viaggia
solo il manifesto, con URL, byte e sha256. `scripts/31_check_docs.py` accetta il percorso
quando il manifesto gli sta accanto, e continua a segnalarlo quando non c'è: così il controllo
dà lo stesso esito su un clone e sulla macchina che ha prodotto il file. Viene dalla
correzione `5eb130c` del 15 settembre, portata il 24.

| Identificatore | Tipo | Stato | Provenienza | Riproducibile con | Nota |
|---|---|---|---|---|---|
| `MyDrive/vcc2026/data/` (Drive), specchio della radice dati | derivato | da-verificare | Copia, con grezzi e derivati: dal 2/10 sera la radice dati si copia qui a percorsi relativi invariati (`<rel>` → `data/<rel>`), a lotti: input dei banchi, originali, derivati, artefatti, intermedi; il CD4 da 41,5 GiB e la cartella R-LEAD attiva restano fuori dal primo giro | `reports/sorgenti/archivio_cloud_2026-10-02/archivio.py`, ricevute in `processed/archivio_cloud_2026-10-02/r1/` | Diventa `attuale` per i soli file che `verify_drive.py` legge dal runtime Colab con lo sha256 atteso; una copia sul mount del portatile non lo prova |
| `C:/Users/ferra/vcc2026-data/processed/archivio_cloud_2026-10-02/` | derivato | attuale | Stato della migrazione: inventario per file fisico, elenco dei metadati di Drive, piano, hash sha256 e md5, ricevute di copia, log | `reports/sorgenti/archivio_cloud_2026-10-02/archivio.py` | Un tentativo per cartella `rN/`; niente si scrive sopra |
| Kaggle, dataset privati `davidmaisterx/rlab-*` del corpus cellulare | derivato | attuale | 21 dataset del corpus pubblicati dai job Colab del 30/09–1/10 (più `rlab-cellnet-code`); il 2/10 il server Kaggle elenca per ciascuno tutti gli shard della ricevuta su Drive, con gli stessi byte. Superati da incidenti: `rlab-k562-gwps`, `-r2`, `rlab-k562-essential`, `rlab-rpe1` (E-20260930-003/-004); copie anteriori su `davideferrante11` | `reports/sorgenti/corpus_cellulare_2026-09-30/publish_kaggle.py` | sha256 lato Kaggle dal kernel `davidmaisterx/archivio-verify-corpus-r1` (`reports/sorgenti/archivio_cloud_2026-10-02/kaggle_verify/`) |
| `C:/Users/ferra/vcc2026-data/processed/ingestione_completa_2026-10-03/` | derivato | attuale | Setup locali dei job dell'ingestione completa (`setup_verify_r2/`; `setup_verify_r2_preflight_order_failed/`, primo tentativo fermato dal preflight locale prima di ogni coda) | `reports/sorgenti/ingestione_completa_2026-10-03/requeue_verify.py` | Un tentativo per cartella; niente si scrive sopra |
| `C:/Users/ferra/vcc2026-data/processed/ibrido_selettivo_2026-10-04/` | derivato | attuale | Ibrido selettivo D-056: stage dei dataset del codice e dei kernel (pre-passo Jurkat, ancore, training, corsie), output piccoli scaricati | `reports/modelli/ibrido_selettivo_2026-10-04/` | Un tentativo per cartella; niente si scrive sopra |
| `C:/Users/ferra/vcc2026-data/processed/rete_ancorata_v4_2026-10-03/` | derivato | attuale | Rete ancorata v4: ricevute grezze dei training v3 r1 (`r1_logs_raw/`, sha256 in `diagnosi_r1/log_r1/fetch_receipt.json`), stage dei dataset del codice e dei kernel (gemelli, ancore, training, generazione), output piccoli scaricati | `reports/modelli/rete_ancorata_v4_2026-10-03/kaggle_*.py`, `diagnosi_r1/fetch_r1_logs.py` | Un tentativo per cartella; niente si scrive sopra |
| Kaggle, output dei kernel `davideferrante11/rcell-v4-fast-{a,b,c}-r1` | derivato | attuale | Gemelli compatti dei 365 shard del corpus a 8 gruppi (21,25 GB contro 53,32), ciascuno con sha256 della sorgente uguale a `files.json` e decodifica esatta; i tre `fast_manifest.json` coprono i 365 shard dei training v3 senza fallimenti (3/10 23:03) | `reports/modelli/rete_ancorata_v4_2026-10-03/build_fast.py` | Manifest e log in `reports/modelli/rete_ancorata_v4_2026-10-03/esito/`; un gemello vale solo per lo shard di quel sha256 |
| `C:/Users/ferra/vcc2026-data/processed/rete_ancorata_2026-10-03/` | derivato | attuale | Rete ancorata: dataset Kaggle del codice delle ancore (`kaggle_anchor_code_r1/`) e kernel delle ancore preparato (`kernel_anchors_r1/`) | `reports/modelli/rete_ancorata_2026-10-03/kaggle_anchors.py` | Un tentativo per cartella; niente si scrive sopra |
| `C:/Users/ferra/vcc2026-data/processed/rete_cellulare_2026-10-03/` | derivato | attuale | Rete cellulare v2: chiavi riconciliate dei bersagli (`target_keys_r1.json`), dataset Kaggle preparati (`kaggle_code_r1/`, `kaggle_gen_r1/`, `kaggle_gen_r2/`), kernel preparati (`kernel_prepass_*_r1/`, `kernel_train_*_r1/`), output piccoli scaricati (`out_prepass_*_r1/`, senza lo stato `.pkl` che resta su Kaggle) | `reports/modelli/rete_cellulare_2026-10-03/target_keys.py`, `kaggle_train.py`, `kaggle_gen.py` | Un tentativo per cartella; niente si scrive sopra |
| `C:/Users/ferra/vcc2026-data/processed/generalizzazione_contesti_2026-10-02/` | derivato | attuale | R-LEAD P0–P3: universo HepG2 (cellule locali di Nadig, stimatore `min_expected` 1, metà A/B indipendenti) in `hepg2_r2/` (`hepg2_r1/` vuota: tentativo fermato prima di scrivere, controlli scartati per `nperts`); copertura dei geni di P0 in `p0_p0_r1/`; cubo del banco in `cube_r1/` (float16, manifest con sha256 di ogni file); corse P3 in cartelle nuove; log in `logs/` | `reports/modelli/risposta_contesto_2026-10-02/hepg2_universe.py`, `p0_inventory.py`, `cube.py`, `p3_run.py` | Un tentativo per cartella; niente si scrive sopra |
| `C:/Users/ferra/vcc2026-data/processed/corpus_cellulare_2026-09-30/` | derivato | attuale | Shard cellulari di R-LAB sul portatile: il pilota HepG2 `pilot_hepg2_r1/` (1.000 cellule, 10,4 MB, sha256 in `pilota_hepg2_r1.json`); le prove locali `smoke_r1/`–`smoke_r3/` su ritagli dei file veri (esito in `smoke.json`); gli snapshot del codice dei job, `setup_r1/` e `setup_r2/`, con sha256 in `jobs_r1/build.json` e `jobs_r2/build.json` | `reports/sorgenti/corpus_cellulare_2026-09-30/shard_writer.py`, `smoke_test.py`, `build_jobs.py` | Un attempt per cartella; niente si scrive sopra |
| `MyDrive/vcc2026/data/processed/corpus_cellulare_2026-09-30/` (Drive) | derivato | da-verificare | Shard cellulari dei job J01 (HepG2), J03 (Jurkat) e J02 (HIPSCI), una cartella per job con ricevute per shard, `manifest.json` per unità e `complete.json` scritto per ultimo. **Al 30/09, 20:50, i job sono in coda e nessuno è partito** | `reports/sorgenti/corpus_cellulare_2026-09-30/rlab_job.py` con `jobs_r1/` | Diventa `attuale` quando si leggono `complete.json` e le parità dei manifest; le ricevute di ambiente e preflight stanno in `MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/receipts/` |
| `MyDrive/vcc2026/data/raw/vcc2025_h1_2026-09-30/` (Drive) | grezzo | da-verificare | Il rilascio H1 della gara 2025 dal bucket pubblico di Arc (`gs://arc-institute-virtual-cell-atlas/virtual-cell-challenge/2025/`): tre h5ad, 34,36 GB, più CSV e asse. **Lo split di test è la riserva scelta dal proprietario il 30/09: non si apre.** Train e validation vanno nel training. Job 089 in coda, dopo J02 | `reports/sorgenti/corpus_cellulare_2026-09-30/fetch.py`, `publish.py`, `jobs_r2/` | crc32c del bucket verificato e sha256 registrato nel `manifest.json` della cartella; ruoli in `reports/modelli/risposta_biologica_2026-09-30/holdout_registry_r2.json` |
| `C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-26.csv` | derivato | attuale | Profili basali (CPM) di K562, CD4 (tre condizioni e media), HCT116 e HEK293T dalle righe di controllo, più A/B/C | `reports/trasferimento/trasferimento_appreso_2026-09-26/basal_profiles.py` | Accanto il `.json` con i conteggi |
| `C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-27.csv` | derivato | attuale | La tabella del 26/09 con le colonne `kolf` e `a549` aggiunte (CPM dei controlli dalle somme, stessa definizione) | `reports/sorgenti/universo_nuovi_2026-09-27/basal_from_sums.py` | Accanto il `.json` con i conteggi |
| `C:/Users/ferra/vcc2026-data/processed/universe_a549_2026-09-27_me1/` | derivato | attuale | A549, knockout Cas9 (GSE345058): 1.000 bersagli su 1.000 con effetti, 2 blocchi, 143 MB, stimatore corretto | `reports/sorgenti/universo_kolf_2026-09-27/kolf_effects.py` (`--name a549`) | Un'altra modalità (knockout), non una sorgente dello stesso intervento; indice e manifest in `reports/sorgenti/universo_nuovi_2026-09-27/a549_me1/` |
| `C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26/` | derivato | attuale | K562 genome-wide pseudobulk (Replogle 2022), tutti i 9.866 bersagli, 17 blocchi npz, 973 MB | `reports/sorgenti/universo_2026-09-26/k562_universe.py` | Formato dello stadio 98; indice e manifest anche nel report |
| `C:/Users/ferra/vcc2026-data/external/cd4_gw/` | grezzo | attuale | Pseudobulk CD4 genome-wide (GSE314342, Marson 2025): `GWCD4i.pseudobulk_merged.h5ad`, 44.566.657.140 byte, dal bucket S3 pubblico `genome-scale-tcell-perturb-seq`, scaricato il 26/09 col via del proprietario; URL, byte e sha256 del file locale nel `.manifest.json` accanto (l'etag S3 è multiparte, non confrontabile) | `reports/sorgenti/universo_2026-09-26/cd4_universe.py` lo legge | Non modificare; è la fonte degli universi CD4 |
| `C:/Users/ferra/vcc2026-data/processed/universe_cd4_2026-09-26/` | derivato | attuale | CD4 genome-wide, tutti i 12.238 bersagli: blocchi npz per condizione (Rest, Stim8hr, Stim48hr) e `cd4_mix`, formato dello stadio 98, `index.csv`, `manifest.json` con gli sha256 | `reports/sorgenti/universo_2026-09-26/cd4_universe.py` | Il primo blocco è il pannello, con parità controllata contro la cache r5 |
| `C:/Users/ferra/vcc2026-data/processed/universe_k562ess_2026-09-26/` | derivato | attuale | K562 essential (Replogle 2022), tutti i 2.057 bersagli, 4 blocchi npz nel formato dello stadio 98 | `reports/sorgenti/universo_2026-09-26/k562_universe.py --name k562ess` | Stessa linea del K562 genome-wide, altro esperimento |
| `C:/Users/ferra/vcc2026-data/processed/universe_rpe1_2026-09-26/` | derivato | attuale | RPE1 essential (Replogle 2022), tutti i 2.393 bersagli, 4 blocchi npz nel formato dello stadio 98 | `reports/sorgenti/universo_2026-09-26/k562_universe.py --name rpe1` | Nessun bersaglio del pannello |
| `C:/Users/ferra/vcc2026-data/processed/universe_orion_hct116_2026-09-26/` | derivato | attuale | X-Atlas/Orion HCT116, tutti i 16.438 bersagli con un pool di almeno 10 cellule (18.293 con cellule), 28 blocchi npz nel formato dello stadio 98, 2,4 GB; 109 file letti in streaming (46,6 GB) | `reports/sorgenti/universo_2026-09-26/orion_universe.py` | Licenza CC-BY-NC-SA-4.0; gli accumulatori per pool stanno in `interim/orion_universe_hct116/` |
| `C:/Users/ferra/vcc2026-data/processed/universe_orion_hek293t_2026-09-26/` | derivato | attuale | X-Atlas/Orion HEK293T, tutti i 17.270 bersagli con un pool di almeno 10 cellule (18.311 con cellule), 29 blocchi npz nel formato dello stadio 98, 2,7 GB; 223 file letti in streaming (79,7 GB) | `reports/sorgenti/universo_2026-09-26/orion_universe.py` | Licenza CC-BY-NC-SA-4.0; gli accumulatori per pool stanno in `interim/orion_universe_hek293t/` |
| `C:/Users/ferra/vcc2026-data/processed/universe_cd4_2026-09-27_me1/` | derivato | attuale | CD4 genome-wide (tre condizioni e `cd4_mix`) ricostruito con lo stimatore corretto (`min_expected` 1); parità esatta con la cache r9 sui bersagli del pannello | `reports/sorgenti/universo_corretto_2026-09-27/rebuild.py` | Sostituisce `universe_cd4_2026-09-26` per i banchi dal 27/09 |
| `C:/Users/ferra/vcc2026-data/processed/universe_orion_hct116_2026-09-27_me1/` | derivato | attuale | HCT116 ricostruito con lo stimatore corretto: 16.438 bersagli, 2,3 GB; parità esatta con r9 | `reports/sorgenti/universo_corretto_2026-09-27/rebuild.py` | — |
| `C:/Users/ferra/vcc2026-data/processed/universe_orion_hek293t_2026-09-27_me1/` | derivato | attuale | HEK293T ricostruito con lo stimatore corretto: 17.270 bersagli, 2,6 GB; parità esatta con r9 | `reports/sorgenti/universo_corretto_2026-09-27/rebuild.py` | — |
| `C:/Users/ferra/vcc2026-data/processed/universe_kolf_2026-09-27_me1/` | derivato | attuale | KOLF2.1J (iPSC), 10.985 bersagli su 11.687 con effetti, 20 blocchi, 1,5 GB, stimatore corretto | `reports/sorgenti/universo_kolf_2026-09-27/kolf_effects.py` | Licenza CC BY 4.0; indice e manifest in `effetti_me1/` |
| `C:/Users/ferra/vcc2026-data/interim/kolf_sums/` | derivato | attuale | Somme per (bersaglio, gruppo di canali) di KOLF2.1J: 32 blocchi e `sums.npz` fuso (92.636 gruppi x 18.533 geni) | `reports/sorgenti/universo_kolf_2026-09-27/kolf_sums.py` | Rigenerabile dal file remoto |
| `C:/Users/ferra/vcc2026-data/interim/a549_sums_r2/` | derivato | attuale | Somme di GSE345058 (A549, knockout) per (bersaglio, gruppo di lane), copiate da Drive con il log del job 048 | `reports/sorgenti/universo_nuovi_2026-09-27/h5ad_sums.py` | Stima ancora da fare |
| `C:/Users/ferra/vcc2026-data/interim/hipsci_sums/` | derivato | da-verificare | Somme dei tre schermi HIPSCI, per linea nel mirato | `reports/sorgenti/universo_hipsci_2026-09-27/hipsci_sums.py` | Esecuzione del 27/09 sera |
| `C:/Users/ferra/vcc2026-data/processed/corpus_basale_2026-09-28/` | derivato | attuale | Corpora di profili basali: `ours` (3.326 profili in 32 contesti), `vcc_abc` (138), `depmap_v2` (1.667 linee), `tahoe_s5u` (650 profili in 48 linee). `depmap` è la prima versione, con `n_cells` −1 che l'encoder avrebbe scartato: non usarla; `tahoe_s5` è la cartella vuota di un tentativo fallito | `reports/sorgenti/corpus_basale_2026-09-28/corpus_ours.py`, `corpus_tahoe.py` | Copie piatte per Kaggle, con il gruppo negli id dei profili, in `kaggle/corpus_basale_r1/` e `kaggle/corpus_tahoe_r1/` |
| `C:/Users/ferra/vcc2026-data/interim/tahoe_dmso_subset_s5_u/` | derivato | attuale | Somme dei conteggi grezzi delle cellule DMSO di Tahoe-100M per linea × piastra, da 678 frammenti su 3.388 (uno ogni cinque): 434.966 cellule, 700 gruppi, 50 linee, 2,69 GB letti. `tahoe_dmso_subset_s5/` è la stessa estrazione con le stringhe salvate come oggetti (servirebbe pickle): non usarla | `reports/sorgenti/tahoe_dmso_2026-09-28/extract_dmso_subset.py` (`--step 5`) | Stessi numeri nelle due cartelle |
| `C:/Users/ferra/vcc2026-data/external/tahoe100m/` | grezzo | attuale | Tahoe-100M (CC0, Hugging Face `tahoebio/Tahoe-100M`): le quattro tabelle piccole di metadati e un frammento intero (`train-01031`) per la verifica dell'estrattore | download diretto | Il frammento serve solo alla verifica |
| `C:/Users/ferra/vcc2026-data/processed/rete_contesti_r1/` | derivato | attuale | Il dataset della rete r1: 91.860 righe (K562, tre condizioni CD4, HCT116, HEK293T, KOLF2.1J; A549 fuori per modalità), 12.477 geni, 6,88 GB; su Kaggle come dataset privato `vcc-rete-contesti-r1` (collegamenti fisici in `kaggle/rete_data_r1/`) | `reports/modelli/rete_contesti_2026-09-27/data.py` | |
| `C:/Users/ferra/vcc2026-data/processed/rete_contesti_r2/` | derivato | attuale | Il dataset della rete r2: 109.586 righe in 13 contesti (A549 fuori per modalità), 13.248 geni, 8,2 GB su disco; controllo con il lettore degli universi: 0 discrepanze su 20 righe per contesto; su Kaggle come `vcc-rete-contesti-r2` | `reports/modelli/rete_contesti_2026-09-27/data.py --registry reports/modelli/rete_contesti_r2_2026-09-28/contesti_r2.csv --basal processed/basal_sources_2026-09-28.csv` | |
| `C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-27_r2.csv` | derivato | attuale | La tabella basale del 27/09 con `rpe1` e `k562ess` (righe non miranti dei file bulk di Replogle) | `reports/sorgenti/universo_nuovi_2026-09-27/basal_from_bulk.py` | Accanto il `.json` |
| `C:/Users/ferra/vcc2026-data/processed/basal_sources_2026-09-28.csv` | derivato | attuale | La tabella r2 del 27/09 con `viperturb`, `hipsci_fit` e `hipsci_nonfit` (CPM dei controlli dalle somme) | `reports/sorgenti/universo_nuovi_2026-09-27/basal_from_sums.py` | Accanto il `.json` |
| `C:/Users/ferra/vcc2026-data/interim/viperturb_sums/` | derivato | attuale | Somme di VIPerturb-seq (Flex, K562) per (bersaglio, pool): `sums_p8.npz` (8 pool), `sums_p1.npz` (uniti), `half_a.npz` e `half_b.npz` (pool 0–3 e 4–7, uniti ciascuno in un pool, per la prova metà contro metà) | `reports/sorgenti/universo_nuovi_2026-09-27/r_sums_pack.py`, `reports/sorgenti/ponte_flex_2026-09-28/half_pools.py` | |
| `C:/Users/ferra/vcc2026-data/processed/universe_viperturb_2026-09-27_p1/` | derivato | attuale | VIPerturb-seq: effetti dai pool uniti, stimatore corretto | `reports/sorgenti/universo_kolf_2026-09-27/kolf_effects.py` (`--name viperturb`) | Indice e manifest in `reports/sorgenti/universo_nuovi_2026-09-27/viperturb_p1/` |
| `C:/Users/ferra/vcc2026-data/processed/universe_viperturb_2026-09-28_halfa/`, `..._halfb/` | derivato | attuale | VIPerturb-seq a metà profondità: 6.063 e 6.162 bersagli con effetti | `kolf_effects.py` su `half_a.npz` e `half_b.npz` | Indici e manifest in `reports/sorgenti/ponte_flex_2026-09-28/r2/` |
| `C:/Users/ferra/vcc2026-data/interim/hipsci_sums/targeted_p2/` | derivato | attuale | Lo schermo mirato HIPSCI con gli 8 pool uniti in 2 (pool % 2): 17.778 gruppi, 444 bersagli per linea | `reports/sorgenti/universo_nuovi_2026-09-27/repool_sums.py --pools 2` | |
| `C:/Users/ferra/vcc2026-data/processed/universe_hipsci_<linea>_2026-09-28_p2/` | derivato | attuale | Effetti per linea dello schermo mirato HIPSCI, 19 linee (circa 440 bersagli ciascuna, 194 per fiaj_3); controllo sul bersaglio in `reports/sorgenti/universo_hipsci_2026-09-27/linee_p2/`: mediana tra −1,0 e −1,8 in 15 linee, debole in fiaj_3, tolg_4, pipw_5, oikd_2 | `reports/sorgenti/universo_kolf_2026-09-27/kolf_effects.py --context <linea>` | |
| Kaggle, uscite dei kernel `vcc-tahoe-arms-s5` e `vcc-tahoe-t1` | derivato | attuale | Bracci farmacologici di Tahoe (73 farmaci più DMSO, un frammento ogni cinque): 13.508 gruppi sull'asse ufficiale in float32; effetti di 10.325 bracci; T1 ridotto | `reports/modelli/tahoe_bracci_2026-09-28/extract_arms.py`, `arms_effects.py`, `t1_knn.py` | Sul conto Kaggle del proprietario, non sul portatile |
| `C:/Users/ferra/vcc2026-data/processed/lct_r3_predictions_2026-09-26/` | derivato | attuale | Previsioni salvate da r3 del trasferimento appreso (t20like, modello centrato, β per gene, verità) per sorgente tenuta fuori; costruite con i centri calcolati prima degli split (R-019) | `reports/trasferimento/trasferimento_appreso_2026-09-26/lct_bench3.py` | Input di r4 |
| `C:/Users/ferra/vcc2026-data/processed/lct_r5_predictions_2026-09-26/` | derivato | attuale | Previsioni del banco isolato r5 (magnitudine, t20like, parte trasferita, testa cis, verità e z) per sorgente tenuta fuori | `reports/trasferimento/trasferimento_appreso_2026-09-26/lct_bench5.py` | Input di `reports/trasferimento/risposta_comune_2026-09-26/` |
| `C:/Users/ferra/vcc2026-data/processed/effects_t21_2026-09-26/` | derivato | storico | Primo t21 dello stadio 104 (esponente 0,25, ripeso di tutte le voci, cache r5): moltiplicava anche la testa cis e il gene del bersaglio. Mai generato né inviato | `scripts/104_learned_reweighting.py --reweight all` | Non usare per un invio: r5 del 26/09 |
| `C:/Users/ferra/vcc2026-data/processed/effects_t22_2026-09-26/` | derivato | attuale | Effetti del t22 (ricetta `configs/recipes/t22.json`, cache r5): 300/300 bersagli, circa il 30 % di geni rilevabili in meno del t20 alla stessa ampiezza | `scripts/100_build_context_effects.py` | Il manifest ha gli hash dei tre file |
| `C:/Users/ferra/vcc2026-data/processed/effects_t23_2026-09-27/` | derivato | attuale | Effetti del t23 (ricetta `configs/recipes/t23.json`, cache r5): 300/300 bersagli, geni rilevabili uguali al t22 per costruzione, energia 0,45–0,53 volte il t22 | `scripts/100_build_context_effects.py` | Il manifest ha gli hash dei tre file e la scala della quota per contesto |
| `C:/Users/ferra/vcc2026-data/processed/effects_t25_2026-09-27/` | derivato | attuale | Effetti del t25 (ricetta `configs/recipes/t25.json`, cache r9): 300/300 bersagli; i geni Y portano lo 0,08 % dell'energia pesata sui geni espressi in A e C (5,3–5,5 % nel t22) | `scripts/100_build_context_effects.py` | Il manifest ha gli hash dei tre file |
| `C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-27_r9/` | derivato | attuale | Cache dello stadio 98 come r5 ma con `--min-expected 1.0`: nessun gene indotto da oltre il 90 % dei knockdown, 86–95 % delle voci identiche a r5, K562 identico | `scripts/98_multisource_effects.py` | Report in `reports/sorgenti/pseudoconteggio_2026-09-27/r9/` |
| `C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-27_r6/` | derivato | storico | Correzione del pseudoconteggio alla media geometrica dei totali: rende repressi 221–993 geni per sorgente | `scripts/98_multisource_effects.py`, con una versione del codice del 27/09 mai committata e descritta nel report | Misurata in `reports/sorgenti/pseudoconteggio_2026-09-27/`; nessuna ricetta la usa |
| `C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-27_r7/` | derivato | storico | Pseudoconteggio nelle unità del gruppo più piccolo (`--pseudo-scale library`): sposta anche i geni con pochi conteggi attesi | `scripts/98_multisource_effects.py` | Misurata in `reports/sorgenti/pseudoconteggio_2026-09-27/`; nessuna ricetta la usa |
| `C:/Users/ferra/vcc2026-data/processed/multisource_2026-09-27_r8/` | derivato | storico | Scarto dei donatori con una regola che guardava anche il conteggio del bersaglio: selezione sull'esito, più geni indotti in Orion | `scripts/98_multisource_effects.py`, con una versione del codice del 27/09 mai committata e descritta nel report | Misurata in `reports/sorgenti/pseudoconteggio_2026-09-27/`; nessuna ricetta la usa |
| `C:/Users/ferra/vcc2026-data/processed/eb_r1_predictions_2026-09-26/` | derivato | attuale | Bracci del banco EB (t20like, eb_k1_det, eb_k2_det, eb_k2_energy) e verità per sorgente tenuta fuori | `reports/trasferimento/trasferimento_gerarchico_2026-09-26/eb_bench.py` | Input di analisi successive |
| `C:/Users/ferra/vcc2026-data/processed/banco_k562_pannello_2026-09-29/` | derivato | attuale | I 9 bracci del banco K562 sul pannello (effetti dello stadio 100 con la chiave di contesto `k562`, sorgenti senza K562), ricette usate, `tempi.jsonl` e `manifest.json`; copia su Drive in `data/processed/banco_k562_pannello_2026-09-29/` | `reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/build_arms.py` (29/09, 19:41–19:45) | |
| `C:/Users/ferra/vcc2026-data/processed/banco_hepg2_v2_2026-09-26/` | derivato | attuale | Effetti t16like, t19like, t20like e cisonly per 300 bersagli HepG2, copiati anche su Drive per il job 046 | `reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/build_effects.py` | Input di un banco, non risultati |
| `C:/Users/ferra/vcc2026-data/raw/vcc_2026_controls.zip` e `raw/controls/` | grezzo | attuale | Bundle ufficiale della gara; `manifest.json` presente nella cartella. Checksum **non** ricalcolato da questo registro | Nuovo download dal sito ufficiale | Sorgente primaria: non modificare mai |
| `C:/Users/ferra/vcc2026-data/external/K562_gwps_raw_bulk_01.h5ad` | grezzo | attuale | Replogle 2022, scaricato con `scripts/10_fetch_external.py`. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | Nonostante il nome `raw_bulk`, i valori per cella sono frazionari: non passarli come conteggi interi |
| `C:/Users/ferra/vcc2026-data/external/K562_essential_raw_bulk_01.h5ad` | grezzo | attuale | Come sopra. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | 0/300 bersagli del pannello: utile come stress test |
| `C:/Users/ferra/vcc2026-data/external/rpe1_raw_bulk_01.h5ad` | grezzo | attuale | Come sopra. Checksum locale **sconosciuto** | `scripts/10_fetch_external.py` | 0/300 bersagli del pannello |
| `C:/Users/ferra/vcc2026-data/external/vcc2025/` | grezzo | attuale | Quattro CSV di metadati H1 2025. **Nessuna matrice RNA presente** | Da acquisire per la via ufficiale Arc | L'assenza dell'RNA è il motivo per cui il benchmark P0 non è partito |
| `C:/Users/ferra/vcc2026-data/interim/` | derivato | attuale | Prodotto dagli script 01/11/12/16 | Rilanciando quegli script | `shared_panel.csv` è di 13 byte: contiene solo l'intestazione, cioè un'intersezione vuota. È un risultato, non un errore |
| `C:/Users/ferra/vcc2026-data/predictions/smoke.h5ad` | derivato | storico | Prodotto da `scripts/02_smoke_test_submission.py` | `scripts/02_smoke_test_submission.py` | **Spostato nel Cestino il 23 settembre** (`reports/invii/trial_2026-09-22/autorizzazioni.md`). È una prova di formato del writer, non una previsione: non valutarlo come modello |
| `reports/storico/data_audit/hipsci_metadata/*.tsv.gz` (21 MB nel repo) | grezzo | attuale | Figshare HIPSCI, **MD5 verificato** contro il valore dichiarato dalla sorgente in `scripts/14_fetch_hipsci_metadata.py` | `scripts/14_fetch_hipsci_metadata.py` | Esempio di dato ancora buono la cui strategia è cambiata: HIPSCI è scesa di priorità, i metadati restano validi |
| `reports/storico/candidate_verification/annotations/` | grezzo | attuale | Scaricato con `scripts/22_fetch_candidate_annotations.py`; URL, byte e sha256 in `annotations/manifest.json` | `scripts/22_fetch_candidate_annotations.py` | Librerie di guide e metadati genici: piccoli e necessari ai join |
| `reports/storico/candidate_verification/pilot/cd4_D1_Rest_64.h5ad` | campione | attuale | Provenienza completa: URL, seed, byte trasferiti e sha256 dell'output in `cd4_D1_Rest_64.manifest.json` | `scripts/25_ingest_cd4_pilot.py` con un `--out` nuovo | 64 cellule: prova che l'ingestione funziona, non abbastanza per scegliere un modello |
| `reports/storico/candidate_verification/*.json` (sonde remote) | derivato | attuale | Sonde remote con budget di byte; manifest con sha256 | Script 20, 21, 23, 24, 26 | Fotografie di endpoint pubblici a una certa data: le sorgenti possono cambiare |
| `.runtime-deps/pyarrow` | temporaneo | storico | Installato solo per la sonda Orion; ignorato da git | Reinstallazione | **Spostato nel Cestino di Windows il 23 settembre** (D-040), con la sonda 23 archiviata. Lo stadio 102 usa il pyarrow 25.0.1 del venv del progetto |
| `C:/Users/ferra/vcc2026-data/artifacts/` (e001, e002, n001..n003) | derivato | attuale | Prodotto dagli stadi 40/41/42 il 2026-09-12; ogni run ha il suo manifesto con hash e ambiente | Rilanciando gli stadi con un `--run-id` nuovo | 541,1 MB di firme (516,1 MiB: somma dei tre `.npz` in `reports/storico/pipeline/manifest_40_build_signatures.json`, ricontata il 24 settembre; la riga diceva 519 MB) piu 3x112 MB di bundle a singola cellula. Fuori dal repository (D-001); i risultati leggeri sono copiati in `reports/storico/pipeline/` |
| `C:/Users/ferra/vcc2026-data/artifacts/m001` | derivato | attuale | Pilot modulare 2026-09-14: split, pesi, `results.json` | `scripts/51_run_modular_pilot.py --run-id` nuovo | Fuori dal repository (D-001). Tabella, inventario, universo e specifica del bundle copiati in `reports/storico/benchmark_2026-09-14/` |
| `C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad` | grezzo | attuale | Mirror scPerturb di GSE264667, 850.590.740 byte, **md5 verificato** contro Zenodo (`af2be47f…`); URL, data e licenza in `reports/storico/hepg2_2026-09-14/acquisition.json` | Riscaricabile dallo stesso endpoint | 0,85 GB compressi contro 5,2 GB della copia GEO: la scelta del mirror è dettata da D-005 (≥10 GiB liberi). Non modificare in place |
| `C:/Users/ferra/vcc2026-data/artifacts/e003` | derivato | attuale | Firme HepG2 (2.346 bersagli), profilo basale NTC, QC e censimento. Controlli appaiati per batch | `scripts/53_build_hepg2_signatures.py --run-id` nuovo | Stessa definizione di log2FC delle firme e001, così un modello che legge le due sorgenti legge la stessa quantità |
| `C:/Users/ferra/vcc2026-data/artifacts/m002`, `m003`, `m004` | derivato | attuale | Benchmark a tre contesti: split, pesi, `results.json`. m003 è il solo fold con HepG2 fuori, con le predizioni salvate; m004 ripete m002 aggiungendo i confronti appaiati con/senza contesto e l etichetta di ampiezza corretta, con le stesse 108 righe numeriche | `scripts/51_run_modular_pilot.py --run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono copiati in `reports/storico/benchmark_3ctx_2026-09-14/` |
| `C:/Users/ferra/vcc2026-data/artifacts/m002-crashed-row-axis-2026-09-14` | derivato | storico | Primo tentativo del run a tre contesti, fermato dal controllo di coerenza fra righe ed etichette in `TrainArrays` | Non rieseguire: è la prova del guasto | Tenuto perché documenta che il controllo ha funzionato, non perché contenga risultati |
| `C:/Users/ferra/vcc2026-data/interim/hepg2_bundle/` | derivato | attuale | Bundle a singola cellula (reale e predetti) e output dello scorer per il confronto generatore×predittore | `scripts/57_generator_x_predictor.py` con un `--out` nuovo | Cellule reali di controllo condivise da tutti i bundle, come chiede il contratto |
| `C:/Users/ferra/vcc2026-data/artifacts/g001`, `g002` | derivato | attuale | Tabella GO slim congelata (140 termini, 2.693 simboli) e run del pilot dei descrittori | `scripts/58_build_go_slim_table.py` e `scripts/51_run_modular_pilot.py` con `--run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono copiati in `reports/storico/go_slim_2026-09-15/` |
| `C:/Users/ferra/vcc2026-data/artifacts/s001`, `s002`, `r001` | derivato | attuale | s001 SVD esatta, s002 randomizzata, r001 confronto di rango. Stessi 160 bersagli; s001/s002 stessi split | `scripts/51_run_modular_pilot.py` con `--run-id` nuovo | Fuori dal repository (D-001). I file leggeri sono in `reports/storico/svd_2026-09-15/` e `reports/storico/rank_2026-09-15/` |
| `C:/Users/ferra/vcc2026-data/artifacts/x001` | derivato | attuale | Run del gate di espressione 2026-09-16: split, pesi dei nove bracci originali, artefatti dei nove bracci gate, `results.json` | `scripts/51_run_modular_pilot.py --config configs/benchmark_expression_gate.yaml` con un `--run-id` nuovo | Fuori dal repository (D-001), 82 MB. Le sue 54 righe dei bracci originali coincidono con quelle di `m002`, differenza assoluta 0,0. I file leggeri sono in `reports/storico/expression_gate_2026-09-16/` |
| `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/` | grezzo | attuale | HGNC, GOA GAF/GPI, GO slim, go-basic.obo, STRING info e physical.links; sha256 in `reports/storico/encoder_inputs_2026-09-14/downloads.json` | `scripts/56_probe_target_descriptors.py` | Snapshot pubblico per i descrittori di modo B. Non modificare in place |
| `reports/storico/jiang_2026-09-15/small_files/` | grezzo | attuale | Readme e liste pathway Jiang (file < 2 MB). Gli RDS non sono stati scaricati | `scripts/61_probe_jiang.py` | Non sono matrici di counts |
| `C:/Users/ferra/vcc2026-data/interim/remote_bundle_2026-09-15/` | derivato | attuale | Snapshot codice 536 KB + `gene_names.csv` + notebook. Nessuna matrice | `scripts/67_remote_ingest.py --prepare-bundle` | Da caricare su Colab/Kaggle; HepG2 e Jiang si scaricano da Zenodo là. Dal 16 settembre HepG2 è già su Drive (CP-0018): va collegato, non riscaricato |
| Google Drive del proprietario: `K562_gwps_raw_singlecell_01.h5ad`, `NadigOConner2024_hepg2.h5ad` | grezzo | da-verificare | Copie caricate dal proprietario, **dichiarate** il 2026-09-16 con le dimensioni mostrate da Drive (61,31 GB e 811,2 MB), coerenti in unità binarie con i 65.830.941.948 e 850.590.740 byte di `configs/remote_catalog.yaml`. Percorso su Drive non comunicato; md5 **non calcolato** su nessuna delle due copie | Nuovo caricamento dalle sorgenti figshare 35775507 e Zenodo 13350497 | Da collegare, non da scaricare. Un run Colab le vede solo in `<VCC2026_DATA_ROOT>/raw/replogle/` e `<VCC2026_DATA_ROOT>/raw/nadig_hepg2/` (predefinita: `/content/drive/MyDrive/vcc2026/data`). Diventano `attuale` quando un run ne verifica l'md5. [CP-0018](checkpoints/0018-drive-storage-confermato.md), [R-013](#r-013--dimensione-del-file-k562-a-singola-cellula-gib-contro-gb) |

## Schede di revisione

### R-001 — `README.md`

- **Perché è segnalato:** è il primo file che chiunque legge, ed è fermo alle 21:51
  dell'11 settembre, cioè a prima dell'analisi del 12 settembre. Un agente che legge
  solo il README prende per correnti priorità e affermazioni già corrette.
- **Affermazioni contestate:**
  1. La sezione "Review and reorientation" chiude il racconto all'11 settembre e non
     cita `docs/storico/candidate_adversarial_review_2026-09-12.md`, che ha riordinato le
     priorità di acquisizione verso CD4 e Orion.
  2. «`mse` cannot go below 0 […] so it is scale-invariant» e «Commit on direction,
     shrink magnitude»: il pavimento è sullo *score normalizzato*, non sull'errore, e
     l'invarianza di scala del PDS vale sul delta già trasformato, non su una
     compressione fatta nello spazio dei conteggi.
  3. «**B** an epithelial-mesenchymal hybrid carrying eye-field transcription factors»:
     l'identità oculare è un'ipotesi debole (PAX6 34, LHX2 38, MITF 27 CPM, contro
     CLU 7.857 e VIM 6.052), non un risultato.
  4. La tabella "Plan" dà la fase 1 come "next" senza dire che è bloccata dall'assenza
     di un bundle di valutazione reale e dall'RNA di H1 2025 non scaricato.
  5. Il layout elenca `notebooks/`, che è vuota.
  6. *Aggiunta il 2026-09-12 (CP-0004).* La tabella "Plan" dà la fase 0 come **done**
     con la formula «streaming submission writer verified against official `prep`».
     **Non esiste alcun log di `vcc prep` anteriore al 2026-09-12**, e l'unico
     artefatto candidato, `smoke.h5ad`, contiene 3 perturbazioni su 300. Misurato il
     2026-09-12: `vcc prep` con le opzioni predefinite **rifiuta** un file che non
     predice esattamente le 300 perturbazioni ufficiali per contesto. Resta possibile
     che sia stato eseguito con `--no-verify-targets`, nel qual caso avrebbe
     verificato asse genico, contesti, conteggi per perturbazione e conteggi grezzi
     ma **non** la lista delle perturbazioni. L'affermazione va letta come «il writer
     produce un h5ad strutturalmente valido», che è sostenuta da
     `scripts/02_smoke_test_submission.py`, non come «la CLI ufficiale ha validato una
     sottomissione», che non lo è.
- **Evidenza contraria:** `docs/storico/candidate_adversarial_review_2026-09-12.md` §§2–3;
  `reports/storico/candidate_verification/scorer_clamp_check.json`;
  `reports/gara/context_identity/markers.csv`; elenco di
  `C:/Users/ferra/vcc2026-data/external/vcc2025/`; per la 6, il log
  `prep_dry_run.log` del pilot in `reports/invii/trial_2026-09-12/`.
- **Cosa resta valido:** descrizione del compito, formato di sottomissione, tabella
  delle sei metriche, layout dei dati, setup, wrapper `.cmd`, autenticazione,
  scadenze. È la parte più consultata ed è corretta.
- **È ancora usato o citato:** sì, è l'ingresso predefinito del repository.
- **Disposizione proposta:** mantenere il file, aggiungere in testa il rimando a
  `docs/PROGETTO.md` e note di stato puntuali accanto alle affermazioni contestate
  (fatto il 2026-09-12). Non riscrivere le sezioni scientifiche finché una misura non
  le risolve.
- **Cosa chiuderebbe la revisione:** un benchmark locale che misuri la postura
  "direzione contro ampiezza" (chiude 2), e una verifica dell'identità di B con un
  riferimento esterno appaiato (chiude 3).
- **Aggiornamento del 28 settembre (D-046):** le sezioni che contengono le affermazioni 1–6 sono
  uscite dal README e stanno in `docs/storico/README_2026-09-11_13.md`, senza modifiche al testo; il
  README tiene solo la parte corretta e diventa `attuale`. L'affermazione 2 è superata dai punteggi
  ufficiali: comprimere l'ampiezza costava punti (t15 e t16, D-042); la 5 non vale più, `notebooks/`
  contiene il dispatcher di Colab. La 3 resta aperta.

### R-002 — `reports/scorer/vcc2026_contract.json`

- **Perché è segnalato:** il campo `floor_note` afferma che
  `clamp_low=0.0 on expr_mse_unbiased_capped_norm makes that metric downside-free`.
  Lo script che lo genera, `scripts/17_extract_scorer_contract.py`, è già stato
  corretto (righe 63–69: «non è una garanzia di restringimento gratuito»), ma il JSON
  non è stato rigenerato e conserva la frase vecchia.
- **Affermazioni contestate:** una sola, il campo `floor_note`. Il pavimento a 0 vale
  sul punteggio normalizzato: chi restringe troppo la previsione non perde punti sotto
  zero, ma può perdere **tutti** i punti positivi della metrica.
- **Evidenza contraria:** `reports/storico/candidate_verification/scorer_clamp_check.json`,
  che eseguendo il pacchetto installato mostra errore grezzo 1,0 → score 0,0 e
  errore 0,55 → score 0,50; `docs/storico/candidate_adversarial_review_2026-09-12.md` §3.
- **Cosa resta valido:** tutto il resto del file, che è la fonte più affidabile che
  abbiamo sul comportamento dello scorer: `official_config` copiato dal pacchetto,
  elenco delle sei metriche punteggiate, direzione, ancora, clamp e aggregazione.
- **È ancora usato o citato:** il file è prodotto da `scripts/17_extract_scorer_contract.py`
  e non è letto da nessun altro script; è citato nei documenti di strategia.
- **Disposizione proposta:** ✅ **fatto il 2026-09-12.** Rigenerato con
  `.\scripts\py.cmd scripts/17_extract_scorer_contract.py --out reports/gara/scorer_2026-09-12`,
  su una destinazione **nuova**: il file originale non è stato sovrascritto, perché
  documenta che cosa diceva l'estrattore prima della correzione. Un confronto campo per
  campo mostra che i due JSON sono identici **tranne** `floor_note`, quindi la
  sostituzione non cambia nessun altro fatto sullo scorer.
- **Cosa chiuderebbe la revisione:** è chiusa. La versione corrente del contratto è
  `reports/gara/scorer_2026-09-12/vcc2026_contract.json`, prodotta dallo stesso
  `cell-eval2` 0.16.0 (D-008) e verificata identica salvo il campo corretto. Registrato
  in [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §7.

### R-003 — `docs/data_strategy_2026-09-11.md`

- **Perché è segnalato:** è il primo documento di strategia. Il suo ordine di
  acquisizione (H1, poi KOLF2.1J, poi HIPSCI) è stato riordinato due volte, prima per
  lignaggio e poi per copertura misurata. Chi lo legge da solo acquisisce le sorgenti
  sbagliate.
- **Affermazioni contestate:**
  1. §3, l'ordine di priorità 1–4: tutte e tre le prime sorgenti sono contesti
     iPSC/ESC, che non corrispondono al lignaggio di nessuno dei tre contesti.
  2. §1, «Pseudobulk raw […] non usarli come input raw-count single-cell allo scorer»
     nella parte in cui li dichiara non ricostruibili come conteggi: la ricostruzione
     è stata poi misurata come possibile.
- **Evidenza contraria:** `docs/storico/revisione_analisi_2026-09-11.md` §§2–3;
  `docs/storico/candidate_adversarial_review_2026-09-12.md` §§1 e 5;
  `reports/gara/context_identity/`.
- **Cosa resta valido:** molto. Il §4 (contratto di preprocessing: provenienza,
  riconciliazione dei geni, maschere di osservazione, QC, controlli appaiati, due
  riassunti, shrinkage) non è mai stato contestato ed è la guida operativa ancora in
  uso. Il §1 (audit dei controlli ufficiali, profondità, duplicati di simbolo) è stato
  verificato in modo indipendente e confermato. La revisione successiva dice
  esplicitamente che «il metodo dell'audit precedente è solido e va conservato».
- **È ancora usato o citato:** sì, da `README.md` e da
  `docs/storico/revisione_analisi_2026-09-11.md`. Non spostarlo: i riferimenti si romperebbero.
- **Disposizione proposta:** lasciarlo dov'è con stato `superato` **come guida di
  acquisizione**, continuando a usarne il §4 come contratto di preprocessing. Nessuna
  riscrittura: la storia del riordino serve a capire perché le priorità sono cambiate.
- **Cosa chiuderebbe la revisione:** nulla da chiudere. È un documento storico il cui
  stato è corretto così; si aggiorna solo se il §4 venisse rimpiazzato da un contratto
  di preprocessing nuovo.

### R-004 — `docs/revisione_analisi_2026-09-11.md`

- **Perché è segnalato:** corregge bene il documento precedente, ma quattro delle sue
  affermazioni sono state a loro volta messe in discussione il giorno dopo. Una di
  queste è una **contraddizione aperta**: nessuno dei due documenti ha una misura che
  chiuda la questione.
- **Affermazioni contestate:**
  1. **Contraddizione aperta.** §2: «L'asse genico della gara è ordinato per Ensembl
     gene ID. Una sola inversione su 9.387 geni mappabili […] si ricostruisce l'ENSG
     esatto di tutti i 18.533 geni». La revisione avversariale sostiene l'opposto:
     `gene_names.csv` contiene simboli, e l'ordinamento non basta a dedurre gli ID.
     Le due affermazioni non sono del tutto incompatibili — l'ordine può essere
     coerente con un ordinamento per ENSG senza che da questo si deducano gli ID dei
     geni ambigui — ma la conclusione operativa («ogni join con dati esterni diventa
     esatto») **non è dimostrata**.
  2. §6, P1: «l'intorno di co-espressione nel contesto è una previsione a costo zero
     di quali geni si muovono». La co-espressione negli NTC non è uno stimatore
     causale del segno: può nascere da regolatori comuni, stato del ciclo cellulare o
     normalizzazione composizionale.
  3. §6, P0: H1 2025 come banco di prova immediato. Localmente ci sono solo quattro
     CSV di metadati: l'RNA va acquisito.
  4. §5, punti 1–2: «incollare i controlli […] non costa quasi nulla» e l'invarianza
     di scala del PDS. Vero sul delta già trasformato; non trasferibile a una
     compressione fatta nello spazio dei conteggi, e le altre cinque metriche
     dipendono dall'ampiezza.
  5. §2: «**Il pannello 2026 è: espresso ovunque, non essenziale.** Conseguenza
     diretta: le risposte sono piccole per costruzione». Due passaggi non
     dimostrati. La misura è 0/300 sovrapposizioni con i pannelli essential di K562 e
     RPE1: dice che quei pannelli non contengono i nostri bersagli, non che i bersagli
     siano non essenziali **nei contesti della gara**, dove l'essenzialità non è stata
     misurata. E un gene non essenziale può comunque produrre una risposta
     trascrizionale ampia: l'essenzialità riguarda la sopravvivenza della cellula, non
     l'intensità del cambiamento di espressione. L'audit precedente l'aveva scritto
     («L'assenza dal pannello essential non dimostra che un gene sia biologicamente non
     essenziale», `docs/storico/data_strategy_2026-09-11.md` §1): la cautela è andata persa in
     questa revisione, ed è stata poi ripetuta come misura nella prima versione della
     mappa. Corretta in [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md).
- **Evidenza contraria:** `docs/storico/candidate_adversarial_review_2026-09-12.md` §§2–4;
  elenco di `C:/Users/ferra/vcc2026-data/external/vcc2025/`;
  `reports/storico/candidate_verification/scorer_clamp_check.json`. Per il punto 5, la cautela
  esplicita in `docs/storico/data_strategy_2026-09-11.md` §1 e il fatto che nessuna misura di
  essenzialità nei contesti A, B, C esista in questo repository.
- **Cosa resta valido:** le parti più usate del documento. L'identificazione di
  lignaggio di A, B e C (§3); il pannello «espresso ovunque, non essenziale» (§2), che
  la revisione avversariale riprende e non contesta; la povertà di segnale in K562
  (§4: mediana 5 geni DE per riga); la tabella dei clamp (§5), verificata poi
  numericamente; e l'osservazione su `control_source: real`.
- **È ancora usato o citato:** sì, da `README.md`, che ne riassume le conclusioni.
- **Disposizione proposta:** mantenere, stato `da-verificare`, con questa scheda come
  chiave di lettura. Non promuoverlo a `superato`: la maggior parte del documento è la
  base su cui lavoriamo.
- **Cosa chiuderebbe la revisione:** per il punto 5, una misura di essenzialità nei tre
  contesti, oppure la rinuncia esplicita a quella conclusione; l'intensità attesa della
  risposta si stabilisce solo con dati perturbati, non deducendola dal disegno del
  pannello. Per il punto 1, allineare l'asse ufficiale a un
  riferimento Ensembl e **contare quanti dei 18.533 geni restano ambigui**, scrivendo
  la tabella di mapping su file. È un lavoro di poche ore e chiude una contraddizione
  che altrimenti resta a tempo indeterminato. Per il punto 2, un test su dati
  perturbati reali che confronti la direzione predetta dalla co-espressione con la
  direzione osservata. Per il 3, l'acquisizione dell'RNA di H1. Per il 4, il benchmark
  locale.

### R-005 — I due stub 404 di `candidate_verification`

- **Perché è segnalato:** `reports/storico/candidate_verification/cd4_readme.txt` contiene
  quattordici byte, `404: Not Found`, e `cd4_repo_tree.txt` contiene il JSON di errore
  di GitHub. Sembrano evidenza, sono il corpo di due richieste fallite: la prima
  esecuzione ha chiesto il ramo `main`, mentre il repository dell'autore usa `master`.
- **Affermazioni contestate:** nessuna affermazione: sono file di contenuto nullo che
  possono essere scambiati per dati.
- **Evidenza contraria:** `reports/storico/candidate_verification/manifest.json` registra
  onestamente `status: 404` per entrambe le richieste; la seconda esecuzione, con il
  ramo giusto, ha prodotto `expanded/cd4_readme.txt` (2.928 byte) e
  `expanded/cd4_repo_tree.txt` (88.510 byte), registrati con `status: 200` e sha256 in
  `expanded/manifest.json`.
- **Cosa resta valido:** il manifest della prima esecuzione resta utile: documenta che
  il ramo `main` non esiste, che è il motivo per cui `scripts/20_verify_candidate_accessions.py`
  oggi chiede `master`.
- **È ancora usato o citato:** i due `.txt` non sono letti da nessuno script; i nomi
  `cd4_readme` e `cd4_repo_tree` compaiono in `scripts/20_verify_candidate_accessions.py`
  come chiavi di richiesta.
- **Disposizione proposta:** conservare entrambe le acquisizioni e collegarle qui, che
  è ciò che questa scheda fa. **Non rieseguire la sonda sopra questi file**: la versione
  corretta esiste già in `expanded/`, e una riesecuzione con la destinazione predefinita
  sovrascriverebbe sia i due stub sia `reports/storico/candidate_verification/manifest.json`,
  cioè l'unica prova che il ramo `main` non esiste. Una nuova esecuzione deve andare in
  una cartella propria, come ha fatto `scripts/27_verify_grok_leads.py` con
  `--out reports/storico/grok_verification`.
- **Cosa chiuderebbe la revisione:** niente da chiudere. La coppia
  fallimento/successo è già completa e documentata; questa scheda resta come chiave di
  lettura dei due file. *(Una versione precedente di questa scheda proponeva la
  riesecuzione sovrascrivendo: correzione registrata in
  [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md).)*

### R-006 — `reports/candidate_pdf_extracted.txt`

- **Perché è segnalato:** sono 49 KB di prosa italiana sicura di sé, dentro
  `reports/`, che nessun file cita. Un agente che lo trova cercando nei report può
  scambiarlo per un'analisi del progetto. È invece un documento **esterno**, un
  insieme di affermazioni da verificare, e la verifica ne ha smentite parecchie.
- **Affermazioni contestate:** fra le altre, Pisces descritto come sorgente
  disponibile (la scheda pubblica dice "Coming Soon"); Nadig presentato come
  componente Jurkat/HepG2 di Replogle (è uno studio a sé); il DOI `20022944` indicato
  come raccolta processata scPerturb (identifica quattro manifest CSV di file di
  sequenziamento; il record processato è `20029387`); una correlazione residua
  attribuita al confronto sbagliato; una attribuzione «Datlinger in vivo» senza studio
  risolto.
- **Evidenza contraria:** `docs/storico/candidate_adversarial_review_2026-09-12.md` §1 e
  sezione "Rejected", con le sonde eseguite salvate in
  `reports/storico/candidate_verification/`.
- **Cosa resta valido:** ha indirizzato la ricerca verso sorgenti reali e utili, in
  particolare CD4 e Orion. Le sue stringhe di accessione esistono quasi tutte: è
  l'interpretazione di disponibilità e semantica a essere sbagliata.
- **È ancora usato o citato:** nessun file del repository lo cita.
- **Disposizione proposta:** conservarlo come evidenza di ciò che è stato verificato.
  Non spostarlo (nessun riferimento da aggiornare, ma nemmeno un guadagno di
  chiarezza che giustifichi lo spostamento); il presente registro è il posto in cui se
  ne dichiara la natura.
- **Cosa chiuderebbe la revisione:** nulla. Lo stato `storico` è quello definitivo per
  una fonte esterna già verificata.

### R-007 — `reports/transfer_ceiling/`

- **Perché è segnalato:** il nome della cartella dice "soffitto di trasferimento", cioè
  esattamente la conclusione che i numeri **non** dimostrano. I valori salvati sono
  correlazioni fra effetti stimati, e i più alti (0,13–0,16 mediana Pearson) sono
  confronti **della stessa linea** K562 essential contro K562 genome-wide, non fra
  linee diverse.
- **Affermazioni contestate:** che quei numeri misurino un limite superiore al
  trasferimento fra contesti. Il confronto fra linee diverse dà una mediana molto più
  bassa, 0,0905 grezza per K562 genome-wide verso RPE1, ma resta positiva e
  discrimina le coppie appaiate da quelle non appaiate: non basta a dichiarare K562
  inutile, che è la conclusione opposta e altrettanto non dimostrata.
- **Evidenza contraria:** `reports/storico/transfer_ceiling/transfer_ceiling.json`, campi
  `similarity.raw.matched.pearson.median` per ciascun confronto (ricontrollati il
  2026-09-12); `docs/storico/candidate_adversarial_review_2026-09-12.md` §3.
- **Cosa resta valido:** i numeri, la stratificazione per numerosità e per intensità
  d'effetto, e il confronto con il nullo esaustivo delle coppie non appaiate. È
  evidenza buona sotto un nome fuorviante.
- **È ancora usato o citato:** sì, da `scripts/18_cells_per_pert_replogle.py` e
  `scripts/19_power_curve_vcc_ntc.py`, che vi scrivono dentro. **Non rinominare la
  cartella** senza aggiornare quei due script.
- **Disposizione proposta:** tenere nome e file, e citare quei numeri sempre come
  "correlazione fra effetti stimati", mai come "soffitto". Il rinominamento non vale
  il rischio di rompere due script per una questione di etichetta.
- **Cosa chiuderebbe la revisione:** un ricalcolo con NTC verificati, spazio di output
  appaiato, replicazione per guida e le regole di esclusione dello scorer, che è
  quanto chiede la revisione avversariale.

### R-008 — `reports/grok_verification/`

- **Scheda chiusa lo stesso giorno in cui è stata aperta.** Si conserva perché mostra il
  meccanismo al lavoro, non perché il materiale sia ancora in dubbio.
- **Perché è segnalato:** alle 15:24 del 12 settembre la cartella è comparsa
  insieme a `scripts/27_verify_grok_leads.py`, dopo CP-0001, e nessun documento del
  repository la citava o spiegava a quale domanda rispondesse. Il controllo di copertura
  ricorsivo l'ha intercettata subito. Alle 15:32, mentre questa scheda veniva scritta, è
  arrivato `docs/storico/revisione_grok_2026-09-12.md`, che spiega tutte le sonde: la cartella è
  tornata `attuale`. Restava scoperto un intervallo di otto minuti, che è esattamente
  quanto deve durare.
- **Affermazioni contestate:** nessuna. Questi file non affermano niente: sono risposte
  di endpoint pubblici. Il loro contenuto non è stato valutato in questa revisione, e le
  conclusioni che `docs/storico/revisione_grok_2026-09-12.md` ne trae non sono state
  controllate qui.
- **Evidenza contraria:** non applicabile. Il suo `manifest.json` registra otto
  richieste, tutte con esito 200, verso GSE247601, GSE208240, i record Zenodo 14217682
  e 13350497, e gli studi E-MTAB-14567 ed E-MTAB-13324.
- **Cosa resta valido:** tutto, come istantanea datata. Lo script riusa la meccanica di
  `scripts/20_verify_candidate_accessions.py` con una destinazione distinta, che è il
  modo corretto di aggiungere sonde senza sovrascrivere le precedenti.
- **È ancora usato o citato:** no. Solo `scripts/27_verify_grok_leads.py` vi scrive
  dentro; nessun documento lo legge.
- **Disposizione proposta:** conservare, stato `attuale`. Il contesto che mancava ora
  esiste.
- **Cosa chiuderebbe la revisione:** è chiusa. Resta aperta una cosa diversa, che non
  riguarda questi file: l'inventario Grok di partenza non è conservato nel repository,
  a differenza del PDF in `reports/storico/candidate_pdf_extracted.txt`, quindi le affermazioni
  che il documento corregge non sono più leggibili nella loro forma originale.

### R-009 — `docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md`

- **Perché è segnalato:** tre sue affermazioni sono state corrette il giorno stesso da
  [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md). Il file **non è stato
  modificato** e non lo sarà: è una fotografia datata. Questa scheda e la colonna
  "Corretto da" dell'indice esistono perché chi lo legge sappia dove sta la correzione.
- **Affermazioni contestate:** §3, il pannello descritto come «non essenziale» sulla
  base dell'assenza da due pannelli *essential*; §4, «gli effetti sono piccoli per
  costruzione»; §5, l'esempio secondo cui sottostimare l'ampiezza «fa perdere poco».
  L'elenco con le correzioni è in CP-0002 §7.
- **Evidenza contraria:** `docs/storico/data_strategy_2026-09-11.md` §1, che conteneva già la
  cautela sull'essenzialità; l'assenza in questo repository di qualunque misura di
  essenzialità o di ampiezza d'effetto nei contesti A, B e C;
  `reports/storico/candidate_verification/scorer_clamp_check.json` per il terzo punto.
- **Cosa resta valido:** tutto il resto, che è la maggior parte: le coperture misurate,
  l'identità di lignaggio dei contesti, i clamp dello scorer, l'assenza dell'RNA di H1,
  i vincoli hardware, e la tabella §7 delle correzioni fra i tre documenti di strategia.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md`, da `CLAUDE.md` e da questo
  registro: è il secondo documento del percorso di lettura.
- **Disposizione proposta:** lasciarlo intatto. Nessuna riscrittura, nessuno
  spostamento: è il primo caso in cui questo sistema fa quello per cui è stato scritto,
  e vale più da leggere che da correggere.
- **Cosa chiuderebbe la revisione:** niente. Un checkpoint corretto resta
  `da-verificare` per sempre: è il modo in cui si dice a chi legge che la fotografia
  contiene qualcosa che poi si è rivelato sbagliato.

### R-010 — `reports/pipeline/`

- **Perché è segnalato:** contiene i primi risultati di modellazione del progetto, ed
  è quindi il primo materiale che si presta a essere citato fuori contesto. La scheda
  esiste per tenere le cautele attaccate ai numeri invece che in un documento a parte.
  Copre anche `transfer_experiment_e001_superseded.json`, marcato `superato`.
- **Affermazioni contestate:** che questi numeri dicano "il trasferimento da K562
  funziona", e che `null_calibration_A.json` sia un benchmark predittivo. Nessuna delle
  due segue. Quello che segue è: a piena ampiezza il trasferimento **peggiora** l'MSE
  del 16% rispetto al non prevedere nulla, e all'ampiezza calibrata lo migliora
  dell'1,0%. Le due frasi non sono la stessa frase. E il nullo ha effetto vero zero per
  costruzione: un modello che lo "battesse" indicherebbe una fuga di informazione.
- **Evidenza contraria:** `reports/storico/pipeline/transfer_experiment.json`, campi
  `cv_mean.untuned_mse_vs_null` (1,162) e `cv_mean.tuned_mse_vs_null` (0,990) per la
  coppia K562 genome-wide → RPE1; `reports/storico/pipeline/null_calibration_A.json`, campo
  `design.true_effect` e il rifiuto di aggregazione registrato in `aggregate_error`.
- **Cosa resta valido:** tutti i numeri, con il loro protocollo. Sono ricalcolabili con
  i comandi di [CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md) §2,
  la selezione degli iperparametri è su bersagli tenuti fuori e il bootstrap è sui
  bersagli. `transfer_experiment_e001_superseded.json` ha numeri di trasferimento
  identici alla versione corrente: differisce solo per un campo di riepilogo a `null`,
  causato da una chiave sbagliata nella funzione di aggregazione. È conservato perché
  una riesecuzione non sovrascrive un'evidenza.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` §3, da D-006, D-012 e D-014, e
  da `configs/sources.yaml` (`signature_qc.json` è evidenza della riga `k562_gwps`).
- **Disposizione proposta:** tenere tutto. Citare sempre questi numeri come metriche
  proxy in spazio pseudobulk log2FC, mai come punteggi VCC, e citare l'alpha di 0,25
  come proprietà della coppia K562 → RPE1, non come costante del progetto.
- **Cosa chiuderebbe la revisione:** un bundle di valutazione a singola cellula (R-1
  della [roadmap](ROADMAP.md)). Con quello le sei metriche VCC si calcolano su effetti
  veri, le metriche proxy scendono al rango di diagnostiche di supporto, e l'ampiezza
  si ricalibra su ciò che assegna davvero i punti.

### R-011 — `reports/trial_2026-09-12/`

- **Perché è segnalato:** contiene i primi artefatti a forma di sottomissione del
  progetto — due previsioni complete per A/B/C e la loro convalida — ed è quindi il
  materiale che più facilmente verrebbe letto come "abbiamo partecipato". Non è così:
  nulla è stato caricato, nessuna quota è stata consumata, e non esiste alcun
  punteggio di leaderboard. La scheda esiste per tenere questa cautela attaccata ai
  file. Copre anche `calibration_c001_peak_memory_unrecorded.json`, marcato `superato`.
- **Affermazioni contestate:** che una convalida di formato superata dica qualcosa
  sulla qualità predittiva; che `trial-00-controls` sia "il baseline a punteggio zero"
  della gara; che l'α di 0,197 misurato su K562 → RPE1 valga per A, B o C; e che le
  metriche proxy pseudobulk si convertano in un punteggio VCC. Nessuna delle quattro
  segue.
- **Evidenza contraria:** `held_out_comparison.md` §3, che separa misura,
  interpretazione e ipotesi riga per riga; `q00prep_prep_dry_run.log` e
  `q01prep_prep_dry_run.log`, che registrano il fallimento della convalida ufficiale
  per esaurimento di memoria; `configs/trials.yaml` campo `not_this` di
  `trial-00-controls`; e il campo `uploaded: false` di ogni `validation.json`.
  `resources.json` copre i quattro run di generazione (due pilot e due completi); i due
  tentativi di packaging hanno i propri `q00prep_validation.json` e
  `q01prep_validation.json`.
- **Cosa resta valido:** tutte le misure, con il loro protocollo. La calibrazione è
  annidata e il bootstrap ricampiona solo previsioni fuori campione; la verifica del
  contratto è ricavata dal file scritto, non dal writer che l'ha prodotto; la
  provenienza dei contesti è verificata contro i profili basali, che è la cosa che
  `vcc prep` non può fare.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` §3, da `docs/SOTTOMISSIONE.md`,
  da D-015, D-016 e D-017, e dall'aggiornamento 2026-09-12 di D-006 e D-012.
- **Disposizione proposta:** tenere tutto. Citare l'α di 0,197 come proprietà della
  coppia K562 → RPE1, mai come costante del progetto; citare la riduzione dell'1,01% di
  MSE come metrica proxy pseudobulk, mai come punteggio; e non descrivere i pacchetti
  come "validati dalla CLI ufficiale" finché `vcc prep` non è stato eseguito su di essi
  con esito positivo.
- **Cosa chiuderebbe la revisione:** un'esecuzione di `vcc prep` completata su una
  macchina con RAM sufficiente, il cui log entri qui accanto; e, per la parte
  predittiva, il bundle di valutazione a singola cellula di R-1 della
  [roadmap](ROADMAP.md).

### R-012 — `reports/trial_2026-09-13/`

- **Perché è segnalato:** documenta un `.vcc` valido, ed è il materiale che più
  facilmente verrebbe letto come "siamo pronti a vincere" o, peggio, come "il server
  ha accettato". Nessuna delle due cose. La scheda esiste per tenere attaccata ai
  file la distinzione fra tre affermazioni diverse: convalida di formato, parità con
  lo strumento ufficiale, accettazione del server.
- **Affermazioni contestate:** che un `.vcc` valido dica qualcosa sulla qualità
  predittiva; che la parità con `vcc prep` implichi l'accettazione da parte del
  servizio di scoring; che i test di parità coprano anche la densità; e che il
  picco di 0,52 GiB sia garantito su qualunque previsione.
- **Evidenza contraria:** `k01pack_packaging.json`, campi `uploaded: false` e `note`;
  [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) §4, che elenca il
  confine della parità e dichiara che i fixture sono a densità sintetica.
- **Cosa resta valido:** tutte le misure. L'archivio è verificato con il validatore
  ufficiale del contenitore, e il suo payload è stato confrontato **con l'input**
  array per array: `X/data`, `X/indices` e `X/indptr` identici bit a bit, asse genico
  e etichette identici, con la sola trasformazione dell'indice di `obs` documentata e
  verificata positivamente.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md`, `docs/SOTTOMISSIONE.md`,
  `docs/ESECUZIONE_REMOTA.md`, e da D-018 e D-019.
- **Disposizione proposta:** tenere tutto. Non descrivere mai il `.vcc` come
  "accettato" finché una sottomissione non è stata valutata; citare il picco di
  0,52 GiB come misurato su questa previsione, non come proprietà generale.
- **Chiusa il 2026-09-13, per la parte sull'accettazione del server.** La
  sottomissione `PNn227rxP3bVByS37W41` è arrivata a `published` con
  `md5_verified: true` ed `error_info: null`: il servizio di scoring ha letto e
  valutato il `.vcc` prodotto da questo percorso
  ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.1). Restano
  contestate le altre affermazioni della scheda: un `.vcc` valido continua a non dire
  nulla sulla qualità predittiva — misurata ora, e bassa: 0,046 — e i fixture di
  parità continuano a non esercitare la densità.
- **Cosa chiuderebbe la revisione:** per l'accettazione del server, è già chiusa (vedi
  sopra). Per il resto, niente che riguardi il packaging: la qualità predittiva si
  affronta con R-1 e R-3 della [roadmap](ROADMAP.md), non con questo materiale, e la
  densità dei fixture si chiuderebbe solo con un fixture a densità reale, che costerebbe
  minuti invece di secondi per ogni test.

### R-013 — Dimensione del file K562 a singola cellula: GiB contro GB

- **Perché è segnalato:** il 16 settembre il proprietario ha riferito le dimensioni
  delle copie su Google Drive. Confrontandole con il catalogo è emerso un errore di
  unità ripetuto in più materiali
  ([CP-0018](checkpoints/0018-drive-storage-confermato.md) §3.2–3.3). Lo stesso giorno
  è cambiato il punto di partenza del notebook remoto: i due file che la selezione
  automatica scaricherebbe per primi sono già su Drive.
- **Affermazioni contestate:**
  1. «65,8 GiB» per `K562_gwps_raw_singlecell_01.h5ad`. I 65.830.941.948 byte sono
     65,83 GB, cioè 61,31 GiB. L'etichetta compare in
     `reports/storico/remote_2026-09-15/COME_APRIRE.md` (tre volte), nel markdown e nei
     messaggi di `notebooks/remote_ingest_hepg2.ipynb`, nelle docstring di
     `src/vcc2026/remote_ingest.py`, `src/vcc2026/remote_catalog.py` e
     `scripts/68_remote_catalog.py`, e in un commento di
     `tests/test_remote_catalog.py`. Compariva anche in
     `docs/PIANO_COMPRENSIONE_2026-09-16.md` §3, in
     `docs/PIANO_IMPLEMENTATIVO_2026-09-16.md` (I-5) e nella riga degli script 61–68 di
     questo registro: corretti il 16 settembre, con un rimando a questa scheda.
  2. «Il 61,3 GB del profilo non è la dimensione di questo file». È la stessa
     dimensione espressa in GiB, come il 9,9 e l'8,1 degli altri due file Replogle a
     singola cellula. L'affermazione compare in `configs/remote_catalog.yaml`
     (`advertised_bytes: 61300000000` e `advertised_note`, ripetuti in
     `reports/storico/remote_catalog_2026-09-15/catalog_run.json`) e in
     `reports/storico/remote_2026-09-15/COME_APRIRE.md`; compariva nella riga del catalogo di
     questo registro, ora corretta. `reports/storico/source_cards_2026-09-15/` converte le tre
     cifre del profilo in byte decimali (`profile_declared_sc`).
  3. Non un errore, ma una circostanza nuova. `COME_APRIRE.md` e il notebook indicano
     `FETCH_BLOCKS = None` come scelta normale. Con i due file già su Drive nel posto
     atteso, quella scelta passa al blocco successivo e scarica `rpe1_raw_singlecell`;
     con i file altrove, riscarica i due file. Per collegare soltanto servono
     `FETCH_BLOCKS = []` o una `SELECT_BLOCKS` ristretta ai due blocchi.
- **Evidenza contraria:** i byte in `src/vcc2026/external.py` e
  `configs/remote_catalog.yaml` divisi per 1.073.741.824 danno 61,31, 9,93 e 8,10 GiB.
  Le dimensioni che Drive mostra per le due copie, 61,31 GB e 811,2 MB, sono una
  dichiarazione del proprietario. Per il punto 3: `recommend_fetch_ids` e `run_catalog`
  in `src/vcc2026/remote_catalog.py`, letti e non eseguiti.
- **Cosa resta valido:** tutto ciò che guida il codice. Byte, md5, URL e `relpath` del
  catalogo sono giusti, e la selezione lavora in byte, non in etichette. La parità
  HepG2, la prova di ripresa e il piano locale restano misure valide. L'ordine dei
  blocchi e la regola «un solo file grande alla volta» non cambiano.
- **È ancora usato o citato:** sì. Il notebook e `COME_APRIRE.md` sono le istruzioni per
  il prossimo run remoto (incarico I-6 del
  [workflow 1](PIANO_IMPLEMENTATIVO_2026-09-16.md)); il catalogo è letto da
  `scripts/68_remote_catalog.py` e dal notebook.
- **Disposizione proposta:** non riscrivere i report: `COME_APRIRE.md` si legge con
  questa scheda accanto. Correggere etichette e `advertised_bytes` nel codice e nel
  catalogo con un intervento a parte, insieme alla modalità «solo collegamento»
  proposta in CP-0018 §6.
- **Cosa chiuderebbe la revisione:** per i punti 1 e 2, la correzione di catalogo,
  notebook e docstring. Per il punto 3, un run remoto che colleghi le due copie senza
  scaricare nulla e ne verifichi l'md5, con il suo `catalog_run.json` conservato.

### R-014 — CP-0018: md5 e provenienza delle copie su Drive

- **Perché è segnalato:** il 17 settembre, con Drive per desktop montato, la cartella
  `MyDrive/vcc2026` conteneva accanto ai due file i sidecar `.fetch.json` scritti dal run
  Colab `catalog_2026-09-15T145842Z`
  ([CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md) §3.1).
- **Affermazioni contestate:**
  1. Le copie sono una dichiarazione del proprietario, con md5 non calcolato
     (CP-0018 §3.1 e §4, e l'incertezza 20 di `docs/PROGETTO.md`). In realtà l'md5 è stato
     calcolato al download e coincide con il catalogo, per entrambi i file.
  2. Il percorso delle copie non è noto. In realtà sono nei percorsi che il catalogo si
     aspetta (`data/raw/replogle/` e `data/raw/nadig_hepg2/`).
- **Evidenza contraria:** `reports/storico/drive_evidence_2026-09-17/` (sidecar, `catalog_run.json`
  del run, elenco dei file con i byte).
- **Cosa resta valido:** le dimensioni e la lettura in unità binarie (CP-0018 §3.2–3.3),
  la descrizione del codice del catalogo (§3.4–3.6), e il fatto che nessun run abbia
  letto il contenuto del K562: il QC di quel run è fallito per un errore di codice prima
  di aprirlo. Resta non misurato anche il tempo di lettura attraverso il mount.
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md` e dai piani del 16 settembre.
- **Disposizione proposta:** CP-0018 resta com'è e si legge con questa scheda accanto.
  Nella mappa l'incertezza 20 si chiude per integrità e percorso, e resta aperta per i
  tempi di lettura.
- **Cosa chiuderebbe la revisione:** il primo run dello script 71 su Colab, il cui
  `report.json` ricalcola l'md5 sui byte letti e misura la velocità di lettura.

### R-015 — `docs/SOTTOMISSIONE.md`: i comandi del §3 e la lista del §6

- **Perché è segnalato:** il 23 settembre gli stadi 43, 44, 46 e 47 sono stati archiviati
  (D-040). Il §3 li dà come «comandi esatti», e il §6 mette lo stadio 46 al primo punto
  della lista da completare prima di inviare.
- **Affermazioni contestate:**
  1. §3, «Rigenerare tutto da zero»: la sequenza 43 → 44 → 45 → 46 → 48 non gira più
     dall'albero, perché 43, 44 e 46 sono nel tag `archivio/pre-pulizia-2026-09-23`.
  2. §3, «Inviare — non ancora autorizzato, e non ancora possibile»: vero il 12 settembre;
     dal 13 gli invii sono stati fatti
     ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) e seguenti).
  3. §6, punto 1: lo stadio 46 non è più un passo dell'invio. Dal t08 le convalide le fa lo
     stadio 48: 24 controlli ufficiali, il contenitore e il payload confrontato con l'input.
- **Evidenza contraria:** [ARCHIVIO.md](ARCHIVIO.md); `reports/invii/trial_2026-09-22/t08_packaging.json`
  e `reports/invii/trial_2026-09-23/t11_manifest_48.json`, che non passano dallo stadio 46.
- **Cosa resta valido:**
  - il contratto (§1) e la questione di trial-00 (§2, D-017);
  - che cosa registrare di ogni voce (§4) e la differenza fra punteggi ufficiali e
    metriche locali (§5);
  - l'impacchettamento a memoria limitata (§7);
  - i comandi per leggere stato e punteggi (§3).
- **È ancora usato o citato:** sì, da `docs/PROGETTO.md`, da `docs/PROCEDURE.md` e da diversi
  checkpoint.
- **Disposizione proposta:** il documento resta com'è e si legge con questa scheda accanto.
  I comandi del percorso vivo stanno in `docs/PROCEDURE.md` §1, le regole dell'invio nel §2
  dello stesso file.
- **Cosa chiuderebbe la revisione:** una decisione del proprietario, fra due strade:
  riscrivere il §3 sul percorso vivo, oppure dichiararlo storico.

### R-016 — Lettura causale del t17

- **Perché è segnalato:** uguagliare il q99 mediano non uguaglia l'ampiezza per bersaglio.
- **Affermazioni contestate:** la regola di `reports/invii/prediction_t17_2026-09-24/prediction.json`
  attribuisce un eventuale guadagno a HEK293T «at matched magnitude».
- **Evidenza contraria:** `reports/analisi/audit_stato_2026-09-24/measurements.json`: il q99 mediano coincide,
  ma 22/300 bersagli cambiano q99 di oltre il 20% e l'energia totale cambia del 6,67%.
- **Cosa resta valido:** ricetta, banda, soglie e compensazione del q99 mediano. Non si
  modifica retroattivamente la preregistrazione.
- **È ancora usato o citato:** sì, guida la lettura futura del t17.
- **Disposizione proposta:** confronto del pacchetto sorgente + miscela + compensazione;
  il contributo isolato dell'informazione di HEK293T resta aperto.
- **Cosa chiuderebbe la revisione:** un'ablazione aggiuntiva che separi scala e sorgente,
  oppure una successiva conclusione che dichiari esplicitamente questo limite.

### R-017 — Banco del 25 settembre: effetti ristretti ricalcolati senza SE

- **Perché è segnalato:** `shrink_sweep.table` ricalcolava la restrizione anche per `cd4_mix`,
  che non ha SE: ogni effetto CD4 diventava 0 e contava come voto per zero in `mix`; i bersagli
  coperti solo da CD4 sparivano, e le varianti erano valutate su bersagli diversi. Trovato da
  due revisioni indipendenti (claude2, grok), in `reports/trasferimento/banco_varianti_2026-09-25/revisioni/`.
- **Affermazioni contestate:** in `reports/trasferimento/banco_varianti_2026-09-25/RISULTATI.md` le colonne
  ristrette delle tabelle 2 e 4 (fino a +0,123 sul PDS proxy), «+0,026 / +0,042 / +0,058 /
  +0,080» con k 64, «raddoppiare quel q99 non aggiunge nulla», la proposta di k 64 con la regola
  del q99; lo stesso nel messaggio del commit `2308ee7` e nelle uscite r2, r4, r5.
- **Evidenza contraria:** `reports/trasferimento/banco_varianti_2026-09-25/CORREZIONE.md`, r7 e r8: +0,01…+0,04
  con la ricostruzione corretta di `cd4_mix`.
- **Cosa resta valido:** tabella 1 (r1), filtro respinto (r3), righe grezze e calibrazione del
  modello sul t11 → t15, fatti sullo scorer.
- **È ancora usato o citato:** sì, da CP-0039 e dalla scheda S-INVII, che citano la correzione.
- **Disposizione proposta:** non usare le righe ristrette di r2, r4 e r5; leggere il report con
  la correzione accanto.
- **Cosa chiuderebbe la revisione:** nulla da rifare sul banco; la scheda resta per chi legge
  il report originale.

### R-018 — MSE proxy e punteggio ufficiale

- **Perché è segnalato:** `reports/trasferimento/banco_varianti_2026-09-25/MSE.md` passa da
  misure nello spazio degli effetti a «mse resta a zero a qualunque ampiezza» e
  attribuisce il limite alla precisione del modello. Il codice dichiara che non
  calcola il punteggio VCC; anche la sintesi del registro ripeteva l'estrapolazione.
- **Affermazioni contestate:** universalità della conclusione sulla MSE ufficiale;
  causa esclusiva; crescita di a* con la sola correlazione; beneficio della
  restrizione senza precisare il riferimento. Sono inferenze non dimostrate,
  non numeri ufficiali smentiti da questa analisi.
- **Evidenza contraria:** alla sufficienza dell'inferenza, non ai numeri r10:
  `reports/analisi/biologia_architetture_2026-09-25/RISULTATI.md`,
  §6, CP-0040 e lettura di `mse_tradeoff.py`: pesi dai controlli medi, nessuna
  cellula generata, esclusione per famiglia di sorgenti, a* stimata sulla verità
  valutata. a* dipende da coseno e rapporto delle norme. T19 migliora rispetto al
  grezzo alla stessa ampiezza; rispetto a 0,788 migliora solo CD4 nel proxy r10.
- **Cosa resta valido:** numeri r10 nel loro modello, tradeoff ampiezza/errore,
  utilità di separare modello e calibrazione. Nessun output originale modificato.
- **È ancora usato o citato:** sì, nella nuova ricerca e nella voce del banco.
- **Disposizione proposta:** leggere MSE.md con questa nota; non usare il proxy
  come dimostrazione del clipping ufficiale né a* come performance fuori campione
  di una calibrazione appresa.
- **Cosa chiuderebbe la revisione:** evidenza su metrica ufficiale comparabile e
  calibrazione indipendente, oppure una nuova conclusione che ritiri esplicitamente
  l'estrapolazione. Questa nota conserva la critica senza riscrivere il report.

### R-019 — Audit del 26 settembre

- **Perché è segnalato:** l'audit trova dipendenze residue dalle risposte escluse
  e una descrizione errata della modalità di perturbazione.
- **Materiale:** [audit piani e dati](../reports/analisi/audit_piani_dati_2026-09-26/RISULTATI.md),
  §§4–5, script e output r1 con hash dei file esaminati durante il lavoro concorrente.
- **Affermazioni contestate:** r2/r3 del trasferimento appreso completamente isolati;
  assimilazione dello split del regressore a bersagli biologicamente nuovi;
  descrizione Mixscale come knockout nel report H6.
- **Evidenza contraria:** le medie delle sorgenti e delle etichette precedono la separazione;
  un controesempio con il vero `mix` cambia la feature training alterando solo un
  esito test. I prior K562 restano anche quando quella linea è esterna. GEO
  GSE281048 documenta CRISPRi dCas9-KRAB-MeCP2.
- **Cosa resta valido:** numeri come output degli esperimenti descritti, correzioni
  parziali r2, segnali esplorativi r3/r4 e misure H6. Nessun impatto del leakage
  sul punteggio è stato quantificato; nessun risultato originale modificato.
- **È ancora usato o citato:** sì, guida lo sviluppo del trasferimento appreso e
  la lettura delle prove di contesto nel piano R-V2.
- **Disposizione proposta:** conservare i risultati e leggerli con questo audit;
  non promuovere r2/r3 a prova indipendente C/T/J senza risolvere le dipendenze.
- **Cosa chiuderebbe la revisione:** nuovo banco con trasformazioni entro fold e controlli di invarianza,
  regime C/T/J o misto esplicito; correzione documentale della modalità Mixscale.

### R-020 — Evidenza citata ma assente dal repository

- **Perché è segnalato:** file committati citano materiali che non sono mai entrati in nessun commit
  (verificato il 28/09 con `git log --all` su ogni percorso). Chi legge la citazione non può
  controllare la fonte, e una delle mancanti è la prova di una perdita di informazione.
- **Affermazioni contestate:** nessuna affermazione è smentita; manca la loro evidenza:
  1. *reports/audit_piani_dati_2026-09-26/RISULTATI.md*, l'audit di codex che ha trovato i centri
     calcolati prima degli split nel trasferimento appreso (r3–r4); citato dalla scheda R-V2, da
     `reports/trasferimento/trasferimento_appreso_2026-09-26/RISULTATI.md` e `lct_bench5.py`, da
     `reports/sorgenti/ricerca_sorgenti_2026-09-26/RISULTATI.md` e da `tests/test_transfer_model.py`;
  2. le schede R-018 e R-019 di questo registro (R-019 è la perdita dei centri), citate dalla riga del
     trasferimento appreso e da `reports/modelli/modello_contesto_2026-09-27/agenti/disegno_claude2.md`;
  3. *docs/checkpoints/0040-biologia-contesti-donatori.md*, citato da
     `reports/trasferimento/trasferimento_gerarchico_2026-09-26/RISULTATI.md` §5 (la varianza fra
     donatori di CD4, dalla sessione `76a3a45e`);
  4. *reports/biologia_architetture_2026-09-25/RISULTATI.md*, citato dal disegno di claude2 (STAT2 con
     IFNB e IFNG);
  5. *reports/prediction_t21_2026-09-26/prediction.json*, la previsione registrata del t21, citata da
     `reports/invii/trial_2026-09-26/submission_texts.md`.
- **Evidenza contraria:** nessuna; i numeri citati da questi materiali non sono stati ricontrollati.
- **Cosa resta valido:** le conclusioni dei report che li citano, che portano le proprie misure (per il
  trasferimento appreso vale la r5, costruita per evitare quella perdita).
- **È ancora usato o citato:** sì, dalla scheda R-V2 e da quattro report.
- **Disposizione proposta:** recuperare i file dal portatile o dai worktree degli agenti e committarli
  come sono, con la data in cui furono scritti. CP-0040 resta libero per quel checkpoint: nessun altro
  checkpoint prende quel numero. Dal 28/09 il controllo documentale verifica i link anche nelle schede
  dei piani e negli indici, dove il link all'audit è stato trovato.
- **Cosa chiuderebbe la revisione:** i cinque materiali nel repository, oppure una nota del proprietario
  che dica che non esistono più, e le citazioni marcate come tali.
- **Recupero del 28/09** (azione 1 della scheda [R-REV](piani/revisione-critica.md); Claude, sessione `f4f38e58`, alle
  12:58 lette con `date`). Quattro materiali su cinque erano sul portatile e sono committati **come trovati**:
  1. l'audit di codex: non tracciato in `reports/audit_piani_dati_2026-09-26/` (file del 26/09, 14:24–14:35),
     ora in `reports/analisi/audit_piani_dati_2026-09-26/`;
  2. R-018 e R-019: nelle modifiche non committate del registro, reinserite com'erano, con i percorsi dei report
     aggiornati alle categorie;
  3. CP-0040: in stage, con la sua riga dell'indice (checkpoint del 25/09);
  4. `biologia_architetture_2026-09-25`: in stage, ora in `reports/analisi/`.
- **La previsione del t21 non è stata trovata.** Dove si è cercato:
  - `git log --all`;
  - i worktree del portatile (repo, `vcc2026-refactor`, `wt8`, codex, agent hub);
  - la radice dati, che ha solo gli effetti, `processed/effects_t21_2026-09-26/`;
  - le trascrizioni delle sessioni.

  Le trascrizioni mostrano che lo script che doveva scriverla (`write_t21_prediction.py`, nello scratchpad della
  sessione `f4f38e58`, 26/09 14:27) è stato scritto ma non risulta eseguito. **Interpretazione:** la previsione
  probabilmente non è mai stata scritta; il t21 è caduto per la regola del banco r5. Non si ricostruisce.

  La scheda resta aperta per questa sola voce: la citazione in `reports/invii/trial_2026-09-26/submission_texts.md`
  va marcata come previsione non scritta, oppure il proprietario ne dice la sorte.

### R-021 — Piattaforma, plateau e inferenze causali nelle sintesi

- **Perché è segnalato:** l'audit Codex del 29/09 ha trovato una premessa di piattaforma falsa
  e inferenze più forti delle prove che le sostengono nelle sintesi del 28–29/09.
- **Affermazioni contestate:** tutte le sorgenti della ricetta in 3'; ricetta satura e nessuna
  ampiezza promettente; differenza di una sola coppia di semi trattata come rumore noto;
  t26 come prova che il guadagno di t23 viene necessariamente dai soli geni espressi;
  assenza di un confronto con DepMap per le ipotesi di identità, invece già svolto e conservato
  fuori dalla repository pubblica.
- **Evidenza contraria:** `reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md` (metadati
  originali CD4 GEM-X Flex, hash verificato) e `AUDIT_SCIENTIFICO.md` nella stessa cartella
  (ricette, ricostruzione di 17 invii e compensazioni tra membri). La critica alle inferenze
  non contraddice i punteggi storici.
- **Cosa resta valido:** misure del ponte K562 Flex–3', punteggi ufficiali, confronto t26–t25
  e soglie operative prefissate. I report originali restano immutati.
- **È ancora usato o citato:** sì, in PROGETTO, negli indici e nelle schede della revisione.
- **Disposizione proposta:** le sintesi vive di PROGETTO e dell'indice generale sono corrette;
  leggere i report storici con i due audit accanto. Le nuove prove separano ampiezza e generatore
  e non chiamano ±0,005 un intervallo di confidenza.
  Il 29/09 sono corretti anche l'indice delle sorgenti e i riferimenti al confronto DepMap;
  il ponte storico conserva le sue misure, con questa scheda come chiave di lettura.
  [CP-0046](checkpoints/0046-audit-lead-e-due-vie-neurali.md) corregge esplicitamente
  causalità t26/t23 e rumore da una coppia nei checkpoint 0042/0045 e nelle sintesi vive.
- **Cosa chiuderebbe la revisione:** propagazione delle qualifiche alle sintesi vive rimanenti;
  una prova indipendente per localizzare causalmente il guadagno t23. Nessun esperimento nuovo
  è necessario per riconoscere il saggio CD4, già dichiarato nei metadati originali.

### R-022 — Ancore aggregate e indipendenza della conferma

- **Perché è segnalato:** audit richiesto dal proprietario il 29/09 sulla verosimiglianza
  dei punteggi. Le sintesi attribuivano esattezza alla conversione affine aggregata;
  la conferma HepG2 richiede inoltre una qualifica della sua indipendenza storica.
- **Affermazioni contestate:** esattezza della conversione tramite ancore aggregate
  e riserva della conferma mai valutata. Le ancore ricavate da due invii non identificano quelle dei
  singoli contesti e non ricostruiscono esattamente i successivi score; il terzo punto
  non è una verifica di esattezza. I 96 target sono disgiunti dal dev48 odierno,
  ma 95 erano già valutati in un banco precedente del progetto.
- **Evidenza contraria:** `reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md`,
  `score_credibility_r1/arithmetic.json` e `score_bias_dati_r1/historical_overlap.json`
  nella stessa cartella. T03: media ricostruita meno pubblicata +0,0007302151;
  t25: +0,0008255620. Nove CSV del generatore, rapporti MSE e CI ricostruiti correttamente.
- **Cosa resta valido:** output ufficiali, pesi congelati come definizione di un indice
  locale, aritmetica e superamento del criterio locale. Non si cambia alcuna soglia,
  non si sottrae un residuo costante agli invii futuri, non si riscrive lo storico JSON.
- **È ancora usato o citato:** sì, nei pesi dei banchi, nelle sintesi e nei derivati
  storici degli score; per questo i JSON restano leggibili insieme alla correzione.
- **Disposizione proposta:** corretti LAVORO §2, indice gara e righe del registro; aggiunta scheda
  R-COMP con inventario degli outcome e nuova riserva per studio/linea prima di nuovi
  claim confermativi. [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md) precisa
  CP-0021, CP-0022 e CP-0047; gli originali restano immutati.
- **Cosa chiuderebbe la revisione:** qualifica dei derivati ancora riusati. Ogni derivato storico ottenuto invertendo queste ancore
  rimane una stima, non una misura ufficiale. Le qualifiche vanno propagate quando
  viene riusato; nessuna nuova stima di ancore contestuali è dichiarata qui.

### R-023 — Rete ancorata v3: pilot incompleto, percorso dei dati e ancore sostituiti

- **Perché è segnalato:** il 3/10 sera le ricevute dei training v3 r1 (lette da Codex, riscaricate dalla sessione
  5eacdf) mostrano che il training H1 non soddisfa il bilanciamento che il protocollo v3 richiedeva, e la revisione
  Codex aveva già trovato la dipendenza delle ancore dai bersagli nascosti. La cartella descrive ancora la generazione
  «da adattare» e RPE1 «in attesa» di una sessione GPU.
- **Affermazioni contestate:** che la ricetta di training v3 dia l'esposizione prevista dei gruppi (vale solo su epoche
  intere); che la riserva di valutazione stimata dalla sonda sia affidabile (6.323 s contro circa 1.066 s in H1); che
  le medie delle ancore siano quelle da usare dal prossimo passo (il §9 della v3 stesso chiedeva il regime J).
- **Evidenza contraria:** [diagnosi dei training r1](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md),
  `test_balanced.py`, `test_train_v4.py`, `test_anchors_v4.py` della cartella v4.
- **Cosa resta valido:** il modello (ancora nei logit, guadagno e correzione a zero all'inizio), il protocollo congelato
  come registrazione, i lanci e le ricevute. I risultati scientifici dei due training non sono stati aperti e non sono
  una bocciatura della famiglia di modelli.
- **È ancora usato o citato:** sì, come base della v4, che ne copia il codice invariato dove non cambia.
- **Disposizione proposta:** `superato` dalla cartella v4, che ha protocollo, test e lanci propri.
- **Cosa chiuderebbe la revisione:** niente da chiudere: la cartella resta evidenza datata.

## Revisione periodica e pulizia

**Nessuna cancellazione fa parte di questo processo.** Serve a decidere cosa merita
uno stato diverso, non cosa eliminare.

L'uscita dall'albero del codice e dei documenti che non sono più vivi è un processo
diverso, con il suo meccanismo: tag annotato, righe in [ARCHIVIO.md](ARCHIVIO.md), poi
`git rm` (D-040). Report, checkpoint e dati ne restano esclusi.

Ogni volta che si scrive un checkpoint, ricontrollare tre cose sole:

1. Le righe `da-verificare` sono ancora tali? Una delle loro schede può essere chiusa
   con il lavoro appena fatto?
2. Il materiale nuovo prodotto va aggiunto al registro?
3. Qualche riga `attuale` è stata smentita da ciò che è appena stato misurato?

Candidati alla pulizia, da proporre a chi possiede il progetto e da eseguire solo con
il suo consenso esplicito:

| Candidato | Perché | Condizione per agire |
|---|---|---|
| `.runtime-deps/` | Dipendenza di runtime installata per la sola sonda Orion; ignorata da git e reinstallabile | **Eseguito il 23 settembre**: spostata nel Cestino di Windows (D-040) |
| `C:/Users/ferra/vcc2026-data/predictions/smoke.h5ad` (43 MB) | Prova di formato del writer, già superata dal fatto che `vcc prep` ha validato — **quest'ultima giustificazione non è sostenuta da nessun artefatto**: non esiste un log di `vcc prep` prima del 2026-09-12, e misurato il 2026-09-12 `vcc prep` **rifiuta** un file con meno delle 300 perturbazioni ufficiali (`reports/invii/trial_2026-09-12/`, log del pilot), quindi non può aver validato un file da 3 perturbazioni senza `--no-verify-targets`. Vedi [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §7. Il file resta un candidato alla pulizia per il motivo originale — è una prova di formato — non per quello smentito | **Eseguito il 23 settembre**: spostato nel Cestino |
| Sonde remote in `reports/storico/candidate_verification/*.json` | Alcune sono grandi e sono fotografie datate di endpoint pubblici | Mai cancellare quelle citate nei documenti: sono l'unica prova di cosa si vedeva a quella data |

### R-024 — Identità della banca, ledger congelati e stato del rifit

- **Perché è segnalato:** inventario r1 riferiva un ledger operativo successivamente ampliato;
  alcuni report del 5/10 conservano stati/PID precedenti e il vecchio no-VCC.
- **Affermazioni contestate:** che un indice storage sia un corpus consumato; che note
  «training non iniziato» o divieti datati siano la coda corrente; che il ledger vivo
  conservi per sempre i byte vincolati dall'inventario precedente.
- **Evidenza contraria:** [riconciliazione](../reports/analisi/riconciliazione_banca_2026-10-05/README.md),
  verifica dei pin, copie storiche byte-identiche e autorizzazione INVIO_DIRETTO.
- **Cosa resta valido:** dimensioni datate, identità della ricetta e prove dei vecchi fit;
  storico preservato, nessuna fonte scartata per età.
- **È ancora usato o citato:** sì, come provenienza. Per agire R-LEAD, RIUSO r2 e expected r2.
- **Disposizione proposta:** inventario r1/riuso r1 superati dai riferimenti congelati r2;
  note datate da verificare contro R-LEAD, non riscritte negli originali.
- **Cosa chiuderebbe la revisione:** percorso completo e consumo di tutte le unità ammesse
  provati nel runtime; la sola verifica documentale non chiude D-053.

Controllo automatico della coerenza del registro:

```bash
python scripts/31_check_docs.py
```
