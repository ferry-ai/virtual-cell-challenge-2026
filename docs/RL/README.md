# RL — idee da riprendere in futuro

**Data:** 15 settembre 2026.
**Stato:** appunti esplorativi, su richiesta dell'utente. Nessuna tecnica adottata,
implementazione avviata o prestazione misurata. Questo filone è rinviato e non
aggiunge attività al piano operativo di oggi.

## Domanda di ricerca

Possiamo migliorare l'uso del calcolo o la qualità delle previsioni scegliendo
azioni sulla base di una ricompensa misurata? Prima di chiamare un metodo
reinforcement learning, specificare stato osservabile, azione, ricompensa e
presenza di vere decisioni sequenziali. Un confronto fra configurazioni può
richiedere soltanto ricerca di iperparametri o bandit.

## Idea 1 — Allocazione adattiva del budget degli esperimenti

**Ipotesi:** assegnare progressivamente più calcolo alle configurazioni promettenti
permette di ottenere un candidato migliore a parità di budget complessivo.

- Stato: metriche di sviluppo, curve di apprendimento, costo e checkpoint dei run.
- Azione: continuare un run, fermarlo oppure avviare una nuova configurazione.
- Ricompensa candidata: miglioramento in validazione rapportato al costo.
- Primo confronto: budget uniforme contro successive halving/Hyperband.
- Misurare: qualità finale, calcolo totale, costo della selezione e variabilità.
- Rischio: scartare modelli che apprendono lentamente; confronti non equi se
  cambiano dati, backend o numero di valutazioni.

È una pista di allocazione tramite bandit, non necessariamente RL sequenziale.
**Quando riaprirla:** esistono più training riprendibili e un budget che impone
scelte fra essi. Nessuna utilità presunta su pochi fit già economici.

## Idea 2 — Scelta dei parametri di calibrazione

**Ipotesi:** un selettore condizionato al basale e al supporto disponibile migliora
pesi delle sorgenti, ampiezza della risposta o parametri del generatore.

- Stato: descrittori disponibili all'inferenza e qualità delle sorgenti misurata
  esclusivamente sui dati di sviluppo.
- Azione: scegliere pochi parametri entro intervalli prefissati.
- Ricompensa: metriche locali su perturbazioni esterne con ground truth disponibile.
- Baseline obbligatorie: parametri globali calibrati, ricerca casuale o bayesiana.
- Primo esperimento: tenere fissi predittore e generatore; variare soltanto il
  selettore, con identico budget di valutazioni.
- Rischio: molti parametri rispetto ai pochi contesti; adattamento alla validazione.

**Quando riaprirla:** le calibrazioni semplici sono già valutate e una dipendenza
dal contesto è sostenuta dai dati. Se manca una sequenza di azioni, formulare prima
il problema come ottimizzazione o contextual bandit.

## Idea 3 — Affinamento di un generatore con ricompensa

**Ipotesi:** dopo il training iniziale, ottimizzare una ricompensa basata sullo
scoring migliora proprietà che la loss di training cattura male.

- Contesto: basale NTC, gene perturbato e covariate consentite.
- Azione: generare un campione o scegliere parametri della distribuzione predetta.
- Ricompensa: qualità rispetto alle cellule perturbate esterne, aggregate al livello
  appropriato. Lo scorer di un insieme di cellule non fornisce automaticamente una
  ricompensa informativa per ogni singola cellula.
- Baseline: stesso generatore prima dell'affinamento e semplice calibrazione con
  uguale budget. Metodo di aggiornamento ancora da scegliere; PPO non è un default.
- Rischi: DE costoso, ricompensa rumorosa, perdita di diversità, sfruttamento di
  particolarità dello scorer e difficoltà ad attribuire merito alle singole azioni.
- Possibili controlli: distanza dal modello iniziale, stabilità delle distribuzioni,
  nullo contro NTC, metriche per contesto e confronto su dati indipendenti.

**Quando riaprirla:** generatore affidabile, scorer riproducibile, ancore locali
stabili e costo della ricompensa misurato. Serve una formulazione concreta e
computazionalmente sostenibile prima di scegliere un algoritmo RL.

## Vincoli comuni

1. RL non fornisce le risposte perturbate mancanti nei contesti della challenge.
   Un simulatore appreso può riprodurre i propri errori: non è ground truth.
2. Separare dati per ottimizzare la ricompensa, selezione del metodo e conferma
   esterna. Appena un risultato guida aggiornamenti o scelte, è sviluppo.
3. Conservare split per linea e, nel protocollo unseen-target, escludere il target
   da tutte le sorgenti di fit/calibrazione. Guide e duplicati restano raggruppati.
4. Non sommare metriche grezze su scale diverse. Definire prima trasformazioni,
   pesi, ancore e gestione dei gate vuoti; riportare anche le componenti separate.
5. Contabilizzare anche il costo dello scoring e dei tentativi falliti. La
   leaderboard non è un ambiente ad alta frequenza per addestrare una policy.
6. Consultare lo stato aggiornato del progetto prima di ripartire: questi appunti
   non sostituiscono protocollo di valutazione o decisioni future.

## Come riprendere il filone

Scegliere una sola idea, fissare baseline e budget, identificare gli input
effettivamente disponibili e scrivere la regola di successo prima di eseguire.
Promuovere il metodo soltanto con un miglioramento su conferma indipendente e
costo giustificato rispetto alla soluzione più semplice. Se il confronto è
inconcludente, conservarlo come tale.

## Riferimenti iniziali

- [Hyperband — Li et al.](https://arxiv.org/abs/1603.06560): allocazione adattiva
  delle risorse fra configurazioni tramite bandit.
- [Offline Reinforcement Learning — Levine et al.](https://arxiv.org/abs/2005.01643):
  introduzione ai metodi che apprendono da dati già raccolti e ai loro limiti.

Riferimenti individuati nella discussione del 15 settembre; lettura mirata ancora
da completare prima di implementare. Non costituiscono evidenza di utilità su VCC.
