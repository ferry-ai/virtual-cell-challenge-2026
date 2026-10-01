# Quarto training della rete cellulare, con la terza ondata e il pavimento su `pi`: protocollo e regola di lettura

1 ottobre 2026, scritto alle 16:02 CEST (ora del file), Claude Code (sessione `07ebf08b`), scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). Il training partirà quando si rinnova la quota GPU di Kaggle:
oggi ne restano circa 40 minuti. Scritto prima di ogni suo numero, con il codice al commit `39f451d` (dataset
`rlab-cellnet-code` aggiornato alle 13:57 UTC).

## 1. Che cosa è

Una **verifica tecnica**, come i tre training precedenti: un seme, HepG2 tenuto fuori, nessuna riserva aperta,
nessun confronto a sei membri. Cambia due cose rispetto al terzo
([cellnet_completo_2026-10-01](../cellnet_completo_2026-10-01/ESITO.md)):
- il corpus aggiunge la terza ondata, e Southard se è pubblicato al lancio del pre-passo;
- entrambi i bracci hanno `--pi-floor 0.05`, perché nel terzo training il braccio `ident` è collassato a `pi` = 0.

## 2. Dati

Il corpus del pre-passo r7 (con Tian 2019 fuori per lo stesso motivo), più:
- `rlab-scp-ko`: Frangieh 2021 in tre contesti, Sunshine 2023, Papalexi 2021 arrayed;
- `rlab-scp-tcells`: Shifrut 2018 in quattro contesti, Datlinger 2017 e 2021 in due contesti ciascuno;
- `rlab-scp-k562-hek`: Dixit 2016 in tre contesti, Xu 2023;
- `rlab-southard-rpe1` e `rlab-southard-hs27`, solo se pubblicati al lancio del pre-passo.

Restano fuori gli stessi dataset del terzo training, con lo stesso motivo. Si aggiungono quelli che il catalogo
r4 segna come non ingeriti, CD4 compreso, che aspetta un disegno di campionamento del proprietario.

## 3. Disegno e budget

- Pre-passo su CPU con gli argomenti del terzo training, e lo stesso `--glob` per `rlab-tian-norman`.
- Kernel GPU T4×2, un processo, `--arm desc=descriptors --arm ident=identity`.
- Argomenti: `--epochs 10 --workers 3 --eval-workers 3 --checkpoint-minutes 15 --eval-reserve-seconds 120
  --pi-floor 0.05`, il resto di default. Ciclo di ripresa 50 → 100.
- Budget: la quota disponibile al lancio, meno 20 minuti di margine, meno avvio e ciclo, e non meno di 60 minuti.
  Si scrive nel file di lancio prima del lancio.

## 4. Regola di lettura, fissata ora

**A.** La stessa dei training precedenti:
- codice 0, ripresa passata, `verify.json` pulito;
- copertura completa se `epochs_done` ≥ 1, non-contaminazione;
- valutazione completa entro il budget per entrambi i bracci;
- throughput, attesa dei dati e memoria riportati.

**B. Lettura descrittiva.** **Attese scritte ora:**
- (i) guadagno rispetto a nessun effetto positivo in media su C e T in entrambi i bracci;
- (ii) su J `descriptors` sopra `identity`;
- (iii) nessuna attesa che la rete batta il trasferimento su C;
- (iv) **il pavimento funziona** se a fine training la `pi` media di ogni braccio, sui perturbati del log, sta sopra
  0,10, cioè lontano dal pavimento. Se un braccio resta fra 0,05 e 0,10, il pavimento impedisce lo zero ma non il
  collasso, e serve un'altra correzione (per esempio una penalità sulla miscela);
- (v) il confronto con il terzo training è descrittivo: cambiano insieme dati e pavimento.

Con un seme e un contesto tenuto fuori nessuna di queste attese, vera o falsa, è una prova; i numeri non entrano in
PROGETTO §0 come risultati.
