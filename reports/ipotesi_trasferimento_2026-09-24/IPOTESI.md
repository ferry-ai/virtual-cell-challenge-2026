# Ipotesi per trasferire perturbazioni a bersagli e contesti nuovi

24 settembre 2026. Ricerca richiesta dal proprietario: ragionamento sui risultati
locali e verifica di fonti primarie. **Ipotesi e proposte**, non modelli validati.
Nessuna sorgente adottata, ricetta modificata o nuova architettura addestrata.
Le priorità qui sotto non sostituiscono D-044 o una preregistrazione sperimentale.

## 1. Tre osservazioni che cambiano la domanda

**Misurato nei confronti già salvati.** La trasferibilità è molto eterogenea.
STAT2 ha Pearson media fra previsione e verità 0,699 con IFNB, ma −0,0167 con
IFNG; il vantaggio rispetto alla previsione che ignora il bersaglio è +0,438 e
−0,0197 rispettivamente. Il vantaggio è positivo in 6/6 e 1/6 linee.
JAK1 è invece a 0,411 e 0,432; STAT1 a 0,272 e 0,459.
Fonte: [tutte le coppie](../pattern_mixscale_2026-09-24/r1/target_stimulus.csv).
Non sono prove di un effetto causale dello stimolo: cambiano anche supporto dei
geni e proprietà delle stime; bassa correlazione non significa effetto nullo.

**Misurato.** Escludendo i dieci bersagli con maggiore vantaggio, il guadagno sui
segni passa da 1,69 a 0,52 punti percentuali; l'intervallo del secondo comprende
zero. Fonte: [rianalisi appaiata](../pattern_mixscale_2026-09-24/RISULTATI.md).
L'ampiezza da sola non risolve il problema dei segni.

**Misurato nel progetto.** Il vecchio predittore praticamente non cambiava
sostituendo il contesto vero con RPE1. DLD-1 mostra bassa riproducibilità persino
fra metà dello stesso esperimento. Fonti:
[CP-0026](../../docs/checkpoints/0026-predittore-neurale-condizionato.md),
[DLD-1](../dld1_ceiling_2026-09-24/RISULTATI.md).
Il problema può essere sia rappresentare il contesto sia ottenere etichette
abbastanza affidabili da impararne l'effetto. Il rapporto fra correlazioni
entro/fra contesti non è una percentuale di informazione biologica trasferita.

## 2. Modello concettuale da mettere alla prova

**Ipotesi:** una risposta perturbata combina programmi condivisi, attivazione
dipendente dal contesto, intensità/penetranza della perturbazione e residui
specifici. Separare questi fattori può facilitare il trasferimento.

Una forma iniziale, volutamente semplice, è:

`effetto(t,c) = risposta_comune(c) + B × [ruolo(t) ⊙ stato(c)] + residuo(t,c)`

`B` contiene programmi di risposta; `ruolo(t)` coefficienti con segno predetti
da descrittori disponibili per bersagli nuovi; `stato(c)` descrive i controlli.
Non imporre che lo stato agisca solo con una moltiplicazione: confrontare anche
interazioni additive, soglie morbide e un modello senza contesto. Un programma
inattivo prima della perturbazione può essere indotto dopo: uno zero basale
non deve diventare un veto assoluto.

Questa è una famiglia di ipotesi, non una spiegazione già identificata dai dati.
La fattorizzazione può ruotare o mescolare programmi senza cambiare le predizioni;
nomi biologici e causalità richiedono riscontri esterni e stabilità tra repliche.

## 3. Ipotesi concorrenti e prove che le distinguono

