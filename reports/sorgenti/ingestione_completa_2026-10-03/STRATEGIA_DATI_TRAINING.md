# Strategia dati per il training: indicazione inoltrata dal proprietario il 3/10

**Provenienza.** Il proprietario ha incollato questo testo in chat alla sessione `c7c07a` (claude2) il 3 ottobre 2026
fra le 17:45 e le 17:47 CEST (ora letta con `date` prima e dopo), senza altre parole. Il testo è di un altro agente,
non dichiarato; porta in fondo l'ora «17:37» e si presenta come «il messaggio che passerei a Claude». La sessione lo
ha preso come indicazione del proprietario e glielo ha detto in chat, chiedendo di essere corretta se non è così.
**Tipo: proposta di metodo**, non un protocollo congelato: soglie, fold e regole del primo confronto vanno scritti da
R-LEAD prima di qualunque numero.

**Che cosa cambia subito.** L'acquisizione completa resta, CD4 compreso: il punto 4 della proposta di
[DIMENSIONAMENTO](DIMENSIONAMENTO.md) (CD4 a tranche) non è adottato. Il campionamento riguarda le copie preparate
per i training.

## Testo ricevuto

Riportato com'è arrivato; alla prima parola manca la lettera iniziale.

> mposterei un training che conservi la varietà biologica e riduca soprattutto la ripetizione delle stesse
> combinazioni. Kaggle riceverebbe campioni preparati per ogni esperimento, mentre il corpus completo resterebbe
> disponibile per ampliarli.
>
> Questo è il messaggio che passerei a Claude:
>
> Prepara una strategia dati per la rete cellulare ancorata al transfer, usando Colab CPU per preparazione e
> valutazione, Kaggle GPU per training. L'obiettivo è ottenere un modello competitivo anche senza attraversare tutte
> le cellule a ogni esperimento.
>
> **1. Separare archivio completo e dati del singolo training.** Mantieni il mandato di acquisizione completa delle
> cellule idonee, incluso CD4. Il campionamento riguarda le copie preparate per gli esperimenti e non diventa un
> limite permanente dell'archivio. Ogni corpus di training deve avere un manifest riproducibile: sorgenti, cellule
> selezionate, esclusioni, controlli, conteggi e hash. Una sorgente entra quando è acquisita e verificata; quelle
> ancora attese vanno elencate esplicitamente.
>
> **2. Preservare le combinazioni biologiche prima della numerosità.** Nel training ammesso da ciascun fold,
> rappresentare tutti i contesti e tutti i bersagli disponibili dopo QC, senza restringersi ai 300 bersagli attuali.
> Il campionamento deve distinguere linea, donatore, condizione e tempo; all'interno di ciascuna combinazione
> preservare, quando presenti, studi, guide e repliche. Donatori o studi della stessa linea non diventano linee
> indipendenti nella valutazione. Dare attenzione ai bersagli osservati in più contesti: sono quelli che permettono
> confronti diretti della risposta fra contesti. Conservare anche i bersagli osservati in una sola sorgente,
> dichiarandone il supporto. CRISPRi, CRISPRa e knockout devono mantenere modalità esplicite e ruoli distinti. I geni
> non misurati restano mascherati.
>
> **3. Preparare campioni crescenti e riproducibili.** Propongo questa scala iniziale, da dimensionare
> sull'inventario reale, non come numerosità già dimostrata sufficiente:
>
> | Livello | Cellule perturbate per combinazione contesto biologico × bersaglio | Uso |
> |---|---|---|
> | Base | Fino a 32 | Confrontare le prime varianti del modello |
> | Ampliato | Fino a 64 | Verificare il beneficio di più cellule |
> | Approfondito | Fino a 128, oppure tutte se meno | Approfondire i candidati promettenti |
>
> Ripartire il campione fra guide e repliche, evitando che una sola libreria lo occupi tutto. Se il tetto impedisce di
> rappresentare gli strati necessari, aumentarlo per quella combinazione e registrare l'eccezione. Usare selezione
> deterministica con campioni annidati: il livello da 64 contiene quello da 32. Le combinazioni poco numerose
> mantengono tutte le cellule idonee. Non scegliere le cellule in base alla grandezza dell'effetto osservato. Prima di
> fissare i livelli, produrre conteggi effettivi, copertura e dimensioni: non assumere che 32 o 64 corrispondano
> automaticamente a pochi milioni di cellule.
>
> **4. Gestire separatamente controlli e bilanciamento.** Conservare tutti i controlli nell'archivio. Per il training
> preparare pool rappresentativi per contesto e libreria, mantenendo gli stati cellulari disponibili: la rete deve
> continuare a ricevere informazione cellulare, non soltanto un profilo medio. Non imporre che ogni passaggio
> attraversi tutti i controlli. Dichiarare separatamente come vengono usati per condizionamento, normalizzazione e
> loss. Bilanciare prima i gruppi biologici, poi le condizioni e i bersagli. Verificare i contributi effettivi alla
> loss e le esposizioni delle cellule: CD4 non deve dominare per numerosità, ma nemmeno perdere donatori o condizioni
> per un taglio indiscriminato.
>
> **5. Congelare la valutazione prima di confrontare i campioni.** Mantenere gli stessi fold, bersagli e dati di
> valutazione passando da 32 a 64 a 128. Per C, escludere le perturbazioni dell'intera linea destinataria da tutti gli
> studi e derivati. Per J, escludere anche i bersagli valutati da tutte le sorgenti. Queste esclusioni devono valere
> anche per le ancore transfer e le rappresentazioni. H1 test resta chiusa. Nei confronti fra quantità di cellule,
> tenere fissi modello, ancore e generatore. Migliorare le ancore usando più dati è un esperimento distinto.
>
> **6. Aumentare i dati attraverso confronti interpretabili.** Prima confrontare i livelli a parità di aggiornamenti
> del modello, registrando anche tempo GPU e cellule uniche viste. Confrontare soltanto lo stesso numero di epoche
> confonderebbe più dati con più calcolo. Per i candidati promettenti verificare poi se un addestramento più lungo
> cambia il risultato, con arresto deciso sulla validation. Successivamente provare campione fisso contro campione
> rinnovato, mantenendo quantità e composizione comparabili: sostituire progressivamente cellule delle stesse
> combinazioni può ampliare l'esperienza del modello senza ingrandire ogni sessione. Le tranche devono essere
> preparate e versionate, senza richiedere che tutto l'archivio sia montato contemporaneamente. Un plateau significa
> «nessun beneficio rilevato in questo confronto», non «le cellule rimanenti sono inutili».
>
> **7. Rendere Kaggle efficiente e decidere sui risultati.** Preparare su Colab shard già selezionati e verificati.
> Misurare sulla nuova rete velocità, attesa dei dati, memoria e costo della valutazione; dimensionare i job sulla
> quota e sulle risorse effettivamente disponibili. Salvare checkpoint riprendibili comprendenti modello,
> ottimizzatore, stato casuale e posizione del campionatore. La scelta finale deve dipendere dal confronto con il
> transfer sulle sei metriche, separando C e J e leggendo i risultati per contesto. Congelare prima soglie e
> regressioni ammesse. Una loss migliore o più cellule viste non bastano.
>
> Prima consegna: inventario dopo QC, campioni proposti con dimensioni reali, manifest degli split, verifica del
> bilanciamento e protocollo del primo confronto. Da lì scegliamo il corpus di training più utile entro le risorse
> Kaggle misurate.

