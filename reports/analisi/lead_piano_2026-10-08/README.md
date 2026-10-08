# Decisioni lead: dati, candidato delle 02:00 e modelli esterni

8 ottobre 2026, Codex. Mandato: analizzare lo stato e scegliere le prossime mosse,
inclusa la conversazione Claude allegata dal proprietario. Scadenza interpretata come
**9 ottobre 2026, ore 02:00 Europe/Rome**. Prima lettura dell'orologio: 17:03 dell'8 ottobre.

**Decisione di pianificazione:** conservare t36 come candidato di riserva; completare
l'interfaccia della banca su tutti i bersagli e contesti idonei; valutare un solo
contrasto nuovo del transfer per la consegna breve; aprire PIE come primo confronto
esterno con pesi pubblici, inizialmente congelati. Non rilanciare la CellNet precedente
invariata e non impilare GEARS, STAR, PLE e un generatore nuovo nella stessa prova.

Questa sessione produce analisi, un riconto riproducibile e decisioni per il piano.
Non produce un nuovo modello addestrato, un nuovo punteggio o una verifica dei runtime
cloud attuali. I job sotto sono da eseguire, non job avviati. La sede operativa rimane
[R-LEAD](../../../docs/piani/strategia-scientifica.md); nessuna autorizzazione di
download, quota, invio o push è desunta da un report precedente.

| Materiale | Natura |
|---|---|
| Questo rapporto | Interpretazione e scelte progettuali, con limiti e piano di consegna |
| [audit_metadata.py](audit_metadata.py), [audit_r1.json](audit_r1.json) | Riconto di piccoli metadati locali con SHA e verifiche di coerenza |
| [FONTI_ESTERNE.md](FONTI_ESTERNE.md) | Fonti primarie riaperte, disponibilità di modelli e catalogo dei dati PIE; nulla acquisito |
| [VERIFICHE.md](VERIFICHE.md) | Controlli eseguiti e limiti della sessione |

## 1. Che cosa funziona, che cosa resta aperto

**Misure preesistenti verificate nei report e nei JSON**, senza nuovo scoring:

| Percorso | Evidenza | Decisione |
|---|---|---|
| Transfer t36, effetti t25 ed emissione t28 con banca estesa | Score ufficiale 0,147249 contro 0,144845 del t28; +0,002404 in un solo invio | Riferimento operativo e riserva per stanotte; non un vincitore statisticamente confermato |
| Banca canonica r1 | 17 tabelle lette, 13 con voti sul pannello; solo 17/300 bersagli cambiano rispetto a t36; nessun banco o invio | Candidato da valutare, non promozione automatica |
| CellNet t29 | Score ufficiale **−0,029625**, non un delta di −0,03; PDS grezzo 0,50 contro 0,79 del t22 | Non ripetere la sostituzione integrale del transfer |
| Rete ancorata v4 | Peggiora l'ancora su tutte le tre linee valutate; correzione comune dominante | Fermare l'espansione di quella formulazione |
| Ibrido t30 | 0,135249, −0,004989 dal t25; guadagno locale ridimensionato con più semi/cellule; regressione PDS nel fold esportato | Conservare infrastruttura e guardie; candidato non promosso |
| Contesto cellulare | Nel pilot lo stato delle cellule aiuta rispetto al loro profilo medio, ma non supera il transfer | Informazione promettente, non una prova che basti aumentare la rete |
| GEARS adattato | Modulo e sette fixture; nessun grafo reale, integrazione completa o training | Seconda priorità di ricerca, non candidato pronto |

Fonti: [t36](../../invii/prediction_t36_2026-10-06/comparison.json),
[invii](../../invii/README.md), [banca r1](../../modelli/banca_canonica_2026-10-07/README.md),
[S-001–S-010](../../../docs/STRADE.md),
[diagnosi t30](../../modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md),
[GEARS](../gears_nella_rete_2026-10-04/README.md).

