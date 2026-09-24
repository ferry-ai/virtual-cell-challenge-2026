# Stato del progetto e interpretazioni da rivedere — 24 settembre 2026

- **Scritto:** 24 settembre, 15:30 UTC circa, **prima** dei punteggi di t16 e t17 (gli invii
  partono alle 00:05 UTC del 25). Le previsioni del §5 valgono solo per questo.
- **Redatto da:** agente (Claude), su richiesta del proprietario in chat. Revisione umana: no.
- **Che cosa è:** una sintesi da leggere per prima. Riunisce due analisi dello stesso giorno:
  - quella di Claude: `reports/analisi_2026-09-24/ANALISI.md`, con i conti in
    `reports/analisi_2026-09-24/calcoli.json`;
  - l'audit di ChatGPT sulle cache delle sorgenti, come il proprietario l'ha riassunto in chat. Il
    suo report (`reports/audit_stato_2026-09-24/ANALISI.md`) e il suo checkpoint
    (`docs/checkpoints/0034-audit-segni-e-ampiezza.md`) sono sul portatile. Questa sessione non li
    ha letti: i numeri presi da lì sono marcati «audit ChatGPT».
- **Che cosa non è:** non è un checkpoint, non cambia ricette né decisioni e non spende quota. Le
  correzioni proposte al §4 passano dal proprietario.
- **Tipi di affermazione:** **misurato** (un numero ricalcolabile, con la fonte),
  **interpretazione**, **ipotesi**, **proposta**.

## 1. In una pagina

1. **Il migliore resta il t15, +0,107533** (rango 436,
   [CP-0033](docs/checkpoints/0033-t15-ampiezza-doppia.md)). t16 e t17 sono generati e impacchettati
   (commit `24c4494`). Il §0 della mappa li dà ancora «in generazione»: è indietro.
2. **I punti mancanti non sono dove guardiamo.** Contro la mediana delle prime dieci del 16
   settembre mancano 0,131 punti. Il PDS, il membro che oggi ci porta, ne spiega solo 0,026;
   MSE (0,042) e `reach` (0,027) pesano di più (§2).
3. **I nostri effetti trasferiti portano discriminazione, ma poca informazione gene per gene.**
   Due strade indipendenti arrivano qui:
   - nello spazio della MSE il coseno con la verità è circa 0,04 (Claude);
   - sui segni, l'informazione specifica del bersaglio vale circa 3 punti sopra un controllo a
     bersagli scambiati (audit ChatGPT).
4. **L'ampiezza sta coprendo, almeno in parte, un artefatto del generatore di trial-01.** A effetto
   nullo fa 429–675 chiamate per bersaglio, all'81% «in su». Il test giusto è un esperimento
   incrociato ampiezza × generatore (§6).
5. **Il 50% non è la soglia giusta per i segni**, e alcune letture della fedeltà vanno riviste (§4).
6. **Il percorso per D/E/F dipende ancora da A/B/C** in due punti: l'asse genico e la centratura
   (§4.7).

## 2. Dove stanno i punti

**Misurato.** Mediana delle prime dieci della classifica del 16 settembre
(`reports/leaderboard_2026-09-16/rows.csv`) contro gli scalati ufficiali del t15
(`reports/trial_2026-09-24/status_U1K3SZuq7w5cef9lBKsn.json`). Il divario è in punti del
complessivo, cioè diviso per sei.

| membro | prime dieci, scalato (grezzo) | t15, scalato (grezzo) | divario |
|---|---|---|---|
| MSE | 0,252 (0,749) | 0 (1,579) | **0,042** |
| `reach` | 0,232 (0,284) | 0,067 (0,139) | **0,027** |
| PDS | 0,761 (0,843) | 0,607 (0,774) | **0,026** |
| fedeltà | 0,011 (0,516) | −0,119 (0,477) | **0,022** |
| `nmae` | 0,165 (0,901) | 0,084 (0,950) | 0,013 |
| Jaccard | 0,008 (0,033) | 0,006 (0,032) | 0,000 |

La somma è 0,131; con il t15 fa 0,238, contro una mediana delle prime dieci di 0,240.