## Che cosa esiste e che cosa manca (letto dalla sessione `c7c07a`, 3/10 17:50)

| Punto | Esiste | Manca |
|---|---|---|
| 1. Archivio e manifest | contratto degli shard con ricevute e `complete.json`; ruoli registrati in `../archivio_cloud_2026-10-02/ruoli_ingestione_r1.json` | manifest del corpus di un training: cellule selezionate, esclusioni e hash per esperimento |
| 2. Combinazioni | gruppi di linea proposti in [line_groups_expanded_v1.json](orion/line_groups_expanded_v1.json), non ancora adottati da R-LEAD; matrice bersaglio × gruppo del corpus r3 (`reports/modelli/rete_cellulare_2026-10-03/target_matrix.py`) | inventario per (gruppo, donatore, condizione, tempo, studio, modalità, bersaglio, guida, libreria) su tutte le sorgenti acquisite |
| 3. Campioni annidati | ordine fissato dall'hash e tranche per Orion (`orion/campionamento_v2.py`, `window`), prime *k* per (file, guida) per CD4 (`../archivio_cloud_2026-10-02/campionamento.py`) | un campionatore unico sugli `obs` degli shard, ripartito fra guide e librerie, con i livelli 32, 64, 128 e le eccezioni registrate; le dimensioni reali |
| 4. Controlli e bilanciamento | quote della loss 1/G per gruppo misurate nei training r3 (`reports/modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md` §6) | pool di controlli per contesto e libreria; verifica delle esposizioni per condizione e bersaglio |
| 5. Valutazione | split e riserve di R-LEAD (`reports/analisi/generalizzazione_contesti_2026-10-02/`); protocollo della rete ancorata con il suo emendamento (`reports/modelli/rete_ancorata_2026-10-03/PROTOCOLLO.md` §9) | il protocollo del confronto fra livelli, scritto da R-LEAD prima dei numeri |
| 6–7. Confronti e Kaggle | velocità e memoria dei training r3 in [DIMENSIONAMENTO](DIMENSIONAMENTO.md); checkpoint ogni 15 minuti nei training (`--checkpoint-minutes`) | misure sulla rete ancorata; verifica che il checkpoint conservi anche stato casuale e posizione del campionatore |

**Una differenza da decidere.** Il testo assegna a Colab la preparazione dei campioni. Alle 16:38 il proprietario ha
scelto la CPU di Kaggle al posto del secondo Colab per l'ingestione, e Orion e KOLF finiscono lì come output di
kernel che un training monta direttamente. Proposta della sessione, detta in chat: preparare su Kaggle CPU i campioni
delle sorgenti che stanno su Kaggle e su Colab quelli delle sorgenti che stanno su Drive.
