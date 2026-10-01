# Il modello competitivo richiede un esperimento più identificabile

1 ottobre 2026. **Verdetto della lead:** conservare l'infrastruttura costruita e continuare
la ricerca neurale, ma correggere prima validazione, controlli e obiettivo. Aumentare il corpus
con l'attuale disegno può aumentare la quantità di training senza chiarire che cosa si è appreso.
Il ramo più plausibile per la gara è un modello che combina trasferimento affidabile,
correzione biologica dipendente dal contesto e generazione coerente delle popolazioni.
La rete da sola non ha ancora evidenza per sostituire il trasferimento.

Questa è una revisione **a posteriori**: non un test indipendente né un punteggio VCC.
Mandato, fonti, script e hash sono nell'[indice](README.md). I conteggi e le statistiche nuovi
sono ricalcolati; le proposte sono esplicitamente distinte. Il test H1 non è stato aperto.

## 1. Che cosa è stato effettivamente costruito

La produzione ha una catena funzionante effetti → cellule → pacchetto → score; t28 è il massimo
osservato, 0,144845, ma non supera la sua soglia congelata contro t25. La ricetta di riferimento
resta t22. La crescita iniziale con sorgenti e ampiezza è reale; la successiva media quasi piatta
nasconde compensazioni fra metriche. L'audit del 29/09 ha già corretto il falso argomento della
saturazione, la stima del rumore da due semi e la riserva HepG2 già usata. Non sono nuove scoperte
di questa revisione. Fonti: [invii](../../invii/README.md),
[audit precedente](../lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md).

R-LAB ha fatto un salto d'infrastruttura: shard tracciati, conteggi individuali, maschere,
deduplicazione, checkpoint e ripresa verificata. Il secondo training ha consumato tutte le
3.354.670 cellule ammesse almeno una volta, per 3,828 epoche; il terzo parte da 4.382.321.
Questi numeri sono nei manifest r5/r7 e nella copertura r2, non dedotti dal nome dei dataset.
Le sei chiavi di studio attive di r2 non sono sei esperimenti biologici indipendenti:
tre chiavi sono schermi Replogle, e le 19 linee HIPSCI sono cloni/donatori di uno stesso sistema.

La rete riceve conteggi individuali come supervisione, ma produce un profilo di base e uno
perturbato per bersaglio/contesto, con una miscela fra i due. L'encoder applica una trasformazione
alle cellule di controllo e ne media gli embedding. Può quindi leggere informazioni della
distribuzione, ma il decoder non mantiene uno stato latente distinto per ogni cellula da
trasformare. Non è corretto né chiamarla pseudobulk supervisionato, né attribuirle una dinamica
cellulare individuale già identificata. Fonte: `cellnet.py`, `context` e `forward`.

**Stato osservato durante questa revisione:** Kaggle ha prima restituito `RUNNING` e nella
lettura avviata alle 14:38 CEST `COMPLETE` per `davidmaisterx/rlab-cellnet-r3`. Gli output arrivati
sono analizzati nell'[aggiornamento R3](AGGIORNAMENTO_R3.md): ramo identity collassato e nuova
prova del difetto del gradiente sotto il clamp. Nel frattempo Claude
ha registrato [t29](../../invii/prediction_t29_2026-10-01/prediction.json): effetti del ramo
`desc` di r2 con il generatore t22. La registrazione non è uno score. L'audit non modifica
training, invio o soglie di quell'agente.

## 2. Nuove diagnosi riproducibili

### 2.1 Aggiungere dati cambia anche i bersagli tenuti fuori

**Misurato.** Il pre-passo r5 esclude 1.100 simboli; r7 ne esclude 1.142. Solo **128** sono
gli stessi: Jaccard **6,05%**. Dei 1.100 precedenti, **972** non sono più nella lista nascosta.
Fra i gruppi valutati in r2, 35 target C diventano esplicitamente nascosti in r7; 206 target J
prima esplicitamente nascosti non lo sono più. Non significa che ciascuno sia necessariamente
ammesso al training dopo QC; significa che la barriera di esclusione è cambiata.

