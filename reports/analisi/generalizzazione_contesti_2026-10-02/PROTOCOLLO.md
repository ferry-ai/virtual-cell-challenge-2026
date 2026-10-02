# Protocollo P2–P3 di R-LEAD: il contesto letto dai controlli migliora il transfer?

**Congelato il 2 ottobre 2026 nel commit `e60767c` delle 17:32:23 CEST**, prima di adattare o valutare
qualunque braccio sui dati reali. Bozza alle 17:25 (versione 1), corretta prima dei dati reali per
l'esito del controllo positivo sintetico (§5). Il testo committato diceva «17:40», un orario scritto a
memoria e sbagliato: corretto alle 17:33 (orario letto con `date`), regola invariata. La versione
eseguibile è [PROTOCOLLO.json](PROTOCOLLO.json): `decide.py` legge la regola da lì. Autore: Claude Code, sessione `22d21f`. Scheda: [R-LEAD](../../../docs/piani/strategia-scientifica.md).
Codice: [risposta_contesto_2026-10-02](../../modelli/risposta_contesto_2026-10-02/).

## 1. Domanda e tipo delle affermazioni

Dai soli controlli di una linea mai vista perturbata si può imparare una correzione della risposta che
migliori il transfer dello stesso bersaglio? Tutto ciò che il banco produce è **misurato nello spazio
degli effetti** su linee pubbliche già lette in passato: è **sviluppo**, non conferma, e non è un
punteggio VCC. I sei membri ufficiali si misurano solo su HepG2 (§7), sempre come sviluppo.

## 2. Banco

- **Unità tenuta fuori: il gruppo di linea**, con tutti i suoi studi, stati, donatori e cloni:
  CD4T (tre stati, quattro donatori), HCT116, HEK293T, HepG2, K562 (GWPS, essential, VIPerturb Flex),
  RPE1, iPSC (KOLF2.1J e 19 linee HIPSCI; KOLF2.1J deriva dal donatore HIPSCI `kolf`, fatto di
  letteratura non verificato su un file primario locale). Matrice e confondimenti in `p0_r1/`.
- **Cubo** (`cube.py`, dati nella radice dati): 4.212 bersagli in tre strati fissati senza guardare
  esiti (2.381 dei due schermi essenziali, 300 del pannello A/B/C, 1.531 genome-scale per hash
  stabile), 10.821 geni misurati in almeno quattro gruppi, effetti grezzi, SE e shrunk in float16.
- **Verità:** l'effetto grezzo (ln) della tabella tenuta fuori, con lo stimatore della sua cache
  (HepG2 ricostruita qui con `min_expected` 1, la correzione del t25). Righe valutate: ≥ 10 cellule e,
  in C, supporto del transfer da almeno un gruppo di training dopo il QC (`p1_r1/split_manifest.json`).

## 3. Regimi e split

C: gruppo escluso da ogni adattamento. J: anche i bersagli del fold tenuto fuori (hash SHA-256 della
chiave Ensembl riconciliata) escono da ogni tabella. T: solo diagnostico. Gli split non dipendono dal
corpus (verificato in P1). Ogni braccio è adattato solo su righe ammesse (`assert_no_leak`); ogni
lettura di tabella è registrata con lo scopo, e la corsa fallisce se un adattamento legge il gruppo escluso.

## 4. Bracci

| Braccio | Che cosa |
|---|---|
| `null` | effetto zero |
| `generic` | risposta comune addestrata: media sui gruppi di training della risposta media grezza; nessuna identità del bersaglio |
| `transfer` | ricetta t25 generalizzata: shrunk − γ·comune (γ 1), affidabilità n/(n+100), media nel gruppo, poi pesi uguali fra gruppi; ampiezza 1,576; coppie non misurate a 0 come in produzione |
| `tm0` | modello del bersaglio senza contesto: transfer e generico ricombinati con guadagni per gene che usano solo il profilo dei controlli delle **sorgenti** |
| `m1` | condizionato, guadagno per gene: gli stessi termini con differenza di espressione, livello e soglia di bassa espressione **dei controlli della linea tenuta fuori** (correzione bilineare diagonale) |
| `m2_0`, `m2` | bilineare a basso rango su una base di geni dei transfer di training; `m2` aggiunge coordinate del contesto sugli assi principali dei controlli di training; k, d e ridge scelti per leave-one-group-out interno |
| `*_swap` | il condizionato con i controlli di un altro gruppo (derangement fisso); basale, bersagli e adattamento invariati |
| `m1_tperm` | `m1` applicato all'effetto condiviso di un altro bersaglio: specificità |
| `*_null1..5` | il condizionato adattato con i controlli permutati fra i gruppi di training (spostamenti ciclici): il nullo della corsa |