**Interpretazione.**
- I tre membri su cui gli altri prendono punti e noi no (MSE, `reach`, fedeltà) leggono le
  cellule generate gene per gene.
- La fotografia ha otto giorni: rileggere la classifica non costa quota.

## 3. Che cosa misura lo scorer

Letto nel codice di `cell-eval2` 0.16.0, la versione del contratto
(`reports/scorer/vcc2026_contract.json`). I riferimenti al codice sono nel report di Claude.

- **La base è un oracolo.** È la risposta media vera delle perturbazioni del contesto, uguale per
  tutti i bersagli. Uno scalato 0 vuol dire «bravo quanto chi conosce la risposta media vera», non
  «nessuna abilità».
- **MSE.** Si calcola sui pseudobulk, senza il gene bersaglio e corretta per il rumore; si
  aggrega come rapporto di somme. **1,0 vuol dire «ha previsto il controllo».** Noi stiamo a
  1,13–1,58; la base è circa 0,99.
- **PDS.** È il coseno fra delta previsti e delta veri, senza i 300 geni del pannello. Il coseno
  non vede la scala: l'ampiezza conta solo perché riduce il peso relativo di ciò che non scala con
  essa, cioè il rumore di campionamento delle 400 cellule e gli scarti del generatore. Il suo
  guadagno satura.
- **Fedeltà.** Vale `k / max(n_pred, n_conf)`. Il numeratore confronta il segno di **tutte** le
  nostre chiamate con il segno del log fold change vero, anche sui geni non significativi nel
  riferimento. Mescola quindi precisione di segno, prevalenza dei segni e copertura.
- **`reach`.** Si guardano solo i geni significativi nel riferimento, ordinati per il **nostro**
  `p_adj`. Conta la purezza di segno della testa di quella classifica.

**Misurato dagli organizzatori, riportato nelle docstring dello scorer, non ricalcolato da noi:**
- nel contesto A ci sono 100.771 coppie significative, cioè circa 336 geni per bersaglio in media;
- il 12–30% dei bersagli ha meno di 10 geni significativi;
- i bersagli con almeno 10 geni significativi sono 272 / 229 / 218 in A / B / C;
- il rumore è il 46–55% della distanza grezza;
- il gene bersaglio è il gene che si muove di più nel 57–66% delle perturbazioni.

## 4. Interpretazioni da rivedere

### 4.1 «La MSE non conta perché è tosata»

- **Misurato.**
  - Le prime dieci stanno a 0,65–0,85 grezzo, sotto la base.
  - Dal t11 al t15, con gli stessi effetti e lo stesso generatore, la nostra MSE va da 1,129 a
    1,579.
  - Nelle proxy dello stadio 98, fra tipi cellulari diversi, l'ampiezza che minimizza l'errore
    quadratico è 0,008–0,05, con uno skill di 0,0001–0,0017 (`reports/orion_2026-09-23/r5/transfer.json`).
- **Interpretazione.** Il modello `MSE(a) = m0 + P·a² − 2·C·a`, con `m0 ≈ 1`, dà un coseno di
  circa 0,04. L'ampiezza ottima per la MSE è circa 0,02, e la MSE minima è circa 1,0. **La MSE è
  tosata per i nostri effetti, non per principio.** Nessuna ampiezza uniforme la porta sotto la
  base; serve un'informazione per bersaglio di altro tipo (§6).

### 4.2 «Raddoppiare l'ampiezza fa sbagliare meno spesso la direzione» (CP-0033, §5)

- **Misurato.**
  - A effetto nullo il generatore di trial-01 fa 460 / 429 / 674 chiamate mediane per bersaglio in
    A / B / C, per l'81% «in su». Le cellule vere, allo stesso test, ne fanno 0
    (`reports/generator_null_2026-09-17/summary.json`).
  - Queste chiamate sono il 74–88% delle chiamate del t11 e il 57–67% di quelle del t15
    (`reports/prediction_calls_2026-09-23/`).
