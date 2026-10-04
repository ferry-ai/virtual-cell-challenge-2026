# CP-0065 — D-056 dopo il t30: il banco a un seme era rumoroso quanto i guadagni; la perdita di PDS del fold esportato è reale

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione ba9b8bcb, su R-LEAD
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-009

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Dopo il t30 ([CP-0064](0064-t30-ibrido-selettivo-punteggio-ufficiale.md)): sul banco, con reti e pesi congelati,
quale differenza fra banco e invio toglie il guadagno della correzione D-056 (baseline, parte comune, procedura
dell'invio)? E il banco a un seme è in grado di leggere differenze di quella grandezza?

## 2. Cosa è stato fatto

- Protocollo `reports/modelli/diagnosi_t30_2026-10-04/PROTOCOLLO_CONFRONTI.md`, congelato a `8f9118c` prima di ogni
  uscita; emendamenti §8 (braccio fedele) e §9 (taratura del rumore) scritti e committati prima delle loro esecuzioni.
- Via del proprietario in chat (14:53 e, dopo, «puoi anticipare tutto quello che vuoi»). Dieci kernel Kaggle CPU su
  due account, nessuna GPU: cinque corsie diagnostiche (`rcell-t30diag-<linea>-r1`, 16 bracci) e cinque tarature
  (`rcell-t30noise-<linea>-r1`: quattro bracci × 5 semi del generatore × due numerosità, 32 mediane e 400 cellule
  previste per bersaglio). Lanci in `reports/modelli/diagnosi_t30_2026-10-04/lancio_diag_r1.jsonl`.
- Letture con `read_diag.py` e `read_noise.py`, scritti prima delle uscite.

## 3. Cosa si è osservato

Tutto in `reports/modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md`, con le ricevute `esito/read_diag_r1.json` ed
`esito/read_noise_r1.json`.

- **Validità:** cinque linee su cinque riproducono con scarto 0 i membri archiviati di CP-0062; parità vera.
- **Rumore.** Guadagno appaiato `ibrido − transfer` su 5 semi, media ± deviazione standard:

| Linea | Archiviato | 32 cellule | 400 cellule | PDS, 400 cellule |
|---|---|---|---|---|
| HepG2 | +0,063 | +0,064 ± 0,020 | +0,031 ± 0,006 | −0,129 ± 0,005 |
| H1 | +0,006 | +0,002 ± 0,007 | +0,004 ± 0,004 | +0,020 ± 0,008 |
| RPE1 | +0,040 | +0,014 ± 0,018 | +0,013 ± 0,003 | +0,061 ± 0,022 |
| Jurkat | +0,037 | +0,021 ± 0,017 | +0,013 ± 0,006 | +0,042 ± 0,009 |
| K562 | +0,074 | +0,023 ± 0,045 | +0,005 ± 0,015 | +0,008 ± 0,017 |

  Regola del §9: «un seme non risolve il guadagno» in 2 linee su 5 sulla baseline del banco (non stabilito con la
  soglia di 3) e in 4 su 5 sulla baseline di produzione (stabilito). A 400 cellule il guadagno è risolto e positivo
  in 3 linee su 5 su ciascuna baseline; la media delle cinque linee è +0,013 contro +0,044 archiviato.
- **Corsie, un seme, verdetti registrati:** baseline incoerente non distinta (D medio −0,001); parte comune sostenuta
  (PDS −0,027 con la quota comune a 0,65; −0,111 su HepG2); guadagno specifico (parte specifica +0,024, positiva in 5
  linee); procedura dell'invio «sostenuta» sulla media (−0,025).
- **Braccio fedele:** la correzione calcolata con la procedura dell'invio coincide con quella del banco sugli stessi
  bersagli (coseno 0,9998–1,0000 su quattro linee, 0,977 su RPE1; stessa quota comune e stessa RMS).

## 4. Interpretazione e incertezza

- **Misura:** il rumore del guadagno a un seme (0,007–0,045) è dello stesso ordine dei guadagni letti in CP-0062.
  La perdita di PDS su HepG2 è molte deviazioni standard lontana da zero.
- **Interpretazione:** il verdetto registrato su C4 non identifica un effetto della procedura: due effetti quasi
  uguali hanno dato medie diverse quanto il rumore misurato. La procedura dell'invio è fedele; la quota comune alta
  dell'invio viene dai bersagli del pannello. I verdetti C2 e C3, a un seme, reggono solo dove l'effetto è grande
  (HepG2).
- **Ipotesi:** che la perdita ufficiale del t30 dipenda dall'aver esportato il fold HepG2; che un altro fold avrebbe
  fatto meglio sul sito. Nessuna misura ufficiale lo dice.
- **Incertezza:** 5 semi del generatore, un seme del banco (stessa metà di verità), una rete per linea, linee già
  lette. La deviazione standard su 5 valori è essa stessa incerta.

## 5. Spiegazione semplice

Stavamo pesando piume con una bilancia da cucina. La bilancia segnava «più 40 grammi» e abbiamo spedito. Ripesando la
stessa piuma cinque volte, i numeri ballano di 20–40 grammi; con una bilancia più fine (più cellule, più pesate) il
guadagno c'è ma è di 13 grammi. E una delle cinque piume, proprio quella spedita, su un piatto pesava meno, in modo
netto.

## 6. Conseguenze

- Il prossimo banco usa 400 cellule previste per bersaglio e almeno 5 semi, con guadagno appaiato e risolto; una
  guardia sul PDS per linea e per fold; bersagli nel regime del pannello. Le soglie di CP-0062 a un seme non si usano
  più così come sono.
- D-056 resta una direzione con un segnale piccolo e reale sul banco; la rete da esportare si sceglie guardando la
  discriminazione del fold, non il numero di cellule.
- Nessun candidato è promosso e nessun invio è autorizzato da queste letture.

## 7. Cosa corregge

- [CP-0062](0062-d056-ibrido-selettivo-esito-banco.md): i guadagni +0,006…+0,074 erano letture a un seme; su 5 semi e
  400 cellule valgono +0,004…+0,031, risolti in tre linee su cinque. «Confermato su Jurkat e K562» regge su Jurkat
  (+0,013 ± 0,006), non è risolto su K562 (+0,005 ± 0,015).
- [CP-0064](0064-t30-ibrido-selettivo-punteggio-ufficiale.md) e il resoconto della diagnosi: l'ipotesi «procedura
  dell'invio» è chiusa sul banco (la procedura è fedele); il controllo locale sui controlli di HepG2 misurava i
  bersagli del pannello, non la procedura.

## 8. Domanda di comprensione

Perché due bracci con effetti quasi identici possono ricevere punteggi diversi, e che cosa bisogna cambiare nel banco
perché una differenza di 0,01 sia leggibile?
