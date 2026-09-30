# Banco per il generatore a bin — protocollo prima degli score

29 settembre 2026. Proposta operativa concordata con la sessione principale,
prima di vedere uno score prodotto dal generatore a bin. La motivazione e la
scelta delle due griglie derivano dalle misure esplorative sui controlli A/B/C
già lette in `depth_bins_r1.json`: non si presenta quella ricostruzione come
conferma indipendente della scoperta.

## Domanda

A parità di profilo pooled della ricetta, conservare una parte della relazione
fra library size e composizione migliora lo score a sei membri, e mantiene PDS?

## Quattro bracci, nessuna ricerca aggiuntiva dei parametri

| Nome | Ampiezza relativa al file effetti | Generatore | Dispersione residua |
|---|---:|---|---:|
| pooled_a1 | 1 | stage45 Poisson | 0 |
| bins_a1 | 1 | bin scelti sui controlli | 0 |
| pooled_a2 | 2 | stage45 Poisson | 0 |
| bins_a2 | 2 | bin scelti sui controlli | 0 |

400 cellule previste per bersaglio. Stessi effetti, maschere observed,
esclusioni geniche e cap di formato. Il profilo target viene costruito da
`predicted_profile`; il braccio pooled chiama `trial01_cells`, già controllato
contro lo stadio45 dal test produttivo. Stesso seme nominale per i due bracci;
le sequenze casuali consumate non sono identiche dopo i diversi campionamenti.

Il fit usa soltanto i controlli del contesto tenuto fuori. Due modelli di
profili: 8 quantili uniformi e i quantili
`[0,.01,.025,.05,.10,.25,.50,.75,1]`; smoothing 1% del pooled in ciascun bin,
uguale nei due modelli. Si sceglie quello che minimizza la RMSE dei CPM medi
per cellula attesi, sui geni con media CPM reale dei controlli >5. Un pareggio
sceglie la griglia uniforme. Questa selezione non legge risultati perturbati.

L'IPF calibra il rapporto dei conteggi attesi al profilo pooled desiderato;
non modifica le somme dei gruppi campionati e non elimina il loro rumore.
Si registrano errore massimo di calibrazione, iterazioni ed eventuali cap.
Un fallimento di convergenza invalida il braccio, non diventa profilo nullo.

## Sviluppo e verifica

Lo sviluppo può usare i medesimi 48 bersagli del banco fattoriale generatore
× ampiezza in preparazione dall'agente scientifico. L'uso successivo dello
stesso sviluppo è **esplorativo e adattivo**: non costituisce una seconda
replica indipendente. La suddivisione dei bersagli, la sorgente di verità e
gli effetti sono quelli già congelati dal banco principale, registrati nel
suo manifest; questa integrazione non li sostituisce.

Il confronto primario è bins meno pooled alla medesima ampiezza. Il modello
scelto passa a 96 bersagli disgiunti e tre semi. Se si portano anche altre
varianti scelte dal fattoriale sullo stesso insieme di conferma, il report
deve elencare tutti i confronti e correggere per quella molteplicità
(Holm sui p-value dei confronti appaiati, oppure intervalli simultanei).
Non si sceglie a posteriori il sottoinsieme di semi o bersagli favorevole.

Il report dà score grezzo e scalato locale per membro, media dei sei,
differenze appaiate per bersaglio e variabilità fra semi. Lo score locale non
è uno score VCC: la forza e la numerosità degli effetti della verità pubblica
devono essere riportate insieme ai numeri. Un esito nullo non prova che il
modello generativo sia inutile nei contesti Flex.

## API pronta per il banco

`depth_candidate.py` espone:

```python
candidate = DepthCandidate.fit(control_csr)  # solo controlli
counts, detail = candidate.sample(
    lfc_ln, observed_mask, 400, rng,
    amplitude=1.0, generator="bins",  # oppure generator="pooled"
)
```

`candidate.selection` registra metrica, griglia scelta ed errori di entrambe.
Il modulo è sperimentale in questa cartella e non è importato dalla pipeline
di produzione. Avvio del banco e cambi della produzione restano coordinati
dalla sessione principale, per memoria e impacchettamento concorrente.