| Ipotesi | Esperimento minimo | Cosa la indebolirebbe | Dato necessario |
|---|---|---|---|
| H1. I programmi si trasferiscono meglio dei singoli geni | Base di risposta a rango ridotto imparata solo nel training; ridge dai descrittori ai coefficienti; confronto con ridge sugli stessi input senza compressione | Guadagno assente in J, oppure solo nella risposta comune | Perturbazioni diversificate con maschere e repliche |
| H2. Conta lo stato del programma, più dell'identità della linea | Descrittori dei controlli: attività di programmi, distribuzioni di stato, espressione di componenti della via; scambio dei contesti a input e confronto con contesto costante | Scambiare il contesto non cambia le prestazioni, come nel vecchio modello | Controlli abbinati alle perturbazioni, stimolo e tempo |
| H3. Il ruolo con segno nella rete permette bersagli nuovi | Annotazioni esterne di regolazione positiva/negativa, complessi, domini e sequenza; confronto contro soli vicini non orientati | Il vantaggio sparisce nascondendo un'intera famiglia o rimescolando i descrittori | Annotazioni versionate, nessuna risposta del bersaglio test |
| H4. Alcuni effetti sono transizioni a soglia | Per programma, confronto fra risposta lineare, curva saturante e soglia morbida; verifica su guide o repliche escluse | La soglia non si riproduce o dipende dai geni usati per costruire lo score | Cellule, guide, efficienza e programmi misurati separatamente |
| H5. Cambia la quota di cellule che risponde | Confronto fra spostamento uniforme e miscela di cellule poco/molto rispondenti a media comparabile | La miscela non migliora distribuzioni o metriche VCC nel banco | Conteggi a singola cellula, non solo DE aggregate |
| H6. Le sorgenti utili dipendono dal bersaglio e dal programma | Pesi regolarizzati per programma, stimati solo in validation, contro pesi uguali e un'unica sorgente | Vantaggio limitato alla validation o alla maggiore copertura | Sovrapposizioni che colleghino sorgenti e repliche |
| H7. Il rumore delle etichette domina parte del fallimento | Stimatori di effetto con shrinkage e pesi da repliche, confrontati a pari cellule/supporto | Migliore riproducibilità senza miglioramento su test indipendente | Repliche, guide, controlli e numerosità; SE non sostituisce repliche biologiche |
| H8. Una parte del cambio di contesto è tecnica | Confronto di K562 in Flex e altri saggi, con bersagli comuni e metadati; calibrazione separata di misura e risposta | Correzione incapace di generalizzare fuori dallo studio di calibrazione | Dati ponte; stesso tessuto da solo non separa saggio e studio |
| H9. Sopravvivenza e tempo selezionano le cellule osservate | Stratificare effetti per tempo, proliferazione e guide; verificare stabilità dei programmi | Il pattern attribuito alla regolazione sparisce controllando la composizione dei sopravvissuti | Serie temporali, conteggi/abbondanze delle guide e controlli |
| H10. Un descrittore di contesto trasferisce solo parte della biologia | RNA basale contro RNA più prior regolativi/epigenetici disponibili; confronto senza prior e su famiglie escluse | I prior non aggiungono nulla o richiedono misure assenti nel contesto finale | Reti esterne e, per training, ATAC/proteine; input finale compatibile con soli controlli RNA |

La soglia di promozione va fissata prima del training; queste prove non sono
ancora un protocollo congelato. Riportare copertura insieme alle prestazioni.

## 4. Che cosa fare degli switch genes

Tre significati da distinguere:

