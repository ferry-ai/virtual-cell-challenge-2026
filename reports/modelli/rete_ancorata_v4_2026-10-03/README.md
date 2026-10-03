# Rete ancorata al transfer, versione 4: percorso dei dati corretto e ancore pulite

3 ottobre 2026, Claude Code, sessione «Integrazione Codex e piano operativo» (`5eacdf`), programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md). Da leggere per primi: [PROTOCOLLO.md](PROTOCOLLO.md) (pilot
dichiarato, regola congelata prima di ogni training) e [diagnosi_r1/DIAGNOSI.md](diagnosi_r1/DIAGNOSI.md) (perché i
training v3 non erano tecnicamente accettabili). Lo stato dei lavori e il prossimo passo stanno nella scheda R-LEAD,
non qui.

Il modello è quello della v3 ([cartella](../rete_ancorata_2026-10-03/README.md)); cambiano il percorso dei batch, la
lettura degli shard, i budget, le medie delle ancore e le loro fonti. Gli originali v3 restano intatti.

| File | Che cosa |
|---|---|
| `PROTOCOLLO.md` | Domanda, cambi dalla v3 con le loro prove, ancore, bracci, accettazione tecnica, misure, regola |
| `diagnosi_r1/` | `DIAGNOSI.md`; `fetch_r1_logs.py` e `log_r1/`: ricevute tecniche dei training v3 senza righe di valutazione |
| `balanced.py` | Batch bilanciati: quote per gruppo di linea e studio a ogni passo, partizione delle celle fra i ruoli dei loader, campionatore a epoche per unità |
| `fastshard.py` | Gemelli compatti degli shard: stesse righe e conteggi, blocchi zstd con indici delta e byte-shuffle; codifica verificata per decodifica |
| `train_cellnet.py`, `cellnet.py`, `cell_data.py` | Versione 4 (copie della v3): `--sampler balanced`, `--fast-roots`, budget separati, ricevuta `exposure.json`, tempi del percorso dei batch; `cellnet` legge anche i gemelli; `cell_data` invariato |
| `anchors.py` | Ancore v4: medie del regime J, regole di fonti `all` / `cells` / `production`, `max_sources` nel manifest |
| `build_fast.py`, `kaggle_fast.py` | Costruzione dei gemelli su Kaggle CPU con verifica contro `files.json`, profilo per shard e ricostruzione del campionatore v3 sullo stato H1 |
| `kaggle_anchors.py`, `kaggle_train.py`, `kaggle_gen.py` | Launcher v4 di ancore, training (gemelli come sorgenti) e generazione (bersagli della corsia B r3, modulo completo) |
| `bench_effects.py`, `lane_b.py`, `decide_anchored.py`, `decide_pilot.py` | Corsie A e B con i tre riferimenti di transfer a medie J; la regola del §7 (`decide_pilot.py` è la copia v3 di cui la regola usa `technical`, `paired`, `rule`) |
| `generate_cells.py`, `extract_cells.py`, `choose_targets.py` | Generazione delle cellule (v4: `--with-baseline`); estrazione e scelta dei bersagli, copie v3 non usate dalla v4 |
| `CAMPIONI_ANNIDATI.md`, `nested_samples.py`, `nested_rule.py`, `kaggle_nested.py` | Binario dati, studio dei campioni annidati 32/64/128 (più 256 e 512 per le eccezioni): protocollo con la regola di sufficienza congelata prima dei numeri e due emendamenti (§9 varianza e zeri; §10, correzione di Codex: la scelta è per fold e legge solo le cellule di training, la corsa su tutte le classi resta esplorativa); campionatore per (libreria, guida) e perdita d'informazione sullo spostamento specifico; regola che rifiuta le tabelle non di training; launcher Kaggle CPU con controllo di codice, stato, shard e gemelli sul runtime |
| `build_fast_units.py`, `kaggle_fast_units.py` | Gemelli compatti degli shard lasciati negli output dei kernel d'ingestione (Orion, KOLF, CD4), verificati contro il manifest dell'unità e per decodifica: il passo che porta le linee nuove dentro un training |
| `lancio_nested_r1.json` | Lancio dello studio esplorativo r1 |
| `fixtures.py` e `test_*.py` | Test: formato (5), costruzione (3), campionatore (6), training end-to-end (8), ancore (6), regola (5), generazione (3), campioni annidati (6), regola dei campioni (10), kernel dei campioni (4), invarianza per fold (5), gemelli delle unità (3) |
| `lancio_fast_r1.json`, `lancio_anchors_r1.json`, `lancio_train_r1.json` | Lanci su Kaggle con autorizzazione, preflight, input e stato |
| `fetch_outputs.py`, `esito/` | Scarico in sola lettura dei file piccoli di un kernel concluso; manifest e log dei gemelli (`fast_<x>_r1/`) e delle ancore (`anchors_r1/`), poi le ricevute dei training |

I dati pesanti stanno nella radice dati, `processed/rete_ancorata_v4_2026-10-03/`: stage dei kernel, ricevute grezze
dei training v3 (`r1_logs_raw/`), output scaricati.

## Riprodurre i test

```powershell
cd reports/modelli/rete_ancorata_v4_2026-10-03
C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe -m unittest test_fastshard test_build_fast test_balanced test_anchors_v4 test_decide_anchored -v
C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe -m unittest test_train_v4 test_generation_v4 -v
C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe -m unittest test_nested_samples test_nested_rule test_kaggle_nested test_nested_fold test_fast_units -v
```

Il secondo comando richiede alcuni minuti (training sintetici su CPU). `scripts/py.cmd` va bene per tutti tranne i
comandi con `|` negli argomenti (lezione operativa in ERRORI).
