# Rete cellulare, versione 2: correzioni dell'audit e pilot su linee escluse intere

3 ottobre 2026, Claude Code (sessione `22d21f`), programma [R-LEAD](../../../docs/piani/strategia-scientifica.md).
Il proprietario vuole una rete addestrata sulle cellule, non sul pseudobulk (30/09, confermato il 3/10). Questa cartella
è il codice corretto e il pilot che decide se espandere. Da leggere per primo: [PROTOCOLLO.md](PROTOCOLLO.md),
congelato prima di ogni training.

| File | Che cosa |
|---|---|
| `PROTOCOLLO.md` | Domande, linee escluse, bracci, misure e regola del pilot |
| `DIFETTI.md` | I difetti dell'audit dell'1/10: riprodotto, corretto o registrato, con il test che lo prova |
| `train_cellnet.py`, `cellnet.py`, `cell_data.py` | Versione 2 (copie di `risposta_biologica_2026-09-30`, originali intatti) |
| `kaggle_train.py` | Kernel Kaggle: codice e kernel su `davideferrante11`, corpus su `davidmaisterx` |
| `line_groups.json`, `target_keys.py` | Gruppi di linea; chiavi riconciliate per le fold a hash del banco |
| `test_v2_units.py`, `test_v2_stages.py`, `test_pi_floor.py` | Test della versione 2; `test_cell_data.py`, `test_prepass.py`, `test_read_csr.py` della versione 1 |
| `bench_effects.py` | Corsia A: spostamenti previsti contro le righe del cubo del banco della linea esclusa, con i transfer delle stesse righe (test: `test_bench_effects.py`, sul cubo vero) |
| `decide_pilot.py` | La regola del §6: accettazione tecnica, collasso, Q1–Q3, espansione (test: `test_decide_pilot.py`) |
| `choose_targets.py`, `generate_cells.py`, `kaggle_gen.py`, `lane_b_hepg2.py` | Corsia B: bersagli per regola, cellule generate dalla rete su Kaggle, sei membri in locale su HepG2 |
| `lancio_*.json` | Kernel, commit, dataset e argomenti di ogni lancio, scritti al lancio |
| `inventory.py` | Quali dataset e quante cellule entrano davvero nel training, e perché le altre restano fuori |
| `export_effects.py`, `target_descriptors.py` | Copie della versione 1, non modificate |

Dati e output pesanti nella radice dati, `processed/rete_cellulare_2026-10-03/`.
