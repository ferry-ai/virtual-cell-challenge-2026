# generatore e banchi — dagli effetti alle cellule, e i banchi con lo scorer vero

Un invio non è una tabella di effetti: sono 360.000 cellule generate, su cui lo scorer chiama i
geni differenziali. Qui stanno le misure del generatore (quante chiamate produce anche a effetto
nullo), del DE dello scorer, e i banchi a sei metriche su cellule perturbate vere di linee
pubbliche. Indice generale: [../README.md](../README.md).

**Da sapere:**
- Il generatore di tutti i migliori invii (stadio 45, trial-01) produce **centinaia di chiamate
  spurie per bersaglio a effetto nullo** (462 / 453 / 684 in A / B / C, l'82 % «in su»);
  `ControlModel` (stadio 76) quasi nessuna, ma nel t14 ha abbassato la fedeltà.
- **Il solo banco con lo scorer vero è HepG2** (un contesto, bersagli essenziali, solo K562 come
  sorgente, verità su metà delle cellule): è la prova più vicina alla gara, non la gara.
- **Il banco fattoriale ampiezza × dispersione del 29/09**, che ha scelto il t28, sta nella
  revisione lead: [indice, sezione «Generatore e t28»](../analisi/lead_scientist_2026-09-29/README.md#generatore-e-t28).
  Sul banco dava +0,0289 d'indice locale, in gara +0,0046
  ([CP-0052](../../docs/checkpoints/0052-t28-punteggio-ufficiale.md)).

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 04/10 | [ripresa_banco_v2_2026-10-04/](ripresa_banco_v2_2026-10-04/STATO_1936.md) | Subentro Codex: cinque reti congelate, 400 cellule × 5 semi, emissione t28, verifica completa degli input; K562 r2 ripara un controllo tecnico | cinque banchi RUNNING; ingestione CD4 12/12 verificata; nessun nuovo risultato scientifico | ★★ |
| 04/10 | [banco_v2_2026-10-04/](banco_v2_2026-10-04/) | Banco v2 dopo CP-0065: bracci come file di effetti, 400 cellule previste per bersaglio, 5 semi, un flusso casuale per (seme, bersaglio) condiviso fra i bracci, emissione t25 o t28, differenze appaiate con deviazione standard | strumento con test; non ancora eseguito su dati veri | ★★ |
| 29/09 | [banco_k562_pannello_2026-09-29/](banco_k562_pannello_2026-09-29/) | Azione 4 di R-REV: banco con lo scorer vero sui bersagli del pannello, verità K562, sorgenti CD4, HCT116, HEK293T; 11 bracci (t22, t23, controllo d'ampiezza, soglia del t26, esclusione del t27 con e senza riscalatura, ampiezze, dispersione, cache r9) × 3 semi del generatore di trial-01; taratura contro i membri ufficiali di t23 e t26. Protocollo e regola fissati alle 18:10, prima del codice | protocollo; bracci costruiti e copiati su Drive il 29/09 sera, job non ancora eseguito (nessun `r1/`) | ★★★ |
| 26–27/09 | [banco_hepg2_v2_2026-09-26/](banco_hepg2_v2_2026-09-26/) | Stadio 75, job 046: la forma t19 batte la t16 (+0,026, intervallo sopra zero); raddoppiare la t19 dà +0,015 con l'intervallo sullo zero; la testa cis non si vede; Jaccard negativo in tutti i bracci: la risposta media del contesto porta geni DE che il K562 non ha | sì (ancore locali, descrittivo, nessuna regola) | ★★★ |
| 23/09 | [dispersion_2026-09-23/](dispersion_2026-09-23/) | Dispersione per gene nel generatore di trial-01 (t13 non costruito: 5 / 15 / 31 chiamate a effetto nullo) e piloti di `ControlModel` per il t14. `--gene-dispersion` **non è mai stato inviato** | sì | ★★ |
| 23/09 | [prediction_calls_2026-09-23/](prediction_calls_2026-09-23/) | Stadio 83 sui file di t11, t14 e t15: chiamate mediane per bersaglio (543–1.009 con trial-01, l'81–86 % «in su»; 136–218 con `ControlModel`) | sì | ★★ |
| 17/09 | [generator_null_2026-09-17/](generator_null_2026-09-17/) | Calibrazione a effetto nullo a scala piena (stadio 72): le chiamate spurie del generatore di trial-01, di `ControlModel` e delle cellule vere | sì | ★★ |
| 17/09 | [generator_null_smoke_2026-09-17/](generator_null_smoke_2026-09-17/) | La stessa prova in versione ridotta | superato da `generator_null_2026-09-17/` | ★ |
| 17/09 | [bench_2026-09-17/](bench_2026-09-17/) | I primi banchi a sei metriche su Colab: K562 del pannello (`b002`) e trasferimento K562 → HepG2 (`h002`); scala locale | storico | ★ |
| 17/09 | [prediction_calls_2026-09-17/](prediction_calls_2026-09-17/) | Stadio 83 sul t02: quante chiamate e quanto scende il gene bersaglio (5–9 % invece dell'85 %) | storico | ★ |
| 17/09 | [call_budget_2026-09-17/](call_budget_2026-09-17/) | Chiamate per bersaglio al variare dell'ampiezza su A, con pochi controlli di riferimento: un limite inferiore | storico | ★ |
| 17/09 | [fast_de_2026-09-17/](fast_de_2026-09-17/) | Il DE veloce dei banchi (`fast_scorer_de`) è identico al percorso scanpy dello scorer (D-037) | sì | ★ |
