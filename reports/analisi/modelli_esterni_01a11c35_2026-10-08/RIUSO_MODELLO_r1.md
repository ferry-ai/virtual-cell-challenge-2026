# Riuso del modello congelato e recupero sicuro

**Implementato e verificato su fixture; nessun modello biologico concluso al
momento della scrittura.** `predict_saved_ridge.py` ricostruisce l'inferenza dal
modello salvato, senza fit, nuove medie o calibrazione sulle query.

Input: cartella `fit` prodotta dal runner (`ridge.npz`, `manifest.json`), stessa
revisione ESM2 e JSON con lista di oggetti `target`, `context_id`, `context_group`.
Si verificano SHA del modello e delle feature, policy e vincoli C/T/J. Le query
protette e duplicate sono rifiutate. `target_only` è il nome convenzionale delle
query di produzione, non l'identità di un contesto biologico.

```powershell
.\scripts\py.cmd reports/analisi/modelli_esterni_01a11c35_2026-10-08/predict_saved_ridge.py --fit <cartella-fit> --esm2 <asset-esm2-fissato> --queries <query.json> --out <nuovo-output.npz>
```

L'output conserva effetti nativi, maschera osservata, disponibilità ESM2 e generico
separato. `receipt.json` indica hash degli input/output e assenza di rifit.
Nessun gain, cis o fattore dell'emissione aggiunto. Le query senza feature restano
NaN/maschera falsa nel ramo specifico. `reload_tests_r1.txt` verifica sul percorso
completo T della fixture che l'inferenza ricaricata coincida esattamente con quella
salvata dal fit. Il comando non costituisce ammissione allo stadio 100.

`collect_cloud_fit.py` recupera solo una whitelist di ricevute, modello e predizioni
da un job terminale privato df11, in una directory nuova **fuori dal repository**.
Sono esclusi HTML, notebook, source, bundle e locator. Non usare il comando Kaggle
di recupero generale sui job di questo esperimento. I metadati dei consumi saranno
verificati da DATI-TRANSFER; il modello e gli array vanno anche ricontrollati per
hash dopo il trasferimento. Nessun punteggio si deduce da un recupero riuscito.
