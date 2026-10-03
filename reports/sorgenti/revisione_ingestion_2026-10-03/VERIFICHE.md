# Verifiche finali della revisione

3 ottobre 2026, Codex. Nessun nuovo job cloud o training; nessuna modifica alle dipendenze.

- **25/25 fixture ingestion PASS**, [log finale](test_corretto_r3.txt). Quattro correzioni circoscritte, documentate in [AUDIT](AUDIT.md), con riproduzioni sull'originale.
- **8/8 hash del codice consegnato verificati**, confrontando i file con [codice_corretto_manifest.json](codice_corretto_manifest.json); zero differenze al controllo del supervisore.
- **11/11 controlli `test_live_tree.py` PASS** dopo staging, in 8,466 secondi. La cartella nuova è tracciata e indicizzata.
- **`git diff --cached --check` PASS** prima del commit.
- **Suite generale:** `.\scripts\py.cmd -m unittest discover -s tests`, 287 test in 486,035 secondi, una failure e tre errori nel sandbox. Le cause e la verifica successiva sono sotto. Non si dichiara una suite complessiva tutta verde.

## Errori dello scorer verificati nell'ambiente nativo

I tre errori sono `ModuleNotFoundError: cell_eval2.config`, nei due casi di
`test_bench_generator.TestStage73Smoke` e in
`test_sc_pipeline.BenchComponentTests.test_components_reproduce_the_scored_fidelity`.

Ripetuti soltanto questi tre test con lo stesso wrapper Python, fuori dal sandbox:
**3/3 PASS in 15,216 secondi**, codice d'uscita 0. Nessuna installazione o modifica del
codice per far passare i test. I warning dello scorer riguardano le fixture, non un invio.
È un limite di visibilità dell'ambiente, già distinto da un difetto del codice.

## Controllo documentale sul checkout condiviso

`scripts/31_check_docs.py` ha segnalato inizialmente tre file non ancora registrati in
`reports/modelli/rete_ancorata_2026-10-03/`. Durante la suite, quella cartella è cresciuta:
`test_doc_workflow.CheckerTests.test_this_repository_is_consistent` ha segnalato 17 file
della stessa cartella non coperti dal registro. Nessun errore segnalato riguarda questa
revisione ingestion.

La cartella appartiene a una sessione concorrente attiva: non è stata modificata né
aggiunta al commit di Codex. Claude1 deve completare indice e registro di quel lavoro
quando lo consegna, poi ripetere il controllo documentale. Questo limite globale rimane
esplicito nel passaggio di consegne.

## Provenienza Git e incrocio fra sessioni

Mentre Codex preparava il commit, il commit concorrente `54405b2` (titolo relativo alla
lane B del pilot) ha incluso anche i 23 file ingestion già presenti nell'indice condiviso:
quattro guide/indici e 19 file della revisione. L'ispezione di `git show --stat 54405b2`
lo conferma; il lavoro ingestion resta attribuito a questa sessione Codex e al reviewer
locale. Non è un'integrazione deliberata del codice ingestion nella pipeline del pilot.

La guardia del commit Codex ha rilevato che restavano tre percorsi staged anziché 24 e
si è fermata prima di creare un commit inatteso. Nessuna cronologia è stata riscritta;
il commit finale Codex riguarda soltanto README, prompt di passaggio e questo riepilogo.
Nelle prossime sessioni condivise usare un worktree o un indice temporaneo per isolare
la preparazione, e committare percorsi espliciti come già richiesto da `docs/AGENTI.md`.
