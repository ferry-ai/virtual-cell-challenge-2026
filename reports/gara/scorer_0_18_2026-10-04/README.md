# cell-eval2 0.18.0 contro la 0.16.0 dei confronti, e la suite di test della repo

4 ottobre 2026, notte. Claude Code, sessione `2b35612c`, R-LEAD. Verifica chiesta dal proprietario: «la segnalazione
sulla versione 0.18.0 di cell-eval2, tramite fonti ufficiali e confronto con quella attualmente usata», senza
aggiornare in silenzio lo scorer dei confronti; e i 3 errori `No module named cell_eval2.config` dell'ultima suite
eseguita da Codex.

## Fatti (misurati)

- **PyPI**, API JSON del progetto `cell-eval2`, lette il 4/10 alle 03:34: versioni pubblicate 0.0.1, 0.16.0
  (2026-08-20T08:15:45Z) e 0.18.0 (2026-10-01T23:38:16Z). Non esiste una 0.17. sha256 delle ruote:
  0.16.0 `c78428ba705a94536e4a55464a34d1905aa5730d4f7e52ea8dbef4e7171d4fbe`,
  0.18.0 `af7deb7c5d81d6f44bb8d7958524b52063db01cd2c8c34d4b670abb789573285`.
- **Lo scorer del venv del progetto è la 0.16.0 ufficiale**: il pacchetto installato
  (`C:/Users/ferra/vcc2026-data/.venv/Lib/site-packages/cell_eval2`) non differisce in nessun file dalla ruota 0.16.0
  scaricata da PyPI (`diff -rq`, cartelle `__pycache__` escluse). Contiene `config.py`. Le ruote stanno nello
  scratchpad della sessione e non sono installate.
- **Che cosa cambia nella 0.18.0** (`diff -rq` delle due ruote: 19 file):
  - `configs/` identica: `vcc2026.yaml` non cambia;
  - `metrics/direction.py`, `scoring.py`, `baseline.py`: cambiano solo percorsi di documenti nei commenti;
  - funzioni nuove opzionali e spente per default: jackknife per gene con un «pavimento di frazione di segnale»
    (`moments.py`, `streaming_bulk.py`, `prep.py`: `per_gene_jk=False`, `gene_mask=None`), tabelle DE per pezzo
    (`partition_inmem.py`, `de_out=None`);
  - controllo nuovo in `run.py`: errore se i nomi di gene della previsione o dei controlli reali sono duplicati;
  - #381: gli artefatti (ancore, pacchetti, baseline) non si rifiutano più quando la versione registrata differisce.
    La versione resta obbligatoria e registrata, ma non viene confrontata.
- **Suite della repo** (`.\scripts\py.cmd -m unittest discover -s tests`, venv del progetto), 4/10 dalle 03:34:
  **290 test, OK**, in 500 s. Log nello scratchpad della sessione, non conservato qui.

## Lettura (interpretazione)

- I 3 errori di Codex (287 superati + 3 errori = 290) sono compatibili con un interprete senza `cell-eval2` 0.16.0:
  con il venv del progetto la stessa suite passa intera. Non è un difetto del codice della repo; chi esegue la suite
  usa `.\scripts\py.cmd` (CLAUDE.md, «Before you finish»).
- Per i banchi del progetto, che chiamano `compute_metrics` con la configurazione `vcc2026` e le funzioni private DE e
  direzione (`src/vcc2026/bench.py`), i cambi della 0.18.0 non dovrebbero muovere i punteggi: configurazione e metriche
  sono identiche e le novità sono opzionali. **Non è provato da un'esecuzione**: serve una parità sugli stessi file con
  le due versioni in ambienti separati.
- **Decisione operativa:** i confronti restano sulla 0.16.0 (D-008), come i banchi già letti. Una prova di parità
  0.16.0 contro 0.18.0 (stesse previsioni, stessi reali, sei membri) va fatta in un ambiente a parte prima di un
  eventuale passaggio. Il passaggio si registra come decisione e non avviene in silenzio.
