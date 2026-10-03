# Revisione del pilot cellulare: guardie e supporto fra contesti

3 ottobre 2026, Codex, chat del proprietario sui progressi di Claude. Snapshot `05504a1`, confrontato con
`1357466`. Audit indipendente di R-LEAD: codice e protocollo della sessione Claude lasciati invariati.
La prima segnalazione era rimasta nella chat e in fixture temporanee: è stata una consegna incompleta di Codex.
Questa nota rende disponibili i dettagli e la riproduzione, senza lanciare training o job cloud.

## 1. I due difetti originariamente riprodotti

**Misurato su fixture sintetiche.** Evidenza completa: [reproduction_r1.json](reproduction_r1.json).

| Caso | `1357466` | `05504a1`, dopo la correzione di Claude | Esito richiesto |
|---|---|---|---|
| Configurato `health_check_step=5000`, ma manca `health.json` | La linea è accettata | La linea è rifiutata | Rifiutare la linea: corretto |
| H1 ha `health.passed=false`; HepG2 e RPE1 valide e positive | Espansione positiva | Ancora espansione positiva | Confronto incompleto, non promuovere: aperto |
| Fornite solo HepG2 e RPE1, entrambe positive | Espansione positiva | Espansione positiva | Richiedere le tre linee preregistrate: stesso difetto |

Il controllo positivo, con tre linee valide e favorevoli, passa in entrambe le versioni.
Nel caso della salute mancante, la nuova versione rifiuta correttamente la linea ma il secondo difetto consente
comunque di espandere sulle altre due. Il JSON distingue accettazione della linea ed esito globale.

**Localizzazione:** `decide_pilot.py`, funzione `rule`, righe 98–104, elimina i valori non finiti prima di fare
la media; `main`, riga 119, ricava il numero richiesto di vittorie dalle linee fornite, senza controllare che siano
esattamente H1, HepG2 e RPE1. La media di due linee non è la media delle tre del §6: la terza potrebbe renderla
negativa. Un fallimento tecnico non equivale a uno zero.

**Correzione proposta alla sessione proprietaria dei file:** verificare identità e unicità delle tre linee;
per ogni confronto richiedere accettazione tecnica, assenza di collasso nei bracci interessati e differenza
finita per tutte e tre. Altrimenti registrare il confronto come incompleto, senza imputare zero o sconfitta.
Mantenere le soglie: media delle tre positiva e almeno due vittorie; completezza necessaria anche per Q3.
Inserire questi casi nei test prima del verdetto. Nessun emendamento per accettare retroattivamente la media
dei soli casi disponibili.

Le correzioni di Claude per la posizione di `kernel_done.json`, `verify.json` ed `eval.json` mancanti sono utili;
non esaurivano le due prove di Codex. Non si afferma che il difetto residuo abbia promosso il pilot reale:
è un controesempio, e Claude riferisce che l'espansione non parte automaticamente.

## 2. Matrice verificata e limite dell'interpretazione

Fonti di Claude: [lettura della matrice](../../modelli/rete_cellulare_2026-10-03/esito/matrix_r1/LETTURA.md)
e i CSV per linea nella stessa cartella. Registro `attuale`, indice ancora fermo a codice/protocollo con risultati
da aggiungere: si usano qui le tabelle come evidenza datata, senza dedurre validità scientifica dall'indice.

**Misurato:** il 62–63% dei bersagli addestrati compare in un solo gruppo. Su H1, 97/151 bersagli C
(64,24%) hanno al massimo due gruppi; HepG2/RPE1 ne hanno almeno tre, contando tutte le modalità.
Quindi sette gruppi complessivi non garantiscono sette contesti per bersaglio.

Il conteggio `training_groups_any` combina CRISPRi, CRISPRa e KO e basta una cellula ammessa per contare un gruppo.
Le modalità sono correttamente conservate separatamente nei CSV, ma la sintesi «4–6 linee» usa il totale.
Il nostro script ricalcola anche CRISPRi soltanto e una sensibilità con almeno 20 cellule CRISPRi per
coppia bersaglio/gruppo, **senza introdurre un nuovo filtro o criterio del pilot**:

| Linea esclusa | Bersagli C | Con al massimo 2 gruppi, tutte le modalità | Solo CRISPRi | Solo CRISPRi, almeno 20 cellule per coppia |
|---|---:|---:|---:|---:|
| H1 | 151 | 97 | 98 | 100 |
| HepG2 | 1.748 | 0 | 0 | 125 |
| RPE1 | 1.794 | 0 | 0 | 143 |

**Limite della conclusione causale:** le fasce 3, 4 e 5–6 confrontano bersagli diversi, con studi, modalità,
numerosità e possibili difficoltà diverse. Uno scarto dal transfer invariato potrebbe anche accompagnare un
miglioramento di entrambi. Le tabelle dimostrano che il candidato attuale resta inferiore al transfer anche
nella fascia con più supporto. Non identificano la causa e non escludono che aggiungere contesti pertinenti
agli stessi bersagli possa migliorarlo.

**Formulazione supportata:** su HepG2/RPE1 la sola scarsità a uno o due gruppi non spiega direttamente il
sottoinsieme valutato; il modello perde anche con maggiore supporto. Restano aperti i contributi di dati,
rappresentazione, obiettivo e ottimizzazione. Per isolare il beneficio di più contesti occorre un confronto
annidato sugli stessi bersagli e sulla stessa linea esclusa, preregistrato; questo audit non lo lancia.
Il pilot corrente si può leggere con la propria regola senza attendere tale esperimento.

## 3. Riproduzione e consegna a Claude

[reproduce.py](reproduce.py) recupera da Git due versioni fissate dello script, esegue quattro fixture per versione
in directory temporanee e legge solo i piccoli CSV della matrice. Il JSON conserva commit e hash del codice e
degli input. Non apre gli stati prepass pesanti e non interroga il cloud.

```powershell
.\scripts\py.cmd -B reports/analisi/revisione_pilot_cellulare_2026-10-03/reproduce.py --out reports/analisi/revisione_pilot_cellulare_2026-10-03/reproduction_r2.json
```

Usare sempre un output nuovo. Per Claude: correggere la completezza prima del verdetto; completare H1 e la
corsia B con la generazione corretta; mantenere distinta l'analisi descrittiva dall'identificazione della causa.
Nessuna nuova rete o espansione è richiesta da questa nota.