**Interpretazione:** i risultati sostengono l'ampliamento controllato delle fonti,
ma non l'idea che più cellule risolvano da sole il trasferimento del contesto.
Nel t36 PDS e NMAE migliorano; reach, fedeltà e Jaccard peggiorano e MSE scalata
rimane zero. Serve migliorare gli effetti specifici senza distruggere PDS.
Il banco locale orienta la scelta: non converte il proprio delta in punti VCC.

## 2. Audit della chat Claude

**Riconto nuovo, solo metadati:** 39.973.948 cellule contabilizzate nella banca;
38.176 controlli H1 sono duplicati fra due unità. Togliendo soltanto questo duplicato
noto si arriva a 39.935.772, non a un totale universalmente deduplicato.
Le 17 unità fuori dal voto contengono 4.237.927 cellule (10,60%), ma includono
K562 GWPS, già rappresentato dalla tabella BULK. Quel 10,60% non misura informazione
biologica interamente perduta.

Le righe controlli+pannello associate alle fonti ammesse rappresentano **2.367.170
cellule, 5,92%** del conteggio di banca. Il numero riproduce il registro, ma **non è
un contatore delle cellule viste da un training**: stage 100 legge tabelle aggregate;
K562 BULK è fuori da questo denominatore e sono inclusi controlli di tabelle senza
voti sul pannello. I 189,195 GB di campioni persistenti non sono consumati da questo fit.
Nelle stesse unità ammesse esistono **32.803.832 cellule etichettate fuori pannello**.

| Affermazione della chat | Giudizio |
|---|---|
| Quattro fonti nuove, 17 target modificati, 283 invariati | Confermata dai metadati del fit |
| La maggior parte delle cellule appartiene a fonti ammesse | Vero come appartenenza; non prova contributo alla previsione |
| Il fit usa solo circa il 6% | Indicazione utile del restringimento al pannello, con i limiti del conteggio appena descritti |
| Per usare il resto servono reti sulle singole cellule | **Troppo forte:** regressione multibersaglio, fattorizzazione, embedding, effetti aggregati e PIE possono condividere informazione fra target. D-053 continua comunque a richiedere anche un percorso cellulare effettivo |
| I campioni cellulari non servono al transfer | Non sono necessari al suo stimatore puntuale attuale; possono servire a controlli di incertezza, eterogeneità, guide/repliche ed emissione. Le sole somme non conservano tutta la distribuzione |
| I target nuovi del 22 ottobre richiederanno necessariamente vicini | No: nuovi per la gara non significa assenti dalle sorgenti pubbliche. Calcolare il supporto del nuovo pannello prima di instradarli |
| CRISPRa è l'opposto di CRISPRi | È un intervento diverso, non il negativo matematico della risposta. Nessuna inversione automatica del segno |
| Usare tutti i target rende la risposta comune più stabile | Può ridurre rumore di stima, ma cambia anche il bersaglio statistico: pannelli mirati e genome-wide hanno composizioni biologiche diverse. Miglioramento non dimostrato |

**Conclusione sulla conversazione:** continuare il suo lavoro sulla banca e fare il
contrasto della centratura. Non farne l'unico programma scientifico. Il collo di
bottiglia è passare da un archivio ampio a consumatori che apprendano e generalizzino;
non soltanto aumentare il numero di tabelle che figurano nel manifest.

## 3. Finalizzare dati → training

**Scelta:** un'unica banca canonica, con viste diverse per consumatore. Non rifare
l'ingestione dei dati verificati e non rendere il pannello di 300 geni l'universo
permanente di training.

`archivio verificato → identità/QC → banca di tutti i target → split → viste del fold → consumatore → ricevuta`

Gli aggregati globali si possono conservare per strato; ogni statistica appresa,
pooling, riferimento, centratura e descrittore derivato dalle risposte viene però
costruito **dopo** le esclusioni del fold. Per J si eliminano i target nascosti e
le loro componenti da tutte le fonti; per C/J la linea esclusa va tolta in tutti
gli studi/stimoli. H1 test resta chiusa.

### Tre consumatori, un solo ingresso

1. **Transfer:** viste di effetti su tutti i target validi, poi selezione del
   pannello richiesto; l'ancora stessa-bersaglio rimane il riferimento.
