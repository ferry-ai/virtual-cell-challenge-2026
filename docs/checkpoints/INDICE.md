# Indice dei checkpoint

Un checkpoint è una fotografia datata di un momento significativo del progetto: un
dataset adottato o scartato, un benchmark completato, un invio valutato, un'ipotesi
contraddetta, un cambio di strategia di modellazione o di validazione. Non serve un
checkpoint per ogni modifica, esecuzione o iterazione. Queste regole stanno qui e solo qui;
la colonna «Corretto da» è la sede delle correzioni di ogni checkpoint, e
`python scripts/31_check_docs.py --status <checkpoint>` la mostra accanto al registro, e dal 30/09
per prima, prima dello stato del registro. Una riga propria del registro che dice `attuale` per un
checkpoint corretto deve nominare il checkpoint che lo corregge: il controllo lo verifica.

**I checkpoint non si riscrivono.** Se una loro conclusione risulta sbagliata, si
scrive un checkpoint nuovo e si compila qui la colonna "Corretto da". Il testo
originale resta leggibile com'era: è così che il disaccordo storico rimane visibile.

Nuovo checkpoint:

```bash
python scripts/30_new_checkpoint.py --slug benchmark-cd4 --title "Primo benchmark su CD4"
```

Lo script assegna il numero successivo, non sovrascrive mai un file esistente e
aggiunge da sé la riga qui sotto.

**Due note del 28 settembre (D-046):**
- **I percorsi dei report citati nei checkpoint sono quelli di allora.** Dal 28 settembre un
  report sta in `reports/<categoria>/<cartella>/` con lo stesso nome: `ls -d reports/*/<cartella>`
  lo trova, e le analisi citate come `docs/<file>` stanno in `docs/storico/`. I checkpoint non si
  riscrivono per questo.
