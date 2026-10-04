# Ibrido selettivo D-056, versione 1: transfer congelato + correzione neurale + selettore fuori fold

4 ottobre 2026, Claude Code, sessione `2b35612c`, programma [R-LEAD](../../../docs/piani/strategia-scientifica.md),
mandato del proprietario del 4/10 ([D-056](../../../docs/DECISIONI.md#d-056--transfer-con-correzione-neurale-selettiva)).
Da leggere per primo: [PROTOCOLLO.md](PROTOCOLLO.md), congelato a `817f42a` prima di ogni training; l'emendamento §12
(obiettivo del selettore invariante di scala) è stato scritto prima di leggere qualunque uscita. Stato dei lavori ed
esiti: la scheda R-LEAD e, alla lettura, un checkpoint.

| File | Che cosa |
|---|---|
| `PROTOCOLLO.md` | Ipotesi, precedenti (S-001–S-007), dati e ruoli delle linee, componenti, guardie, selettore, misure, regole di lettura, regola degli invii, accettazione |
| `cellnet.py`, `train_cellnet.py` | Versione 5 (copie v4): guadagno fisso, testa comune fuori dalla previsione, penalità L2 sulla correzione, coppie di validazione a peso zero, guardie con arresto e stato migliore esportato |
| `guards.py` | Coppie di validazione (scelta per hash) e metriche delle guardie: rango di discriminazione, ampiezza, componente comune, beneficio |
| `hybrid_lanes.py` | Righe per il selettore, corsia A (indici degli effetti sulle righe C e J) e corsia B (sei membri) con il controllo di parità `ibrido_w0` |
| `selector.py` | Selettore a sei parametri e miscela fissa: `lolo` (sviluppo), `final` (sistema congelato), `apply` (linee di conferma, senza leggere l'esito) |
| `decide_hybrid.py` | Le regole del §8–§10 e il punteggio di banco del §9, scritte prima di ogni uscita |
| `accept_training.py` | Accettazione tecnica di un training dalle ricevute (§10) |
| `kaggle_train.py`, `kaggle_hybrid.py`, `kaggle_anchors.py`, `kaggle_extract.py` | Launcher Kaggle: training, righe e corsie, ancore di una linea nominata, cellule vere della corsia B prima del training |
| `replicate_datasets.py`, `share_to.py` | La catena sul secondo account: dataset del codice copiati byte per byte, cubo condiviso in lettura |
| `cell_data.py`, `balanced.py`, `fastshard.py`, `anchors.py`, `fixtures.py`, `line_groups.json`, `fetch_outputs.py` | Copie v4 invariate |
| `test_hybrid_train.py`, `test_guards.py`, `test_selector.py`, `test_train_v4.py` | Test: training v5 end-to-end (7), guardie (6), selettore e ibrido (6), v4 sul trainer v5 (8) |
| `lancio_train_r1.json`, `lancio_train_r2.json`, `lancio_replica_r1.json`, `lancio_hybrid_r1.jsonl`, `lancio_extract_r1.jsonl` | Lanci con autorizzazione, verifiche prima del push e stato |
| `esito/` | Ricevute dei training (senza file di valutazione) con `acceptance.json`, righe, ancore ed estrazioni delle linee di conferma |

I dati pesanti stanno nella radice dati, `processed/ibrido_selettivo_2026-10-04/` (stage dei kernel e output
scaricati).

## Riprodurre i test

```powershell
cd reports/modelli/ibrido_selettivo_2026-10-04
C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe -m unittest test_guards test_selector -v
C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe -m unittest test_hybrid_train test_train_v4 -v
```

Il secondo comando richiede alcuni minuti (training sintetici su CPU); `test_selector` vuole `src/` nel `PYTHONPATH`.
