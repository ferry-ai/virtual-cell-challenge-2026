# Lettura riproducibile della conferma generatore

29 settembre 2026. **Implementato e verificato con soli report sintetici. Nessun
risultato reale, completo o parziale, della conferma è stato letto per preparare
questo codice.** Non contiene conclusioni sul modello.

L'analizzatore non importa lo scorer, il generatore, Torch o dati cellulari. Legge
soltanto JSON/CSV piccoli, al massimo 2 MB ciascuno. Non esegue nuovi esperimenti,
non modifica le predizioni e non propone altri finalisti.

## Quando eseguirlo

Solo dopo l'arrivo del `selection.json` completo, che il banco scrive per ultimo.
Se manca, lo script si ferma **prima di aprire qualunque report parziale**. Servono
anche `bench.json`, `run_manifest.json` e, per riferimento e ciascun finalista,
i tre semi completi di `result_*`, `per_pert_*`, `components_*`, `diagnostics_*`.
Può leggere gli originali oppure una copia locale con gli stessi byte.

Esempio PowerShell da adattare alle directory complete, senza eseguirlo durante il run:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/confirmation_analysis/analyze_confirmation.py `
  --run-dir PERCORSO_CONFERMA_COMPLETA `
  --target-manifest PERCORSO_TARGET_MANIFEST_JSON `
  --development-selection reports/analisi/lead_scientist_2026-09-29/generator_development_r3/development/selection.json `
  --anchors reports/gara/anchors_2026-09-17/anchors.json `
  --out NUOVA_DIRECTORY_ANALISI
```

Non ci sono opzioni per cambiare soglie, semi, numero di bersagli o bootstrap.
La directory di output deve essere nuova. Prima di crearla, tutti i file letti
vengono riletti per verificare che non siano cambiati durante l'analisi.

## Regola che viene ricostruita, senza modificarla

Fonte: `../PROTOCOLLO_GENERATORE.md` e gli emendamenti 01 e 02. I soli candidati
ammessi sono la shortlist dello sviluppo completo più il riferimento pooled 1/0.
La conferma deve avere **96 bersagli disgiunti**, tutta la verità, **semi 1/2/3**,
2.000 controlli e 400 cellule predette. Lo script verifica il manifest congelato,
gli hash delle ancore e del codice generatore, e che ogni CSV contenga tutti i target.

La proiezione usa cinque variazioni moltiplicate per le pendenze delle ancore e
divise per sei. Ogni membro mantiene la propria popolazione eleggibile, invariata
fra bracci e semi. La MSE resta separata e viene verificata come **rapporto di somme**.

Promozione locale preregistrata: delta medio almeno **0,005**, positivo in ciascuno
dei tre semi, limite inferiore bootstrap sopra zero. Sono **2.000** estrazioni
appaiate di bersagli con seed **20260929**, comuni a tutti i membri e semi; intervallo
bilaterale **97,5%** con due finalisti, 95% con uno. Non vengono ricampionati i semi.
La deviazione standard dei tre delta viene riportata separatamente.

Lo script confronta i propri numeri e il booleano finale con `selection.json`.
Qualunque differenza oltre la tolleranza numerica produce un errore, non una
decisione alternativa. Il bootstrap viene calcolato due volte: prima indicizzando
i bersagli estratti, poi moltiplicando per una matrice delle loro frequenze. I due
calcoli devono coincidere. Questo è il **bootstrap preregistrato locale**, non una
procedura ufficiale del servizio VCC.

## Derivati descrittivi, esclusi dalla regola di promozione

- `raw_by_seed.csv`: sei grezzi per braccio/seme, numero di chiamate e accordi.
- `target_by_seed.csv`: contributi appaiati di ogni bersaglio per i tre semi,
  `n_conf`, `n_pred`, `k` e i rispettivi valori del riferimento.
- `target_contributions.csv`: media sui tre semi dei contributi additivi al delta
  della proiezione, cellule reali, `n_conf`; contributo MSE indicato separatamente.
- `n_conf_subgroups.csv`: strati fissati ora **0, 1–9, 10–99, 100–499, 500–1999,
  ≥2000**. Per ogni membro riporta numero eleggibile, contributo alla proiezione
  dell'intero pannello e media condizionata allo strato quando definita.
- `registered_bootstrap_draws.csv`: i 2.000 delta per finalista per poter verificare
  direttamente quantili e distribuzione della procedura registrata.
- `analysis.json`: ricostruzione e controllo della decisione, top/bottom cinque,
  quota netta dei primi cinque quando il delta è positivo, concentrazione assoluta,
  sensibilità ricalcolata togliendo i primi 1/3/5 bersagli, hash degli input e script.

Il contributo del bersaglio t è la somma, sui membri m, di
`media_semi(delta_tm * pendenza_m / 6) / N_eleggibili_m`.
I contributi sommano al delta totale. Non si mediano ingenuamente cinque membri
per bersaglio: così si darebbe un peso diverso ai target non eleggibili per NMAE o
reach. Anche dopo le esclusioni descrittive i denominatori vengono ricalcolati;
se uno diventa vuoto, il diagnostico è nullo e non produce un verdetto.

Le analisi degli strati e dei primi cinque non hanno intervalli usati per promozione,
non selezionano nuovi target e non cambiano i candidati. Il bootstrap sui bersagli
non misura l'incertezza dovuta a controlli, cellule reali, contesto o generazione
oltre i tre semi osservati. Nessuna uscita è un punteggio VCC o autorizza un invio.

## Verifica eseguita

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/confirmation_analysis/test_analysis.py
```

**8 test PASS, 3,319 secondi** nel runner unittest. Input interamente sintetici,
in directory temporanee. Coprono denominatori diversi, pairing e variabilità dei
semi, intervallo Bonferroni, bordi delle soglie, variazioni di eleggibilità,
bootstrap senza osservazioni eleggibili, rifiuto dei report parziali prima della
lettura, percorso completo 96 target × 3 bracci × 3 semi, mancato overwrite,
decisione registrata alterata e perdita di un bersaglio nei CSV.