- **Interpretazione.** La fedeltà è salita soprattutto perché le chiamate da effetti hanno diluito
  quelle da artefatto, e forse anche per più copertura (audit ChatGPT; §4.3). Che il segno delle
  nostre chiamate sia più spesso giusto non è dimostrato.

### 4.3 «Precisione di segno sopra o sotto il 50%»: la soglia è sbagliata

- **Misurato, audit ChatGPT.** HCT116 tenuto fuori:
  - la miscela delle altre sorgenti ha il segno giusto nel 56,6% dei casi;
  - con i bersagli scambiati si arriva già al 53,8%;
  - prevedere sempre «aumento» sugli stessi geni dà il 63,6%.
- **Conseguenze, anche per l'analisi di Claude:**
  - il 50% non è il caso. Il riferimento giusto è la prevalenza dei segni sui geni chiamati, e
    l'informazione specifica del bersaglio va misurata contro i bersagli scambiati;
  - il paragone fra la precisione delle chiamate da effetti stimata sui punteggi ufficiali (circa
    0,53) e lo stadio 103 (0,52–0,55) **non è una conferma indipendente**: i due numeri mescolano
    prevalenza e specificità. Claude lo ritira;
  - la stima di circa 0,44 per le chiamate da artefatto non va letta come «sotto il caso». La
    lettura corretta è un'**ipotesi**: sono chiamate sempre «in su» su geni che nei dati di gara
    scendono più spesso di quanto salgano;
  - il modello di Claude che separa le chiamate da artefatto da quelle da effetti assume
    `n_pred ≥ n_conf`. Con circa 336 geni significativi medi in A e 543 chiamate nel t11 è
    un'ipotesi fragile, quindi le due precisioni stimate sono confuse con la copertura.

### 4.4 Il riferimento stesso è rumoroso

- **Misurato, audit ChatGPT:**
  - fra due gruppi di donatori CD4 l'accordo di segno è solo il 57,2%;
  - sui geni più affidabili alcuni confronti fra sorgenti arrivano al 62–66%.
- **Misurato:** la correlazione per bersaglio fra le metà dei donatori CD4 è 0,04–0,11 (CP-0028).
- **Interpretazione.** Le misure nello spazio degli effetti sono limitate dal rumore del
  riferimento, e rumore e differenze biologiche non sono ancora separati. Serve usarle con due
  controlli, bersagli scambiati e repliche, e distinguere i geni significativi nel riferimento
  (quelli che contano per `reach`) da tutti gli altri (che contano anche per la fedeltà).

### 4.5 Il t14 non chiude la questione della fedeltà

- **Misurato:**
  - il t14 aveva 136 / 213 / 218 chiamate mediane (`reports/prediction_calls_2026-09-23/t14/`);
  - nel contesto A i geni significativi sono in media circa 336 per bersaglio.
- **Interpretazione.**
  - Il t14 era con buona probabilità nel regime che paga il silenzio, cioè la seconda lettura
    lasciata aperta da CP-0032.
  - La frase del §0 della mappa «Contraddetto dal t14» perde questa seconda lettura.
  - **Proposta:** riportare entrambe le letture.

### 4.6 D-042 attribuisce all'ampiezza un effetto del generatore

- **Misurato:**
  - D-042 dice che in `ControlModel` alzare l'ampiezza ha abbassato il PDS, ma nel t14 sono
    cambiati insieme generatore e ampiezza;
  - dentro `ControlModel`, dal t02 al t03, l'ampiezza doppia ha alzato il PDS da 0,609 a 0,649,
    anche lì con un secondo cambio.
- **Proposta:** scrivere che l'effetto dell'ampiezza in `ControlModel` non è separato.

### 4.7 Il percorso per D/E/F dipende da A/B/C

- **Misurato, verificato nel codice:**
  - `official_axis()` (`src/vcc2026/genes.py`) legge sempre `raw/controls/gene_names.csv` e
    richiede 18.533 simboli;
  - `--controls-dir` non cambia l'asse negli stadi 45, 76, 98 e 100. Se l'asse finale fosse
    diverso, gli stadi si fermerebbero con un errore, non sbaglierebbero in silenzio;
  - con γ = 1, `mix` sottrae la media di ogni sorgente sui bersagli del pannello presenti nella
    cache (`AxisTable.common`). **Un pannello nuovo cambia anche la risposta tolta.**
