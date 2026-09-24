# CP-0034 — Audit dei segni, del confronto t17 e della preparazione al set finale

- **Data:** 2026-09-24
- **Tipo:** osservazione
- **Redatto da:** Codex
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali interpretazioni dello stato attuale non sono identificate dai dati, e quali
controlli servono prima di complicare il modello o passare a D/E/F?

## 2. Cosa è stato fatto

Lettura degli artefatti ufficiali e del codice vivo; audit riproducibile della cache r5:
`.\scripts\py.cmd reports\audit_stato_2026-09-24\audit.py`.
Il report `reports/audit_stato_2026-09-24/ANALISI.md` descrive metodo e limiti;
`measurements.json` nella stessa cartella contiene hash degli input e risultati per bersaglio.

## 3. Cosa si è osservato

**Misurato**, nel report e nel JSON citati:
- HCT116 γ=0: accordo medio del segno 56,60%, controllo a bersagli scambiati 53,85%,
  sempre aumento sugli stessi geni 63,58%.
- CD4 halfA → halfB, γ=0: accordo 57,23%, controllo 53,04%.
- t17 contro t15: q99 mediani 0,229116 e 0,229091, ma 22/300 bersagli cambiano q99
  di oltre il 20%; energia totale degli effetti +6,67%.
- `cd4_mix.se` interamente NaN; impossibile stratificare quella miscela per SE.
**Verificato nel codice:** stadi 45/76/98/100 usano ancora l'asse predefinito dei controlli A/B/C.

## 4. Interpretazione e incertezza

**Interpretazione:** il segno contiene informazione specifica, ma il confronto col 50%
non separa prevalenza, rumore e specificità. Il confronto t17 valuta una miscela con
compensazione globale, non l'effetto isolato della sorgente a tutte le scale.
**Limiti:** analisi esplorativa nello spazio degli effetti; gli SE non catturano tutta
la variabilità biologica; il confronto CD4 include differenze fra donatori. Nessun nuovo
punteggio ufficiale e nessuna dimostrazione di un tetto biologico.

## 5. Spiegazione semplice

Indovinare il 56% dei segni significa poco senza sapere quanto si indovina ignorando
il bersaglio. E due previsioni possono avere la stessa intensità media ma cambiare
molto per singolo bersaglio: entrambe le cose si osservano qui.

## 6. Conseguenze

Nessuna ricetta, preregistrazione o decisione modificata. Proposte nel report:
diagnostiche con controlli negativi e repliche; banco ampiezza × generatore;
asse genico esplicito lungo tutta la pipeline; affidabilità fra donatori/condizioni;
ablazioni di sorgenti e centratura. Nessun invio eseguito.

## 7. Cosa corregge

Precisa CP-0033 §5: una FID maggiore non dimostra da sola che la precisione dei segni
sia maggiore, perché FID = k / max(n_pred, n_conf). Precisa §6: una perdita del t16
non prova che l'ottimo sia compreso fra 0,394 e 0,788; provare il punto medio resta
una proposta sensata. Non corregge i punteggi o l'esito della regola del t15.
La lettura causale proposta per t17 va accompagnata da R-016 nel registro.

## 8. Domanda di comprensione

Se scambiando i bersagli l'accordo è già 54%, quale parte di un accordo del 56%
possiamo attribuire all'identità del bersaglio?