2. **Apprendimento degli effetti:** tutte le coppie contesto × target ammesse,
   con maschere dei geni, numerosità, incertezza e modalità. PIE e un modello
   semplice di controllo leggono questa vista, non necessariamente tutte le cellule
   a ogni epoca. È un ramo complementare, non sostituisce il mandato cellulare.
3. **Training cellulare:** shard stratificati e annidati, bilanciamento verificato
   per linea/donatore/stimolo/target/modalità e controlli abbinati. Un livello
   iniziale come 32 o 64 è una proposta da dimensionare sui dati di training;
   non si eliminano contesti e non si scelgono i tetti sulle risposte del test.

La banca registra livelli 32/64/128 per 43 unità su 45: le somme dei conteggi
riportati sono 12,48/15,60/22,61 milioni. Sono livelli sovrapposti, non dati da sommare;
per due unità HIPSCI genome-wide il dettaglio non è numerico. Nessun numero certifica
un loader neurale già pronto su tutto il corpus. Verificare anche deduplica e controlli
prima di usarli per dimensionare una corsa.

### Decisioni sulle esclusioni

| Fonte o lacuna | Scelta scientifica e lavoro richiesto |
|---|---|
| KO: A549, Frangieh, Sunshine, Dixit, Shifrut | Integrare in un ramo con modalità distinta; possibile supervisione/descrittore ausiliario. Nel breve non aggiungerli con peso unitario ai voti CRISPRi. La mancata discesa dell'mRNA non basta a invalidare un KO |
| CRISPRa: Norman, Tian, Southard | Ramo distinto con identità dell'intervento e combinazioni; mai negazione automatica del delta né voti KD indiscriminati |
| K562 BULK e GWPS cellulare | Un esperimento, un voto. Le cellule possono supervisionare il ramo cellulare senza costituire una seconda sorgente indipendente |
| Tian 2019 RFK | Nuova release candidata r2 senza il voto RFK quasi nullo, motivata dalla scarsa evidenza di KD; conservare r1. Non riscrivere l'esito della regola originaria e non escludere per questo l'intero contesto neuronale dal programma |
| Tian 2019 iPSC, Sunshine e altri label set enormi | Decodificare guide/combinazioni e verificare QC prima di chiamare ogni etichetta un gene: i 39.161/41.357/24.194 target nativi del registro richiedono riconciliazione, non sono conteggi certificati di geni singoli |
| HIPSCI genome-wide | Pochi NTC: riferimento gerarchico o uso documentato delle non assegnate solo con sensibilità e incertezza; non chiamare automaticamente NTC le cellule senza guida. Se non identificabile, ruolo basale/ausiliario e lacuna supervisionata esplicita |
| Papalexi arrayed | Sotto soglia è quella coppia del pannello, non automaticamente tutto lo studio. Integrare tutti i target scientificamente utilizzabili, senza inventare precisione dalle quattro cellule |
| Datlinger/Adamson/Papalexi RNA | Mappa guida→gene/controllo da metadata primari; niente stripping euristico non verificato e niente duplicazione delle combinazioni come singoli interventi |
| DLD-1/Mixscale/Southard aggregati | Adapter di effetti, scala/SE e maschera di risposta; nessuna cellula sintetica spacciata per supervisione osservata. Per i file cellulari, conversione separata |
| Farmaci, ORF, enhancer, proteine, dati normalizzati, topo | Ruoli separati secondo compatibilità; non sono tutti automaticamente inutili né conteggi RNA umani. Esclusione dal ramo attuale distinta dall'esclusione definitiva dal programma |

**Coda prioritaria:** prima decodifiche/adapter e derivati di materiale già verificato;
poi lacune di contesto e combinazioni informative; infine nuove acquisizioni motivate.
Nessuna priorità bassa diventa cancellazione di una linea idonea.

