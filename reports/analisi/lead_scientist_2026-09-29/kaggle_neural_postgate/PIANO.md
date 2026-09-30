# Seed 1 e produzione: preparazione condizionale

**Preparato, non eseguito.** Il job originale `vcc-lead-neural-sources-r1` continua.
Nessun suo file o metadata viene modificato. Sono riservati soltanto nel piano due
nuovi slug, assenti dall'inventario dell'account: `vcc-lead-neural-seed1-r1` e
`vcc-lead-neural-production-r1`, privati sullo stesso account davidmaisterx.

`plan_r1/` congela 38 file, SHA256 dell'archivio
`baa60909f4ab98ca5c41f6f6f1bf784d1f06e8e316b4b2f8f71f8d8493079ee2`.
Training, architettura, protocollo e Pool sono estratti byte per byte dal payload r1
originale. Il lettore è la sola correzione documentata `keep_default_na=False`, con
originale conservato, wrapper e guardia di provenienza. Si aggiungono l'adapter
congelato con i suoi 8 test già misurati, la documentazione e le dipendenze `src` dal
codice r3. I 300 nomi di target sono derivati dal CSV ufficiale, con hash della fonte;
non si caricano nuovi grandi dataset né credenziali.

Il dataset rimane il privato `davidmaisterx/vcc-rete-contesti-r2`, con SHA256 del
manifest `2e59376b103dc6578b9a52e3c37c655207567ecc0375481bc5e3560e7fb8b32a`.
Gli array vengono aperti mmap in sola lettura; Internet nel notebook resta spento.

## Condizione che precede la creazione del notebook

`build_neural_postgate.py --freeze-plan` ha creato soltanto piano e archivio. Non ha
creato alcun `.ipynb`. Per costruire i notebook, il comando richiede `--frozen-plan`,
cinque directory complete con `--seed0-runs`, e un nuovo `--out`. Ricontrolla codice,
identità r2, split, copertura e presenza di summary; poi ricalcola la lettura con il
reader corretto. Non accetta un verdetto JSON fornito senza i cinque fold sottostanti.

La soglia rimane quella iniziale: regime C e seed 0, incremento di rango medio per
famiglia almeno 0,01, limite inferiore del bootstrap sopra zero, nessuna famiglia
sotto −0,01. Il gate incorpora hash completi dei manifest, per_target e summary e
viene ricontrollato dal runtime. Un risultato parziale o negativo non produce
notebook pronto per il push. Il push richiede comunque la revisione della lead.

## Le due corse preparate

- **Replica seed 1:** stessi cinque fold e tutte le opzioni r1 salvo seed; processi
  separati e tutti tentati anche dopo un errore. Lettura solo se completano tutti.
  Usa la guardia di provenienza e il reader corretto, conserva il confronto completo
  fra i due semi. Il proxy non diventa uno score VCC.
- **Produzione seed 0:** `--holdout none --regime C` sul medesimo r2, stessa scelta
  dei passi interna e nessun cambiamento alla rete. Conserva checkpoint e manifest;
  l'adapter esporta `factors_A/B/C.npz` per i 300 target. Non applica qui i fattori
  alla ricetta t25: cache r9, coordinate cis e t25 originali restano input locali
  per l'apply separato. L'adattatore non eredita un vantaggio cellulare del proxy.

Entrambe usano GPU0 della risorsa gratuita T4. Non è stata richiesta una nuova GPU.
La quota letta prima del freeze era 8,14 ore GPU residue su 30, reset 3 ottobre;
la API di quota non espone il numero di slot contemporanei liberi. La documentazione
Kaggle descrive sessioni batch concorrenti e il riuso di input dei notebook, ma qui
non si promette un preciso limite corrente senza averlo osservato. Il dataset è già
accessibile allo stesso account e non richiede inviti o nuovi token.
[Documentazione notebook](https://www.kaggle.com/docs/notebooks) e
[uso GPU](https://www.kaggle.com/docs/efficient-gpu-usage).

Il freeze e i test del gate sono preparazione software, non training completato,
conferma dell'ipotesi o autorizzazione a inviare una submission.
