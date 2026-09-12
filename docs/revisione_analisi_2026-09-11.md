# Revisione dell'audit dati e riorientamento — 11 settembre 2026

Revisione di `docs/data_strategy_2026-09-11.md`. Il metodo dell'audit precedente è
solido e va conservato; tre delle sue conclusioni vanno corrette e la sua priorità
di acquisizione va riordinata. Il motivo del riordino è una misura nuova: **i tre
contesti anonimi non sono anonimi per il trascrittoma**, e nessuno dei tre appartiene
al lignaggio delle sorgenti che stavamo per scaricare.

Riproduzione: `scripts/py.cmd scripts/16_probe_context_identity.py` e
`scripts/py.cmd scripts/17_extract_scorer_contract.py`. Nessun dato sorgente
modificato, nessun download effettuato.

## 1. Cosa dell'audit precedente regge

Il codice di `12_audit_data_strategy.py` è read-only, in streaming, verifica l'ordine
dei geni, la non-negatività e l'interezza dei conteggi, e calcola CPM per cellula
*prima* di mediare. Quest'ultimo dettaglio non è cosmetico: riproduce esattamente
`filter_gene_min_cpm_cell: 5.0` del config ufficiale. Va tenuto.

Verificato in modo indipendente e confermato: ordine e identità dei 18.533 geni,
profondità mediane, 272/300 bersagli in K562 GWPS per simbolo, i duplicati di simbolo,
e la cautela su `core_control` come annotazione d'autore.

## 2. Tre correzioni

**Il pseudobulk Replogle è recuperabile come conteggi.** `X * num_cells_filtered` è
intero entro l'1% sul 100% delle celle della matrice, e la somma di riga di `X` sta a
1,022 da `UMI_count_unfiltered`. Quindi `X` è la media per cellula dei conteggi grezzi
con numerosità nota: si possono ricostruire somme intere e pesare correttamente una
stima di log2FC. Resta vero che non sono singole cellule e che non vanno dati allo
scorer come tali; non è vero che siano inutilizzabili a livello di conteggio.

**Lo 0/300 in essential e RPE1 non è un artefatto di parsing: è disegno del pannello.**
Confermato con matching sia per simbolo sia per ENSG estratto da `obs_names`. Con 300
bersagli estratti a caso fra i geni espressi ci si aspetterebbero circa 33 sovrapposizioni
con un pannello essential da ~2.000 geni. Zero è una scelta. Coerentemente, 288/300
bersagli superano 5 CPM in tutti e tre i contesti e solo 3 scendono sotto 1 CPM in
almeno uno. **Il pannello 2026 è: espresso ovunque, non essenziale.** Conseguenza
diretta: le risposte sono piccole per costruzione, e selezionare sorgenti esterne per
"perturbazioni forti" — il subset `Strong_Perturbations` di KOLF, per esempio — campiona
il regime sbagliato. L'audit lo sospettava; ora è misurato.

**L'asse genico della gara è ordinato per Ensembl gene ID.** Una sola inversione su
9.387 geni mappabili. Il problema aperto del "mapping alias" non è euristico: si
ricostruisce l'ENSG esatto di tutti i 18.533 geni allineando l'asse a un riferimento
Ensembl ordinato, e da lì ogni join con dati esterni diventa esatto.

**Misurato ciò che l'audit dichiarava non misurato:** la sovrapposizione fra il
pannello 2026 e H1 2025 è **25/300** (13 da Training, 4 da Validation, 8 da Test).
Lo spazio genico invece è quasi identico: 18.077 dei 18.080 geni 2025 sono nell'asse
2026. H1 2025 quindi non è una sorgente di copertura dei bersagli — è un banco di prova.

## 3. Chi sono A, B e C

Marcatori in CPM medio per cellula, dai soli controlli ufficiali. Evidenza completa in
`reports/context_identity/markers.csv`.

| Contesto | Lignaggio | Evidenza principale | Sesso |
|---|---|---|---|
| **A** | T-linfoide (T-ALL corticale) | CD3D 939, CD3E 760 (det. 100%), ZAP70 671, LCK 431, TRAC 396, DNTT 638, RAG1 209, CD1A 140, TAL1 149, MYB 749; cheratine epiteliali a zero | maschile (DDX3Y, EIF1AY, UTY, KDM5D) |
| **B** | ibrido epiteliale-mesenchimale, firma di campo oculare | CLU 7.857, VIM 6.052, KRT7 2.428, KRT8 2.506, KRT18 835, CDKN2A 2.480, COL1A1 358; PAX6 34, LHX2 38, MITF 27 | femminile (cromosoma Y assente) |
| **C** | epiteliale squamoso | TP63 854, KRT15 2.146, KRT5 1.812, KRT13 1.601, CSTA 1.084, KRT14 303, SOX2 143, EPCAM 310, CDH1 127; VIM 2,0 | maschile |