Il catalogo non è chiuso: 100 record = 42 associati a banca + 13 alias + 44 senza
banca + 1 solo archivio. Inoltre Orion HCT116/HEK293T sono fuori dal catalogo r4.
I 44 motivi di esclusione sono stati riportati dal registro, non riverificati oggi.
VIPerturb cellulare, microglia e PerturbFate compaiono ancora come lacune in AMBITI:
riconciliare anche questi nomi e le 77 accessioni aggregate, non limitarsi al conteggio
dei 100 record. Le difformità CD4 fra righe originali e ammesse richiedono un ledger QC.

**Criterio di chiusura D-053:** per ogni contesto idoneo, ruolo realmente eseguito;
per ogni esclusione, evidenza e condizione di riesame. La ricevuta deve separare
atteso/ammesso/campionato/letto, target/guide, controlli, contributo alla loss o alla
predizione, peso effettivo e ripresa da checkpoint. Invarianti per ogni finestra di
training, non solo a fine epoca. Se manca un contesto richiesto, il training è parziale.

## 4. Il contrasto del transfer che autorizzerei scientificamente

**Mantenere la proposta 1 di Claude, con una domanda più precisa:** cambiare la
popolazione di bersagli usata per centrare ogni sorgente migliora le sei metriche,
a banca, ampiezza, testa cis e generatore fissi?

Tre riferimenti logici, senza confondere i contrasti:

- **T0:** t36 ricostruito esattamente, riferimento ufficiale.
- **T1:** release r2 candidata (r1 senza il voto RFK dubbio), centratura attuale.
  T1−T0 misura il pacchetto delle fonti candidate, non la nuova centratura.
- **T2:** stessa release di T1, media di tutti i target ammissibili del training
  per sorgente, con maschere. T2−T1 isola la centratura.

La formula è `d_s,t,g − gamma × m_s,g`; non si aggiunge al contesto destinatario
una risposta media perturbata osservata. Il vettore congelato è già supportato da
[stage 100](../../../scripts/100_build_context_effects.py), righe 88–100 e funzione
`load_common`; richiede gli assi e tutte le sorgenti della ricetta. Nei fold J,
`m_s,g` non vede alcun target nascosto. Nel fold C non vede risposte della linea fuori.
Media sui target, non sulle cellule: altrimenti i target più abbondanti cambiano i pesi.
Variare questa scelta è un'altra ablation, non un dettaglio del codice.

**Precedenti:** S-010 riguarda l'ampliamento delle sorgenti; S-006/S-009 insegnano
che la componente comune può danneggiare PDS e che il banco deve coincidere con
l'export. Il [banco della risposta comune](../../trasferimento/risposta_comune_2026-09-26/RISULTATI.md)
provava ad aggiungerla e aveva esito negativo: non è questo contrasto. Gli universi
genome-wide, medie J e la gestione di vettori congelati esistono già: la novità
proposta è il confronto controllato sulla banca canonica attuale, non l'idea di
leggere altri bersagli.

**Segnale precoce e arresto:** errori di split/asse/copertura o mancata parità a
ramo nullo bloccano l'accettazione. Perdita PDS ripetuta o aumento della componente
comune porta a diagnosi, non a spostare la soglia dopo il risultato. Non inseguire
il 100% delle cellule rappresentate come obiettivo predittivo.

## 5. Che cosa prendere dagli altri predittori

L'ordine seguente è una **decisione di priorità**, non una classifica di efficacia
misurata nel progetto. Il vincolo «solo equazioni, pesi fuori» del rapporto del 5/10
era il suo perimetro: la richiesta attuale include esplicitamente modelli già fatti.

