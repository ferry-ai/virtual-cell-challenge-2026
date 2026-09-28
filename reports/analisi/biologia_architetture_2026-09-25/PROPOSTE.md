# Architetture e prove biologiche da sviluppare

25 settembre 2026. **Proposte**, collegate alle misure di [RISULTATI.md](RISULTATI.md).
Non è un protocollo congelato: soglie, split e criteri di promozione devono essere
fissati prima del training. Nessuna riattivazione del codice archiviato.

## 1. Programmi con interazioni e incertezza gerarchica

Forma candidata: `effetto(t,c) = comune(c) + B × a(t,c) + residuo(t,c)`.
B contiene programmi appresi solo nel training oppure annotati esternamente.
a combina descrittori del bersaglio e dei controlli con interazioni bilineari
o nonlineari. Un residuo regolarizzato evita che l'asse IFN o altri programmi
dominanti cancellino risposte più rare. Il modello non deve vietare l'induzione
di un programma solo perché poco espresso prima della perturbazione.

Input del bersaglio: complessi, ruolo regolativo con segno, domini e sequenza
opzionale, tutti disponibili per bersagli mai perturbati. Input di contesto:
controlli e loro distribuzione di stati, non le cellule perturbate di test.
Stimolo/tempo sono input solo se disponibili anche al test; altrimenti servono
come supervisione ausiliaria o fattori da marginalizzare, non etichette nascoste.

Obiettivi: perdita mascherata sui geni misurati, separazione fra risposta comune
e specifica, errore sui contrasti fra contesti, incertezza su donatori/guide/studi.
Una forma iniziale della varianza è `SE_entro² + tau_donatore² + tau_studio²`,
con termini stimati da repliche, non costanti inventate. Bilanciare studi e
bersagli: milioni di cellule di una sola linea non sono milioni di contesti.

La restrizione verso la previsione del programma è candidata solo quando questa
è validata: includere componente nulla e incertezza del prior. In T/J non si può
usare l'effetto osservato del bersaglio nascosto nemmeno come prior o embedding.

Confronti: ridge sugli stessi input/base, modello senza interazioni, senza
residuo, programmi rimescolati e risposta comune con ampiezza predetta. Un
programma interpretabile richiede stabilità fra repliche e riscontri esterni:
la fattorizzazione può ruotare senza cambiare le previsioni.

## 2. Grafo multirelazione condizionato dallo stato

Encoder distinti per complessi, interazioni fisiche, TF→gene con segno e
similitudine funzionale; pesi degli archi modulati dallo stato basale. Embedding
del bersaglio e contesto alimentano il decoder di programmi del §1, con un
percorso residuale per gli effetti non rappresentati nel grafo.

Il pattern STAT2/USP18 motiva la distinzione fra vicinanza e ruolo. Non rende
causali i pesi di attenzione. Archi con segno possono essere specifici di un
contesto; geni ben annotati possono ricevere un vantaggio artificiale.

Prove: MLP con gli stessi attributi, rete senza segni/direzioni, archi rimescolati
preservando il grado, singole relazioni e nodi poco connessi. Escludere intere
famiglie/complessi oltre alle identità dei bersagli. Tracciare i grafi derivati
da perturbazioni: un altro laboratorio non rende lecite le risposte del test.

