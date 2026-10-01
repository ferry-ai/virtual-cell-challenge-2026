# R-LEAD — strategia scientifica e modello competitivo

- **Stato:** aperto; revisione consegnata, programma da eseguire attraverso R-LAB/R-COMP.
- **Aggiornato:** 1 ottobre 2026, dopo lo scoring t29.
- **Mandato:** revisione lead richiesta dal proprietario; facoltà di riformulare vincoli scientifici precedenti motivandone i bias.
- **Assegnazione:** audit completato da Codex, chat `01a0f724-6a42-7dd0-bd2f-3496d9195695`.
  Il 1/10 il proprietario affida il programma al teammate: [consegna e prompt](../CONSEGNA_TEAMMATE.md).
  Il teammate registra sessione, commit base, macchina e perimetro alla presa in carico secondo
  PIANI §3. Il training corrente e gli invii restano all'agente R-LAB; nessun nuovo training
  avviato dall'audit o dalla consegna.
- **Evidenza:** [revisione con nuove misure](../../../../../reports/analisi/lead_audit_2026-10-01/REVISIONE.md),
  [consegna tecnica](../../../../../reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md).
- **Prossimo passo:** completare A/B: split immutabili, controlli e pesi verificati, baseline
  addestrate e verifica dei gradienti della miscela. Il pavimento `pi` implementato da R-LAB
  è una modifica da valutare, non dimostra risolto il problema di apprendimento
  ([diagnosi r3](../../../../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md),
  [protocollo del quarto training](../../../../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md)).
  Prima consegna sperimentale proposta: banco diagnostico di sviluppo a sei membri per
  transfer e reti disponibili, con gli stessi target, geni, controlli e generatore;
  controllare il percorso di esportazione e la discriminazione fra bersagli. Le coorti
  già valutate restano sviluppo; una conferma richiede una riserva separata.
- **Vincolo dopo t29:** applicare il ramo c registrato: nessun altro invio della rete prima
  che il banco a sei membri la mostri almeno al livello del transfer
  ([CP-0055](../../../../checkpoints/0055-t29-rete-cellulare-punteggio.md)). Un residuo sul transfer è
  ancora un'ipotesi, non un candidato promosso.
- **Riordino documentale (1/10, 23:13 CEST):** Codex, chat
  `01a0f949-2230-7703-b5c2-7d467397b431`, su richiesta di orientamento dopo lo score.
  Il proprietario conferma in chat che Claude e teammate sono fermi. Perimetro: mappe
  `PROGETTO`, `PIANI`, `AMBITI` e intestazioni delle schede; nessuna riassegnazione del
  programma, nuovo training o modifica di protocolli congelati. Esito: mappe e otto schede
  riallineate al t29, con consegne storiche distinte dai passi vigenti; nessuna nuova scheda.
  Le evidenze restano quelle citate; il prossimo passo scientifico è quello sopra.
- **Dipendenze:** [R-LAB](piano-giorno-2026-09-30.md), [R-COMP](modello-competitivo.md),
  [GENERALIZZAZIONE](../../../../GENERALIZZAZIONE.md), D-050 in [DECISIONI](../../../../DECISIONI.md).
- **Chiusura della revisione:** rapporto, misure riproducibili e programma consegnati.
  **Chiusura del programma:** vantaggio verificato sul banco indipendente, produzione
  riproducibile e valutazione ufficiale; nessun piazzamento promesso.

## 1. Obiettivo e criterio di competitività

Il modello deve prevedere la distribuzione di risposte in un contesto nuovo usando i suoi
controlli e le informazioni lecite sul bersaglio. Deve sfruttare la memoria dello stesso
intervento quando esiste (C) e condividere informazione biologica quando manca (J).
Un esito T è utile per capire il meccanismo, ma non sostituisce il contesto nuovo.

Per la gara, «competitivo» significa un miglioramento confermato sull'intera catena rispetto
alla ricetta di riferimento, con sei membri espliciti e robustezza ai contesti; non il solo
abbassamento della loss o un massimo di classifica isolato. La graduatoria finale D/E/F resta
la verifica esterna. Per la ricerca scientifica, significa in aggiunta generalizzazione J
su contesti e famiglie esclusi, con ablation e incertezza appropriate alla dichiarazione.

## 2. Architettura candidata, da giustificare per componenti

**Ingresso:** cellule di controllo e loro maschere, library size, assay/studio quando disponibili;
bersaglio e descrittori funzionali con provenienza, modalità CRISPRi/a/KO, dose/tempo/guida quando
noti. Metadati mancanti hanno una maschera: non si inferisce il tempo dalla risposta di test.

**Memoria del bersaglio:** stima degli effetti osservati dello stesso intervento, con incertezza
per studio/replicato e supporto genico esplicito. Non fondere CRISPRa, CRISPRi e KO come se fossero
interventi equivalenti; condizionare sulla modalità e verificare il trasferimento fra modalità.