Il test di contrasto — correlazione fra `log(RPE1) − log(K562)` e `log(contesto) − media
degli altri due`, che cancella l'effetto di pipeline — dà A −0,24, B +0,15, C +0,13:
A sta dal lato ematopoietico, B e C dal lato epiteliale. Concorda con i marcatori.

Questo identifica lignaggi, non nomi di linee cellulari. L'ipotesi più semplice per A
è Jurkat (T-ALL, maschile, CD3 di superficie, TAL1 da delezione STIL-TAL1); per B una
linea di epitelio pigmentato retinico tipo hTERT-RPE1; per C un carcinoma squamoso di
tipo esofageo o orale, dato che KRT4 e KRT13 sono specifici di mucosa squamosa non
cheratinizzante. Nessuna di queste attribuzioni è necessaria alla strategia: basta il
lignaggio.

**Conseguenza sulle priorità.** Nessuno dei tre contesti è eritroide: K562, l'unica
sorgente locale con copertura del pannello, è del lignaggio sbagliato per tutti e tre.
E nessuno dei tre è pluripotente: H1, KOLF2.1J e HIPSCI sono tutti contesti iPSC/ESC,
cioè un solo lignaggio che non corrisponde né ad A, né a B, né a C. L'audit precedente
li metteva in priorità 1–3 per copertura di bersagli e numero di donatori; per
**corrispondenza di contesto** valgono meno di una sorgente Perturb-seq in linea
linfoide T o epiteliale. Restano utili per ampiezza e per variazione fra donatori, non
come sorgente di trasferimento vicina.

## 4. Quanto segnale c'è davvero in K562 sui nostri bersagli

280 righe GWPS corrispondono a 272 bersagli unici. Il knockdown funziona: `pct_expr`
mediano −0,866, e 270/280 righe superano il 50% di abbattimento. Ma la risposta
trascrizionale misurabile è scarsa:

- energy test p < 0,05 in 154/280 righe (55%); p < 0,001 in 84 (30%)
- numero mediano di geni DE per riga: **5**; 90° percentile 71; 37 righe con zero
- riferimento sull'intero atlante GWPS: mediana 2 geni DE, 48% a p < 0,05

La copertura 272/300 non è segnale 272/300. Con 168 cellule mediane per riga la stima è
limitata dalla potenza, quindi questo è un limite inferiore sul segnale biologico — ma è
il segnale che possiamo effettivamente stimare. Per circa due terzi del pannello il
trasferimento da K562 non ha quasi nulla da trasferire.

## 5. Lo scorer era già installato e non era stato aperto

`cell-eval2 0.16.0` è nel venv, con il config ufficiale `configs/vcc2026.yaml`. Il
punteggio è `(u − b) / (r − b)` per metrica e contesto, media non pesata su 18 celle,
con `b` = baseline pubblicata e `r` = replicato split-half misurato. Quello che decide
la strategia non è la formula ma i **clamp**, che sono fortemente asimmetrici.

| Metrica | Direzione | Clamp basso | Nota |
|---|---|---|---|
| `pds_cosine` | ↑ | non vincolato | b = 0,5304 / 0,5284 / 0,5102 sui tre contesti ufficiali; r ≈ 1,00 (derivato) |
| `expr_mse_unbiased_capped_norm` | ↓ | **0,0** | nessun rischio al ribasso; aggregata come `ratio_of_sums` |
| `de_wilcoxon_lfc_nmae` | ↓ | **−6,0** | b ≈ 0,96; una tabella di LFC tutti nulli vale ≈ −0,04 |
| `..._direction_fidelity_yield_raw` | ↑ | non vincolato | b = 0,5015 (il caso), r = 0,8194 → fondo −1,58 / −2,68 / −1,85 |
| `..._direction_reach_raw` | ↑ | non vincolato | b = 0,0251, r = 0,9118 → fondo −0,05 / −0,12 |
| `de_wilcoxon_sig_jaccard` | ↑ | non vincolato | fondo −0,07 / −0,10 |

Fatti che ne discendono, tutti dal sorgente installato:

1. **Il PDS usa distanza coseno sul delta con segno**, quindi è invariante di scala.
   L'ampiezza della risposta prevista non conta per il PDS; conta solo la direzione nello
   spazio dei geni. Incollare i controlli dà esattamente 0,5000, cioè circa −0,065 di
   score: non costa quasi nulla e non rende nulla.
2. **Anche "non prevedere alcun cambiamento" è quasi gratuito su nmae** (circa −0,04).
   Il fondo −6 si raggiunge solo con log2FC grossolanamente sovradimensionati.
3. **Quattro metriche su sei sono di direzione o di ordinamento** (pds, fid, reach, jac).
   Le due di ampiezza o non hanno rischio (mse) o lo hanno solo in eccesso (nmae). La
   superficie di punteggio premia la direzione e punisce la sovrastima.