- **CP-0040 è arrivato il 28/09.** Era scritto da un'altra sessione il 25/09 e mai committato
  (registro, scheda R-020); è stato recuperato dal portatile e committato com'era, con il suo numero
  (azione 1 della scheda [R-REV](../piani/revisione-critica.md)). Questa nota riguarda il recupero storico; il prossimo numero si ricava dall'indice corrente.

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
| [0021](0021-ancore-ufficiali-e-troppe-chiamate.md) | 2026-09-17 | Le ancore ufficiali, e perche' chiamare troppi geni costa il punteggio | osservazione | [0050](0050-credibilita-score-e-riserva.md), §7: la conversione con ancore aggregate non è esatta sui successivi invii |
| [0022](0022-previsione-verificata-t03.md) | 2026-09-17 | La previsione registrata contro il punteggio reale del t03 | osservazione | [0027](0027-t07-punteggio-ufficiale.md), §4: lo strumento vale per la stessa famiglia di modelli, non per una diversa; [0050](0050-credibilita-score-e-riserva.md), §7: il terzo punto non verifica l'esattezza delle ancore |
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
| [0037](0037-t16-ampiezza-quadrupla.md) | 2026-09-25 | Il t16 in classifica: +0,138, nuovo migliore; raddoppiare ancora l'ampiezza migliora soprattutto i membri DE | esperimento | — |
| [0038](0038-t17-hek293t-non-attribuibile.md) | 2026-09-25 | Il t17 in classifica: +0,109, pari al t15; HEK293T a pesi uguali non è attribuibile | esperimento | — |
| [0039](0039-banco-varianti-restrizione.md) | 2026-09-25 | Banco a sorgente esclusa: gli effetti ristretti aiutano il PDS proxy, ma meno di quanto scritto prima della revisione | osservazione | — |
| [0040](0040-biologia-contesti-donatori.md) | 2026-09-25 | Programmi con segno, dipendenze di contesto e instabilita fra donatori: ricerca esplorativa | osservazione | — |
| [0041](0041-proxy-contro-ufficiale.md) | 2026-09-28 | Il proxy dei banchi contro le differenze ufficiali: due coppie su quattro non lette, non si sceglie più sul solo proxy | esperimento | — |
| [0042](0042-t23-esclusione-pds.md) | 2026-09-29 | Il t23 in classifica: +0,1419, non conclusivo; il PDS sale di dodici volte il rumore del seme, i membri DE scendono | esperimento | [0045](0045-t26-soglia-espressione.md), §7, proponeva un'attribuzione; [0046](0046-audit-lead-e-due-vie-neurali.md), §7, ne corregge causalità e uso della differenza fra semi come rumore noto |
| [0043](0043-misura-decisiva-relazioni.md) | 2026-09-29 | La misura decisiva per la rete relazionale: inconclusiva per W1, e la via delle relazioni non prevede nulla nemmeno nella stessa linea | osservazione | — |
| [0044](0044-prova-generale-22-ottobre.md) | 2026-09-29 | La prova generale del 22 ottobre riesce in forma ridotta: .vcc di D/E/F verificato; restano da correggere la cache che sbaglia in silenzio e il riferimento di gamma | esperimento | — |
| [0045](0045-t26-soglia-espressione.md) | 2026-09-29 | Il t26 in classifica: +0,1387, non conclusivo; togliere gli effetti sui geni poco espressi non alza il PDS, quindi il guadagno del t23 veniva dai geni espressi | esperimento | [0046](0046-audit-lead-e-due-vie-neurali.md), §7: gli interventi diversi non identificano questa attribuzione causale; punteggi confermati |
| [0046](0046-audit-lead-e-due-vie-neurali.md) | 2026-09-29 | Revisione lead: piattaforma CD4, compensazioni fra metriche e due vie neurali da verificare | cambio-di-strategia | — |
| [0047](0047-conferma-generatore-t28.md) | 2026-09-29 | Conferma pubblica del generatore e registrazione t28 | osservazione | [0050](0050-credibilita-score-e-riserva.md), §7: calcolo confermato, ma 95/96 target erano già valutati nello storico |
| [0048](0048-rete-sorgenti-primo-seme.md) | 2026-09-29 | La rete che pesa le sorgenti non supera la soglia nel primo seme | osservazione | — |
| [0049](0049-rete-sorgenti-replica.md) | 2026-09-29 | La replica conferma il guadagno neurale sotto soglia e il limite del condizionamento | osservazione | — |
| [0050](0050-credibilita-score-e-riserva.md) | 2026-09-29 | Le ancore aggregate non sono esatte e la riserva HepG2 era gia valutata | correzione | — |
| [0051](0051-stack-ab-negativi.md) | 2026-09-29 | Stack A e B non superano il transfer; il ricontrollo numerico chiude la selezione senza candidati | osservazione | — |
| [0052](0052-t28-punteggio-ufficiale.md) | 2026-09-30 | T28 nuovo migliore osservato, sotto la soglia di miglioramento registrata | osservazione | — |
| [0053](0053-audit-cellnet-e-strategia.md) | 2026-10-01 | Audit cellnet e strategia per un modello competitivo | cambio-di-strategia | [0054](0054-visibilita-scorer-e-consegna.md), §7: precisa soltanto la diagnosi ambientale delle verifiche citate; misure scientifiche invariate |
| [0054](0054-visibilita-scorer-e-consegna.md) | 2026-10-01 | Lo scorer funziona fuori dal sandbox: consegna verificata al teammate | correzione | — |
| [0055](0055-t29-rete-cellulare-punteggio.md) | 2026-10-01 | t29: la rete addestrata sulle singole cellule sulla classifica, -0,030 | esperimento | — |
| [0056](0056-banco-contesto-c-j.md) | 2026-10-03 | R-LEAD P3: i controlli di una linea mai vista non migliorano il transfer su sette gruppi di linea | esperimento | — |
| [0057](0057-p4-dieci-gruppi-pseudobulk.md) | 2026-10-03 | R-LEAD P4: dieci gruppi e una rete non lineare sul pseudobulk non danno beneficio dal contesto; sui sei membri vince il transfer | esperimento | — |
| [0058](0058-copertura-integrale-contesti.md) | 2026-10-03 | Copertura obbligatoria di tutte le linee e i contesti idonei | cambio-di-strategia | — |
| [0060](0060-direzione-x-transfer-pilot-v4.md) | 2026-10-03 | Direzione X + transfer, diagnosi dei training v3 e pilot v4 lanciato | cambio-di-strategia | — |
