# Oracolo numerico

Prototipo indipendente dall'orchestratore multiagente e da `vcc2026`.
Verifica un'affermazione numerica ricalcolandola da un CSV. Non valuta
ipotesi biologiche e non chiama modelli. Versione 0.2.1: calcolo e
confronti su `fractions.Fraction`; le stringhe decimali del report
sono solo visualizzazione. I campi numerici del JSON sono numeri,
non stringhe; un `csv.Error` del parser è un esito `error`.

Contratto, formule, segno della differenza e mappatura degli esiti:
[`docs/oracle/CONTRATTO.md`](../../docs/oracle/CONTRATTO.md).

```
.\scripts\py.cmd -m oracle --csv percorso.csv --candidate affermazione.json --config soglie.json --report report.json --summary riepilogo.txt
```

Codici di uscita: `0` pass, `1` fail, `2` unverified, `3` error.
La CLI non sovrascrive un file di uscita già esistente, salvo `--force`.
