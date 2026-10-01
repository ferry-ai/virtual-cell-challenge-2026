# docs/storico — analisi e testi superati, conservati com'erano

Documenti che hanno guidato il progetto fra l'11 e il 30 settembre e che oggi **non sono una
guida**: le loro conclusioni sono state corrette, sostituite o riguardano linee chiuse con il
codice archiviato. Si aprono quando una decisione o un checkpoint li cita, dopo aver letto la
loro riga nel [registro](../REGISTRO.md) (`python scripts/31_check_docs.py --status <file>`).
Le analisi sono state spostate qui il 28 settembre (D-046), le sezioni tolte da PROGETTO il 28 e
il 30 settembre, senza cambiare il testo salvo i percorsi dei link; un checkpoint che li cita come
`docs/<file>` li trova qui.

| Data | File | Nocciolo | Vale? |
|---|---|---|---|
| 30/09 | [PROGETTO_direzione_2026-09-30.md](PROGETTO_direzione_2026-09-30.md) | Apertura della direzione generale prima dell'audit D-050/CP-0053 del 1 ottobre | storico; programma attuale R-LEAD, esecuzione R-LAB |
| 11/09 | [data_strategy_2026-09-11.md](data_strategy_2026-09-11.md) | Prima strategia dei dati e ordine di acquisizione | superato come ordine; il contratto di preprocessing (§4) e le misure locali (§1) restano (R-003) |
| 11/09 | [revisione_analisi_2026-09-11.md](revisione_analisi_2026-09-11.md) | Identità dei contesti dai marcatori, povertà del segnale in K562, clamp dello scorer | da verificare: contraddizione aperta sull'asse in Ensembl (R-004) |
| 12/09 | [candidate_adversarial_review_2026-09-12.md](candidate_adversarial_review_2026-09-12.md) | Verifica avversaria delle sorgenti candidate: CD4 prima, Orion seconda; coperture misurate | attuale per le misure; l'ordine è superato da D-031 e D-039 |
| 12/09 | [revisione_grok_2026-09-12.md](revisione_grok_2026-09-12.md) | Verifica di un inventario esterno di Grok: correzioni di accessione e piste nuove | attuale come verifica datata |
| 14/09 | [BENCHMARK_MODULARE.md](BENCHMARK_MODULARE.md) | Primo confronto modulare su K562/RPE1: inconcludente | chiuso (CP-0011, codice archiviato) |
| 14/09 | [BENCHMARK_TRE_CONTESTI.md](BENCHMARK_TRE_CONTESTI.md) | Benchmark a tre contesti con HepG2, e il confronto generatore × predittore | chiuso (CP-0013); l'acquisizione di HepG2 e il suo md5 restano validi |
| 14/09 | [ENCODER_INPUTS.md](ENCODER_INPUTS.md) | Specifica dei descrittori di bersaglio e contesto per i geni mai perturbati | vale come inventario; l'estensione GO slim è scartata (CP-0014) |
| 15/09 | [SVD_E_RANGO.md](SVD_E_RANGO.md) | SVD randomizzata e scelta del rango | chiuso (CP-0015, D-029, D-030) |
| 28/09 | [PROGETTO_sezioni_3_4_2026-09-28.md](PROGETTO_sezioni_3_4_2026-09-28.md) | La tabella delle misure del 12–17/09 e le 21 incertezze numerate, com'erano in PROGETTO | storico; lo stato di ogni incertezza è in PROGETTO §4 |
| 30/09 | [PROGETTO_sezioni_0_6_7_2026-09-30.md](PROGETTO_sezioni_0_6_7_2026-09-30.md) | Il preambolo, il §0, il §6 e il §7 di PROGETTO com'erano la mattina del 30/09: la cronaca del t28, della rete sulle sorgenti e di Stack, la vecchia tabella dei punteggi e il vecchio percorso di lettura (D-049) | storico; lo stato è nel §0 di PROGETTO, i punteggi in `reports/invii/README.md` |
| 28/09 | [README_2026-09-11_13.md](README_2026-09-11_13.md) | Le sezioni storiche del README in inglese (piano per fasi, revisioni dell'11–12/09) | storico; sei affermazioni contestate in R-001 |