**Causa nel codice:** `cell_data.splits` applica `random.sample` alla lista ordinata dei
bersagli disponibili. Un seme fisso conserva il risultato solo se la lista resta identica.
**Conseguenza:** r3 meno r2 non identifica l'effetto dei nuovi dataset. Cambiano difficoltà,
etichette disponibili e popolazione di valutazione. I protocolli precedenti restano descrittivi;
non si riscrivono i loro numeri. Prossimo confronto: manifest esplicito e immutabile degli split,
con assegnazione stabile dei nuovi simboli e gruppi biologici esclusi insieme.
Fonte: [data_r1](data_r1/data_diagnostics.json), `split_change`.

### 2.2 Il bilanciamento per studio non realizza il peso dichiarato

**Misurato con replay esatto:** tutti i 50.172 batch e le esposizioni per studio coincidono
con il log r2. I coefficienti medi con cui gli esempi di ogni studio entrano nella loss sono:

| Chiave del dataset | Peso effettivo | Obiettivo se le sei chiavi pesassero uguale |
|---|---:|---:|
| K562 genome-wide | **32,61%** | 16,67% |
| HIPSCI mirato | 18,92% | 16,67% |
| H1 | 13,71% | 16,67% |
| K562 essential | 12,69% | 16,67% |
| Jurkat | 11,18% | 16,67% |
| RPE1 | 10,90% | 16,67% |

**Causa:** la loss divide `sum(w * loss_cell)` per `sum(w)` del singolo batch. Il campionatore
mescola quattro shard, non l'intero corpus. In 4.414 batch c'è una sola chiave: il peso si
cancella esattamente. Anche nei batch misti il denominatore casuale cambia l'estimando.
Con un denominatore fisso i coefficienti ricalcolati stanno fra 16,37% e 16,90%.

Questi sono coefficienti della loss, **non quote delle norme del gradiente o della conoscenza
appresa**. Adam, clipping e ordine dei batch complicano ancora l'effetto sull'ottimizzazione.
Prima correzione candidata: loss con normalizzazione globale e pesi sulle sole sorgenti attive,
oppure batch gerarchici bilanciati. La scelta fra studi, contesti e target deve essere esplicita.
Fonte: [sampler_r1](sampler_r1/replay.json).

### 2.3 Il serbatoio dei controlli distrugge l'appaiamento per libreria in HepG2

**Misurato dai metadati e ricostruito con gli stessi seed:** 4.976 controlli in 56 librerie.
52 librerie hanno almeno 64 controlli; coprono il **97,61%** delle cellule perturbate.
Dopo il serbatoio da 2.048 controlli per contesto, **nessuna libreria ne conserva 64**.
`draw_controls` richiede almeno 64 per scegliere la libreria propria: quindi in questa
valutazione il **100% delle cellule perturbate ricorre al pool fra librerie**.

L'adattatore originale usa proprio `batch` come `library`; ordine degli otto shard,
numerosità e totale dei controlli sono verificati. Non sono stati rifiutati controlli HepG2
dal QC registrato. Fonte: [design_r1](design_r1/design.json), [script](analyze_design.py).

C'è anche un secondo difetto del merge: il vecchio serbatoio e lo shard nuovo vengono
concatenati e ricampionati senza il numero storico di cellule rappresentate. Con dieci shard
uguali, ciascuno grande quanto il limite, l'ultimo rappresenta in attesa il 50% del serbatoio,
il primo lo 0,195%: rapporto 256. È un **controesempio**, non il rapporto misurato in HepG2.
Servono reservoir uniformi indipendenti dall'ordine, stratificati per libreria; se i controlli
sono pochi, stimare l'incertezza o usare ricampionamento nella libreria, non una fusione tacita.

### 2.4 Il confronto con unknown non è una baseline che ignora il bersaglio addestrata correttamente

**Riprodotto:** nel ramo identity l'embedding unknown riceve gradiente esattamente zero
mentre il target noto riceve gradiente non nullo. Sui controlli viene selezionata `ll0`, quindi
il ramo di risposta unknown non viene supervisionato. Per i descrittori, unknown è una riga
di descrittori zero e una diversa feature di espressione, senza un obiettivo apposito.