- **Misurato, stadio 103** (`reports/direzione_2026-09-24/direction.json`): γ = 0 dà segni
  migliori di γ = 1 per tre sorgenti tenute fuori su quattro. HCT116 passa da 0,48–0,50 a 0,56;
  K562 non cambia. Va rimisurato contro i bersagli scambiati: fra le due linee Orion il vantaggio
  può essere solo prevalenza di segno condivisa.
- **Misurato, audit ChatGPT:** il §0 della mappa è arretrato su t16 e t17.

### 4.8 Scelte della ricetta mai provate da sole

- **Effetti grezzi invece che ristretti.**
  - Scelti il 22 settembre per parità con trial-01, e mai confrontati
    (`reports/multisource_2026-09-22/PRIMA_DEI_RISULTATI.md`).
  - «Lo shrinkage è inattivo» (CP-0004) era stato misurato con un altro stimatore e in un'altra
    metrica.
  - `mix` usa l'affidabilità `n/(n+100)` solo per pesare le sorgenti fra loro: non restringe mai
    verso zero un bersaglio misurato male.
- **Gli stessi effetti per A, B e C.**
  - CD4 pesa circa il 43% anche nei contesti epiteliali, dove le proxy dicono che trasferisce
    peggio: 0,59–0,63 contro 0,76–0,78 di K562.

### 4.9 Identità dei contesti

- **Ipotesi da marcatori** (`reports/context_fingerprints_2026-09-22/fingerprints.json`):
  - B ha il profilo di una linea cervicale HPV-positiva, del tipo di HeLa: femminile, p16
    altissimo, niente E-caderina, vimentina alta, 5p guadagnato. LIN28B è assente, e questo va
    contro HEK293T;
  - A somiglia a una T-ALL maschile del tipo di Jurkat;
  - C somiglia a un carcinoma squamoso maschile.
- **Interpretazione.** Nessuna linea Orion coinciderebbe con un contesto di validazione.

## 5. Previsioni registrate prima dei punteggi di t16 e t17

**Proposta di lettura, non misura.** Si aggiungono alle previsioni ufficiali
(`reports/prediction_t16_2026-09-24/prediction.json`, `reports/prediction_t17_2026-09-24/prediction.json`)
e non le sostituiscono.

| invio | membro | atteso | come si legge |
|---|---|---|---|
| t16 | MSE grezza | 3,2–3,8; circa 3,44 se `m0 = 1` | con t11, t15 e t16 si ricava `m0` (formula in `reports/analisi_2026-09-24/ANALISI.md` §4). Un `m0` fra 0,95 e 1,05 conferma il §4.1 |
| t16 | PDS | sale meno che dal t11 al t15, da +0,005 a +0,02 | un guadagno di +0,035 o più smentisce la saturazione |
| t16 | fedeltà | 0,49–0,51 | il valore dipende anche dalla copertura (§4.3): non si legge come precisione di segno |
| t16 | `nmae`, `reach` | `nmae` 0,90–0,94, `reach` in salita | — |
| t17 | complessivo | la sola crescita di ampiezza vale circa +0,002 (energia degli effetti +6,7%, audit ChatGPT) o circa +0,0045 (ampiezza nominale +8,8%) | un t17 fra +0,005 e +0,008 sopra il t15 non si può attribuire a HEK293T. Oltre ciò che vale la crescita dell'ampiezza, il guadagno va all'intera modifica, perché 22 bersagli su 300 cambiano ampiezza di oltre il 20% (audit ChatGPT) |

## 6. Priorità

In ordine. Le prime quattro non spendono quota, o ne spendono poca.

1. **Stadio 83 su t16 e t17**, prima dei punteggi.
   - Costo: nessun invio, pochi minuti per file.
   - Serve a sapere quante chiamate fa ciascuno, e quindi a leggere fedeltà e t17.