**Correzione biologica:** modello regolarizzato di programmi di risposta e interazioni con
lo stato dei controlli. Addestrare inizialmente un residuo bilineare/a basso rango, poi una rete
solo se supera quel confronto con gli stessi input. Il ramo J non accede alle risposte dei
bersagli esclusi. Un peso di affidabilità, imparato out-of-fold, decide quanto usare memoria
e correzione. Nessun selettore usa il vincitore osservato nel test.

**Popolazione:** preservare più stati latenti dei controlli; stimare cambiamenti entro stato
e variazioni delle proporzioni di stato. Il decoder genera conteggi e profondità coerenti.
Iniziare da una miscela compatta; attenzione su insiemi e flow matching restano candidati
se la miscela fallisce su multimodalità o cambiamenti di stato misurati. Non inventare coppie
fra cellule di controllo e perturbate che sono state misurate distruttivamente.

**Obiettivo:** likelihood di conteggi mascherata più vincoli sui contrasti trans e sui momenti
delle popolazioni, stimati da gruppi del solo training. Pesare per disegno, non per dimensione
del file. Scegliere i coefficienti sulla validation interna; usare i sei membri dello scorer
per selezionare il candidato finale. È una proposta da confrontare, non una ricetta adottata.

## 3. Programma con deliverable e condizioni di avanzamento

| Passo | Deliverable | Condizione per avanzare | Se non passa |
|---|---|---|---|
| A. Rendere interpretabile il training | Split immutabile; ruoli dopo QC; controlli stratificati; replay dei pesi; baseline generica addestrata; test dei controesempi | Gruppi stabili all'aggiunta di dati; coefficienti conformi; fallback misurati; esclusioni globali verificabili | Correggere il contratto prima di attribuire prestazioni all'architettura |
| B. Banco a più contesti | Matrice contesto × studio × target × modalità × assay, fold C/T/J, sviluppo separato da riserva e confronti semplici | Ogni dichiarazione ha supporto e gruppi indipendenti adeguati; H1 qualificata correttamente | Limitare la dichiarazione ai gruppi disponibili; acquisire dati ponte solo con accesso e risorse autorizzati |
| C. Primo modello ibrido | Transfer, generico, bilineare, rete corretta e residuo out-of-fold sugli stessi fold | Vantaggio ripetuto fra gruppi e semi, nel regime dichiarato, secondo una regola congelata prima | Tenere transfer in C e confronto semplice in J; studiare gli errori senza aumentare automaticamente la capacità |
| D. Informazione dei dati | Ablation annidate per dati ponte, assay e modalità con split fisso; curve per numero di target/contesti/cellule | Guadagno a esposizione e copertura comparabili, replicabile sui contesti esclusi | Cambiare campionamento e qualità, non continuare a sommare cellule alla cieca |
| E. Distribuzioni e generatore | Stima di stato e composizione; confronto miscela compatta / generatore attuale; eventuale flow | Miglioramento della catena completa sui sei membri, stabilità fra semi e ablation del contesto positiva | Conservare il generatore più semplice; non attribuire al predittore un guadagno di sola emissione |
| F. Conferma e produzione | Candidato congelato, riserva aperta una volta, pacchetto a forma piena, manifest e riproduzione | Regola registrata soddisfatta, nessuna fuga, supporto finale auditato, preparazione e inferenza complete | Nessuna promozione retroattiva; usare il riferimento affidabile e trattare l'esito come sviluppo futuro |

L'ordine esprime dipendenze, non tempi stimati o limiti preventivi al lavoro.
R3 e t29 sono conclusi: leggerli secondo i protocolli loro, senza riscriverli.
Il t29 non supera la sua regola; il banco richiesto dal ramo c precede ogni nuovo invio neurale.

## 4. Contratto di valutazione del nuovo programma

1. **Split:** congelare target e gruppi di contesto/studio prima del fit; assegnare i nuovi
   target senza cambiare quelli vecchi. Separare holdout per identità e per famiglia
   funzionale, senza chiamare il primo extrapolazione funzionale forte. Salvare ruolo
   previsto, QC e ruolo effettivo. Audit di alias, guide, duplicati e pretraining.
2. **Indipendenza:** controlli del contesto nuovo ammessi in ingresso; risposte perturbate
   escluse da fit e selezione. Le librerie usate per misurare il contrasto devono essere
   separate o incrociate con quelle che stimano il basale quando il disegno lo permette.
   H1 test resta chiusa e non è un contesto nuovo, dato che H1 train/val sono nel corpus.
3. **Confronti:** nullo, generico addestrato, transfer dove disponibile, bilineare con gli
   stessi descrittori, rete con target/descrittori permutati, contesto ignorato o scambiato.
   Parità di tuning, informazioni e supporto, non soltanto di seed.
