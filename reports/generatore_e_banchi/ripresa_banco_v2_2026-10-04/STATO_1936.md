# Stato osservato il 4 ottobre 2026, 19:36 CEST

**Misurato:** le ultime verifiche D4_Rest e D4_Stim8hr sono COMPLETE e hanno
`ok=true`, tutti i verdetti positivi, rilettura SHA degli shard e copertura delle righe.
La [riconciliazione](copertura_cd4_r2.json) comprende tutte le 12 unità previste:
33.610.471 righe originali = 21.980.517 cellule idonee + 11.629.954 escluse;
206.002.856.371 byte di shard verificati. Nessuna unità mancante.
Le ricevute nuove sono in `verifica_d4_rest_r1/` e `verifica_d4_stim8hr_r1/`.
Questa è la chiusura verificata dell'ingestione CD4, non del corpus D-053 completo
né della sua integrazione o dell'uso effettivo nel training.

**Banchi:** tutti e cinque ancora RUNNING, K562 nella revisione r2;
[lettura remota](stato_avanzamento_r1.json). Nessun nuovo punteggio letto.
Nessuna GPU usata. Restano validi protocollo, emendamento e prossimi passi dello
[stato precedente](STATO_1910.md), salvo le verifiche CD4 ora concluse.
Nessun monitor automatico installato, invio o push Git effettuato.
