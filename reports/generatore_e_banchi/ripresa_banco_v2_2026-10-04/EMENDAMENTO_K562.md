# Riparazione tecnica K562, prima di qualsiasi suo scoring

Il preflight remoto r1 passa; l'esportatore si arresta su `prod` dopo 30 secondi,
prima di chiamare il banco: alcuni target non hanno geni osservati nella baseline di
produzione. La guardia nuova trattava questo caso come input corrotto, diversamente
dal banco archiviato. Non è un risultato negativo del modello.

La r2 conserva ogni target, effetto, maschera, seme e regola di lettura. Ammette righe
interamente non osservate soltanto nei bracci `prod` e `prod_wR`, e soltanto se anche
la corrispondente baseline `prod` non ha osservazioni. Il generatore usa in entrambi
i casi il medesimo profilo basale, come prima. Le righe sono nominate nel manifest.
Qualunque riga vuota di `all` o incoerenza di maschera resta un errore.
R1 e log conservati; output e slug r2 distinti, nessun cambiamento agli altri quattro job.
