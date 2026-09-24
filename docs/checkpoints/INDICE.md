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
| [0018](0018-drive-storage-confermato.md) | 2026-09-16 | Grezzi pesanti già su Google Drive: si collegano, non si scaricano | osservazione | [0020](0020-singola-cellula-cis-generatore.md), §3.1 e §4 (le copie le ha scaricate il run Colab del 15 settembre, con md5 verificato) |
| [0019](0019-catena-cicli-guardiano.md) | 2026-09-16 | Catena di cicli: guardiano, collaudo scritto prima e controllo di Grok | cambio-di-strategia | — |
| [0020](0020-singola-cellula-cis-generatore.md) | 2026-09-17 | Pipeline a singola cellula: effetto cis trasferibile, DE esatto e veloce, md5 del K562 gia verificato | cambio-di-strategia | — |
| [0021](0021-ancore-ufficiali-e-troppe-chiamate.md) | 2026-09-17 | Le ancore ufficiali, e perche' chiamare troppi geni costa il punteggio | osservazione | — |
| [0022](0022-previsione-verificata-t03.md) | 2026-09-17 | La previsione registrata contro il punteggio reale del t03 | osservazione | [0027](0027-t07-punteggio-ufficiale.md), §4: lo strumento vale per la stessa famiglia di modelli, non per una diversa |
| [0023](0023-rpe1-contro-k562-su-hepg2.md) | 2026-09-18 | RPE1 trasferisce su HepG2 meglio di K562, anche a parita' di chiamate; non copre alcun bersaglio ufficiale | esperimento | — |
| [0024](0024-identita-del-bersaglio-su-hepg2.md) | 2026-09-18 | Il controllo d'identita' del bersaglio: il trasferimento e' specifico, il vantaggio di RPE1 e' soprattutto comune | esperimento | — |
| [0025](0025-componente-comune-scartata.md) | 2026-09-18 | Componente comune RPE1: scartata dalla sua regola | esperimento | — |
| [0026](0026-predittore-neurale-condizionato.md) | 2026-09-19 | Primo predittore neurale condizionato su bersaglio e contesto: scartato; il modello lineare con gli stessi input lo pareggia o lo batte | esperimento | — |
| [0027](0027-t07-punteggio-ufficiale.md) | 2026-09-19 | Il t07 in classifica: -0,016; la previsione del banco non regge per una famiglia di modelli diversa | esperimento | — |
| [0028](0028-cd4-sorgente-flex-trasferimento.md) | 2026-09-22 | CD4 adottato come sorgente; la gara è 10x Flex; fra contesti il trasferimento per gene è debole e la discriminazione satura | esperimento | — |
| [0029](0029-t08-punteggio-ufficiale.md) | 2026-09-23 | Il t08 in classifica: +0,060, nuovo migliore; a generatore fisso gli effetti K562 + CD4 migliorano tutti e sei i grezzi | esperimento | [0032](0032-t14-controlmodel-fedelta.md), §4 (la fedeltà non è governata dalle sole chiamate spurie del generatore: senza di esse scende) |
| [0030](0030-t10-attribuzione-cd4.md) | 2026-09-23 | Il t10 (t08 senza CD4): +0,050; CD4 porta circa 0,010 dei 0,014 guadagnati dal t08, ma la regola scritta prima dà esito non attribuibile | esperimento | — |
| [0031](0031-t11-punteggio-orion.md) | 2026-09-23 | Il t11 in classifica: +0,071, nuovo migliore; con Orion HCT116 la regola scritta prima dice che Orion aggiunge informazione, ma i pesi di K562 e CD4 sono cambiati insieme | esperimento | — |
| [0032](0032-t14-controlmodel-fedelta.md) | 2026-09-24 | Il t14 in classifica: +0,065; ControlModel all'ampiezza scelta per le chiamate è non attribuibile per la sua regola, e la fedeltà scende invece di salire | esperimento | — |
| [0033](0033-t15-ampiezza-doppia.md) | 2026-09-24 | Il t15 in classifica: +0,108, nuovo migliore e sopra 0,1; raddoppiare l'ampiezza migliora tutti i membri che contano, e D-006 si riapre | esperimento | [0034](0034-audit-segni-e-ampiezza.md), §7: FID non identifica la precisione dei segni; una perdita del t16 non confina da sola l'ottimo |
| [0034](0034-audit-segni-e-ampiezza.md) | 2026-09-24 | Audit dei segni, del confronto t17 e della preparazione al set finale | osservazione | — |
| [0035](0035-dld1-mixscale-audit.md) | 2026-09-24 | DLD-1 e Mixscale: copertura misurata e primi confronti fra contesti | osservazione | [0036](0036-generalizzazione-bersagli-contesti.md), §7: la copertura dei bersagli attuali non è un criterio di ammissione alla ricerca; confronto fra linee distinto da generalizzazione a bersagli nuovi |
| [0036](0036-generalizzazione-bersagli-contesti.md) | 2026-09-24 | La ricerca valuta bersagli e contesti nuovi senza richiedere overlap col pannello | cambio-di-strategia | — |