4. **Misure:** effetti trans, numerosità e affidabilità per target; likelihood e calibrazione
   sui controlli; sei metriche ufficiali per le popolazioni. Separare score grezzi, normalizzati
   e indice locale. Non convertire con ancore globali stimate un proxy in score ufficiale.
   Verificare import e versione dello scorer nel runtime effettivo prima del banco.
   [CP-0054](../../../../checkpoints/0054-visibilita-scorer-e-consegna.md) precisa la diagnosi del 1/10:
   `cell_eval2.config` non era visibile dal sandbox; lo stesso Python fuori dal sandbox
   passa tutti i 287 test senza reinstallazioni. Confrontare i contesti di esecuzione prima
   di riparare un ambiente, senza sostituire tacitamente la metrica.
5. **Aggregazione:** macro per contesto e regime per la lettura scientifica; media coerente
   con il contratto di gara per quella operativa. Riportare entrambe e i supporti.
   Nessun tetto «400 più numerosi» che cancelli silenziosamente interi contesti.
6. **Incertezza:** almeno tre seed per i finalisti quando si intende attribuire stabilità
   al seme; intervalli appaiati e bootstrap per studio/contesto/famiglia quando il numero
   di gruppi lo permette. Tre seed non garantiscono potenza o indipendenza. Stabilire
   numerosità dopo la varianza del pilot, senza «rumore = 0,005». Considerare il numero
   di candidati selezionati e confermare su riserva.
7. **Promozione:** prima della prova registrare metrica primaria, aggregazione, miglioramento
   pratico richiesto e perdite ammissibili sugli altri membri. Per una dichiarazione J serve
   J; un miglioramento C può essere adottato per C se preserva il ramo J secondo la regola
   registrata. Nessun obbligo che tutti i membri migliorino. Le soglie dei protocolli vecchi
   restano immutate (D-050).

## 5. Strategia dei dati e insight da approfondire

Priorità al grafo delle sovrapposizioni: lo stesso bersaglio in più linee, lo stesso contesto
in assay diversi, donatori e guide replicati. Registrare componenti disconnesse: non attribuire
alla biologia un effetto che coincide perfettamente con lo studio. CD4 Flex è una priorità
informativa per assay/stato; HIPSCI per donatore; Orion amplia il transfer ma il suo assay va
qualificato. VIPerturb richiede verifica/accesso prima di entrare nel training. L'inventario
completo resta in R-LAB; questa scheda non dichiara nuovi dataset scaricati.

Le analisi HepG2 mostrano J più rumoroso e meno osservato di C. Il prossimo studio deve
ripetere split metà/metà e sottocampionare a numerosità appaiata, possibilmente per libreria
e guida; confrontare separatamente risposta cis e trans. Per POGLUT3, TFAM e gli altri casi
anomali, controllare espressione basale, guide, distribuzione dei conteggi e repliche prima
di concludere che una funzione sia imprevedibile. Non filtrare la valutazione in base
all'efficacia osservata delle guide (D-011).

I vantaggi della rete su BOP1/MED4/NCL e altri target motivano un'analisi funzionale congelata:
arricchimento con universo corretto, controllo di numerosità/espressione e conferma su target
esclusi. Sono ipotesi generate dall'audit, non conferme di pathway.

## 6. Dal programma al set finale, e oltre

**Prima del 22 ottobre:** completare A/B, misurare C e il contributo informativo D; promuovere E
solo se i confronti lo giustificano. Congelare un riferimento riproducibile, criteri per
supporto C/J, fallback per geni mancanti e una prova a forma piena. Verificare disco, memoria,
tempi misurati di inferenza e preparazione, senza assumere lo spazio del 30/09.

**Dal rilascio D/E/F del 22 ottobre alla chiusura del 5 novembre:** audit dei nuovi controlli,
assi, bersagli e supporto pubblico; applicare le regole di adattamento già congelate.
Rieseguire estrazione e inferenza sul nuovo pannello; controllare target, maschere, conteggi,
semi e manifest. Distinguere nuovo pannello da target mai osservati. Non usare il risultato
finale per scegliere a posteriori la dichiarazione di generalizzazione. Nuovi invii/calcoli
seguono le autorizzazioni operative già vigenti.

**Dopo la gara:** benchmark continuo su studi e contesti esterni acquisiti dopo il congelamento,
ablation pubblicabili e analisi degli errori per programmi/stati. Se il limite misurato è la
mancanza di collegamenti biologici, progettare un pannello di perturbazioni ponte; se è la
multimodalità, estendere la transizione di stato; se è l'incertezza, introdurre astensione e
calibrazione. La scala del modello viene dopo la dimostrazione di quale limite risolve.

Date e impostazione della gara verificate il 1/10 sulla
[pagina degli organizzatori](https://arcinstitute.org/news/virtual-cell-challenge-2026).
Questa è la direzione della lead, non un'autorizzazione a spesa, download o nuovi job.
