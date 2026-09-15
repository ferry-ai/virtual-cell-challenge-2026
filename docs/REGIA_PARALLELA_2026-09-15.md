# Regia parallela — tutto il lavoro disponibile oggi

**Data:** 15 settembre 2026. **Mandato:** aggiornamento esplicito dell'utente.
**Stato:** piano operativo approvato dall'utente; incarichi da avviare e supervisionare
personalmente dall'utente. Questa pagina non attesta l'avvio di alcun agente.

Le attività prima distribuite nella settimana sono concentrate oggi. Tutte le
opzioni già individuate entrano nell'audit e nella preparazione in parallelo.
Solo il training può proseguire oltre oggi. Un impedimento esterno reale viene
segnalato subito con prova e alternativa: non diventa un rinvio silenzioso.
I risultati che richiedono un training non concluso restano esplicitamente pendenti.
Il rilascio ufficiale dei dati finali resta una dipendenza esterna di calendario.

## 1. Incarichi da avviare contemporaneamente

Ogni riga è un incarico autonomo da assegnare a un agente. Leggere prima
`CLAUDE.md`, `docs/PROGETTO.md`, il registro e il piano operativo. Il responsabile
legge anche le istruzioni applicabili al proprio percorso. Non cambiare i report
esistenti. Il pannello è già allegabile da
`configs/orchestrator/briefs/materiali/vcc2026-panel-2026-09-15.csv`.

| ID | Incarico da assegnare | Consegna di oggi | Dipendenze |
|---|---|---|---|
| A | Audit e pilot Jiang: file primari, counts/NTC, target, stimoli, conversione RDS, split per intera linea | Manifesto verificato, copertura misurata se elenco accessibile, estratto valido e conversione riprendibile | Audit subito; esecuzione pesante dopo preflight E |
| B | Audit Nadig/Jurkat e riconciliazione HepG2 originale/mirror: barcode, geni, guide, filtri e counts | Differenze documentate, inventario del quarto contesto e pilot utilizzabile | Audit subito; download dopo E |
| C | Audit Replogle single-cell, H1/Atlas e CD4: novità rispetto ai dati locali, duplicati e costo | Scheda per ciascuna sorgente, percorsi di acquisizione e pilot fattibili entro risorse | Audit subito; eventuale estrazione dopo E |
| D | Audit Srivatsan, McFaline-Figueroa, Tahoe/scBaseCount: perturbazione, controlli, licenza, utilità e confondenti | Decisione motivata per ogni fonte; adattatori/pilot pertinenti o esclusione documentata | Indipendente; nessuna equivalenza farmaco/KO/CRISPRi implicita |
| E | Infrastruttura Kaggle/Colab: misurare risorse, preflight, parità HepG2, persistenza, checkpoint e ripresa | Notebook eseguibile, prova di ripresa/export, capacità misurata e assegnazione dei job | Subito, sui dati già disponibili; non attende la GPU del compagno |
| F | Valutazione: audit leakage, ancore locali, sei metriche, bootstrap appaiato, predittore × generatore | Protocollo congelato prima dei nuovi risultati, codice e confronti eseguibili oggi sui dati esistenti | Subito; nuove fonti aggiunte dopo QC di A–D |
| G | Modelli: audit di calibrazione e descrittori; fattibilità State e PRiMeFlow; implementazione dei confronti giustificati | Configurazioni, budget, controlli e job pronti; avvio dei training ammessi dalle verifiche | Audit/implementazione subito; fit dipende da dati validi e protocollo F |
| H | Orchestratore e integrazione: diagnosticare database di stato, controllare i canali, preparare snapshot e raccolta risultati | Causa verificata del blocco, prova operativa, manifesti e indice delle consegne | Indipendente; evitare due processi sullo stesso profilo browser |

Gli incarichi A e F possono riusare i brief Jiang e validation-review già pronti;
G può riusare primeflow-audit. DeepSeek svolge ricerca primaria, Kimi revisione del
materiale e dei controesempi; browsing di Kimi non presunto. Gli agenti con accesso
al repository implementano e verificano. Le risposte web non eseguono codice locale.

## 2. Proprietà dei file e integrazione

- Ogni incarico scrive in una propria cartella di report con ID di run univoco.
  Nessun report condiviso in scrittura. Per il codice usare checkout/worktree
  separati quando possibile; altrimenti assegnare file esclusivi prima di editarli.
- Un solo integratore aggiorna mappa, registro, decisioni, configurazioni comuni e
  checkpoint scientifici. Gli altri consegnano le righe da inserire e il diff.
- E assegna RAM, disco e runtime prima dei job pesanti: ricerca parallela non
  implica otto processi che caricano matrici sulla stessa macchina da 8 GB.
- H serializza l'accesso ai profili DeepSeek/Kimi se l'orchestratore non supporta
  sessioni concorrenti isolate. Non avviare copie concorrenti presumendo che il
  database o i browser siano indipendenti.
- Risultati nuovi con input/checksum, versione del codice, configurazione, seed,
  split, unità, backend, tempo e picco memoria. Codice presente non significa eseguito.

## 3. Sincronizzazioni basate sulle consegne

**Prima barriera:** E consegna capacità e persistenza; F congela protocollo e split;
A–D consegnano file e controlli minimi. Nel frattempo audit e sviluppo continuano.

**Seconda barriera:** ogni pilot supera QC, mapping e deduplicazione; l'integratore
accetta i manifesti. Solo allora entra nel fit. La disponibilità di un file non
dimostra utilità predittiva e non autorizza il tuning sul test esterno.

**Terza barriera:** eseguire oggi i confronti che hanno già gli input disponibili;
preparare immediatamente gli altri e collegarli all'output del training. Risultati
consultati per selezionare diventano sviluppo: non riutilizzarli come conferma.

**Chiusura di oggi:** ogni opzione ha una decisione e ogni implementazione un
risultato di verifica. Il training eventualmente attivo ha checkpoint persistente,
comando di ripresa, destinazione degli output e valutazione successiva pronta.
Una submission richiede risultati che la giustifichino e convalida del pacchetto;
non è una conseguenza automatica della scadenza interna di oggi.

## 4. Come riferire al lead scientist

Formato da incollare quando serve una decisione:

```text
INCARICO / RUN:
STATO: pronto | in corso | verificato | bloccato
ARTEFATTI: percorsi + versione o commit
EVIDENZA: misura o fonte primaria; separare ipotesi
RISULTATO: cosa cambia rispetto alla baseline o all'inventario
VERIFICHE: test, QC, split, risorse
BLOCCO: causa osservata + alternativa già tentata
DECISIONE RICHIESTA: scelta precisa e opzioni
PROSSIMO PASSO:
```

L'utente avvia e supervisiona gli agenti. Il lead valuta evidenze e contraddizioni,
risolve le dipendenze scientifiche e decide l'integrazione quando interpellato.
Non sono attivati monitoraggi o esecuzioni automatiche in background da questo piano.
