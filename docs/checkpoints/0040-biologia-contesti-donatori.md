# CP-0040 — Programmi con segno, dipendenze di contesto e instabilita fra donatori: ricerca esplorativa

- **Data:** 2026-09-25
- **Tipo:** osservazione
- **Redatto da:** Codex
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali pattern biologici e limiti delle etichette giustificano nuove architetture,
oltre alla calibrazione di T18/T19? Come si riconciliano con il banco MSE appena
aggiunto da un'altra sessione?

## 2. Cosa è stato fatto

Rieseguite le analisi esplorative discusse in chat dopo autorizzazione alla
scrittura, senza modificare dati o ricette. Script, comando, supporti e limiti in
[RISULTATI](../../reports/biologia_architetture_2026-09-25/RISULTATI.md), §1.
L'esecuzione r1 registra gli hash degli input e le versioni in
[measurements.json](../../reports/biologia_architetture_2026-09-25/r1/measurements.json).
Tre agenti interni hanno contribuito alla ricerca; una revisione aggiuntiva ha
controllato il ragionamento MSE. Nessun training o nuovo dataset acquisito.

## 3. Cosa si è osservato

- **Misurato:** STAT2 su 3.688 geni comuni ai due stimoli e sei linee conserva
  Pearson 0,528–0,710 con IFNB contro −0,035–0,052 con IFNG; HT29 ha riduzione
  dell'RNA bersaglio quasi identica. Fonte:
  [matched_stimuli.csv](../../reports/biologia_architetture_2026-09-25/r1/matched_stimuli.csv).
- **Misurato:** USP18 ha profilo anticorrelato con STAT2 in tutte le sei linee
  IFNB (mediana −0,484), contro +0,827 per IFNAR2. Fonte:
  [signed_geometry.csv](../../reports/biologia_architetture_2026-09-25/r1/signed_geometry.csv).
- **Misurato:** il deficit MCF7/TNFA è concentrato su FADD/TRAF3/TRAF2;
  escludendoli il divario medio Δr scende in valore assoluto da 0,01758 a 0,00310.
  Fonte: [tnfa_mcf7.csv](../../reports/biologia_architetture_2026-09-25/r1/tnfa_mcf7.csv).
- **Misurato:** fra gruppi disgiunti di donatori CD4, segni opposti in
  33.775/96.688 coppie con z assoluto ≥ 2 in entrambi; Pearson mediana 0,0844
  sul supporto comune a cinque condizioni/gruppi. Fonte:
  [cd4_per_target.csv](../../reports/biologia_architetture_2026-09-25/r1/cd4_per_target.csv).

## 4. Interpretazione e incertezza

**Interpretazione:** programmi con ruoli opposti e interazioni circoscritte
meritano modelli strutturati; l'SE entro sorgente non certifica trasferibilità.
**Limiti:** casi scelti a posteriori, sorgenti condivise, filtro sui due effetti,
numerosità e donatori non separati. Non sono switch causali, errori sull'intero
trascrittoma o un test J. La restrizione migliora modestamente il confronto fra
donatori sul suo supporto; non viene scartata.

## 5. Spiegazione semplice

Due geni della stessa via possono fare da acceleratore e freno. Una previsione
deve distinguere il ruolo e lo stato della cellula. Prima di imparare queste
differenze, però, deve sapere quanto le risposte si ripetono in altri donatori:
un numero preciso dentro un gruppo può trasferirsi male a un altro.

## 6. Conseguenze

Nessuna decisione di produzione cambia. Proposte di programmi gerarchici,
grafi con segno e generatori con quota di rispondenti in
[PROPOSTE](../../reports/biologia_architetture_2026-09-25/PROPOSTE.md).
Rimandi aggiunti a R-DATI, R-MODELLI e R-SWITCH; protocollo e training restano
aperti. Jost GSE132080 è candidato per dose–risposta, non dato adottato.

## 7. Cosa corregge

Nessun checkpoint precedente viene superato. Si restringono interpretazioni
troppo generali della chat su reti, switch e confidenza. Per
[MSE.md](../../reports/banco_varianti_2026-09-25/MSE.md), la nuova scheda R-018
in [REGISTRO](../REGISTRO.md) segnala come non dimostrata l'estensione del proxy
a MSE ufficiale zero per ogni ampiezza e alla sua causa esclusiva. Numeri r10 e
report originali restano conservati. La correzione riguarda l'inferenza,
non una smentita tramite nuovo punteggio ufficiale.

## 8. Domanda di comprensione

Perché il 34,93% di segni opposti fra gruppi CD4 non prova che il donatore
determini il segno biologico, e perché non basta scegliere effetti con SE piccolo?