| Priorità | Risorsa | Primo impiego | Perché/non ancora |
|---|---|---|---|
| 1 | **PIE** | Predittore congelato di effetti, confrontato con transfer; poi eventuale componente o insegnante | Affronta C/J con conoscenza biologica e risposte di training; checkpoint pubblici. Integrazione e utilità nostre non misurate |
| 2 | ESM2, GO/STRING e fonti biologiche PIE | Descrittori congelati dei target; regressione semplice di controllo e poi residuo cellulare | Permettono condivisione fra target. Annotazione non è risposta causale né garanzia di vantaggio |
| 3 | GEARS adattato | Encoder a grafo del bersaglio nel correttore già esistente | Prototipo locale disponibile; GEARS originale non supporta automaticamente il trasferimento cross-contesto |
| 4 | STATE SE/ST | SE come descrittore dei controlli; ST come concorrente separato | Distinguere embedding da predittore; il checkpoint e lo split devono corrispondere al problema genetico |
| 5 | X/scFoundation e PRiMeFlow | Da X: residuo, descrittori proteici e calibrazione; da PRiMeFlow: generatore solo dopo verifica degli effetti | I vincitori 2025 non costituiscono una prova per contesti mai perturbati nel training; PRiMeFlow cambia anche emissione e scala |
| 6 | AMMI/STAR/FiLM moltiplicativo | Un solo residuo semplice senza ramo additivo libero, se PIE non è operativo | Ipotesi generali, non modelli biologici pronti. Non impilare PLE/HorNet/cross-attention prima dell'ablation semplice |
| Sospeso | Arc Stack | Nessun rilancio identico | Il confronto locale A/B era già negativo; riaprire solo per una differenza concreta di input/checkpoint/contratto |

Evidenze locali: [GEARS](../gears_nella_rete_2026-10-04/STUDIO.md),
[catalogo del 5/10](../pezzi_adottabili_2026-10-05/CATALOGO.md),
[vincitori 2025](../lezioni_vcc2025_2026-10-03/README.md),
[Stack A/B](../../../docs/checkpoints/0051-stack-ab-negativi.md).
Per STATE/PRiMeFlow e le informazioni nuove di PIE: [fonti primarie](FONTI_ESTERNE.md).

**Correzione concettuale al catalogo:** togliere bias o usare un prodotto bersaglio
× contesto non garantisce residuo medio zero: gli embedding dei bersagli possono
avere media non nulla o essere quasi costanti. Servono centraggi definiti sul training,
controlli con target permutati e guardie all'inferenza. «Specifico per costruzione»
non va dichiarato dalla sola presenza del bersaglio nell'equazione.

### PIE: integrazione concreta

