# Dalla geometria dei geni a una correzione trasferibile

**Stato:** lettura del codice, prova tecnica locale e proposta. Nessun risultato predittivo.
Codice GEARS fissato a `f374e43e197b295016d80395d7a54ddb81cc6769`, consultato il 4/10/2026.
SHA e percorsi in [upstream_manifest.json](upstream_manifest.json). Le osservazioni sul codice
valgono per questa revisione; non ricostruiscono da sole la versione usata nel paper.

## 1. Che problema risolve GEARS

Il [paper di Roohani, Huang e Leskovec](https://www.nature.com/articles/s41587-023-01905-6)
studia risposte a perturbazioni singole e combinate, anche di geni non perturbati nel training.
Usa conoscenza biologica per collegare perturbazioni nuove a quelle supervisionate.
Non tratta i geni come pixel: usa grafi per arricchire le rappresentazioni.
I risultati riportati riguardano i dataset, split e confronti del lavoro, non il nostro
trasferimento a una linea interamente nuova. Il
[README ufficiale](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/README.md)
esclude esplicitamente come caso supportato training fra tipi cellulari e trasferimento fra essi;
avverte anche che addestrare solo su singole perturbazioni non basta per combinazioni affidabili.

Per noi la distinzione è decisiva: GEARS offre soprattutto un'idea per **T**, bersaglio nuovo
in contesto visto. Il nostro requisito include **C**, contesto nuovo, e **J**, entrambi nuovi.
Non basta replicare un risultato T per soddisfarli.

## 2. Anatomia verificata nel codice

Fonti primarie: [model.py](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/gears/model.py),
[utils.py](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/gears/utils.py),
[pertdata.py](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/gears/pertdata.py),
[gears.py](https://github.com/snap-stanford/GEARS/blob/f374e43e197b295016d80395d7a54ddb81cc6769/gears/gears.py).

| Componente | Implementazione consultata | Che cosa significa per noi |
|---|---|---|
| Rappresentazione del gene di risposta | Embedding proprio più embedding arricchito da `SGConv` sul grafo di coespressione | Separare identità del gene e informazione dei vicini |
| Rappresentazione della perturbazione | Seconda tabella e `SGConv` sul grafo GO; somma dei codici per perturbazioni multiple, poi MLP | Un bersaglio nuovo può ricevere informazione dai vicini annotati, senza osservare la sua risposta |
| Decodifica | MLP condiviso, pesi specifici per gene, riassunto globale `cross_gene_state`, seconda testa specifica | Condivisione statistica mantenendo uscite distinte; il riassunto globale non equivale a contesto biologico nuovo |
| Uscita | Correzione aggiunta al profilo di controllo in ingresso | Conservare un riferimento è utile; nel nostro caso il riferimento include già il transfer |
| Controlli | Campionamento casuale di controlli come ingresso per cellule perturbate | Non è un appaiamento sperimentale della stessa cellula prima/dopo; il codice non ne prova un destino individuale |
| Supervisione | Errore alla quarta potenza mediato per perturbazione del batch, più termine direzionale; maschera dei geni non nulli | Non copiare il nome “MSE” come se descrivesse la formula; distinta dalla nostra likelihood NB e dalle maschere di misura |

La coespressione è Pearson in valore assoluto: perde il segno. Il codice seleziona condizioni
del training il cui nome contiene `ctrl`, dunque anche singole perturbazioni come `GENE+ctrl`;
non è corretto descriverla come grafo ottenuto soltanto da cellule di controllo.
GO usa similarità fra insiemi di annotazioni (Jaccard), con selezione dei vicini.
Questi grafi rappresentano somiglianze: non sono una mappa causale firmata di attivazione/repressione.

### Due differenze fra lettura intuitiva e codice

**Accertato per flusso dei dati:** in `GEARS_Model.forward`, il tensore di espressione `x`
è letto soltanto nel ramo senza perturbazione e nella somma finale (righe 126 e 206).
La correzione del ramo perturbato non dipende dai valori di `x`, a pesi, grafi e metadati fissati.
Passare un controllo di una linea diversa non rende quella correzione specifica della linea.
Questo precisa la spiegazione data in chat: il condizionamento biologico sul contesto che proponiamo
è un'aggiunta nostra, non una capacità dimostrata dal GEARS consultato.

**Riprodotto localmente:** `loss_fct` usa `torch.sign` per penalizzare il verso sbagliato.
Nella [fixture](audit_upstream_r1.json), aumentando `direction_lambda` da 0 a 10,
la loss passa da 1,241600 a 41,241600, ma la differenza massima fra gradienti è esattamente zero.
Il termine può cambiare valori riportati e decisioni che li leggano; non fornisce un gradiente
direzionale utile al consueto backprop in questa implementazione. Non prova che il modello non impari:
il termine alla quarta potenza ha gradiente. Un'eventuale loss direzionale nostra richiederebbe
una forma differenziabile, una soglia di affidabilità del segno e un contrasto separato.

**Accertato nel loader:** vengono escluse condizioni i cui bersagli non sono nel grafo GO.
Non adottare questa regola: per D-053 l'assenza di annotazione deve produrre un fallback
tracciato, non la sparizione del bersaglio o del contesto dal training e dalla valutazione.

Il ramo di incertezza esiste, ma non è una probabilità già calibrata del beneficio della
correzione sul nostro banco. Non può sostituire automaticamente il selettore fuori fold.

## 3. Che cosa prendere e che cosa cambiare

La nostra [CellNet v5](../../modelli/ibrido_selettivo_2026-10-04/cellnet.py) possiede già:
encoder di insiemi di controlli e maschere, descrittori del bersaglio, modalità, ancora,
decoder a basso rango, likelihood per cellule e testa comune esclusa dall'export.
Il grafo aggiunge **condivisione fra rappresentazioni di bersagli biologicamente vicini**;
non serve a sostituire tutte queste parti insieme.

Proposta per il codice del bersaglio t nel contesto c:

\[
e_{t,c}=\phi(d_t)+W_o\sum_{j\to t}
\frac{a_{jt}}{\sum_k a_{kt}}\,
\sigma\!\left(q(z_c)^T k(d_j,d_t)/\sqrt h\right)W_m d_j.
\]

`d` sono descrittori biologici leciti; `a` è un grafo di similarità versionato;
`z_c` viene dai controlli con l'encoder esistente. Il ramo proprio `phi(d_t)` rimane.
I pesi positivi descrivono similarità, mentre le trasformazioni apprese possono produrre
messaggi con componenti positive e negative. Non interpretiamo queste componenti come
effetti causali identificati. La normalizzazione usa il peso prima del cancello: se fosse
rinormalizzata dopo, un unico vicino cancellerebbe l'effetto del suo cancello.

**Implementato su fixture:** [ContextGraph e GraphCellNet](graph_adapter.py).
Il messaggio entra nel codice del bersaglio prima del trunk della vera CellNet v5.
`W_o=0` all'inizio: nessuna perturbazione iniziale del modello di base, anche se questo
ha già una correzione non nulla. L'uscita resta `ancora + residuo`, con guadagno fisso;
loss, testa comune e generatore non sono stati cambiati.
Il grafo senza vicini aggiunge zero e mantiene il ramo descrittivo. L'ultima riga
unknown/controllo è isolata. Non si inventano identità apprese per bersagli J.

Il prototipo usa l'asse dei bersagli del modello e descrittori già pronti: non contiene
ancora l'universo completo di nodi GO ausiliari. L'estensione richiede una mappa distinta
fra nodi biologici e bersagli previsti, senza eliminare i secondi se mancano i primi.
Il cancello legge `z_c`, non una nuova rete di correlazioni stimata nel contesto escluso.
Questa è una prima forma controllabile di geometria dipendente dal contesto; non coincide
con inferire un grafo causale specifico per ogni linea.

**Rinvii motivati:** il grafo dei geni di risposta e la testa globale di GEARS vanno provati
solo dopo il ramo del bersaglio. Cambiarli insieme impedirebbe di identificare il beneficio.
La propagazione fra geni di risposta potrebbe anche appiattire la specificità che ci serve
per PDS. Nessuna nuova loss, decoder generativo o rete su pixel nel primo confronto.

## 4. Precedenti e contrasto che può smentire l'idea

| Precedente | Differenza di questa proposta | Verifica prima di promuovere |
|---|---|---|
| S-008, [CP-0043](../../../docs/checkpoints/0043-misura-decisiva-relazioni.md): covariazione delle risposte non prediceva l'intervento | GO e descrittori esterni strutturano un encoder, senza trasformare una correlazione in effetto causale | Baseline lineare con gli stessi descrittori e grafo; nessuna promozione dal solo aspetto biologico |
| S-001/S-002/S-006: risposta comune, PDS basso, correzione dannosa | Ancora coerente preservata; innesto sul codice del bersaglio | PDS e quota comune della correzione, prima e dopo generazione; mantenere guardie del trainer |
| S-007: contesto medio senza beneficio | Cancelli sui messaggi, informati dall'encoder cellulare già esistente | Riaddestrare senza contesto; scambiare il solo contesto del correttore, mantenendo il vero basale del generatore |
| S-009: banco/export diversi e rumore del generatore | Stessa definizione del residuo, baseline e supporti lungo l'intera catena | Parità effetti, cellule e metriche a ramo nullo; 400 cellule e almeno 5 semi appaiati |
| S-005: copertura promessa ma non eseguita | Grafo come input aggiuntivo, nessuna esclusione dei contesti | Bilancio previsto/letto/contributo alla loss, con arresto per lacune non dichiarate |

**Segnale precoce e arresto:** fermare l'accettazione per leakage, assi incoerenti, contesti
richiesti non usati, non-finiti o mancata parità. Per la salute scientifica conservare
le guardie su PDS, ampiezza e quota comune; soglie e frequenza vanno congelate nel protocollo
del nuovo fit, con linee interne escluse. Una fixture riuscita non passa queste regole.

Sequenza proposta, sullo stesso corpus, split, baseline e generatore:

1. **G0:** correttore corrente senza messaggi; baseline transfer a fianco.
2. **G1:** stessi descrittori, messaggi su grafo GO, cancello costante; semplice
   regressione regolarizzata con le stesse informazioni come ulteriore controllo.
3. **G2:** G1 con cancello condizionato dal contesto. Confrontare anche capacità aggiuntiva
   senza informazione relazionale, per non attribuire al grafo più parametri.
4. **Controlli distruttivi:** G1/G2 riaddestrati con grafi ricablati conservando gradi e
   distribuzione dei pesi; più ricablaggi. Valutare G2 con contesto scambiato come diagnosi,
   distinto dal modello riaddestrato senza contesto.

G1 > G0 ma non > ricablato non sostiene il valore dei legami biologici. G2 non > G1 non
sostiene il valore del contesto. Un miglioramento di fit non sostiene C/J. Se G1 non aiuta,
non aggiungere immediatamente un secondo grafo per salvare l'ipotesi.

Leggere C e J separatamente e T come diagnosi; sei metriche, PDS esplicito, media senza JAC
come sensibilità senza sostituire l'obiettivo. Semi del generatore misurano solo il rumore
di emissione: servono anche semi di fit e variabilità fra contesti. Le cinque linee già
lette sono sviluppo; H1 test resta chiusa. Regola numerica, riserva di conferma e gestione
delle regressioni devono essere congelate prima del training, non scelte sui nuovi esiti.

## 5. Grafo e dati: condizioni prima di un training reale

- Manifest del grafo: annotazioni/versione/licenza, identificativi riconciliati, nodi e
  archi, tipi di relazione, pesi, gradi, componenti isolate, copertura di ogni bersaglio.
  Documentare l'assenza di annotazioni; mantenere quei bersagli e riportarne l'esito separato.
- Non scaricare il pickle preconfezionato e trattarlo come provenienza sufficiente.
  Preferire formati ispezionabili, assi e SHA; non installare il pacchetto come requisito del prototipo.
- Il grafo statico GO può essere comune ai fold se deriva esclusivamente da annotazioni
  esterne lecite. Ogni grafo ricavato dall'espressione o dalle risposte deve rispettare il fold:
  esclusione della linea e, in J, di tutti i bersagli nascosti in tutte le sorgenti e derivati.
- I controlli del contesto escluso sono input dichiarati; nessuna sua risposta perturbata
  sceglie grafo, geni, normalizzazioni, iperparametri o arresto. Test di contaminazione:
  alterare quelle risposte deve lasciare invariati gli artefatti del fit.
- Tutti i contesti idonei D-053 mantengono un ruolo. Sorgenti aggregate non diventano
  cellule, geni non misurati non diventano zeri, CRISPRi/a/KO e metadati restano distinti.
- Serializzazione del wrapper verificata come `state_dict`, ma trainer, optimizer,
  resume, loader di checkpoint, guardie ed export reali richiedono un'integrazione dedicata
  in nuovi snapshot. La verifica end-to-end non è stata eseguita.
- Profilare su un batch realistico costo, RAM e GPU: il prototipo itera sui target distinti
  e non costruisce una matrice densa geni × geni, ma la velocità su corpus reale è ignota.

## 6. Cosa dicono i confronti indipendenti

[Ahlmann-Eltze et al., Nature Methods 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12328236/)
trovano che modelli complessi non superano consistentemente baseline semplici nei loro
confronti; includono rappresentazioni GO anche in modelli lineari. Il loro benchmark ha
quattro dataset e non dimostra che qualsiasi rete su qualsiasi compito sia inutile.

[Systema](https://pmc.ncbi.nlm.nih.gov/articles/PMC13271886/) mostra che variazioni comuni
fra controlli e perturbati possono gonfiare metriche di risposta. È pertinente al nostro
problema della componente comune; usare una media perturbata osservata del test come
diagnostica non ne autorizza l'uso per costruire la previsione o scegliere parametri.

[Miller et al., 1 ottobre 2026](https://www.nature.com/articles/s41587-026-03307-w)
mostrano, su 14 dataset e 18 metriche, che la calibrazione delle metriche può cambiare
il confronto con baseline non informative. Propongono controlli positivi basati su repliche
divise e un'interpolazione. Per noi: verificare la sensibilità del banco con controlli
positivi/negativi. Queste diagnosi non cambiano a posteriori le sei metriche VCC.

Le tre letture motivano controlli più forti, non una promessa di vittoria o una bocciatura
preventiva del grafo. Prima priorità: stabilire se la geometria aggiunge segnale specifico
e trasferibile oltre descrittori, transfer e capacità del correttore.
