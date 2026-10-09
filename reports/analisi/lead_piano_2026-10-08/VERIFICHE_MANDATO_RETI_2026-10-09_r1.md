# Verifiche del cambio di priorità del 9 ottobre

Tipo: misurato, sola verifica tecnica e coordinamento; nessuno score nuovo.

- Mandato salvato nel commit `bbe24219`, senza push. DATI e MODELLI hanno
  riconosciuto la priorità alle reti nei loro messaggi di avanzamento.
- `esm2-t-01a11c35-r3.verified_terminal_collection_r1.json` di MODELLI:
  PASS tecnico alle 01:57:20 Europe/Rome, 3.102 query × 18.533 geni;
  tutte le celle delle predizioni verificate, beneficio non valutato,
  compatibilità con l'emissione non ancora stabilita. DATI ha iniziato
  il controllo indipendente del consumo della vista congelata.
- `slots_preflight_r9.json`, alle 01:59:56: T COMPLETE; produzione, C-K562,
  J-K562 e C-iPSC RUNNING; J-iPSC r5 ERROR. Per il motivo DNS e il precedente
  avanzamento effettivo si rimanda a `ESECUZIONE_FIT_r5.md` di MODELLI.
- `scripts/31_check_docs.py`: PASS strutturale, 68 checkpoint e 12 strade.
- `.\scripts\py.cmd -m unittest discover -s tests`: 290 test in 285,280 s;
  287 riusciti e tre errori `ModuleNotFoundError: cell_eval2.config`, nei due
  smoke test dello stadio 73 e in `test_components_reproduce_the_scored_fidelity`.
  È lo stesso impedimento ambientale già riportato da MODELLI in r4/r5;
  nessuna dichiarazione di suite interamente passata. Dipendenze condivise
  non modificate in questo lavoro di coordinamento.

Gli artefatti MODELLI citati sono in
`reports/analisi/modelli_esterni_01a11c35_2026-10-08/`.
Il nuovo ramo contestuale è assegnato per sviluppo e prova tecnica:
queste verifiche non attestano che il suo training sia già partito.
