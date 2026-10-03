# Rete cellulare ancorata al transfer (versione 3)

3 ottobre 2026, Claude Code, sessione «R-LEAD implementazione vcc2026» (`22d21f`), programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md).

Dopo il verdetto del pilot r3 il proprietario ha scelto di non espandere la rete versione 2: si parte dal transfer e la
rete impara a correggerlo, sempre sulle singole cellule (§11 del
[protocollo r3](../rete_cellulare_2026-10-03/PROTOCOLLO.md)). Da leggere per primo: [PROTOCOLLO.md](PROTOCOLLO.md).
È una **bozza** finché un commit non lo congela; il congelamento viene dopo il controllo delle miscele
([MISCELE.md](../rete_cellulare_2026-10-03/MISCELE.md)) e prima di ogni training.

| File | Che cosa |
|---|---|
| `PROTOCOLLO.md` | Domanda, modello, dati, bracci, misure e regola |
| `anchors.py` | Le ancore: il transfer t25 del banco per ogni coppia (linea, bersaglio) di training e per i bersagli C della linea esclusa, mai dalla linea della riga né da quella esclusa (test: `test_anchors.py`, sul cubo vero) |
| `cellnet.py`, `train_cellnet.py`, `generate_cells.py` | Versione 3, copie della versione 2 con l'ancora nei logit, il guadagno, il braccio `ancora_sola` e i controlli delle ancore (test: `test_v3_anchored.py`; regressione della versione 2: `test_v2_units.py`, `test_v2_stages.py`, `test_pi_floor.py`) |
| `cell_data.py`, `extract_cells.py`, `target_descriptors.py`, `line_groups.json` | Copie della versione 2, non modificate |
| `kaggle_train.py`, `kaggle_gen.py`, `lane_b.py`, `bench_effects.py` | Copie della versione 2, da adattare: le ancore come sorgente dei kernel, e la corsia B con le due definizioni del transfer |
| `test_prepass.py` | Copia della versione 1: fornisce `GENES` e `counts` ai test |

I dati pesanti e gli output vanno nella radice dati, `processed/rete_ancorata_2026-10-03/`.