Un vantaggio rispetto a quell'ingresso misura sensibilità alla sostituzione, non dimostra
un vantaggio rispetto al miglior modello senza identità del bersaglio. Il ramo identity su
T/J è inoltre privo di embedding addestrati per quei simboli: batterlo è un confronto debole.
L'identità può restare una diagnostica, ma vanno aggiunti modello generico addestrato,
bilineare sugli stessi descrittori, target permutati e ablazione per blocco di annotazioni.
Fonte: [controesempi](counterexamples_r1/counterexamples.json).

### 2.5 La baseline appresa può assorbire gli effetti delle perturbazioni

**Riprodotto nel grafo del modello:** la loss delle sole perturbate dà un gradiente non nullo
alla testa `base` (massimo 1,381 nel caso controllato). Dunque la frase «baseline imparata dai
controlli» non significa «stimata esclusivamente dalla loss dei controlli». Il ramo di risposta
può compensare un errore di baseline e guadagnare likelihood senza orientare correttamente il
cambiamento rispetto ai controlli reali. Non ho misurato quanto questo spieghi il risultato r2.

La prossima ablazione deve confrontare baseline empirica smussata dai soli controlli, baseline
appresa con loss solo sui controlli e baseline congiunta attuale. Fare anche controlli tenuti
fuori e scambio di target/contesto. Non chiamare `pi` «efficienza del knockdown» senza validarla
con guide o misure indipendenti: la miscela può spiegare eterogeneità, mismatch o dropout.

### 2.6 Le classi C/T/J precedono il QC

**Controesempio end-to-end riprodotto:** G2 esiste in una sorgente che viene poi interamente
esclusa per pochi controlli. Nel training ammesso resta solo G1; le cellule G2 nel contesto
tenuto fuori vengono ancora chiamate C, mentre sono J. Il controllo della copertura verifica
le classi già assegnate e quindi non rileva questo errore semantico.

Ricalcolare l'insieme dei bersagli effettivamente ammessi dopo tutte le esclusioni, preservando
la lista proibita. Per r2 **non sostengo** che i 400 gruppi C siano falsi: hanno tutti un transfer
disponibile. La portata quantitativa su altri gruppi/r3 va misurata dal prepass completo.

## 3. Che cosa dicono i dati, oltre alla media

### 3.1 Il risultato T cambia molto fra sistemi biologici

Ricalcolo del ramo `desc` di r2. Coseni diagnostici sui 200 geni selezionati dalla risposta
osservata, non score ufficiali. «Generica» è la risposta media di training del contesto.

| Contesto/schermo | Gruppi T | Coseno rete | Coseno generica |
|---|---:|---:|---:|
| H1 | 17 | **−0,517** | +0,421 |
| Jurkat | 21 | +0,170 | +0,212 |
| K562 essential | 30 | +0,485 | +0,445 |
| K562 genome-wide | **315** | **−0,128** | −0,056 |
| RPE1 | 17 | +0,346 | +0,335 |

Il 78,75% dei gruppi viene da un solo schermo. Le 19 linee HIPSCI, 571.338 cellule di training,
non compaiono nel test T selezionato. La regola «prendi i 400 gruppi più numerosi» produce questa
copertura. La quota complessiva del 93,25% con likelihood migliore di unknown nasconde **268
gruppi** con tale guadagno e coseno negativo; 239 appartengono a K562 genome-wide.

**Interpretazione:** la likelihood attuale non è un criterio sufficiente per scegliere i
modelli. Il buon comportamento su essential/RPE1 suggerisce una pista circoscritta; non prova
generalizzazione globale. Le differenze fra i due schermi K562 non sono differenze di linea:
target, profondità, forza degli effetti, tempi e studio vanno separati prima di attribuirle a
biologia specifica del contesto. Fonte: [r1](r1/diagnostics.json).

### 3.2 Su C il transfer vince, ma la rete non è ridondante

Su 400 target HepG2: rete **0,26565**, transfer **0,38995**, differenza **−0,12431**;
la rete vince nel **38,25%** dei target. Il bootstrap descrittivo per target dà
−0,14766…−0,10208; riguarda questo contesto, non corregge le dipendenze fra target della stessa
famiglia funzionale e non stima l'incertezza fra contesti.

