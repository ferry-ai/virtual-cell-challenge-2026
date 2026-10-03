# P4, rete non lineare sul pseudobulk, sette gruppi: lettura con la regola congelata

3 ottobre 2026, 03:26 CEST (`written_utc` di `decision.json`: 01:25:48 UTC). Regola:
[PROTOCOLLO_NN.json](../p4/PROTOCOLLO_NN.json), congelato prima di ogni fit sui dati reali. Corse: `p4_nn_r1`
(locale, cubo `cube_r1`, sette gruppi, finita alle 03:25:11 dopo 17.400 s) con i riferimenti `p3_c_r2`, entrambe nella
radice dati (`processed/generalizzazione_contesti_2026-10-02/`). Comando: `decide.py --run p3_c_r2 p4_nn_r1
--protocol p4/PROTOCOLLO_NN.json`. Indici sugli effetti, linee di sviluppo, non punteggi VCC.

**Esito: `no_benefit`.**

| Confronto | Primaria (coseno specifico), media sui gruppi | Gruppi positivi | Altro |
|---|---:|---:|---|
| `nn` − `nn0` (contesto) | −0,0019 (bootstrap sui gruppi −0,0085…+0,0042) | 4 su 7 | nulli permutati −0,0020, +0,0011, −0,0080; scambio dei controlli +0,0044 |
| `nn0` − transfer | +0,0127 | 4 su 7 | PDS −0,184; MSE relativo migliore (+0,31 orientato) |
| `nn0` − `tm0` | +0,0038 | 4 su 7 | PDS −0,066 |
| `nn` − transfer | +0,0108 | 4 su 7 | PDS −0,186 |

Per gruppo, `nn` − `nn0`: CD4T −0,0169, HCT116 +0,0013, HEK293T +0,0112, HepG2 +0,0033, K562 −0,0114, RPE1 +0,0007,
iPSC −0,0014.

**Misurato:** la versione non lineare della correzione condizionata dai controlli non batte il suo gemello senza
contesto e sta sotto il miglior nullo permutato. Nessuna variante batte il transfer sulla discriminazione fra bersagli
(PDS); come in P3, la calibrazione verso la risposta comune alza coseno e MSE e perde PDS.

**Interpretazione:** con questi input mediati, né la forma lineare (P3) né quella non lineare (P4) estraggono un
beneficio dal contesto su sette linee. Non dice che il limite sia la media: restano dati, rumore e confondimento linea /
studio. Il proprietario ha chiesto il 3/10 di non addestrare altre reti sul pseudobulk: questo risultato vale come
baseline della rete cellulare ([pilot](../../../modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md)). La versione a dieci
gruppi (kernel GPU `rlead-bench-nn-r1`, output in `kaggle_nn_r1/`) si legge quando il kernel CPU fornisce i suoi
riferimenti `p3_c_r3`.
