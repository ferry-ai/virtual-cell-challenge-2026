# Consegna verificabile al teammate — 1 ottobre 2026

Mandato: push dello stato versionato, brief e prompt per Claude sul clone del teammate.
Le istruzioni modificabili sono in [CONSEGNA_TEAMMATE](../../../docs/CONSEGNA_TEAMMATE.md)
e [PROMPT_CLAUDE_TEAMMATE](../../../docs/PROMPT_CLAUDE_TEAMMATE.md); questa cartella conserva
strumento e verifica sulla macchina di origine. Nessuna modifica del training corrente.

`preflight_handoff.py` è un inventario offline con libreria standard: Git, interprete,
pacchetti individuabili, input minimi, spazio e codice rispetto al commit dell'audit.
Usarlo con l'interprete del destinatario e una destinazione nuova:

```text
python reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py --data-root <radice_dati> --out <file_nuovo.json>
```

Un processo concluso conferma soltanto l'inventario. Import reali, round trip H5AD,
RAM/GPU, scorer e fixture CPU sono richiesti dal prompt e da `validate_runtime.py` del corpus.
Il preflight non legge H1 test, pesi o credenziali, e non verifica gli hash dei dataset.
Prima di pubblicare un manifest della propria macchina, controllarne le informazioni locali.

La prova sul computer di origine e gli esiti finali sono registrati in `VERIFICHE.md`.
