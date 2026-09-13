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
