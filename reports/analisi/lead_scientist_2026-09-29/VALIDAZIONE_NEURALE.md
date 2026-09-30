# Implementazione e verifiche della rete sulle sorgenti

29 settembre 2026. **Implementato e verificato su dati sintetici; nessun risultato
biologico reale ancora misurato da questi test.** I file runtime sono stati consegnati
al lead per una copia privata immutabile prima del calcolo remoto.

- `neural_sources.py`: lettore dei profili separati per contesto, maschere e fallback
  STRING, prior e basali comparativi, attenzione vincolata al trasferimento.
- `train_neural_sources.py`: split famiglia esterna/interna, passo zero, early stopping,
  modello cieco separato, refit, confronti ed export sull'asse ufficiale.
- `read_neural_sources.py`: lettura congiunta obbligatoria dei cinque fold registrati,
  con pesi uguali per famiglia e contesto. Le soglie sono nel protocollo.
- `test_neural_sources.py`: test sintetici riproducibili con il wrapper del progetto.

**Misurato:** 11 test passati, 23,786 secondi del test runner locale, PyTorch
2.14.0+cpu. Questo tempo riguarda soltanto la fixture sintetica, non stima il training
reale. Le prove includono inizializzazione identica alla baseline, equivarianza alla
permutazione delle sorgenti, apprendimento di una scelta di sorgente piantata, canarino
sugli outcome nascosti in C e J, esclusione della famiglia propria e del cis,
supporto comune delle etichette nella loss, previsione nulla senza fonte mantenuta
nel rango, split annidati, ciclo CLI completo di due passi e roundtrip NPZ di una
famiglia di test e del contesto A con `allow_pickle=False`. Il ciclo sintetico ha
selezionato correttamente il passo zero: non è stato forzato a scegliere una rete
modificata.

**Misurato dai soli metadata reali**, senza lettura degli effetti né scoring:
dataset r2 con 109.586 righe, 13 contesti e 13.248 geni memorizzati. Nel fold K562 la
famiglia interna selezionata è Orion. Il manifest di questa sola preparazione è
`neural_plan_k562/manifest.json`; fotografa il codice prima dell'ultima correzione
della copertura e non costituisce il manifest del training. Un run reale scrive
nuovamente il proprio manifest prima di leggere gli effetti.

Le sole feature dei token hanno dimensione 16 × 13 × 1.024 × 20 float32, cioè
17.039.360 byte per batch; si aggiungono attivazioni, gradienti, matrici di verità,
export e cache del sistema operativo. Il corpus rimane mmap, non una copia intera
sulla GPU. Il numero di feature non è una promessa sulla memoria massima o sul tempo.

Esecuzione remota, preservando la struttura del repository:

```text
python reports/analisi/lead_scientist_2026-09-29/train_neural_sources.py --data DATASET_R2 --out NUOVO_K562 --holdout k562 --device cuda
```

Ripetere in cartelle nuove per `cd4`, `orion`, `ipsc`, `rpe1`; il lettore richiede
tutti e cinque. Il solo `pool.py` del report r1 è dipendenza runtime storica. Per
eseguire anche i test servono inoltre `train.py` e `net.py` dello stesso report.
Il dataset Kaggle privato già disponibile può essere montato senza ricaricarlo.

L'export di produzione è implementato con `--holdout none --predict-contexts A,B,C
--predict-targets PANEL.txt`. Non equivale a una promozione: direzione, ampiezza,
fallback e generatore devono essere valutati insieme prima di un invio. Le maschere
degli export distinguono geni non modellati da previsione nulla per assenza di fonte.
