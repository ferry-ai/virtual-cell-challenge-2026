# Audit dal profilo alle cellule — 29 settembre 2026

**Tipo:** audit del codice, nuove misure sui controlli, proposta sperimentale. Nessun
punteggio ufficiale nuovo. I file produttivi e i dati originali non sono stati modificati.

## 1. Esito operativo

Il collo di bottiglia tecnico verificato è il legame fra profondità di lettura e
composizione delle cellule. Il generatore pooled di trial-01 lo elimina. Conserva la
composizione dei conteggi aggregati, utile a PDS/MSE, ma introduce una deriva nella
media CPM per cellula, usata nei quattro membri DE. In A/C la deriva più grande
coinvolge geni del ciclo cellulare; in B esiste una piccola popolazione di controlli
a bassissima library che cambia molto alcune medie CPM.

**Non è stato trovato un errore ln/log2 o log1p/mean nella MSE.** È una scelta del
modello generativo con conseguenze misurabili, già descritta in parte nei moduli ma
non risolta dalla ricetta attuale. Un generatore condizionato su bin di profondità
è stato implementato in questa cartella, con calibrazione della media pooled e
sette test sintetici. Rimane un candidato: il punteggio deve stabilire se il
miglioramento delle distribuzioni aiuti i sei membri insieme.

## 2. Verifica del contratto

