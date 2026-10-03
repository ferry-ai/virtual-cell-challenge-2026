# Lo scorer `cell_eval2` 0.18.0 confrontato con la 0.16.0

2 ottobre 2026, 23:15 CEST, Claude Code per Alfredo, che ha autorizzato il download in chat. La 0.18.0 è uscita su
PyPI il 1° ottobre; il progetto usa la 0.16.0 del 20 agosto
([contratto](../scorer/vcc2026_contract.json)). La domanda viene dalla
[revisione del 2 ottobre](../../analisi/letteratura_strade_2026-10-02/README.md), strada 0: la nuova versione chiude
la separazione fra profilo medio e cellule?

## Che cosa è stato fatto

- **Download** delle due ruote pubbliche con `pip download --no-deps`, in una cartella temporanea della sessione:
  - `cell_eval2-0.16.0-py3-none-any.whl`, sha256 `c78428ba…`: identica, file per file, alla copia installata nel venv;
  - `cell_eval2-0.18.0-py3-none-any.whl`, sha256 `af7deb7c…`.
- **Confronto** con `diff -r` dei pacchetti estratti. Niente è stato installato: il venv resta sulla 0.16.0.

## Che cosa è cambiato (misurato sul codice)

- **19 file diversi**, circa 840 righe di diff. **Invariati:**
  - `configs/` (quindi `vcc2026.yaml`);
  - `competition.py` (la regola e il suo digest);
  - `metrics/delta.py`, `metrics/de.py`, `metrics/discrimination.py`.
- **`metrics/direction.py` e `catalog.py`:** solo un percorso in un commento.
- **#381:** la versione dello scorer è registrata ma non più confrontata fra bundle e anchor. Una baseline costruita
  con un'altra versione ora si accetta.
- **#387:** si possono scrivere le tabelle DE grezze (`de_real.parquet`, `de_pred.parquet`) anche nel percorso
  a streaming.
- **`run.py`:** errore esplicito se l'asse dei geni della previsione ha nomi duplicati.
- **La novità che conta: le primitive di una «soglia sulla frazione di segnale» per la MSE.** Sono in `moments.py`,
  `prep.py`, `streaming_bulk.py` e `gpu/bulk.py`: `jackknife_per_gene` e `signal_fraction_mask`.
  - **Che cosa fa:** tiene nel calcolo della MSE solo i geni (per bersaglio) dove il cambiamento **vero** supera il
    rumore di campionamento di una quota η.
  - **Il commento:** il gene tenuto «è proprietà del pannello, che nessuna sottomissione può muovere».
  - **Lo stato:** **non è attiva.** Il codice dice: «No consumer of that kind ships on this branch — the floor policy
    and its gene-subset plumbing live on the local `fix/expr-mse-signal-fraction-floor` branch, which is also where
    `rule_version` moves to 4».

## Che cosa dice dei piani degli organizzatori (lettura dei commenti, non misura nostra)

- **Una leva sulla MSE che conoscono.** La chiamano «layout exploit» e l'hanno misurata sul pannello val A:
  - senza soglia vale **0,9121** dell'intervallo del membro;
  - con η = 0,95 il limite teorico scende a 0,053 (misurato 0,0153), ma si tiene solo il 18,1% della massa degli
    effetti;
  - con η = 0 vale 0,2845.

  È lo stesso filone di #247 e #348: la correzione del rumore di campionamento nel pseudobulk, sfruttata disponendo le
  cellule in modo che il loro sparpagliamento si cancelli nella somma.
- **Una regola nuova è in preparazione** (`rule_version` 4). Quando e se arriverà in gara non si sa. Se arriva, la
  MSE leggerà solo i geni ad alto segnale di ogni bersaglio.

## Che cosa implica per la strada 1 (proposta)

- **Oggi i punteggi della 0.18 e della 0.16 sono gli stessi per costruzione** (regola, configurazione e metriche
  invariate). Non serve aggiornare il venv per la validazione.
- **La forma onesta del doppio momento non è toccata:** un profilo medio previsto bene vale con o senza soglia. Con la
  soglia conta di più azzeccare i geni che cambiano molto.
- **Le forme che sfruttano la correzione del rumore** (cellule disposte per cancellarsi nella somma, «portatrici»)
  sono esattamente ciò che gli organizzatori stanno chiudendo. Su D/E/F potrebbero valere zero o meno, e sarebbero
  sleali. Restano escluse.
- **Da fare per la strada 1:** valutare localmente ogni variante **anche** con una soglia simulata. Si chiama
  `signal_fraction_mask` della 0.18 con η = 0,95 su un banco con verità nota, così la variante scelta non dipende
  dalla regola che uscirà.