1. **Switch topologico:** SWIM/SWIMmeR identifica candidati in reti di
   co-espressione, tipicamente confrontando due condizioni e selezionando DE.
   La topologia è un descrittore candidato, non un intervento causale.
   Con i soli controlli A/B/C non osserviamo la transizione indotta da ogni
   perturbazione. Fonte: [SWIMmeR](https://academic.oup.com/bioinformatics/article/38/2/586/6370739).
2. **Regolatore di stato dimostrato in un contesto:** un intervento modifica un
   programma in quello studio. Può essere un esempio di training; non autorizza
   a copiare lo stesso effetto su ogni linea.
3. **Risposta a soglia:** il programma cambia poco fino a una certa intensità
   e poi rapidamente. La soglia può essere specifica di gene, programma e stato.

**Verificato in letteratura:** nello studio sulla microglia di McQuade e colleghi,
ZNF532 mostra una risposta descritta come binaria, mentre PRDM1 è più graduale.
Lo studio profila 31 regolatori in due modelli di microglia derivata da iPSC e
deposita CROP-seq/CITE-seq in GSE335887. È un candidato mirato per H4/H5, anche
se distante dalle linee della gara. Fonte:
[articolo](https://pmc.ncbi.nlm.nih.gov/articles/PMC13505846/).

**Controllo decisivo:** uno score di intensità ricavato dagli stessi geni che
usiamo per dimostrare una soglia può creare circolarità. Stimare lo score su
geni disgiunti o con una misura indipendente, congelarlo e verificare la forma
della risposta su altre guide/repliche. Una distribuzione bimodale da sola non
dimostra bistabilità, isteresi o un interruttore causale.

**Proposta:** usare gli switch come caratteristiche o come esempi di programmi
regolati. Confrontarli con hub casuali appaiati per grado/espressione, semplici
fattori di trascrizione e annotazioni di pathway. Non restringere tutti i bersagli
ai TF: recettori, enzimi e regolatori epigenetici possono essere informativi.

## 5. Altri approcci: quale problema risolvono

**Prima linea:** ridge con interazioni bersaglio–contesto e pochi programmi;
ensemble regolarizzato fra trasferimento dello stesso bersaglio, modello per
bersagli nuovi e componente comune. Il peso di ciascun esperto deve dipendere
da input disponibili al test; la calibrazione dell'ampiezza resta separata dalla
scelta della direzione. Il ramo same-target non può accedere ai bersagli nascosti
nel regime J, neppure per costruire embedding.

**Reti biologiche:** GEARS offre un esempio di uso di relazioni fra geni per
predire perturbazioni non osservate; CellOracle combina prior regolativi e
contesto per simulare perturbazioni di TF. Sono confronti pertinenti a H3/H10,
non prove di successo con bersaglio e contesto entrambi nuovi nel nostro problema.
Fonti: [GEARS](https://www.nature.com/articles/s41587-023-01905-6),
[CellOracle](https://www.nature.com/articles/s41586-022-05688-9).

**Embedding di sequenza o modelli fondazionali:** usarli inizialmente come input
congelati dello stesso modello semplice; così si misura l'informazione del
descrittore. Audit del pretraining e confronto con annotazioni economiche.
Un benchmark del 2025 trova che i modelli profondi valutati non superano
baseline lineari semplici; è una ragione per fare quel confronto, non per
escludere ogni rete. Fonte:
[Nature Methods](https://www.nature.com/articles/s41592-025-02772-6).

**Trasporto di distribuzioni e modelli generativi:** pertinenti a H5 quando
abbiamo cellule, non solo medie. Dai soli campioni prima/dopo non è identificata
la traiettoria della singola cellula: un accoppiamento di trasporto non è una
storia biologica osservata. Non iniziare dalla generazione se il predittore degli
effetti non supera la risposta comune.

**Reti causali dinamiche:** interessanti con tempo, perturbazioni multiple e
misure indipendenti. Con poche condizioni statiche molte reti spiegano gli
stessi dati; usarle prima come prior falsificabili, non come simulatore già fedele.

## 6. Quali dati cercare e perché

La domanda utile è quale ambiguità risolve una sorgente. Nessun requisito di
overlap coi 300 attuali per ammetterla; un pannello ponte ha invece bisogno di
interventi confrontabili per stimare il relativo cambio di misura o modalità.

| Priorità proposta | Sorgente / acquisizione | Domanda resa verificabile | Stato e costo conosciuti |
|---|---|---|---|
| 1 | Controlli, cellule e repliche di Mixscale | H1/H2/H4: effetto di programma, contesto e intensità | Oggetti Seurat pubblici: IFNG 2,9 GB, IFNB 4,3 GB; verificare metadati, RAM e conteggi prima del download |
| 2 | Microglia GSE335887 | H4/H5: soglia contro gradualità e stati multipli | Deposito dichiarato nell'articolo; dimensioni, schema dei file e licenza dei dati da verificare; nessun file acquisito |
| 3 | K562 CRISPRi GEM-X Flex di 10x | H8: ponte di misura verso il saggio della gara | Pagina ufficiale, dati pubblici e CC BY 4.0; dimensioni delle matrici e asse delle sonde da controllare |
| 4 | Universi completi di K562, CD4, Orion, DLD-1 già individuati | H1/H3/H7: molti bersagli, qualità delle etichette e famiglie nuove | Riutilizzare manifest e originali; cache di ricerca nuova, non soltanto i 300 bersagli |
| 5 | Confronto diretto CRISPRko/CRISPRi di Drepanos et al. | H7/H9: coerenza fra guide, modalità e tempi | Preprint: 25 geni, quattro guide per gene, due linee; accessioni/file e licenza non verificati qui |

Fonti verificate: [Mixscale Zenodo](https://zenodo.org/records/14518762),
[10x Flex](https://www.10xgenomics.com/datasets/16-plex_GEM-X_Flex_1M_human_K562_CRISPR_aggregate),
[confronto KO/i](https://www.biorxiv.org/content/10.64898/2026.07.04.736492v1.full).
La pagina 10x riporta 1.233.421 cellule, mentre la vecchia scheda interna cita
1.233.385 da una nota tecnica: non usare questi numeri come conteggio del file
senza ispezionarlo. Non cambiano la funzione del dataset come candidato ponte.

**Dati complementari:** controlli esterni e atlanti possono migliorare i
descrittori; ATAC e proteine aiutano a valutare i prior durante training;
CRISPRa, farmaci e knockout richiedono modalità esplicite. Un segno di CRISPRa
non si converte automaticamente invertendolo in un effetto CRISPRi. Dati di
fitness o imaging sono supervisione ausiliaria, non etichette trascrittomiche.
Non contare aliquote, stimoli o studi duplicati come nuove linee indipendenti.

## 7. La dipendenza dei risultati Mixscale resta da risolvere

**Verificato:** la documentazione degli autori permette analisi multivariata
per più linee; il deposito include firme da MultiCCA e firme specifiche di linea.
Fonti: [tutorial](https://satijalab.github.io/Mixscale/),
[deposito](https://zenodo.org/records/14518762).
**Non verificato:** quali dipendenze precise entrino nei log2FC e nei filtri del
nostro archivio. L'esistenza di una regressione con più linee non dimostra da
sola che ogni log2FC sia contaminato; occorre tracciare calcolo, normalizzazione
e selezione effettivamente usati.

Non usare le firme pubblicate, costruite anche con linee o bersagli di test,
come caratteristiche in una prova che si dichiara indipendente su quel dataset.
Ricalcolare entro i fold, oppure usare firme esterne con provenienza compatibile.
La specificità va verificata anche dopo aver separato variazione sistematica e
componente comune; questo è il problema trattato da
[Systema](https://www.nature.com/articles/s41587-025-02777-8).

## 8. Ordine di lavoro proposto

1. Audit di schema/provenienza delle stime Mixscale e dei controlli abbinati;
   audit leggero dei file di microglia e Flex. Stabilire quali prove sono fattibili.
2. Protocollo C/T/J, metriche nello spazio degli effetti, controlli negativi,
   metrica primaria e soglia fissati prima di addestrare. Famiglie geniche escluse
   come prova aggiuntiva alla separazione per identità.
3. Confronto H1/H2/H3: modello semplice, base di programmi, interazioni di stato;
   stesse partizioni e stessi input per le ablazioni. Base, normalizzazione,
   selezione e iperparametri solo sul training/validation.
4. In parallelo logico, H4/H5 su cellule e guide indipendenti: distinguere
   intensità continua, quota di rispondenti e soglia. Non è autorizzazione a
   lanciare lavori pesanti simultanei sul portatile.
5. Solo sui candidati che reggono, generazione di cellule e banco VCC. Valutare
   segnali specifici, distribuzioni, copertura e score: nessuna metrica da sola
   rappresenta tutte le domande.

Se un esperimento non usa davvero il contesto o migliora solo la componente
comune, rivedere l'ipotesi prima di aumentare capacità o numero di dataset.
