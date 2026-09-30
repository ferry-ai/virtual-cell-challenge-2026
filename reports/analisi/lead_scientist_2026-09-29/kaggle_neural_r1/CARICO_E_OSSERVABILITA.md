# Carico previsto e limiti dell'osservazione remota

**Misurato sui metadati, non sul training remoto.** `static_work_r1.json`, prodotto
da `quantify_neural_work.py`, conta il lavoro del codice congelato senza leggere
gli effetti: solo CSV, manifest e indice di target per riga. Sono 12 contesti CRISPRi,
13.248 geni e 6.144 target valutati, 512 per contesto, nei cinque fold.

- 20 fit: 10 con scelta dei passi mediante validazione interna, 10 refit. Il limite
  superiore complessivo è 20.000 passi di training; arresto anticipato e passi
  selezionati possono ridurli.
- Fino a 8.064 batch forward per la validazione interna, inclusa la valutazione a
  passo zero. Il limite deriva da 21 controlli per fit e dai contesti realmente
  assegnati alla famiglia interna: Orion, K562, K562, Orion, Orion nei cinque fold.
- 24.960 batch forward di test: 5 bracci × 12 contesti × 32 blocchi di target ×
  13 blocchi di geni. Quattro bracci usano la rete; transfer salta la rete ma
  ricostruisce ugualmente gli input. Il braccio nullo non richiede un forward.
- Nei test, 3.727.360 chiamate a `_profile` ricostruiscono profili sorgente con
  letture NumPy/mmap e cicli Python. Ogni profilo usa una riga diretta oppure fino
  a otto partner disponibili. I cinque bracci ricostruiscono questi input.
- I soli tensori di 20 feature del test sommano 303.877.324.800 byte float32
  costruiti/trasferiti lungo l'intera corsa, **non residenti insieme**; il massimo
  singolo tensore previsto è 14.417.920 byte. La centratura dei contesti comporta
  34.525.135.872 byte sorgente float16 complessivi nei cinque fold, grazie al riuso
  della cache fra selezione e refit. Metriche, label, intermedi e compressione NPZ
  sono lavoro aggiuntivo.

**Interpretazione:** una piccola rete non implica un job breve: preparazione CPU
degli input, letture, ricostruzione ripetuta e valutazione estesa sono candidati
concreti a spiegare il carico. Senza profiling non è misurato quale passaggio
domini il tempo. Questi conteggi non stimano durata o completamento.

**Misurato sul servizio, 19:16 UTC del 29 settembre:** `session_latest_r2.json`
riporta `RUNNING`, `failureMessage: null`, versione 1, privato, GPU T4 e dataset
atteso. La lista file è ancora vuota. Il pull precedente in
`pull_comparison_r1.json` aveva confermato codice, payload e cinque hash uguali
al notebook approvato. Il campo metadata `last_run_time` rimane incoerente con
la data del push e non viene usato come prova dell'ora di avvio.

La SDK installata espone nel servizio di stato soltanto status/failure_message;
non espone in questa risposta PID, session ID, step o fold. I file di output possono
apparire solo alla pubblicazione finale. Quindi **RUNNING non prova avanzamento
di un fold o attività GPU corrente**. Si conservano tempo trascorso dalla conferma
del push, metadata e cambiamenti di stato, con controlli distanziati. Nessun
riavvio, stream dei log già fallito o endpoint inventato viene usato per colmare
questa assenza di visibilità.
