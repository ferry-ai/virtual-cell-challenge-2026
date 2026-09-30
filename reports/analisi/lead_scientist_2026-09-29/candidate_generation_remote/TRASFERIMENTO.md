# Effetti t25 disponibili sul mount Drive

**Misurato il 29 settembre 2026, 18:31 UTC.** Dopo l'autorizzazione della sessione
principale, i soli tre NPZ e il manifest t25 sono stati copiati nella nuova cartella
`G:/Il mio Drive/vcc2026/data/processed/effects_t25_2026-09-27`.

Totale 52.892.600 byte; ogni SHA256 completo è identico alla sorgente locale e al
manifest congelato. Nessun file preesistente è stato sovrascritto. L'evidenza con
timestamp e hash è `transfer_manifest_r1.json`; lo script è `transfer_effects_t25.py`.
Il preflight r1 resta la fotografia precedente al trasferimento, quando i file
mancavano. Il launcher controlla comunque la presenza e gli hash sul runtime Colab.

La verifica è una rilettura dal mount Drive locale; la sincronizzazione visibile
nel runtime remoto sarà verificata dal preflight del job. Non è stata avviata alcuna
generazione, impacchettamento o submission.