Le correzioni sono adattate sui residui di transfer **fuori fold**: una riga del gruppo h usa il transfer
calcolato senza il gruppo escluso e senza h. Per J: `embed` (modello senza memoria: carico del gene
bersaglio sulla base delle risposte di training, mappa ridge), `jm1_0`, `jm1`, `jm1_swap`, `jm1_null*`.

## 5. Metriche e aggregazione

Indici nello spazio degli effetti (`metrics.py`), pesati per espressione dei controlli tenuti fuori,
gene del bersaglio escluso: **primaria `cos`** (coseno pesato fra previsto e vero); secondarie con
vincolo di non regressione `pds` (discriminazione in blocchi di 300 bersagli, come il PDS ufficiale),
`cos_spec` (parte specifica del bersaglio), `sign_sig` (segno sui geni significativi), `mse_ratio`.

**Revisione prima dei dati reali.** Nella bozza la primaria era `pds`. Il controllo positivo sintetico
(`test_p3_synthetic.py`: guadagno per gene piantato, β = 0,8) ha mostrato `pds` saturo e cieco al
contesto (m1 − tm0: pds +0,0003, cos +0,125, mse_ratio −0,25) quando il transfer discrimina già.
La primaria è diventata `cos` prima del commit delle 17:32:23, con `pds` come vincolo; nessun dato reale
era stato adattato.

Aggregazione: per gruppo, media delle differenze appaiate per bersaglio; macro = media non pesata
sui gruppi. Incertezza: bootstrap sui gruppi (descrittivo, sette unità) e sui bersagli entro gruppo
(descrittivo, non misura l'incertezza fra contesti).

## 6. Regola di decisione

**Beneficio del contesto (C)**, per `m1` (gemello `tm0`) e `m2` (gemello `m2_0`), tutte insieme:
1. macro Δctx(cos) > 0 e maggiore del massimo dei cinque nulli permutati;
2. Δctx > 0 in almeno 6 gruppi su 7;
3. scambio dei controlli: macro Δswap > 0 e positivo in almeno 5 gruppi su 7;
4. nessun secondario peggiora più del peggior nullo permutato.

**Soglie motivate**, nessun numero inventato: 1 e 4 confrontano con adattamenti identici ma con
un'associazione linea–controlli sbagliata; 2 e 3 contano linee, l'unità d'inferenza (6 su 7 ha p
unilaterale 0,0625 nel test dei segni). Due candidati, ognuno con i propri nulli, senza correzione per
molteplicità (dichiarato).

**Miglioramento della catena (C)**, per `tm0`, `m1`, `m2_0`, `m2` contro `transfer`: macro Δ(cos) > 0,
positivo in almeno 6 gruppi su 7, nessuna regressione macro sui secondari. Se passa solo un braccio
senza contesto, è calibrazione e non apprendimento del contesto.

**J:** il riferimento `embed` deve discriminare (macro pds sopra `generic`); stessa regola 1–4 per
`jm1`. **Protezione J:** una correzione adottata in C si applica ai bersagli J solo se `jm1` passa; il
ramo J non deve scendere sotto `embed`. **T:** diagnostico.

**Esiti:** beneficio del contesto → conferma P5 su riserva appropriata e sei membri; catena senza
contesto → candidato di calibrazione da giudicare sui sei membri e in P5; inconclusivo (fallisce solo
la 2 con 5 gruppi su 7, o solo la 4) → nessuna adozione, prossimo contrasto mirato; nessun beneficio →
resta il transfer, con ciò che è escluso e il contrasto successivo giustificato. Nessuna adozione nasce
da questo banco: tutte le linee sono sviluppo.

