# CP-0009 — Oracolo 0.2.1: numeri JSON e csv.Error

- **Data:** 2026-09-13
- **Tipo:** correzione
- **Redatto da:** agente (Grok 4.6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

I due problemi residui della 0.2.0 — stringhe JSON accettate come
numeri, e `csv.Error` non intercettato su un campo oltre il limite
del parser — restano dopo le tre correzioni di
[CP-0008](0008-oracle-fraction-regression.md)?

## 2. Cosa è stato fatto

Contratto e verificatore portati a 0.2.1. Formule, soglie e
confronti esatti invariati. Tipo dedicato `JsonNumber` per i token
numerici JSON, senza conversione in float: i campi numerici
accettano quel tipo e rifiutano le stringhe, anche se il contenuto
è un decimale. La stessa distinzione vale per la configurazione
dell'operatore. I limiti di dimensione restano applicati prima di
costruire la `Fraction`. `csv.Error` intercettato in lettura
dell'intestazione e in iterazione; il limite interno del parser
non è stato alzato. Nessuna modifica a `src/orchestrator/`. Il
report `reports/oracle/example_pass.json` della 0.1.0 non è stato
sovrascritto.

Due input della revisione, usati così com'erano:

```
{"mean_loss_a": "0.2", "mean_loss_b": "0.3", "mean_difference": "-0.1", "conclusion": "A_lower"}
```

```
campo CSV di 140.000 caratteri (oltre `csv.field_size_limit` = 131072)
```

```
.\scripts\py.cmd -m unittest tests.test_oracle_pairwise_loss -v
```

## 3. Cosa si è osservato

**Misura, 0.2.0, prima della correzione, in questa sessione.** Non
è stato salvato un report: l'osservazione è della sessione sul
codice 0.2.0.

- candidato con medie in stringa (`"0.2"`, `"0.3"`, `"-0.1"`) →
  `candidate_readable` in `pass`, esito complessivo `pass`.
- configurazione con `"abs_tol": "1e-12"` → `operator_config` in
  `pass`.
- campo dati o intestazione di 140.000 caratteri → eccezione
  `_csv.Error: field larger than field limit (131072)`, non un
  esito `error`.

**Misura, 0.2.1.** `tests.test_oracle_pairwise_loss`: 43 test,
tutti ok, 0,400 s. I tre test `ReviewRegression` di CP-0008
restano verdi. Nove test nuovi coprono i due difetti.

- numeri JSON, anche `3.0e-1` / `3.5e-1` / `-5.0e-2` →
  `candidate_readable` in `pass`; i valori dichiarati coincidono
  con `3/10`, `7/20`, `-1/20` calcolati a mano.
- stringhe numeriche nel candidato → `candidate_readable` in
  `error`, esito complessivo `error`.
- stringhe numeriche nella configurazione → `operator_config` in
  `error`, nessun ricalcolo.
- `true` / `false` → errore di tipo (`bool`); `NaN`, `Infinity`,
  `-Infinity` → `valore non finito`.
- campo troppo lungo in intestazione o nei dati → `csv_readable`
  in `error`, esito complessivo `error`, nessun ricalcolo.
- CLI sul campo troppo lungo: report JSON strutturato, riepilogo
  `Esito complessivo: ERROR`, codice di uscita 3, nessuno
  `Traceback` su stdout o stderr.

**Non misurato.** Loss reali della gara. Chiamata dall'orchestratore.

## 4. Interpretazione e incertezza

**Interpretazione.** `parse_float=str` e `parse_int=str` rendevano
indistinguibili un numero JSON e una stringa con le stesse cifre.
Il contratto chiedeva numeri; il parser li appiattiva a testo.
L'eccezione `_csv.Error` avveniva nel parser, prima del controllo
sugli 80 caratteri, e usciva dal verificatore.

**Non segue.** Che ogni eccezione del runtime sia coperta: si
intercetta `csv.Error` in due punti, non ogni allocazione. I
limiti di dimensione restano sui token, non sul parser CSV.

## 5. Spiegazione semplice

Prima `"0.2"` tra virgolette e `0.2` senza virgolette erano la
stessa cosa per l'oracolo, e un campo CSV enorme faceva cadere il
programma invece di produrre un esito `error`. Ora i numeri JSON
restano numeri, le stringhe restano stringhe, e un CSV che il
parser non riesce a leggere è un errore strutturato, con codice 3.

## 6. Conseguenze

Il verificatore è 0.2.1. D-020 resta: l'oracolo è autonomo e il
candidato non è fidato. Formule, soglie e confronti esatti non
cambiano.

## 7. Cosa corregge

I due difetti residui della 0.2.0, non coperti dai 34 test di
[CP-0008](0008-oracle-fraction-regression.md). CP-0008 non si
riscrive: le sue tre regressioni (terzi esatti, intestazioni
duplicate, esponente enorme) restano vere. Il report
`reports/oracle/example_pass.json` documenta ancora la 0.1.0.

## 8. Domanda di comprensione

Perché `"0.2"` tra virgolette deve essere un `error` anche se, da
stringa, si potrebbe costruire la stessa frazione di `0.2`?