Se un oracolo scegliesse per ogni target il migliore dei due, arriverebbe a **0,42862**,
cioè +0,03867 sul transfer. Questo usa la verità del test e **non è un ensemble ottenibile né
un guadagno VCC**. Dimostra solo spazio potenziale per complementarità. BOP1, MED4, NCL,
POLR2I, POLR2D, TSR1 e PES1 compaiono fra i vantaggi maggiori della rete: una pista per analizzare
funzioni condivise, da verificare con annotazioni congelate e controlli per numerosità, non
un arricchimento funzionale già dimostrato.

**Proposta:** imparare una correzione del transfer con predizioni out-of-fold e un peso di
affidabilità dipendente da bersaglio, supporto e disaccordo fra sorgenti. Mai scegliere il ramo
per un target usando il suo esito di test. Fonte: [design_r1](design_r1/design.json).

### 3.3 La difficoltà di J contiene anche rumore di misura

Ho letto in blocchi **tutte le 145.473 cellule HepG2 locali**, 9.624 geni nativi, valori
interi verificati; 4.976 sono controlli. La lettura non ricostruisce il QC di R-LAB né lo scorer.
Per i 626 target C/J valutati, una divisione casuale indipendente di cellule e controlli in
due metà fornisce la seguente diagnostica su effetti bulk, escludendo il bersaglio proprio:

| Coorte | Target | Cellule mediane | Coseno metà/metà mediano |
|---|---:|---:|---:|
| C | 400 | 103,5 | **0,373** |
| J | 226 | 50,5 | **0,148** |

Il benchmark J ha contemporaneamente bersagli meno osservati e verità meno riproducibile.
La differenza non può essere attribuita tutta alla generalizzazione. È un'unica divisione
cellulare, non repliche biologiche; non è un ceiling direttamente confrontabile con il coseno
top-200 della rete. Il prossimo banco deve riportare numerosità, riproducibilità, strati di
segnale e analisi a numerosità appaiata. Non dividere automaticamente lo score per un ceiling
rumoroso. I target inclusi hanno mediana 92 cellule contro 39 per i non inclusi.

Il cis è nei top-200 nell'84,25% dei target C e nel 72,57% dei J. Il suo contributo mediano
all'energia top-200 è modesto (2,13% e 1,13%), ma per **TFAM vale 32,96%** e per **POGLUT3
23,06%**. Un buon knockdown del target non garantisce una risposta trans prevedibile:
POGLUT3 ha 386 cellule, cis lnFC −3,096, ma coseno metà/metà trans 0,047. Il caso non dimostra
assenza di risposta; mostra perché cis, numerosità e segnale trans vanno separati.

Le metriche ufficiali escludono il bersaglio proprio; PDS esclude tutti i target del pannello.
Il coseno attuale della rete non applica questa esclusione. Va mantenuto solo come diagnostica,
con la versione trans accanto. [Specifica ufficiale](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md).
Numeri e hash: [data_r1](data_r1/data_diagnostics.json).

## 4. Bias strategici da riformulare

1. **Più cellule non equivale a più problemi biologici identificabili.** Il corpus r7 non
   contiene ancora CD4, Orion o VIPerturb-seq, mentre espande altri domini e modalità. CD4 è
   già Flex e offre donatori/stimoli; i dati ponte fra assay e gli stessi target in più contesti
   hanno valore informativo diverso da milioni di cellule aggiuntive nello stesso schermo.
   Conservare l'intero corpus; scegliere il campionamento per informazione e affidabilità.
2. **J non è l'unico regime della gara.** I bersagli nuovi per il pannello possono essere già
   nei dati pubblici. J resta essenziale per una rivendicazione scientifica di generalizzazione,
   mentre la produzione deve funzionare in C e J con supporto dichiarato. Non imporre a un
   miglioramento utile in C di risolvere J prima di essere considerato.
3. **La riserva H1 non conferma contesti nuovi.** Train/validation H1 sono già nel training.
   Inoltre il solo nome dello split H1 test non garantisce bersagli globalmente mai visti:
   serve escluderne gli alias in tutte le altre sorgenti se si vuole chiamarlo T. Altrimenti
   è un test di nuovi esiti con contesto noto. Mantenere la riserva chiusa; non usarla per
   risolvere adesso i difetti del banco.