- Lo scorer installato è `cell_eval2 0.16.0`. In
  `cell_eval2/metrics/delta.py:981` la MSE confronta la composizione pooled
  `log1p(50000 * sum_gene_counts / sum_all_counts)`, con esclusione del gene
  bersaglio e correzione di campionamento. La correzione è limitata sia per
  perturbazione sia dalla dispersione fra perturbazioni, tramite rho (#348).
  Il file letto ha SHA256
  `6067d0c5bd7cac4715406cd4935ec86326e91c6217f204f6bfc5b0a7bb948a8c`.
- [inference.py](../../../src/vcc2026/inference.py), righe 198 e 230:
  `predicted_profile` applica il fold change dopo clipping e corregge la massa
  solo sui geni osservati. L'unità dello stadio 100 viene convertita da ln a log2
  nello [stadio 45](../../../scripts/45_generate_prediction.py), riga 164.
  Non emerge un doppio log o un cambio di base errato.
- [de_tools.py](../../../src/vcc2026/de_tools.py), righe 154–156 e 183–214:
  il gate DE usa la **media dei CPM per cellula** maggiore di 5; il log2FC è il
  rapporto fra quelle medie. Il test Wilcoxon usa le distribuzioni dei CPM.
  La composizione pooled e questa media coincidono soltanto quando la profondità
  non è correlata con la composizione.
- [sampling.py](../../../src/vcc2026/sampling.py), riga 85: ogni cellula ha la
  stessa composizione, con library ricampionata. La dispersione per gene cambia
  la forma marginale ma non ricrea la covarianza fra stato e profondità.

**Limite della precedente conclusione sulla MSE.** Il fit
`u ≈ 1 + E / 4786` in
[risposta_comune](../../trasferimento/risposta_comune_2026-09-26/RISULTATI.md)
descrive sei invii simili. E deriva dai profili attesi, senza generare cellule;
il codice dichiara esplicitamente l'assunzione che le correzioni non leghino.
Il fit sostiene un problema di energia e direzione; non identifica da solo né
l'energia vera D né la covarianza reale, e non prova l'impossibilità universale
di ottenere MSE positiva cambiando famiglia generativa o modello.

## 3. Misure nuove sui 18.400 controlli di ciascun contesto

[Codice](generatore/audit_profile.py), [uscita](generatore/profile_r1.json).
Lettura completa in blocchi: nessun campionamento per queste medie.

| Misura | A | B | C |
|---|---:|---:|---:|
| Geni con media CPM per-cell >5 | 9.929 | 9.626 | 10.124 |
| Geni fra questi con bias nullo assoluto >0,1 log2 | 184 | 380 | 271 |
| CV delle library size | 0,459 | 0,385 | 0,438 |
| Energia bulk per bersaglio se si sostituisce pooled con mean-per-cell | 2,838 | 6,161 | 3,861 |
| E×300/4786 della stessa sostituzione (proxy, non score) | 0,178 | 0,386 | 0,242 |

Il bias è `log2(pooled_fraction / mean_cell_fraction)`, quindi è la deriva
attesa del generatore corrente a effetto nullo. Esempi A: PIF1 +0,304, PLK1
+0,237, AURKA +0,230, UBE2C +0,227. Esempi C: UBE2C +0,307, CDK1 +0,296,
TOP2A +0,273. **Interpretazione:** una componente legata al ciclo cellulare
è confusa con differenze di profondità; non è prova di risposta a un knockdown.

Sostituire semplicemente il profilo pooled con quello per-cell correggerebbe
una media e sposterebbe l'altra. Le energie sopra quantificano questo costo
nel comparatore bulk, su tutti i geni; non sono MSE ufficiali e non tengono
conto dell'effetto vero o delle correzioni dello scorer.

### Il caso B

[Codice](generatore/audit_lowlibrary.py), [uscita](generatore/lowlibrary_r1.json).

- 178 cellule hanno library <1.000: 0,967% delle cellule, 0,0415% delle letture.
- 458 hanno library <2.000: 2,489% delle cellule, 0,1446% delle letture.
- Queste ultime forniscono il 90,8% della media CPM per-cell di RNF151, il 93,2%
  di CCM2L, l'89,2% di SOCS1 e il 78,0% di MAFB. Il bias pooled corrispondente
  è −3,74, −3,59, −3,50 e −2,41 log2.
- In A/C non esiste alcuna cellula con library <2.000.

**Misurato:** la differenza fra le due medie è concentrata anche in una
sottopopolazione rara. **Non stabilito:** se essa rappresenti stato biologico,
qualità tecnica o entrambe. Non è una ragione per cancellare controlli: lo
scorer usa la loro distribuzione come riferimento.

## 4. La decisione sul t13 va riaperta

Il controllo nullo storico del 17 settembre
[summary.json](../../generatore_e_banchi/generator_null_2026-09-17/summary.json)
misura, con 400 cellule previste e 9.200 controlli:

| n_pred nullo mediano | A | B | C |
|---|---:|---:|---:|
| Poisson pooled | 460,5 | 429 | 674,5 |
| ControlModel KDE | 0 | 0 | 1 |
| Dispersione per gene, prova del 23/09 | 5 | 15 | 31 |

L'ultima riga viene da
[calls.json](../../generatore_e_banchi/dispersion_2026-09-23/null/calls.json):
stessi numeri di cellule, ma un'altra prova e un altro seme, quindi non un
confronto appaiato. I geni chiamati sotto il nullo sono falsi positivi;
non sono il `n_conf` dei veri knockdown, che resta ignoto.

La [regola del t13](../../generatore_e_banchi/dispersion_2026-09-23/PRIMA_DEI_RISULTATI.md)
bloccava la costruzione se un contesto superava 10 chiamate nulle. Perciò la
dispersione per gene non è mai stata inviata, pur riducendo l'artefatto di oltre
un ordine di grandezza. **Bias della scelta:** aver trasformato la pulizia
del nullo in condizione necessaria di competitività, senza misurare il
compromesso PDS/DE. La regola storica è stata rispettata; non dimostra che il
candidato fosse peggiore.

Il t14 cambiava anche ampiezza, scelta su un obiettivo di almeno 60 chiamate
mediane, quindi non isola il generatore. La proposta è un banco fattoriale
ampiezza × frazione della dispersione, più il braccio a bin descritto sotto,
con selezione e verifica su bersagli disgiunti. La scelta non deve basarsi
soltanto sulle chiamate nulle.

Il nuovo [protocollo nullo](generatore/PROTOCOLLO_NULLO.md) e il relativo
[codice](generatore/audit_null.py) sono preparati. Il processo è stato
interrotto prima di produrre risultati perché l'impacchettamento concorrente
lasciava poca RAM. Non si dichiara eseguito il confronto.

## 5. Candidato: composizioni condizionate sulla profondità

[Implementazione sperimentale](generatore/depth_bins.py),
[test](generatore/test_depth_bins.py).

Per ogni bin b si memorizza `q_b = somma conteggi nel bin / somma library nel
bin`. I pesi di profondità `W_b` sono la frazione dei conteggi totali del bin;
i pesi cellulari `w_b` la frazione delle cellule. Al nullo:

- `sum_b W_b q_b = q_pooled` esattamente;
- `sum_b w_b q_b` approssima la media CPM per cellula, diventando precisa se
  la covarianza residua entro bin è piccola.

Si campiona indipendentemente una library, il relativo bin e conteggi nuovi
Poisson dal profilo del bin. Si possono aggiungere dispersioni **residue** per
gene; riusare tutta la dispersione del profilo pooled rischia di contare due
volte l'eterogeneità già spiegata dai bin.

Per applicare gli effetti si costruisce prima il profilo target con
`predicted_profile` di produzione. Un'IPF sulla matrice bin × gene conserva
i margini di riga W e porta i margini di colonna al profilo desiderato. Questo
è un tilt globale per gene con normalizzazione per bin. Preserva la media
pooled attesa e lascia cambiare la distribuzione fra cellule.

**Supporto:** un gene presente solo in un bin può rendere impossibili alcuni
margini. L'opzione `support_smoothing=0.01` mescola ciascun profilo con l'1%
del pooled. Conserva esattamente il pooled al nullo e rende positivo in ogni
bin il supporto globale. Il test dedicato usa proprio un target impossibile
prima di questa regolarizzazione.

**Differenza da ControlModel:** quello apprende PCA, stati GMM/KDE e profili
kNN, con `mean_fix` stimato Monte Carlo e tagliato fra 0,5 e 2
([generator.py](../../../src/vcc2026/generator.py), righe 160–174). Qui la
dipendenza è limitata alla profondità, e il profilo aggregato atteso è
calibrato con una tolleranza esplicita. Nessuna correzione forza le somme
dei gruppi generati: le cellule restano indipendenti, con rumore campionario.

**Verifica:** sette test sintetici passati con
`scripts/py.cmd reports/analisi/lead_scientist_2026-09-29/generatore/test_depth_bins.py`.
Controllano ricostruzione dei due funzionali al nullo nel caso sintetico,
conservazione del profilo target dopo effetto, conteggi nuovi senza somme
prefissate, bordi dei bin e fattibilità del supporto regolarizzato.
I due test di integrazione verificano anche la parità bit per bit del braccio
pooled con `trial01_cells` e la diagnostica di calibrazione del braccio a bin.

La garanzia sul profilo è in aspettativa e prima dei cap di formato. Il sampler
registra quante cellule incontrano i cap di conteggi o sparsità. Rumore,
Wilcoxon, n_pred e PDS devono ancora essere misurati sui bracci reali.
Più precisamente, è esatto il rapporto fra i conteggi attesi di popolazione:
`E[C_gene] / E[L]`. Su 400 cellule il rapporto dei conteggi campionati e il suo
log1p hanno rumore e possibile bias non lineare; l'uguaglianza in popolazione
non garantisce che la MSE media dello scorer sia identica fra generatori.

## 6. Verifica sui profili attesi A/B/C

[Codice](generatore/audit_depth_bins.py), [uscita](generatore/depth_bins_r1.json).
Due letture streaming per contesto: la prima ricava library e media CPM esatta,
la seconda accumula i profili dei bin. Il file h5ad non contiene library size
nei metadati. Nessuna generazione o scoring in questa prova.

I bin uniformi usano otto quantili. I bin di coda usano i bordi di quantile
`[0, .01, .025, .05, .10, .25, .50, .75, 1]`, fissati dopo la misura delle
library basse, usando soltanto i controlli. La tabella riporta la RMSE in CPM
della media per-cell attesa sui geni con media per-cell reale >5.

| Profilo atteso | A | B | C |
|---|---:|---:|---:|
| Poisson pooled corrente | 7,199 | 5,465 | 6,088 |
| 8 bin uniformi + smoothing 1% | 0,237 | 2,143 | 0,229 |
| 8 bin di coda + smoothing 1% | 0,402 | 0,448 | 0,565 |

**Misurato:** con uniformi in A/C e coda in B il bias RMSE scende del 96,7%,
91,8% e 96,2%. I geni con bias assoluto >0,1 log2 passano da 184/380/271 a
0/0/0. La differenza massima assoluta del pooled atteso resta sotto
`1,8e-18`: la correzione non richiede lo spostamento di energia del cambio
ingenuo `pooled → per-cell`.

**Interpretazione:** conservare il legame fra profondità e composizione
risolve quasi tutto il disallineamento delle medie osservato nei controlli.
Questo risultato non misura i falsi positivi Wilcoxon: una distribuzione può
avere media corretta e forma sbagliata. Non dimostra neppure miglioramento
PDS/MSE: il rumore delle cellule generate e la risposta vera restano da valutare.

**Proposta di braccio:** stesso effetto t25/t27, stessi 400 campioni, bin
uniformi A/C e di coda B, smoothing 1%, nessuna dispersione residua nel primo
braccio. Confrontare poi una dispersione residua calibrata sui controlli.
Per un nuovo contesto il criterio fra le due griglie si può fissare dalla
ricostruzione delle medie dei soli controlli; non richiede esiti perturbati.

L'integrazione per il banco è pronta in [depth_candidate.py](generatore/depth_candidate.py),
con [protocollo](generatore/PROTOCOLLO_BANCO_BINS.md) a quattro bracci:
ampiezza relativa 1/2 × pooled/bin, dispersione residua zero. La scelta della
griglia usa soltanto i controlli. L'agente scientifico gestisce l'esecuzione
e gli insiemi di sviluppo/conferma; questa sessione non avvia un banco in parallelo.
