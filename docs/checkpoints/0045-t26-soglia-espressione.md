# CP-0045 — Il t26 in classifica: +0,1387, non conclusivo; togliere gli effetti sui geni poco espressi non alza il PDS, quindi il guadagno del t23 veniva dai geni espressi

- **Data:** 2026-09-29
- **Tipo:** esperimento
- **Redatto da:** Claude (Opus 5.5, sessione f2abd9a6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il guadagno di PDS del t23 ([CP-0042](0042-t23-esclusione-pds.md)) veniva dai geni poco espressi che il t23 azzerava?
Se sì, azzerare gli effetti sui geni sotto 5 CPM nei controlli del contesto (il t26) avrebbe dovuto alzare il PDS
senza perdere i membri DE. È una regola calcolabile dai soli controlli, quindi valida anche per D/E/F.

## 2. Cosa è stato fatto

- **Stadio 100:** un blocco nuovo `expression_gate`, con test e confronto prima/dopo identico bit per bit sul t25.
- **Ricetta** `configs/recipes/t26.json`: il t25 più la soglia a 5 CPM, un solo fattore.
- **Registrato prima della generazione:** previsione e regola alle 12:24 UTC del 29/09
  ([prediction.json](../../reports/invii/prediction_t26_2026-09-29/prediction.json)); testi in
  [trial_2026-09-29](../../reports/invii/trial_2026-09-29/submission_texts.md). Commit `586fbc3`.
- **Generato e impacchettato** da una copia del codice di `586fbc3`, a forma piena, seme 20260912: stadi 45 e 48,
  archivio sha256 `e359a4ba…`.
- **Invio** con il via del proprietario ([autorizzazioni](../../reports/invii/trial_2026-09-22/autorizzazioni.md)):
  - il primo tentativo, alle 13:48 UTC, l'ha fermato il sistema per memoria scarsa mentre la sessione era ferma al
    limite d'uso; l'entry è rimasta in `uploading`;
  - il secondo l'ha rifiutato il lucchetto rimasto nella CLI;
  - il terzo ha ripreso lo stesso upload alle 15:19 UTC, con un processo Windows separato, pubblicato alle 15:39.

  Tutti gli output in `trial_2026-09-29/` (`submit_t26_*`, `submit_t26_resume_*`, `submit_t26_resume2_*`, due file di
  stato).
- **Letto con la regola:** [comparison.json](../../reports/invii/prediction_t26_2026-09-29/comparison.json).

## 3. Cosa si è osservato

- **Media:** +0,138721, rango 384. Sta nella banda registrata (+0,134…+0,156).
- **Rispetto ai riferimenti:**
  - t26 − t25 = −0,0015, dentro la banda della differenza;
  - contro la media t22/t24, −0,0034; contro il t23, −0,0031.
- **La soglia:** azzera 8.604, 8.907 e 8.409 geni per contesto, con il 71,8 %, 70,8 % e 67,2 % dell'energia prevista
  (manifest dello stadio 100).
- **Membri grezzi, t26 − t25** (fra parentesi t23 − t22 e il solo seme, t24 − t22):
  - `pds_cosine` −0,0020 (+0,0109; +0,0009);
  - `nmae` +0,0007 (+0,0099; −0,0020);
  - `reach` −0,0055 (−0,0085; +0,0052);
  - fedeltà +0,0005 (+0,0031; −0,0006);
  - Jaccard +0,0001 (−0,0018; +0,0000);
  - `mse` grezza −0,055, scalato 0.

## 4. Interpretazione e incertezza

- **Per la regola:** non conclusivo. La soglia non entra nel riferimento né nella pipeline per D/E/F.
- **L'ipotesi registrata non regge.** Togliere il 70 % circa dell'energia prevista, quella sui geni poco espressi,
  lascia i membri quasi fermi, e il PDS scende appena invece di salire come nel t23.
- **Interpretazione, non verificata:** il guadagno di PDS del t23 veniva da quello che il t23 faceva ai geni espressi:
  la pesatura e l'esclusione dei geni che meno di due universi stimano, e la riscalatura ×1,4 che riportava i geni
  rilevabili a quelli del t22. L'energia sui geni poco espressi pesa poco sul punteggio, in un verso o nell'altro.
- **Incertezza:** l'unità di rumore del seme resta una coppia sola; −0,0020 di PDS è circa due volte quella coppia.

## 5. Spiegazione semplice

Si pensava che il t23 fosse migliorato nel riconoscere i knockdown perché aveva tolto «rumore» sui geni che la cellula
quasi non esprime. Il t26 ha tolto solo quello, e non è migliorato: quel rumore non pesava. Il merito del t23 va
cercato sui geni che la cellula esprime.

## 6. Conseguenze

- **Resta il riferimento** della ricetta del t22/t25.
- **La prossima domanda,** da registrare con la sua regola prima di generare, è sui geni espressi. Per esempio, il t25
  con la sola esclusione dei geni espressi (≥ 5 CPM) che meno di due universi stimano, oppure la pesatura del t23
  limitata ai geni espressi, con e senza riscalatura. È anche la parte che il banco con lo scorer vero (azione 4 di
  R-REV) vede.
- **Invii:** un upload fermato lascia l'entry in `uploading` e un lucchetto nella CLI. Da qui l'invio gira come processo
  Windows separato, che il sistema non ferma quando la sessione è inattiva (procedura da aggiungere a LAVORO §2,
  regola 5).

## 7. Cosa corregge

Smentisce l'ipotesi scritta nella registrazione del t26 e nel §6 di [CP-0042](0042-t23-esclusione-pds.md): «tenere
l'esclusione (il guadagno di PDS) e recuperare i membri DE». Quel guadagno non viene dalla parte dell'esclusione che
tocca i geni poco espressi. CP-0042 non si riscrive.

## 8. Domanda di comprensione

Perché un effetto grande su un gene che la cellula quasi non esprime cambia poco il punteggio?
