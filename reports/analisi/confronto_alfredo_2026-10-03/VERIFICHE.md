# Verifiche della consegna

3 ottobre 2026, Codex. Analisi e messaggio committati in `8939511`; nessun push.

- `scripts/31_check_docs.py`: **OK**, 57 checkpoint, registro, decisioni e collegamenti coerenti; 197 percorsi archiviati riconosciuti. Controllo strutturale, non validazione delle conclusioni.
- `calcoli_analitici.py`: eseguito; output in `calcoli_analitici.json`. Solo scalari e libreria standard, nessun training o dato cellulare.
- `git diff --check`: passato prima del commit. Il commit comprende solo i dieci file di questa revisione e una riga ciascuno negli indici di analisi e registro.
- Suite richiesta `.\scripts\py.cmd -m unittest discover -s tests`: **287 test, 1 failure e 3 errori**, 562,987 s nel sandbox.

## Errori isolati e verifica successiva

I tre errori erano `ModuleNotFoundError: cell_eval2.config`, nei due test `TestStage73Smoke` di `test_bench_generator` e in `BenchComponentTests.test_components_reproduce_the_scored_fidelity` di `test_sc_pipeline`. Il precedente [CP-0054](../../../docs/checkpoints/0054-visibilita-scorer-e-consegna.md) documenta la stessa differenza di visibilità. Ho ripetuto **solo quei tre test**, con lo stesso wrapper Python, fuori dal sandbox: **3 test passati in 33,934 s**. Nessuna installazione o modifica delle dipendenze. I warning dello scorer riguardano le fixture e non sono risultati di modelli o invii.

La failure iniziale del controllo dei report era sulla nostra cartella: il test enumera i file attraverso Git e la cartella non era ancora aggiunta quando è stata acquisita quella vista. Dopo staging e commit, la replica del solo `test_live_tree.py` non segnala più `analisi/confronto_alfredo_2026-10-03`; segnala invece `sorgenti/revisione_ingestion_2026-10-03`, introdotta nel frattempo da una sessione concorrente con indice già modificato e file ancora non tracciati. Ho lasciato intatti quei file. La replica ha eseguito 11 test, con quella singola failure, in 4,597 s.

Non dichiaro quindi una suite complessiva tutta verde sul checkout condiviso. Le tre anomalie dello scorer sono risolte nella verifica nativa; la nostra incongruenza di tracciamento è risolta; la vista globale dei report resta soggetta alle modifiche della sessione ingestion. Non è stato rieseguito l'intero banco biologico, né il codice di Alfredo.
