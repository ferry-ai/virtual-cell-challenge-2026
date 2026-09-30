# Intersezione esatta con il banco storico e cronologia della conoscenza

29 settembre 2026, precisazione successiva a `SCORE_BIAS_DATI.md`, su richiesta
del lead. **Misurato sulle liste di target, senza usare valori delle metriche.**
Questa nota rende precisa la precedente affermazione sul riuso della truth e
corregge la data: «26 settembre» nel nome della cartella indica la preparazione;
il job storico terminò **27 settembre 2026, 16:16:43 UTC**.

| Insieme del banco odierno | Dimensione | Già valutati nei file storici | Non presenti in quei file |
|---|---:|---:|---|
| Development | 48 | 48 | Nessuno |
| Confirmation | 96 | **95** | RPS15 |
| Universo eleggibile | 274 | 273 | RPS15 |

Non è un'inferenza dal fatto di usare lo stesso studio. La lista di 299 target
di `bench.json` coincide esattamente con la colonna `perturbation` di **tutti
gli undici file `per_pert*.csv`**: dieci bracci e la replica. Ognuno contiene
i medesimi 95 dei 96 target odierni di conferma. I bracci storici comprendono
t16like a ampiezza 0/0,5/1/2, t19like a 0,5/1/2 e tre aggiunte cis. Questa
verifica non legge né confronta i loro valori numerici.

Prova riproducibile: [`historical_overlap.json`](score_bias_dati_r1/historical_overlap.json),
con lista dei 96, intersezioni per ciascun file e SHA, da
[`audit_historical_target_overlap.py`](audit_historical_target_overlap.py).
Manifest storico SHA256
`b39196b3d05383fef1ad0435764c998c6588c66ac502f1cb9ae97c880929f46c`;
manifest odierno SHA256
`7b7459ca86d0bef53d4a53f3b7bcae983189a44f623deb2510d7ed33da07d79f`.

Il codice odierno `generator_bench.select_targets` sceglie lo sviluppo e i
successivi 96 dalla stessa permutazione degli eleggibili. Non carica una lista
dei target valutati storicamente e non li esclude. Il protocollo e i due
emendamenti garantiscono separazione **dalla scelta della griglia odierna**;
non registrano l'assenza di valutazioni precedenti. Le cellule usate oggi sono
tutte quelle disponibili, mentre il banco storico divideva ciascun target
in due metà: non sono due studi né una nuova raccolta sperimentale.

**Limite della ricostruzione:** i file attestano esecuzione precedente e
disponibilità di risultati su quei target; non attestano quali numeri il lead
abbia effettivamente letto prima di scegliere i 14 bracci. La documentazione
odierna cita effetti t19like congelati e le precedenti prove t13/t14; l'emendamento
02 attribuisce l'aggiunta dei bins all'analisi dei soli controlli. Non ho trovato
nei manifest una prova sufficiente per attribuire al lead la lettura di tutti
gli outcome storici target per target. Qualunque affermazione più specifica
sulla conoscenza del lead deve citare la cronologia della sessione.

La formulazione sostenuta è quindi: **conferma interna della selezione odierna,
su 95/96 bersagli già valutati in un banco precedente**. Non «96 bersagli mai
visti». Questo espone un possibile bias adattivo fra esperimenti; non dimostra
da solo fitting del predittore sulle risposte di conferma o manipolazione della
griglia odierna. Gli intervalli restano condizionali al banco e alla procedura
registrata, senza incorporare l'intera storia della ricerca.