## 7. Sei membri su HepG2 (sviluppo)

`vcc2026.bench.Bench`: verità = metà A delle cellule di 300 bersagli HepG2 (≥ 50 cellule, ordine hash)
più 4.976 controlli; replica = metà B; baseline = profilo generico dello scorer; generatore trial-01
(t22/t25), identico bit per bit allo stadio 45 (`export_parity.json`). Bracci C con HepG2 esclusa,
nessuna testa cis. Lettura descrittiva dei sei membri e della media; scala locale, non VCC.

## 8. Che cosa cambia rispetto al predittore condizionato del 19 settembre (CP-0026)

| Limite di CP-0026 | Qui |
|---|---|
| Due contesti di training (K562, RPE1): il condizionamento per gene aveva due punti da cui imparare | sette gruppi di linea, sei in ogni adattamento; il guadagno per gene si stima su migliaia di geni × sei linee |
| Iperparametri scelti su un contesto già visto | nulla si sceglie sul gruppo escluso; m2 per leave-one-group-out interno |
| Un solo contesto nuovo (HepG2), bootstrap sui soli bersagli | sette gruppi tenuti fuori a turno; unità d'inferenza = linea |
| Contesto scambiato solo in previsione, nessun gemello riaddestrato | gemello senza contesto riaddestrato sulle stesse righe, scambio, cinque nulli permutati, permutazione dei bersagli |
| La rete modellava l'effetto intero (cancello sulla risposta K562 più bilineare bersaglio × gene) | si modella solo il **residuo del transfer fuori fold**: la domanda è la correzione, non la ricostruzione |
| Rete non riproducibile (configurazione e previsioni cambiate al rilancio) | soluzioni chiuse ridge, deterministiche |
| Trasferimento dalla sola K562 | transfer t25 su sei gruppi a pesi uguali, stimatore corretto |
| Punteggio previsto con ancore aggregate | indici sugli effetti dichiarati come tali; sei membri con ancore locali solo su HepG2 |

**Il contrasto nuovo** che rende informativo riprovare: residuo del transfer fuori fold spiegato dai
controlli della linea tenuta fuori, contro lo stesso modello riaddestrato senza contesto e contro
associazioni linea–controlli sbagliate, su sette linee. Se il contesto serve, il condizionato deve
battere tutti e tre in quasi tutte le linee; se no, il risultato esclude questa forma di correzione
(guadagni per gene e interazioni di programma a basso rango) a parità di dati.

## 9. Limiti noti prima dei risultati

Sette gruppi, con confondimenti: HCT116 e HEK293T stesso studio; K562 e RPE1 stesso laboratorio
di HepG2 (Weissman, da verificare); iPSC 20 tabelle di un solo tipo cellulare. Saggi diversi (3′, 5′,
Flex) confusi con le linee. La verità è pseudobulk con rumore proprio (riproducibilità HepG2 metà/metà
in `hepg2_r2`). Nessuna riserva intatta in locale (`p1_r1/reserve_manifest.json`).

## 10. Correzioni d'implementazione prima dei risultati

- **Selezione interna di M2** (versione 2 del runner, `fitting.py`). La versione 1 (commit `e60767c`) non
  ricostruiva senza il gruppo di validazione interna né la base dei geni né i transfer fuori fold delle
  righe di training: il tuning interno era ottimista, il gruppo tenuto fuori nel test esterno non era
  coinvolto. Segnalato da una revisione esterna inoltrata dal proprietario in chat. Nella versione 2 base,
  transfer e PCA del fold interno escludono il gruppo di validazione; ogni fold registra le proprie
  sorgenti (`inner_audit`), controllate dai test. La corsa `p3_c_r1` è stata fermata alle 17:50:42 durante
  il secondo gruppo; il suo unico file parziale (CD4T) non è stato letto ed è conservato com'è.
- **Riferimento J per i guadagni:** base, risposta comune e mappa ridge si riadattano senza il fold
  interno, più stretto dell'approssimazione dichiarata nella regola J.

Nessuna regola, soglia o metrica cambia con queste correzioni.
