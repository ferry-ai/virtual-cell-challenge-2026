# CP-0046 — Revisione lead: piattaforma CD4, compensazioni fra metriche e due vie neurali da verificare

- **Data:** 2026-09-29
- **Tipo:** cambio-di-strategia
- **Redatto da:** Codex, sessione 01a0ee03-b357-7012-81a9-e8d7de767478
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali conclusioni della storia del progetto sono sostenute, quali confondono fattori,
e quali esperimenti possono migliorare direzione biologica e generazione delle cellule?
Il proprietario ha chiesto esplicitamente una revisione critica e un modello neurale.

## 2. Cosa è stato fatto

Tre audit paralleli, ricostruzione dei punteggi da artefatti originali, lettura dei
metadati delle sorgenti e del codice dei vecchi modelli. Codice, hash e risultati:
`reports/analisi/lead_scientist_2026-09-29/`, in particolare `AUDIT_SCIENTIFICO.md`,
`AUDIT_DATI.md`, `AUDIT_GENERATORE.md` e `neural/AUDIT_BIOLOGICO.md`.

Sono preregistrati un banco con 14 candidati ampiezza × generazione e due vie neurali:
source-attention addestrata sui dati r2, e pilot del modello preaddestrato Stack con
prompt di cellule reali. Protocolli: `PROTOCOLLO_GENERATORE.md`, relativi due emendamenti,
`PROTOCOLLO_NEURALE.md` e `neural/PROTOCOLLO_STACK.md` nella stessa cartella.

## 3. Cosa si è osservato

- **Ricostruzione misurata:** nel confronto t23−t22 il 94,5% del movimento lordo dei
  membri si cancella nella media; l'ultimo raddoppio isolato t16−t15 guadagnava 0,03009.
  La coppia t22/t24 è una sola differenza fra semi, non una deviazione standard nota.
  Evidenza: `reports/analisi/lead_scientist_2026-09-29/audit_scientifico/r1/`.
- **Metadati verificati:** CD4 usa GEM-X Flex v1. Rest e Mix differiscono anche per
  cellule disponibili ed energia degli effetti; cambiare stato e mantenere la stessa
  ampiezza non isola soltanto il contesto. Evidenza: `AUDIT_DATI.md`, `cd4_r1/` e
  `dati_r1/` nella cartella dell'audit.
- **Codice verificato:** la vecchia rete fonde i profili entro famiglia e poi fra
  famiglie prima di apprendere la correzione. Il nuovo modello conserva i profili
  separati; i suoi sette prior non sono annotazioni GO/CORUM. Evidenza:
  `neural/AUDIT_BIOLOGICO.md`, `neural/metadata_r3.json`, `PROTOCOLLO_NEURALE.md`.
- **Implementato e testato, non prova di guadagno:** opzioni di scala della dispersione
  e generazione condizionata sulla profondità. Parità degli output preesistenti e
  verifiche sintetiche in `VERIFICA_CODICE.md` e `generatore/default_parity_r1/`.
- **Esecuzione osservata:** Colab ha avviato il banco r3 il 29/09 alle 17:43:27 UTC,
  dopo due arresti tecnici prima di ottenere metriche. Kaggle ha accettato la versione 1
  privata `davidmaisterx/vcc-lead-neural-sources-r1` e restituito RUNNING. Questo
  checkpoint non contiene ancora un confronto completo, una conferma o un guadagno
  neurale misurato. Evidenza operativa: `CALCOLO.md` e `kaggle_neural_r1/push_r1.log`.

## 4. Interpretazione e incertezza

**Interpretazione:** una media quasi invariata può nascondere scambi fra metriche;
non dimostra saturazione dell'ampiezza né ottimalità del generatore. La soglia 0,005
rimane una regola operativa, senza trasformarla in significatività statistica.

**Ipotesi:** selezionare le sorgenti prima che siano fuse può migliorare la direzione
della risposta. La source-attention viene verificata su cinque famiglie escluse,
contro il trasferimento e una rete senza contesto. Una vittoria sul proxy non autorizza
la promozione diretta a modello da gara. Il pilot Stack non garantisce esclusione di
HepG2 dal pretraining e richiede scoring e conferma distinti.

## 5. Spiegazione semplice

Un punteggio medio piatto può derivare da un criterio che migliora e un altro che
peggiora. Inoltre, se mescoliamo subito le risposte di cellule diverse, una rete non
può più scegliere quale sorgente sia più pertinente. Le nuove prove separano questi
due problemi e tengono una parte dei bersagli fuori dalla selezione dei candidati.

## 6. Conseguenze

Si riaprono ampiezza e generatore come ipotesi verificabili; si procede con i due
protocolli neurali sotto l'incarico esplicito del proprietario. Non si riavvia il
vecchio orchestratore e non si dichiara utile una rete per la sola complessità.

La conferma del generatore usa 96 bersagli disgiunti, tre semi e al massimo due
candidati selezionati con regola congelata. Per la rete occorrono tutti i cinque fold,
una replica e lo scorer cellulare prima di una pretesa di competitività. L'adattamento
alla ricetta t25 deve preservarla esattamente quando la correzione neurale è nulla.
Il pacchetto t27 resta pronto senza invio, secondo la decisione del proprietario.

## 7. Cosa corregge

Corregge l'interpretazione causale di CP-0045 e il richiamo nella colonna «Corretto da»
di CP-0042: t26 azzera geni sotto 5 CPM, mentre t23 combina una lista di esclusione,
pesi continui e riscalatura su un'altra cache. Il risultato di t26 non localizza
causalmente il guadagno di t23 nei geni espressi. Rimangono validi i punteggi misurati.

Corregge anche l'uso della singola differenza fra semi come rumore noto in CP-0042.
Le altre conclusioni contestate sono elencate nella scheda R-021 di `docs/REGISTRO.md`;
gli artefatti storici rimangono intatti.

## 8. Domanda di comprensione

Perché una media invariata non basta a concludere che non resti alcuna leva utile?
