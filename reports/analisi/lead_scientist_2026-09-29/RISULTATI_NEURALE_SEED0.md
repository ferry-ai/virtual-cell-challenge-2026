# Rete sulle sorgenti: seed 0 completo, promozione respinta

**Misurato, 29 settembre 2026.** La guardia di provenienza e copertura passa sui
cinque fold esterni completi: **6.144 coppie target–contesto**, 12 contesti e 5
famiglie, con 512 target fuori pannello per contesto. Le 6.144 coppie non sono
6.144 geni bersaglio distinti; uno stesso target può ricorrere in contesti diversi.

Il guadagno di rango medio rete − transfer, pesato prima ugualmente per famiglia
e poi per contesto, è **+0,00222233**, CI95 `[+0,00055605; +0,00390661]`.
La soglia preregistrata era **+0,01**: `eligible_for_cell_scorer=false`.
Famiglie: CD4 `+0,00515737`, iPSC `+0,00327814`, K562 `−0,00722898`,
Orion `−0,00131291`, RPE1 `+0,01121805`. Nessuna è sotto `−0,01`, ma il criterio
macro non è superato. Non si prepara il fit di produzione né un candidato ABC.

Rete − rete cieca è `−0,00041611`, CI95 `[−0,00104444; +0,00021331]`: non emerge
un vantaggio significativo nella lettura registrata. Rete − contesto scambiato
è `−0,00022283`, CI95 `[−0,00043760; −0,00001679]`, lieve differenza nella
direzione opposta a quella ipotizzata. Questi risultati significano **nessun
beneficio utile del condizionamento biologico dimostrato da questa prova**;
non dimostrano che il modello ignori computazionalmente il contesto, né che ogni
modello contestuale o neurale debba fallire.

Il bootstrap primario ricampiona i ranghi già calcolati all'interno di ogni
contesto ed è condizionato alle cinque famiglie osservate. Non conserva la
dipendenza di un target ripetuto fra contesti. La diagnostica cluster già
congelata può descrivere questa sensibilità, ma non cambia il criterio originale,
non promuove il modello e non è uno score VCC. Manca una validazione cellulare.

**Esecuzione:** tutti i fold hanno `returncode=0`, `complete=true`; lo stato ERROR
del notebook deriva esclusivamente dal `KeyError: 'null'` nel reader finale.
Il reader meccanicamente corretto e verificato legge l'intero insieme senza
riaddestramento. Sono stati recuperati 61 piccoli report, 14.190.933 byte;
12 NPZ e 10 checkpoint restano disponibili nell'output remoto.

Evidenze: `kaggle_neural_r1/readout_verified_r1/verdict.json` e `provenance.json`;
`kaggle_neural_r1/results_small_r1/download_manifest.json` e, sotto
`neural_sources_r1/`, `completion.json`, `cross_family.log` e i cinque fold.
Il dettaglio operativo è in `kaggle_neural_r1/RISULTATO_SEED0.md`.

La replica seed 1 era stata avviata prima di questa lettura, come registrato in
`EMENDAMENTO_NEURALE_SCHEDULING_01.md`. Viene letta integralmente anche dopo il
fallimento di seed 0; non si seleziona il seme favorevole. Nessuna submission è
autorizzata da questo benchmark.
