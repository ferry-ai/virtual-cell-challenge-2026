# Indice dei checkpoint

Un checkpoint è una fotografia datata di un momento significativo del progetto: un
dataset adottato o scartato, un benchmark completato, un'ipotesi contraddetta, un
cambio di strategia di modellazione o di validazione. Non serve un checkpoint per
ogni modifica, esecuzione o iterazione.

**I checkpoint non si riscrivono.** Se una loro conclusione risulta sbagliata, si
scrive un checkpoint nuovo e si compila qui la colonna "Corretto da". Il testo
originale resta leggibile com'era: è così che il disaccordo storico rimane visibile.

Nuovo checkpoint:

```bash
python scripts/30_new_checkpoint.py --slug benchmark-cd4 --title "Primo benchmark su CD4"
```

Lo script assegna il numero successivo, non sovrascrive mai un file esistente e
aggiunge da sé la riga qui sotto.

## Elenco

| N | Data | Titolo | Tipo | Corretto da |
|---|---|---|---|---|
| [0001](0001-ricostruzione-stato-2026-09-12.md) | 2026-09-12 | Ricostruzione dello stato al 12 settembre 2026 | ricostruzione-retrospettiva | [0002](0002-correzioni-dopo-revisione-umana.md), §§3, 4 e 5 |
| [0002](0002-correzioni-dopo-revisione-umana.md) | 2026-09-12 | Correzioni dopo la prima revisione umana | correzione | — |
| [0003](0003-prima-pipeline-e-calibrazione-ampiezza.md) | 2026-09-12 | Prima pipeline verticale e calibrazione dell'ampiezza di trasferimento | osservazione | — |
| [0004](0004-primo-trial-locale-e-pacchetti.md) | 2026-09-12 | Primo trial locale: calibrazione annidata, inferenza A/B/C e limite di packaging | osservazione | [0005](0005-packaging-streaming-trial01.md), §3.5 e §4 (il limite era di `vcc prep`, non del problema) |
| [0005](0005-packaging-streaming-trial01.md) | 2026-09-13 | Packaging in memoria limitata: parita con vcc prep e .vcc di trial-01 | osservazione | — |
| [0006](0006-prima-sottomissione-e-punteggio.md) | 2026-09-13 | Prima sottomissione: il server accetta, e il punteggio e 0,046 | osservazione | — |
| [0007](0007-oracle-pairwise-loss.md) | 2026-09-13 | Primo oracolo numerico: confronto pairwise sulla loss | osservazione | — |
| [0008](0008-oracle-fraction-regression.md) | 2026-09-13 | Oracolo 0.2.0: frazioni esatte e tre regressioni della revisione | correzione | — |
| [0009](0009-oracle-json-number-csv-error.md) | 2026-09-13 | Oracolo 0.2.1: numeri JSON e csv.Error | correzione | — |
| [0010](0010-modalita-ricerca-scientifica.md) | 2026-09-14 | Modalita di ricerca scientifica a tre fasi nell'orchestratore | osservazione | — |
| [0011](0011-primo-benchmark-modulare.md) | 2026-09-14 | Primo benchmark modulare su pseudobulk K562/RPE1 | esperimento | [CP-0013](0013-hepg2-terzo-contesto.md) (solo la differenza appaiata di modular_frozen) |
| [0012](0012-encoder-inputs-unseen-target.md) | 2026-09-14 | Input degli encoder per bersagli mai perturbati | osservazione | — |
| [0013](0013-hepg2-terzo-contesto.md) | 2026-09-14 | HepG2 acquisito: benchmark a tre contesti e generatore contro predittore | esperimento | — |
| [0014](0014-go-slim-e-gpu.md) | 2026-09-15 | GO slim scartato dalla sua stessa regola; la GPU non tocca questo codice | esperimento | — |
| [0015](0015-svd-randomizzata-e-rango.md) | 2026-09-15 | SVD randomizzata misurata; il rango oltre 16 non trasferisce | esperimento | — |
| [0016](0016-piano-operativo-audit-protocollo.md) | 2026-09-15 | Piano operativo: audit sorgenti e protocollo di valutazione congelato | cambio-di-strategia | — |
| [0017](0017-gate-espressione-destinazione.md) | 2026-09-16 | Gate di espressione sul contesto di destinazione: misurato, non promosso | esperimento | — |
| [0018](0018-drive-storage-confermato.md) | 2026-09-16 | Grezzi pesanti già su Google Drive: si collegano, non si scaricano | osservazione | — |