4. **Non imporre una scelta ideologica fra cellule e medie.** Le cellule servono per stati,
   eterogeneità e generazione. I momenti delle distribuzioni e i contrasti fra condizioni
   sono vincoli utili, purché non sostituiscano l'archivio cellulare né contino lo stesso
   esperimento come due prove indipendenti. La rete deve migliorare la risposta, non soltanto
   la likelihood di una trascrittomica dominata dal basale.
5. **Una sola soglia proxy non chiude un'architettura.** I precedenti negativi chiudono le loro
   formulazioni, dataset e split. La selezione su sei metriche ammette compromessi registrati
   prima; non richiede che ogni membro migliori. «0,005 di rumore del seme» resta scorretto:
   può essere una soglia pratica, non una stima statistica da una sola coppia.
6. **La verifica tecnica è necessaria e produce già informazione scientifica descrittiva.**
   Chiamare r2 «solo tecnica» non deve nascondere la sconfitta contro transfer o le anomalie
   fra contesti. Non promuovere questi numeri a conferma, ma usarli per formulare il prossimo
   esperimento. Il 58% di attesa dati è un limite del loader, non una diagnosi biologica.

## 5. Strade promettenti e prove che possono smentirle

**A. Trasferimento con residuo biologico.** Mantenere l'effetto dello stesso target quando
esiste, con incertezza per studio/guida; imparare il residuo di contesto e un ramo senza memoria
per J. Prior funzionali e moduli forniscono condivisione tra target, non prova di causalità.
Smentita: nessun vantaggio su transfer e bilineare a pari dati dopo correzione del banco.

**B. Distribuzioni di stati.** Usare cellule/stati latenti distinti e una transizione
condizionata dal target; confrontare distribuzioni perturbate e predette senza inventare
coppie controllo–perturbata. Prima una miscela compatta di stati con decoder di conteggi,
poi flow matching solo se risolve un limite misurato. Smentita: stesso score con contesti
scambiati o collassati, oppure vantaggio dovuto solo al generatore.

**C. Dati ponte e contrasto dello stesso intervento.** HIPSCI per donatore, CD4 per stato e
donatore, coppie della stessa linea in assay diversi. Quantificare replicabilità e separare
efficacia, stimolo e laboratorio. Campionare CD4 per donatore × stimolo × guida, con tutti i
controlli utili e una curva di saturazione, mantenendo probabilità di inclusione. Nessun
download autorizzato da questo report. Smentita: i contrasti non superano il rumore da
repliche o non migliorano un contesto/studio escluso.

**D. Emissione coerente con entrambe le medie.** Predire congiuntamente stato, composizione,
profondità e variabilità; controllare sia composizione pooled sia media delle proporzioni
cellulari. La distinzione è già misurata nell'[audit del generatore](../lead_scientist_2026-09-29/AUDIT_GENERATORE.md).
Smentita: migliora una metrica ma il compromesso sui sei membri resta peggiore del candidato
semplice. T29 esporta la media della miscela e usa il generatore t22: **non valida l'emissione
NB della rete né la sua eterogeneità completa**.

La letteratura motiva queste prove, non garantisce il risultato: un confronto del 2025 trovava
modelli profondi inferiori a baseline semplici nel proprio disegno
([Ahlmann-Eltze et al.](https://www.nature.com/articles/s41592-025-02772-6)); State propone
attenzione su insiemi cellulari ([Arc](https://arcinstitute.org/news/virtual-cell-model-state));
PRiMeFlow fornisce una via generativa da valutare ([codice degli autori](https://github.com/altoslabs/primeflow)).
La gara 2025 includeva adattamento nello stesso contesto: non trasferire automaticamente quel
successo al zero-shot 2026 ([organizzatori](https://arcinstitute.org/news/virtual-cell-challenge-2026)).

Il programma, le condizioni di avanzamento e i deliverable sono nella scheda
[R-LEAD](../../../docs/piani/strategia-scientifica.md). Non prometto un piazzamento: propongo
un percorso che possa distinguere un modello migliore da una validazione più favorevole.
