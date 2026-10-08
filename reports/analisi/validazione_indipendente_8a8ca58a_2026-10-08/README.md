# Validazione indipendente — sessione 8a8ca58a, 8 ottobre 2026

Claude Code, sessione `8a8ca58a`, incarico del proprietario in chat: protocollo scientifico, banco di valutazione,
controlli indipendenti, confronto dei candidati e raccomandazione per la consegna della notte fra l'8 e il 9
ottobre. Binario [R-LEAD](../../../docs/piani/strategia-scientifica.md), che resta la sede delle decisioni operative.
Questa cartella possiede protocollo, banco, risultati comparativi e raccomandazione; **non** possiede banca, trainer
e pipeline di produzione (DATI-TRANSFER, sessione `01a11c34`) né l'adattatore esterno (MODELLI-ESTERNI, sessione
`01a11c35`).

## Che cosa leggere prima

| File | Contenuto | Tipo |
|---|---|---|
| [PROTOCOLLO_v1.md](PROTOCOLLO_v1.md) | Contratto sperimentale: identità, fold C/T/J, interfaccia, emettitore, metriche, matrice dei confronti, regola di adozione | protocollo, congelato prima dei numeri |
| [manifest_fold_v1.json](manifest_fold_v1.json) | Lo stesso contratto leggibile da macchina: lignaggi con alias, fold, bracci, regola dei bersagli nascosti, riserve | manifest congelato |
| [build_manifest.py](build_manifest.py) | Scrive il manifest dai metadati committati e fallisce se un'unità di banca o una tabella non ha un lignaggio | implementato |
| [preflight_kaggle_r1.json](preflight_kaggle_r1.json) | Stato dei kernel sui tre account alle 18:06 dell'8/10, in sola lettura | misurato |

I file che seguono (banco, audit, risultati, raccomandazione) si aggiungono a questo indice quando esistono.

## Regole di questa cartella

- Un numero comparativo si legge solo con la regola del §8 del protocollo che era congelato quando è stato prodotto.
- I punteggi dei banchi sono **locali**: non sono punteggi VCC. I punteggi ufficiali stanno solo in
  [reports/invii/README.md](../../invii/README.md).
- Nessun file di un altro incarico è modificato da qui: un problema trovato diventa una segnalazione con
  riproduzione minima, impatto e criterio di accettazione, consegnata al suo proprietario.
- Gli artefatti di validazione (effetti a linea esclusa, banchi) non sono artefatti di produzione e non si inviano.