**Letteratura verificata nella ricerca:**
[TxPert, Nature Biotechnology 2026](https://doi.org/10.1038/s41587-026-03113-4)
combina encoder basale e grafi e valuta perturbazioni/linee non osservate.
L'uso di mappe perturbazionali richiede audit della disponibilità e del leakage;
non è una prova di successo nel nostro regime J.

**Ulteriore riferimento da verificare:**
[Stable-Shift](https://arxiv.org/abs/2606.24940), segnalato dall'agente come
preprint del 2026, è un confronto candidato a basso rango; dettagli e protocollo
vanno riletti prima di implementarlo. Non si assume che dimostri contesti nuovi.

## 3. Distribuzioni: probabilità di risposta e intensità condizionale

Un encoder di insiemi descrive gli stati delle cellule di controllo. Dati
bersaglio e stato, due rami predicono la probabilità di risposta e la trasformazione
della cellula rispondente. Un decoder stocastico o conditional flow rappresenta
la distribuzione finale. Soglie e saturazione devono poter dipendere da
bersaglio × programma × contesto, non da una sola etichetta «gene switch».

Confronti a media comparabile: spostamento uniforme, sola variazione di dispersione,
miscela semplice, modello con soglia morbida e flow senza gate. Loss su media,
programmi e distribuzioni, con guide/repliche escluse. Controllare proliferazione,
composizione e sopravvivenza; non eliminare automaticamente stress/ciclo cellulare,
che possono essere effetti veri.

Con sole medie, quota e intensità non sono identificabili. Al test l'efficacia
vera della perturbazione non è disponibile: predirla o marginalizzarla. Una
buona distribuzione predetta non identifica traiettorie individuali, bistabilità
o isteresi. Intensità e risposta su geni disgiunti riducono la circolarità diretta,
ma programmi correlati non diventano misure indipendenti.

## 4. Dati mirati e cosa permettono di distinguere

Questi sono candidati; nessun download o adozione. Non è richiesto overlap con
i 300 bersagli attuali. Prima di acquisire verificare licenza, risorse, schema,
guide, controlli e repliche nei file effettivi.

| Candidato | Evidenza e verifica svolta | Prova proposta | Limite |
|---|---|---|---|
| Jost, GSE132080 | [Articolo letto](https://pmc.ncbi.nlm.nih.gov/articles/PMC7065968/) e [GEO indicizzato](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE132080): guide attenuate con mismatch; matrice processata compressa 335,9 MB, identità cellulari e tabella guide | Curva continua contro soglia e miscela; guide intermedie escluse; probabilità ISR contro intensità condizionale | Pannello meccanicistico piccolo, non prova J; circa 5% di possibili assegnazioni guida errate secondo gli autori |
| Microglia, GSE335887 | [Articolo](https://pmc.ncbi.nlm.nih.gov/articles/PMC13505846/), letto dall'agente; accesso diretto del coordinatore ostacolato da reCAPTCHA in questa sessione | Soglia per programma, guide/repliche indipendenti; possibile verifica proteica | La dose inferita da Mixscale non è indipendente dal trascrittoma di risposta |
| PerturbFate, GSE291147 | [GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE291147), file RNA/sgRNA/metadati segnalati dall'agente; riapertura diretta bloccata da reCAPTCHA | RNA nuovo/vecchio per distinguere risposta dinamica e convergenza di stato, con ATAC come supervisione ausiliaria | Ricontrollare schema/file/licenza prima di adottare; RNA marcato non equivale a traiettoria longitudinale, ATAC post-perturbazione non è input lecito al test |
| Confronto KO/CRISPRi, Drepanos et al. | [Preprint](https://www.biorxiv.org/content/10.64898/2026.07.04.736492v1.full), letto dall'agente: guide, tempi, K562 e A549; accessione non individuata | Separare modalità, efficacia, tempo ed effetti sui TSS vicini | Pista bibliografica, non sorgente pronta; KO non equivale a CRISPRi amplificato |

**Risultato degli autori di Jost, non misura nostra:** per ATP5E la frequenza di
risposta ISR aumenta con la deplezione ma restano non-rispondenti anche a RNA
molto basso; GATA1 mostra una relazione con soglia nell'abbondanza totale di UMI.
Questo rende sensato distinguere quota e intensità senza dimostrare bistabilità.
I programmi e la selezione dei geni vanno stimati nel training o da fonti esterne.

Per i dati già censiti, restano utili VIPerturb-seq come ponte di saggio e gli
universi completi delle sorgenti. Si rinvia alla
[ricerca del 25 settembre](../ricerca_sorgenti_2026-09-25/RISULTATI.md), senza
duplicare le sue schede o trasformare candidati in dati adottati.

## 5. Protocollo da congelare prima del training

1. Separare scoperta e conferma: STAT2 e MCF7/TNF sono casi esplorati, non test
   intatti. Conferma su altri bersagli definiti prima, guide/repliche o studio.
2. Usare un nucleo incrociato di bersagli, stimoli e linee. Con 181/218 bersagli
   in un solo stimolo, la rete può memorizzare l'appartenenza al pannello.
   I bersagli monostimolo restano utili, ma non identificano interazioni arbitrarie.
3. C/T/J secondo [GENERALIZZAZIONE](../../docs/GENERALIZZAZIONE.md), base,
   normalizzazione e selezione solo nel training; calibrazione su validation.
4. Confrontare risposta comune, comune con ampiezza specifica predetta, programmi
   con ruolo e modello completo con contesto. Negli split T/J anche ampiezza e
   ruolo del bersaglio nascosto sono predetti senza accedere ai suoi esiti.
5. Misurare il contrasto dello stesso intervento fra contesti e, dove osservabile,
   la differenza di tali contrasti fra due interventi. Il solo scambio del contesto
   non prova apprendimento biologico: può introdurre input fuori distribuzione.
6. Controlli/repliche indipendenti per stimare incertezza; permutazioni entro
   stimolo e gruppi comparabili; riportare supporto, copertura e casi deboli.
   La sottrazione dello stesso background può creare correlazioni artificiali.
7. Metrica primaria, unità di ricampionamento e soglia di promozione fissate prima.
   Score di gara, ricostruzione degli effetti e distribuzioni restano risultati
   distinti. Una calibrazione oracolare non sostituisce validation indipendente.

## 6. Prossime azioni proposte

- **R-DATI:** contrasti CD4 per donatore/guida; confronto entro/fra donatori a
  uguale numerosità, poi calibrazione dell'incertezza su donatori esclusi.
- **R-MODELLI:** formalizzare programmi con segno e contrasti di contesto;
  confrontare seriamente architettura gerarchica e grafo multirelazione.
- **R-SWITCH:** audit Jost per dose–risposta progettata e microglia per programmi;
  scegliere la prova che separa intensità e quota senza input post-perturbazione
  illeciti. PerturbFate resta una pista per la dinamica.

L'ordine è una proposta di ricerca, non autorizzazione a download, training,
consumo di quota o invio. Non serve attendere T18/T19 per disegnare queste prove.