PIE è stato annunciato il 5 ottobre. La sua previsione è a livello di effetto,
non un pacchetto di cellule già nel nostro formato. Usa conoscenza biologica,
controlli del contesto e risposte del training. Questo lo rende una priorità
pertinente, non prova che superi t36. [Annuncio Arc](https://arcinstitute.org/news/pie).

Scelgo **prima un checkpoint `wdataset` del fold corrispondente alla linea esclusa**
per verificare l'adapter: quattro fold distinti, non ensemble già validato; asse
Replogle di 6.642 geni. Poi `xdataset`, che usa Tahoe/Jiang/VCC25/Orion, solo dopo
aver verificato accessi, split e riserva H1. «Replogle escluso» è una dichiarazione
sul dataset: per il nostro C serve verificare anche l'identità delle linee in
tutte le sorgenti. La dimensione effettiva dell'intersezione con l'asse VCC va misurata.
[Scheda wdataset](https://huggingface.co/arcinstitute/PIE_replogle_wdataset),
[scheda xdataset](https://huggingface.co/arcinstitute/PIE_replogle_xdataset).

Per un checkpoint fissato non si può cambiare arbitrariamente lo split e chiamarlo
J: pesi e memoria delle risposte possono avere già visto i target. Prima valutazione
sugli split leciti pubblicati; per il nostro J stretto serve sovrapposizione verificata
degli holdout oppure un rifit con le esclusioni. Togliere righe dalla cache non
disimpara i pesi. Nessun checkpoint potenzialmente esposto a H1 test entra nella
valutazione della riserva.

**Adapter proposto:** `PIE → tabella effetti+maschere → emitter t28 → scorer reale`.
`lfc_pred` è log2: conversione a log naturale `ln(2) × lfc_pred`, seguita dalla
verifica di equivalenza delle normalizzazioni e del comportamento del generatore;
non applicare meccanicamente l'ampiezza t25 a un modello già calibrato. `p_de`
è una probabilità predetta, non un p-value osservato né una chiamata dello scorer;
`delta_p_pred` non è un log-fold-change. Nessun doppio cis o doppio guadagno.
Fuori supporto PIE si conserva il transfer; nei confronti si riporta sia il supporto
comune sia il pannello intero con questo fallback.
[Contratto output](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/model/heads.py),
[inferenza](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/infer.py).

Per i nuovi contesti usare i soli controlli osservati; non inventare identità
Cellosaurus o descrizioni certe. Verificare il comportamento del checkpoint in
assenza di `context_text`; un'ablation da riaddestrare non equivale a spegnere
arbitrariamente una sorgente in un modello congelato.

**Ordine di riuso:** (1) benchmark congelato; (2) ramo alternativo con fallback;
(3) miscela/affidabilità calibrata fuori fold, solo se gli errori sono complementari;
(4) distillazione o fine-tuning sulla banca, continuando la supervisione cellulare
del modello principale. Distillazione e pseudo-label ereditano eventuale leakage
del teacher. Nessun ensemble «perché due modelli sono meglio di uno».

**Fattibilità:** Python 3.12 e ambiente separato. Il checkpoint richiede anche
gli asset originali delle risposte di training per la propria memoria, non solo
un file di pesi. I commit della model card differiscono da alcuni puntatori del
`main` corrente: usare quelli incorporati nel checkpoint e verificarli; non
mescolarli. Batch/chunk, RAM host, VRAM, compatibilità precisione e copertura
vanno misurati prima di assegnargli una scadenza.
[Codice di inferenza](https://raw.githubusercontent.com/ArcInstitute/pie/main/src/pie/predict.py),
[repository](https://github.com/ArcInstitute/pie).

La documentazione riporta per il training `wdataset` due H100, circa 20 GiB/GPU;
per `xdataset` otto H100 e circa 78,5 GiB/GPU. Sono le corse degli autori, **non**
requisiti minimi o tempi trasferibili a Kaggle. Stanotte: pesi congelati e prova
di fattibilità, non una riproduzione da zero del training grande.
[Specifiche delle corse](https://raw.githubusercontent.com/ArcInstitute/pie/main/AGENTS.md).

## 6. Consegna entro le 02:00

**Definizione di finito:** release identificata e ricostruibile, input/versioni
congelati, effetti e generazione tecnicamente verificati, report del confronto
con t36 e manifest della copertura. Un nuovo candidato viene promosso solo se
passa il banco; altrimenti la consegna conserva t36 e documenta il risultato.
Questo non garantisce un nuovo massimo ufficiale, un risultato del server entro
le 02:00 o il completamento dell'intero D-053 stanotte.

Le ore sotto sono **punti decisionali**, imposti dalla scadenza richiesta, non
stime di durata dei job. La pianificazione va aggiornata con throughput e risorse
misurati; non si sposta la qualità minima per rispettare l'orologio.

| Entro, Europe/Rome | Risultato richiesto | Se non disponibile |
|---|---|---|
| 18:00, 8/10 | Preflight attuale di Colab e account Kaggle configurati, accessi/input; snapshot t36 e protocollo dei contrasti | Registrare il blocco; nessuna esecuzione pesante sul portatile per comodità |
| 19:00 | Release candidata e derivazioni necessarie identificate; splits/assi coerenti; priorità delle lacune D-053 | La banca continua su release successive; niente fonti non verificate nella consegna |
| 21:00 | T0/T1/T2 disponibili per il banco; PIE deve avere completato almeno inferenza reale, adapter e verifica di esposizioni/assi/risorse | PIE resta ricerca e non entra nella selezione notturna. Se T2 non è pronto, si confronta T1 con T0 |
| 23:00 | Confronto appaiato completato e candidato unico congelato | Nessuna promozione da un banco incompleto: t36 resta la consegna; se necessario congelare prima secondo il tempo residuo misurato |
| 01:30, 9/10 | Generazione/packaging, hash, formato e diagnostiche della release scelta verificati | Consegnare esplicitamente lo stato incompleto; non chiamare pronto un artefatto solo lanciato |
| 02:00 | Modello/pacchetto e report, oppure fallback t36 identificato con i limiti | Un eventuale upload e il tempo di scoring del servizio sono eventi distinti |

**Assegnazione dei runtime:** Colab CPU per banco e generazione; Kaggle CPU per
derivazioni indipendenti e fold; Kaggle GPU soltanto per inferenza/training neurale
con CUDA effettiva. Distribuire i job autorizzati negli slot consentiti, con
input accessibili e ricevute di esecuzione reale. RAM non sommabile fra runtime;
nessun acquisto o aggiramento di quota. I numeri del preflight del 7/10 non attestano
disponibilità oggi. Pacchettizzare anche `reports/`, assente dal mirror standard.

**Blocco locale rilevato nei controlli della sessione:** anche usando
`.\scripts\py.cmd`, tre test dello scorer falliscono perché manca
`cell_eval2.config` nell'ambiente del progetto. Questo non prova un difetto del
runtime cloud; impone che il preflight del banco verifichi import e preset dello
scorer nel runtime effettivo prima di spendere il resto della corsa. Dettagli in
[VERIFICHE](VERIFICHE.md). Non è stato modificato o reinstallato l'ambiente.

### Regola per accettare un candidato

Prima dei lanci congelare target, linee, artefatti, asse, calibrazione e trattamento
dei denominatori locali. Le cinque linee già lette sono **sviluppo**, non una
nuova conferma indipendente. Scegliere una riserva realmente non esposta per una
conferma successiva, senza aprire H1 test.

- Stesso supporto, controlli, 400 cellule per target e cinque semi appaiati del
  generatore, flussi casuali per blocco; sei membri e grezzi, non solo proxy.
- Per la decisione operativa di stanotte: media macro dei delta positiva, vantaggio
  risolto con un intervallo appaiato sui target, nessuna linea con regressione
  risolta della media o del PDS; riportare anche sensibilità senza JAC instabile.
  Se l'evidenza è mista o insufficiente, nessuna promozione. Non applicare questa
  nuova regola retroattivamente a t36/t30.
- I semi di emissione non sono repliche biologiche: l'intervallo è condizionato
  ai contesti osservati. Una promessa di generalizzazione richiede conferma su
  altri contesti/studi e, per training stocastici nuovi, variabilità dei fit.
- Export e banco devono usare esattamente gli stessi checkpoint, centratura,
  selettore e trasformazioni. Parità a peso zero del correttore; guardie PDS,
  ampiezza e quota comune anche in inferenza, non soltanto durante il training.
- PIE già addestrato mantiene una scheda separata di esposizione: non entra
  silenziosamente in un confronto dichiarato sul nostro identico training.

Questo è il criterio progettuale. Per eseguirlo manca ancora il manifest numerico
dei fold/target e delle modalità dell'intervallo: il presente rapporto non è un
runner né la prova di un protocollo eseguito. Un test tecnico ridotto può fermare
un ramo, non promuoverlo al posto del banco concordato.

## 7. Dopo la consegna breve, verso il 22 ottobre

1. Chiudere catalogo/identità/adapter e consumatori per tutte le fonti idonee;
   ogni nuova release mantiene gli split preesistenti.
2. Valutare PIE sul supporto verificato e sul pannello completo con fallback;
   decidere se tenere effetti, descrittori o teacher in base al contributo misurato.
3. Aprire un solo nuovo correttore cellulare: innesto biologico congelato o
   residuo vincolato, con baseline a pari informazioni e prova contro collasso
   comune. Il grafo reale GEARS viene prima di altra complessità architetturale.
4. Preparare due instradamenti per D/E/F: target osservato in banca e target
   realmente assente. STRING/cis è un fallback da battere, non una certezza sulla
   composizione del pannello finale. Prova generale della catena completa.

La continuità da conservare è la banca riusabile e il riferimento t36. Il nuovo
flusso da aprire è il confronto con conoscenza biologica e pesi esterni verificati.
La prossima decisione va presa sui loro errori misurati, non sulla quantità di
gigabyte o sul nome dell'architettura.
