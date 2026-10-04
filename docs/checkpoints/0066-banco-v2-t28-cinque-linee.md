# CP-0066 — Banco v2 t28: Jurkat supera la regola su entrambe le baseline

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Codex, chat 01a107a9-9c9c-76c2-9161-258f22bd57b1
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-009

## 1. Domanda

Le cinque correzioni D-056 esistenti mantengono un guadagno risolto senza perdere
PDS con 400 cellule, cinque semi ed emissione t28, sulle due baseline?

## 2. Cosa è stato fatto

Cinque kernel Kaggle CPU autorizzati dal proprietario, quattro bracci per linea.
Protocollo congelato a `55ae28b`; K562 r2 ripara una guardia tecnica prima dello
scoring, emendamento `9cad688`. Reti e verità congelate, casualità condivisa per
bersaglio. [Protocollo](../../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/PROTOCOLLO.md).

## 3. Cosa si è osservato

Tutti i kernel e le verifiche passano. La regola richiede guadagno risolto positivo
sui sei membri e senza Jaccard, senza perdita risolta di PDS; risolto significa
`abs(media) > 2 * sd / sqrt(5)`.

- Baseline all: passano H1, RPE1, Jurkat e K562; HepG2 perde PDS.
- Baseline prod: passa solo Jurkat. H1 e K562 non risolvono il guadagno;
  HepG2 perde PDS; RPE1 non risolve il guadagno e perde PDS.
- Media fra linee: +0,013057 su all, +0,020458 su prod, in scala locale.
- HepG2 PDS: −0,12111 all, −0,12533 prod. RPE1: +0,06162 all, −0,07014 prod.

[Esito e limiti](../../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/ESITO_BANCO_V2.md),
[valori e verifiche](../../reports/generatore_e_banchi/ripresa_banco_v2_2026-10-04/decisione_r1.json).

## 4. Interpretazione e incertezza

Il beneficio dipende dalla baseline; la media non basta a proteggere il PDS.
Rumore solo del generatore, con cinque linee già usate per sviluppo e un corpus
pilot a otto gruppi. Non è una conferma indipendente né un punteggio VCC.
R resta appresa contro all: applicarla a prod non equivale a riaddestrare su prod.

## 5. Spiegazione semplice

La correzione può migliorare la media e insieme distinguere peggio le perturbazioni.
Jurkat supera entrambi i controlli su entrambe le basi; questo non prova ancora
che sia il fold migliore da inviare su cellule nuove.

## 6. Conseguenze

Banco autorizzato concluso; nessun fold promosso e nessun invio. Per il prossimo
training mantenere baseline coerente fra fit ed esportazione e guardia PDS per
linea. Ingestione CD4 12/12 verificata, integrazione e copertura effettiva D-053 aperte.

## 7. Cosa corregge

Nessun checkpoint precedente: CP-0065 misura un banco diverso. La differenza
non isola t28 perché cambia anche il flusso casuale. Aggiorna S-009 con un nuovo
contrasto diagnostico; la causa dei risultati sul sito rimane non isolata.

## 8. Domanda di comprensione

Perché una media positiva su cinque linee non basta se il PDS di alcune linee cala?