4. **`reach` è la metrica col miglior rapporto rischio/rendimento**: baseline 0,0251
   contro replicato 0,9118, con un fondo di −0,12. È anche la guardia contro l'astensione:
   un predittore che non chiama nulla porta `fidelity_raw` a 0,9999 ma resta a 0,005–0,05
   su `reach_raw`.
5. **`fid` è la metrica pericolosa**: il suo punto di non-abilità è il caso (0,5) e il
   fondo è −2,68. Chiamare geni significativi nella direzione sbagliata costa lì più che
   altrove.
6. **`control_source: real`**: l'effetto predetto è misurato contro le cellule di
   controllo *reali*. Qualsiasi differenza sistematica fra le nostre cellule generate e
   gli NTC reali diventa DE fittizio condiviso da tutte e 300 le perturbazioni, e **non si
   cancella nella baseline**. Generare trasformando cellule di controllo reali
   ricampionate, non da un modello parametrico stimato altrove.
7. **La correzione di rumore di campionamento su mse è limitata dalla varianza fra
   perturbazioni della sottomissione stessa** (#348). 400 cellule quasi identiche
   rinunciano a quella correzione: la dispersione per cellula deve essere realistica.

## 6. Come procedere

**P0 — Banco di prova locale, con dati veri.** Manca un *real bundle*: conteggi
perturbati più NTC in un qualunque contesto, per calcolare baseline e ancore di replicato
e confrontare modelli sulla stessa scala della gara. Il candidato più vicino per saggio e
pipeline è H1 2025 di Arc. I 25/300 bersagli in comune non sono un limite: rendono il
benchmark locale onestamente zero-shot. Primo risultato atteso: il punteggio di tre
baseline banali — incolla-controlli, risposta media del pannello, trasferimento per
bersaglio da K562 — sulla scala vera.

**P1 — Il modello a costo zero che non abbiamo ancora provato.** Abbiamo 55.200 cellule
di controllo reali sui tre contesti esatti della validazione. Danno tre cose che nessun
download fornisce: i moduli di co-espressione *specifici di quel contesto*, il modello di
rumore per cellula necessario alla generazione, e il gate DE con la sua distribuzione
nulla. Per ogni bersaglio, il suo intorno di co-espressione nel contesto è una previsione
a costo zero di quali geni si muovono — ed è esattamente il tipo di previsione che le
quattro metriche di direzione premiano. Da confrontare, su P0, contro il trasferimento
da K562.

**P2 — Dati perturbazionali di lignaggio corrispondente.** Cercare Perturb-seq CRISPRi
pubblico in linea linfoide T e in linee epiteliali. Questo sposta gli atlanti iPSC
(KOLF2.1J, HIPSCI) più in basso, non fuori: restano la migliore sorgente di variazione
fra donatori e di copertura di bersagli, ma su un lignaggio che non corrisponde a nessuno
dei tre contesti. Verificare disponibilità e licenza prima di pianificare volumi.

**P3 — Replogle a singola cellula solo per la dispersione.**
`k562_essential_raw_singlecell` (10,6 GB) basta per stimare il modello di conteggi e la
frazione di cellule che rispondono. I 65 GB del genome-wide non servono a quello scopo.

**P4 — Priori di conoscenza al posto dei dati mancanti.** Dato che solo circa un terzo del
pannello ha segnale specifico stimabile in K562, e che quattro metriche su sei sono di
direzione, un priore curato bersaglio → risposta attesa (complessi proteici, pathway,
regulon di fattori di trascrizione) è la leva col miglior rapporto fra valore e costo di
acquisizione. Va validato su P0 come tutto il resto.

**Postura di sottomissione, dalla sezione 5.** Decidere con forza sulla direzione,
comprimere l'ampiezza, calibrare il *numero* di chiamate DE sul numero tipico del
riferimento, mantenere realistica la dispersione per cellula. È una postura conservativa
sulle due metriche di ampiezza e aggressiva sulle quattro di direzione, che è esattamente
la forma dell'asimmetria misurata.

## 7. Limiti di questa revisione

Nessun modello allenato, nessun punteggio di leaderboard, nessun download eseguito.
L'identificazione dei contesti è di lignaggio, non di linea cellulare, e si basa su
marcatori e su un test di contrasto, non su un riferimento esterno appaiato. Le ancore
di replicato citate per `pds_cosine` sono derivate dai numeri misurati riportati nel
sorgente di cell-eval2, non misurate da noi. Il valore di `r` per nmae, mse e jaccard
resta ignoto: si ottiene costruendo P0. La disponibilità pubblica di Perturb-seq in linee
T ed epiteliali è un'ipotesi di ricerca, non una verifica.