2. **Diagnostiche dei segni con due controlli** (audit ChatGPT): bersagli scambiati e repliche.
   - Si separano i geni significativi nel riferimento da tutti gli altri.
   - Vale per ogni misura futura: grezzi contro ristretti, γ, pesi.
   - Costo: nessun invio.
3. **Esperimento incrociato ampiezza × generatore** (audit ChatGPT). È anche il test dell'ipotesi
   del §4.2.
   - t15 (0,394) e t16 (0,788) sono già i bracci con il Poisson.
   - Mancano due invii con lo stadio 45 `--gene-dispersion`, che esiste già e non è mai stato
     inviato. A effetto nullo porta l'artefatto da 429–675 a 5–31 chiamate
     (`reports/dispersion_2026-09-23/RISULTATO_NULLO.md`).
   - Prima dell'invio, lo stadio 83 sul pilota.
   - **Previsione:** senza artefatto il raddoppio di ampiezza guadagna meno in fedeltà e `reach`.
4. **Asse genico parametrico** lungo tutta la pipeline (audit ChatGPT), e una risposta media
   indipendente dal pannello, oppure γ = 0.
   - Serve prima del 22 ottobre, non prima dei prossimi invii.
5. **Grezzi contro ristretti, poi pesi per contesto, poi γ.** Prima fuori quota con i controlli del
   punto 2, poi un invio per fattore.
6. **La strada verso la MSE**, fuori quota e in parallelo:
   - un'ampiezza per bersaglio dall'accordo fra sorgenti;
   - un test dell'ipotesi degli «assi di stato»: i delta veri starebbero su pochi assi condivisi,
     con carico diverso per bersaglio. È un'ipotesi. Spiegherebbe perché le prime dieci hanno MSE
     0,65–0,85 ma PDS solo 0,82–0,87.
   - Prima prova: nella cache r5, la correlazione fra sorgenti dei carichi per insieme di geni
     contro quella gene per gene.
7. **Preparazione del 22 ottobre:**
   - verificare se i punteggi su D/E/F saranno visibili durante la fase finale;
   - identificare le linee con le impronte genetiche contro DepMap/CCLE;
   - separare le scelte generiche da quelle tarate su A/B/C.

## 7. Che cosa non fare

Le docstring dello scorer descrivono tre emissioni che guadagnano punti senza biologia (#343, #348,
#351), tutte chiuse o limitate nella 0.16.0:
- geni del pannello «accesi» per il PDS;
- somme per gruppo bloccate con dispersione finta per la correzione della MSE;
- geni sotto soglia che rivelano il segno.

Non vanno inseguite. Per la stessa ragione, il vantaggio delle prime dieci sulla MSE non va letto
come prova di biologia.

## 8. Note pratiche

- **Suite dei test.** L'errore «`cell_eval2.config` non trovato» è quasi certamente d'ambiente: il
  modulo esiste nella 0.16.0. Si esegue con `.\scripts\py.cmd -m unittest discover -s tests`, che
  usa il venv del progetto; per controllo, `.\scripts\py.cmd -c "import cell_eval2.config"`.
- **Pull sul portatile.** I commit di Claude sono su `feat/multi-source-transfer`. `docs/REGISTRO.md`
  ha una riga nuova sopra `reports/direzione_2026-09-24/`. Se l'audit di ChatGPT ha aggiunto righe
  nello stesso punto, nel conflitto si tengono tutte e due.
- **Controllo documentale.** In questa sessione `python scripts/31_check_docs.py` segnala solo due
  problemi che c'erano già. Riguardano `reports/candidate_verification/pilot/cd4_D1_Rest_64.h5ad`,
  escluso da git e presente solo sul portatile.

## 9. Limiti

- Nessun numero qui è un punteggio VCC nuovo: i soli punteggi sono quelli ufficiali già nel
  repository.
- I modelli dei §4.1 e §4.3 sono interpretazioni. Si basano su due punti ufficiali e su mediane di
  20 bersagli per contesto.
- I numeri marcati «audit ChatGPT» vengono dal riassunto del proprietario. Questa sessione non ha
  letto i file.
- Le identità di linea sono ipotesi da marcatori; nessun confronto con DepMap è stato fatto.
