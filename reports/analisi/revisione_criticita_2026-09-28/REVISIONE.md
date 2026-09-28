# Revisione critica del progetto — 28 settembre 2026

- **Redatto da:** agente (Claude, sessione cloud), su richiesta del proprietario in chat del
  28/09: «analizza le criticità e i possibili bias nel progetto». Revisione umana: no.
- **Base:** `main` al commit `517c49e` (28/09, 10:44), più la riorganizzazione di D-046 fatta
  nella stessa sessione.
- **Che cosa è:** una revisione. Legge i report, le ricette, il codice e i punteggi già nel
  repository. **Nessuna misura nuova sui dati**: la radice dati (`C:/Users/ferra/vcc2026-data`)
  non era raggiungibile da questa sessione, e nessun banco è stato eseguito. I soli calcoli nuovi
  sono quelli sul rumore del §3, fatti sui punteggi ufficiali già registrati e mostrati per intero.
- **Tipi di affermazione:** **misurato** (con la fonte), **interpretazione**, **ipotesi**,
  **proposta**. La valutazione delle critiche di Alfredo sta in
  [ALFREDO_VCC_MINI.md](ALFREDO_VCC_MINI.md).

## 0. In una pagina

| # | Criticità | Gravità | Tipo |
|---|---|---|---|
| 1 | La ricetta di trasferimento è satura e la sua direzione gene per gene è quasi ortogonale al vero; i prossimi punti non vengono da altre sorgenti o ampiezze | alta | misurato + interpretazione |
| 2 | Le decisioni di ricerca dal 25/09 si prendono su un proxy di due membri su sei, contro verità pubbliche rumorose, mai confrontato con le differenze ufficiali | alta | misurato (definizione) + interpretazione |
| 3 | Molti confronti in sequenza, regole «positivo su 3 linee su 4» con poca potenza, intervalli che ignorano semi e correlazione fra bersagli | media-alta | interpretazione |
| 4 | Il rumore del punteggio ufficiale è stimato su una coppia; ampiezza e sorgenti sono state scelte su A/B/C e rischiano di non valere per D/E/F | alta | calcolo + interpretazione |
| 5 | I banchi più vicini alla gara usano bersagli essenziali; il pannello non ne ha | media | misurato |
| 6 | Piattaforma (gara in Flex, sorgenti in 3') e normalizzazione dei profili basali su insiemi di geni diversi | media | misurato + verificato nel codice |
| 7 | L'artefatto del generatore di trial-01 è intrecciato con l'ampiezza, e l'esperimento incrociato proposto il 24/09 non è mai stato fatto | media | misurato + interpretazione |
| 8 | Evidenza citata ma assente dal repository; codice di ricerca non testato nascosto nei report; stati di decisioni e schede non aggiornati | alta per il processo | verificato |
| 9 | La prova generale del 22 ottobre non è fatta, e alcune scelte dipendono dal pannello di A/B/C | alta per la scadenza | verificato |
| 10 | Licenza non commerciale di Orion negli invii, non verificata con gli organizzatori | da chiarire | verificato |

Quello che il progetto fa bene, e va conservato: previsioni e regole registrate prima (CP-0030),
un fattore alla volta, correzioni che lasciano leggibile la storia, audit incrociati fra famiglie
di agenti, parità byte per byte quando si tocca la pipeline. Le criticità qui sotto non tolgono
valore a questo metodo; dicono dove il metodo misura meno di quanto sembra.

## 1. Dove siamo, in numeri

- **Misurato.** Il riferimento della ricetta del t22 è 0,14207 (t22 e t24); il rango all'invio
  va da 337 a 361. La mediana dei primi 100 della classifica è 0,219, dei primi 10 0,273
  ([lezioni](../../invii/lezioni_invii_2026-09-28/RISULTATI.md)).
- **Misurato.** I guadagni ufficiali sono venuti in due modi: sorgenti nuove quando l'ampiezza era
  bassa (circa +0,010 ciascuna) e ampiezza (+0,037 e +0,030). Dal t16 i cambi a un fattore valgono
  +0,0012, +0,0020, +0,0016, −0,0010, e il solo seme +0,0016.
- **Misurato.** La `mse` grezza dei nostri invii segue 1 + E/4786, con E l'energia prevista
  ([risposta comune, r2](../../trasferimento/risposta_comune_2026-09-26/RISULTATI.md)): il termine
  incrociato fra previsione e verità è trascurabile. Tutte le prime 100 squadre hanno la `mse`
  scalata positiva; noi 0 in ogni invio.
- **Interpretazione.** Contro la mediana dei primi 100 perdiamo circa 0,038 sulla `mse`, 0,020 sul
  PDS, 0,012 su reach, 0,009 sulla fedeltà ([lezioni](../../invii/lezioni_invii_2026-09-28/RISULTATI.md)).
  Più della metà del divario sta in membri che la nostra famiglia di previsioni non può muovere
  con l'ampiezza.

## 2. Bias nella valutazione

### 2.1 Il proxy vede due membri su sei, e non è mai stato tarato sulle differenze ufficiali

- **Misurato (definizione).** Dal banco delle quattro sorgenti del 26/09 in poi, quasi ogni regola
  si legge su Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen contro una sorgente pubblica tenuta fuori
  (`reports/trasferimento/quattro_sorgenti_2026-09-26/four_sources_bench.py`, `W_PDS, W_NMAE`). I pesi
  sono «le pendenze ufficiali dei due membri sulla media dei sei, per unità di grezzo», cioè vengono
  dalle ancore (`reports/trasferimento/trasferimento_gerarchico_2026-09-26/RISULTATI.md`). Fedeltà,
  reach, Jaccard e `mse` non entrano.
- **Misurato.** Dal t15 al t16 il guadagno ufficiale è venuto per quasi tutto dai membri DE (+0,171
  scalato contro +0,009 del PDS, CP-0037): proprio quelli che il proxy non vede.
- **Misurato, tre confronti fra proxy e ufficiale:**
  - t15 → t16: il modello del banco prevedeva +0,005…+0,026 di PDS; l'ufficiale ha dato +0,0037
    (CP-0037);
  - t20 → t22 (HEK293T): proxy +0,011 con K562 fuori e +0,001 con CD4 fuori; ufficiale +0,0016,
    dentro il rumore;
  - riscalatura: l'ablazione del t23 preferisce non riscalare (il proxy peggiora), mentre alzare
    l'energia ha sempre aiutato il punteggio ufficiale fino al t16.
- **Interpretazione.** Il proxy può guidare scelte che il punteggio ufficiale non premia, e scartare
  scelte che premierebbe. Non è un difetto di nessun banco preso da solo: è che nessuno l'ha tarato.
- **Proposta, a costo quasi nullo.** Calcolare il proxy, con lo stesso codice dei banchi, per ogni
  coppia ufficiale a un fattore già misurata (t08→t10, t08→t11, t11→t15, t15→t16, t16→t20, t20→t22,
  t22→t25), usando i file di effetti già nella radice dati; riportare accordo di segno e
  correlazione. Finché questo non c'è, un «passa» del proxy va letto come ipotesi, non come candidato.

### 2.2 La verità dei banchi è una sorgente pubblica rumorosa

- **Misurato.** Il tetto di rumore delle verità è basso: fra metà dei donatori CD4 la correlazione
  per bersaglio è 0,04–0,11 (CP-0028); metà contro metà di VIPerturb-seq 0,110 di coseno
  ([ponte Flex](../../sorgenti/ponte_flex_2026-09-28/RISULTATI.md)); nelle sorgenti Replogle la somma
  degli SE² supera l'energia osservata (1,7–3 volte), per cui la correzione per il rumore fallisce
  ([atlante](../../trasferimento/atlante_2026-09-26/RISULTATI.md)).
- **Interpretazione.** Una verità rumorosa comprime ogni differenza verso zero, e favorisce i bracci
  che restringono: un braccio con meno energia perde meno contro il rumore. Parte dei «non passa»
  può essere mancanza di potenza, e parte dei «passa» dei bracci che tolgono energia (esclusione,
  quota condivisa) può venire da qui.
- **Proposta.** Accanto a ogni Δ riportare il tetto della verità usata (metà contro metà); preferire
  verità con repliche (le 19 linee HIPSCI, i donatori CD4, K562 essential contro genome-wide).

### 2.3 Molti confronti, regole a bassa potenza, intervalli troppo stretti

- **Misurato (conteggio).** Dal 25 al 28/09 i report registrano più di quindici banchi con regole
  proprie e diverse decine di bracci; diverse ipotesi sono nate dal braccio «più vicino» di un banco
  precedente (la quota condivisa dall'atlante r1, dichiarato nel report).
- **Interpretazione, tre effetti che si sommano:**
  - le linee tenute fuori sono quattro, e due vengono dallo stesso laboratorio (HCT116, HEK293T):
    «positivo su almeno 3 di 4» succede per caso circa una volta su tre, e l'n efficace è più vicino
    a 3 che a 4;
  - il bootstrap è sui bersagli: non contiene la varianza fra semi (lo dicono le regole dell'encoder)
    né la correlazione fra bersagli dello stesso complesso (Mediator, ribosoma), quindi gli
    intervalli sono più stretti del vero;
  - con molti confronti in parallelo e ipotesi scelte dopo i risultati, qualche «passa» è atteso
    per caso. Il t23 ne è l'esempio: la regola è passata, l'ablazione ha mostrato che il meccanismo
    dichiarato non era quello che funzionava.
- **Proposta.** Un registro di tutte le regole registrate con esito (passa, non passa, non letta);
  un'adozione solo dopo una replica su bersagli nuovi, come si è fatto con r2 dell'ablazione;
  bootstrap a blocchi per famiglia di geni; almeno tre semi per i modelli appresi, come chiedeva
  la regola di r1 della rete (il seme 2 non è mai partito).

### 2.4 Il rumore del punteggio ufficiale, e la scelta dei parametri su A/B/C

- **Calcolo (nuovo, su punteggi registrati).** Da una sola coppia di semi, |t24 − t22| = 0,0016,
  l'intervallo al 95 % per la deviazione standard σ della differenza fra due invii è molto largo:
  0,0016 / 2,24 ≈ 0,0007 fino a 0,0016 / 0,031 ≈ 0,05. Se invece si trattano come puro rumore le
  cinque differenze a un fattore sotto soglia (+0,0012, +0,0020, +0,0016, +0,0016, −0,0010), la loro
  radice quadratica media è 0,0015, con un intervallo al 95 % per σ di 0,0009…0,0037.
- **Interpretazione.** La seconda stima è un tetto (se quei cambi avessero un effetto vero, il rumore
  sarebbe più piccolo) e le differenze non sono indipendenti (t22 compare in tre). Insieme dicono
  che la soglia ±0,005 vale fra 1,3 e 5 deviazioni standard: ragionevole, ma **nessun invio singolo
  può distinguere effetti sotto 0,003–0,005**. Spendere le due quote giornaliere su cambi di quella
  taglia compra poca informazione.
- **Interpretazione, sul set finale.** L'ampiezza 1,576 è stata scelta raddoppiando sul punteggio di
  A/B/C; l'ottimo dipende dal generatore e dal numero di geni DE per bersaglio, che cambiano con
  contesto e pannello. Anche le squadre in testa, con 26–53 invii, rischiano di aver tarato sulla
  validazione più di quanto il finale confermerà. Per noi il rischio è concreto: sul banco HepG2
  raddoppiare la forma t19 non è distinguibile da zero (+0,015, intervallo sullo zero).
- **Proposta.** Per D/E/F fissare l'ampiezza con una regola calcolabile dai soli controlli (per
  esempio la mediana dei geni rilevabili, già nello stadio 100 come `match_detectable`), provata
  prima sul banco con lo scorer vero; non copiare 1,576.

### 2.5 Bersagli essenziali nei banchi più vicini alla gara

- **Misurato.** Nessuno dei 300 bersagli è nei pannelli *essential* di K562 e RPE1, e i bersagli del
  pannello hanno forza tipica (percentile mediano 0,54 nel K562). I bersagli essenziali hanno
  un'energia mediana doppia e trasferiscono di più (coseno K562×CD4 0,022 contro 0,008)
  ([atlante](../../trasferimento/atlante_2026-09-26/RISULTATI.md)).
- **Misurato.** L'unico banco con lo scorer vero (HepG2) usa bersagli dello schermo essenziale e il
  solo K562 come sorgente ([banco HepG2](../../generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md)).
- **Interpretazione.** Il banco più vicino alla gara sovrastima quanto trasferisce la ricetta sui
  bersagli della gara. L'atlante esclude già gli essenziali: è la scelta giusta.
- **Proposta.** Un banco con lo scorer vero su bersagli non essenziali: K562 genome-wide a singola
  cellula (già letto dallo stadio 71) come verità, CD4 e le due Orion come sorgenti.

### 2.6 Piattaforma e normalizzazione dei profili basali

- **Misurato.** L'asse ufficiale è un pannello di sonde Flex (niente RPL/RPS, HLA, XIST, MALAT1);
  tutte le sorgenti tranne VIPerturb-seq sono in 3'. A parità di bersagli, metà contro metà di uno
  schermo Flex 0,110, Flex contro 3' 0,030
  ([ponte Flex](../../sorgenti/ponte_flex_2026-09-28/RISULTATI.md)).
- **Verificato nel codice.** I profili basali delle sorgenti sono in CPM calcolati su **tutti** i geni
  di ciascun file, prima di restringerli all'asse
  (`reports/trasferimento/trasferimento_appreso_2026-09-26/basal_profiles.py`, funzione `cpm`); quelli
  di A/B/C sono sull'asse Flex. Le sorgenti 3' contano anche i geni che l'asse non ha (RPL/RPS fra
  tutti), quindi i loro CPM sull'asse sono più bassi di un fattore per sorgente.
- **Interpretazione.** Ogni quantità che confronta livelli basali fra sorgenti e contesti eredita uno
  scarto sistematico: le soglie «espresso sopra 5 CPM», le differenze di espressione dei modelli a
  cancelli (β1 negativo e stabile in sei fit, forse anche per questo), il corpus dell'encoder che
  mescola 3', Flex e DepMap. È lo stesso difetto che Alfredo segnala nel suo P4.
- **Proposta.** Ricalcolare i CPM di tutti i profili sui soli geni dell'asse ufficiale (o sui geni
  comuni), e misurare di quanto cambia il fattore; per il ponte di piattaforma un fattore per gene
  da VIPerturb-seq, dichiarato come stima da un solo schermo.

### 2.7 L'artefatto del generatore e l'ampiezza

- **Misurato.** A effetto nullo il generatore di trial-01 dichiara 462 / 453 / 684 geni significativi
  per bersaglio in A / B / C, l'82 % «in su»; le cellule vere quasi nessuno
  ([generator_null](../../generatore_e_banchi/generator_null_2026-09-17/)). Sono il 57–67 % delle
  chiamate del t15.
- **Verificato.** L'esperimento incrociato ampiezza × generatore proposto il 24/09 (stadio 45 con
  `--gene-dispersion`, che porta l'artefatto a 5–31 chiamate) non è mai stato inviato.
- **Interpretazione.** Una parte del guadagno dell'ampiezza può venire dalla diluizione delle
  chiamate spurie, non da segni giusti. Sul set finale l'artefatto dipende dai profili basali di
  D/E/F: l'ampiezza che lo compensava su A/B/C può non compensarlo.

## 3. Bias nel metodo e nella strategia

### 3.1 La ricetta è satura; il margine sta altrove

- **Misurato.** Riponderare sorgenti, bersagli, geni o programmi non batte la media a pesi uguali
  nei banchi proxy; i profili di linee diverse si somigliano poco (0,02–0,07 di coseno); il segno
  giusto è al 51–56 % contro il 53,8 % dei bersagli scambiati (CP-0034).
- **Interpretazione.** Il trasferimento fra linee porta discriminazione (PDS) ma quasi nessuna
  informazione gene per gene. Il margine sta nella `mse` (la risposta comune del contesto più la
  parte propria del bersaglio con l'ampiezza giusta) e nei membri DE, non in un'altra sorgente.

### 3.2 Il contesto letto dai controlli non ha ancora mostrato valore

- **Misurato.** Modello a cancelli, rete, encoder e Tahoe T1 non passano; dove battono la versione
  cieca non battono quella con il contesto scambiato; la perdita sulla famiglia tenuta fuori sale dopo
  50–100 passi ([modelli](../../modelli/README.md)).
- **Interpretazione.** Con 4–13 contesti di poche famiglie, in cui laboratorio e piattaforma coincidono
  con la linea, un modello impara lo studio più che la biologia. La misura proposta dalla sessione del
  28/09 (la co-variazione fra geni è più conservata fra linee dell'effetto del singolo bersaglio?) è il
  test giusto da fare prima di reti più grandi: costa poco e dice se la rete relazionale ha una base.
- **Rischio di bias di conferma (interpretazione).** L'encoder è stato valutato con un solo seme e
  la parte K562/CD4 non è ancora letta; la tornata r2 della rete cambia insieme contesti, geni e
  calibrazione (lo dice la sua regola). Un eventuale «passa» su una di queste va replicato prima di
  essere creduto.

### 3.3 Dati della stessa linea

- **Ipotesi (della scheda R-V2).** Chi è in testa può usare Perturb-seq pubblici della stessa linea
  dei contesti, dopo averla identificata. È anche l'unica leva che l'atlante indica come forte: la
  stessa linea in due esperimenti tiene 0,16 di coseno, un'altra linea 0,02–0,07.
- **Verificato.** Il confronto delle impronte genetiche di A/B/C con DepMap/CCLE, proposto il 24/09,
  non è stato fatto; le identità restano ipotesi da marcatori.
- **Proposta.** Preparare adesso, su A/B/C come prova, il percorso «impronta → linea candidata →
  sorgenti pubbliche di quella linea», così che il 22/10 sia una decisione del proprietario e non un
  cantiere. Le regole della gara sull'uso di linee identificate vanno lette prima.

### 3.4 Il 22 ottobre

- **Verificato.** La prova generale F8 della scheda R-V2 non è fatta. LAVORO §7 elenca i passi, e gli
  stadi accettano `--controls-dir`, `--contexts` e `--targets-csv`.
- **Verificato nel codice e nel report del 24/09.** Con γ = 1 la ricetta toglie a ogni sorgente la sua
  risposta media sui bersagli del pannello presenti nella cache: con un pannello nuovo cambia anche la
  risposta tolta. Con gli universi (migliaia di bersagli) come cache cambierebbe ancora: la scelta va
  fatta per iscritto prima.
- **Interpretazione.** Il 22/10 sono 14 giorni con due invii al giorno: un difetto di pipeline scoperto
  quel giorno costa più di qualunque guadagno di ricetta ottenuto adesso.

### 3.5 Licenza di Orion

- **Verificato.** Orion (HCT116, HEK293T) è CC-BY-NC-SA-4.0; il proprietario l'ha ammessa negli invii
  il 23/09 «per decisione del proprietario, non per verifica della licenza presso gli organizzatori»
  (`reports/invii/trial_2026-09-22/autorizzazioni.md`). Due delle quattro sorgenti della ricetta sono
  Orion.
- **Proposta.** Chiedere agli organizzatori prima del set finale, o preparare una ricetta di riserva
  senza Orion con il suo punteggio misurato.

## 4. Processo e documentazione

### 4.1 Evidenza citata ma assente dal repository

Verificato con la storia di git (`git log --all`): questi materiali sono citati da file committati ma
non sono mai entrati in nessun commit. Probabilmente stanno in un worktree di un agente o solo sul
portatile.

| Che cosa manca | Chi lo cita | Che cosa conteneva, secondo chi lo cita |
|---|---|---|
| `reports/audit_piani_dati_2026-09-26/` | scheda R-V2; `trasferimento_appreso_2026-09-26/RISULTATI.md` e `lct_bench5.py`; `ricerca_sorgenti_2026-09-26/RISULTATI.md`; `tests/test_transfer_model.py` | l'audit di codex che ha trovato i centri calcolati prima degli split nel trasferimento appreso (r3–r4) |
| schede R-018 e R-019 del registro | `trasferimento_appreso_2026-09-26/RISULTATI.md`, la riga del registro, `modello_contesto_2026-09-27/agenti/disegno_claude2.md` | la perdita dei centri (R-019); R-018 non è descritta |
| `docs/checkpoints/0040-biologia-contesti-donatori.md` | `trasferimento_gerarchico_2026-09-26/RISULTATI.md` §5 | la varianza fra donatori di CD4 (1,65–2,17), dalla sessione `76a3a45e` |
| `reports/biologia_architetture_2026-09-25/` | `modello_contesto_2026-09-27/agenti/disegno_claude2.md` | STAT2 predetto dalle altre linee con IFNB e non con IFNG |
| `reports/prediction_t21_2026-09-26/prediction.json` | `invii/trial_2026-09-26/submission_texts.md` | la previsione registrata del t21, mai generato |

**Proposta.** Recuperarli dal portatile o dai worktree e committarli così come sono, con la data in
cui sono stati scritti; CP-0040 va lasciato libero per quel checkpoint (questa revisione non lo usa).
Il registro ha ora la scheda R-020 con questo elenco. Da questa sessione il controllo documentale
verifica i link anche nelle schede dei piani e negli indici dei report, dove il link all'audit mancante
è stato trovato.

### 4.2 Il codice di ricerca nei report

- **Verificato.** Circa 22.000 righe di Python stanno nei report, contro circa 10.800 fra `scripts/` e
  `src/`. Diversi file sono librerie per altri banchi, importati per percorso: i proxy
  (`modulo_cis/cis_bench.py`, `banco_varianti/noise_sim2.py`), il lettore degli universi
  (`atlante/atlas_bench.py`), lo stimatore degli universi nuovi (`universo_kolf/kolf_effects.py`).
  Fino a questa revisione solo `kolf_sums.py` aveva un test; ora li hanno anche i proxy
  (`tests/test_proxy_banchi.py`, aggiunto il 28/09), che verifica fra l'altro che il passo di
  profilo dei proxy (`noise_sim2.realise`) dia gli stessi numeri di `inference.predicted_profile`,
  quello che lo stadio 45 applica. La mappa è in [reports/README.md](../../README.md).
- **Interpretazione.** L'affermazione «nell'albero resta solo il codice che produce o valuta una
  sottomissione» (D-040) è vera ma fuorviante: il motore delle decisioni di ricerca sta fuori
  dall'albero e fuori dai test. Un difetto in `noise_sim2.realise` o in `cis_bench.pds_proxy`
  toccherebbe ogni banco dal 25/09.
- **Proposta.** Portare in un pacchetto testato (per esempio `src/vcc2026/banco/`, con una regola del
  test di `test_live_tree.py` che accetti i banchi come chiamanti vivi) i proxy, il bootstrap e il
  lettore degli universi, con un test di parità numerica contro i file di oggi; i report restano la
  registrazione di come hanno girato.

### 4.3 Stati non aggiornati (corretti in questa sessione, D-046)

- **D-012** («l'ampiezza si calibra su bersagli tenuti fuori, non si sceglie») era ancora `attiva`,
  contraddetta da D-042 (l'ampiezza degli invii si sceglie sul punteggio ufficiale).
- **D-034** («il generatore delle sottomissioni è `ControlModel`») era `da-verificare`: tutti i migliori
  invii usano il generatore di trial-01, e il t14 con `ControlModel` ha abbassato la fedeltà.
- **D-031** e **D-032** descrivevano un ordine di lavoro e un protocollo non più seguiti.
- Le schede S-INVII (26/09), R-DATI (25/09), R-MODELLI e R-SWITCH (24/09) non erano aggiornate.
- Il report nella radice del repository diceva che il migliore era il t15; il README portava in coda
  il piano per fasi dell'11 settembre.

### 4.4 Altro

- **Autorità dei commit.** Tutto il lavoro degli agenti è committato a nome del proprietario: chi ha
  fatto che cosa sta solo nel testo. Proposta: una riga `Agent:` nei messaggi di commit.
- **Una cartella condivisa, molti agenti, nessun lock** (PIANI §3 lo dice). I risultati dei worktree
  isolati possono non tornare mai in `main` (§4.1).
- **Volume.** Circa 1,1 MB di Markdown nei report, 1.000 righe di registro, 1.200 di decisioni: le
  informazioni cruciali si perdevano. Gli indici per categoria di D-046 servono a questo.

## 5. Che cosa è cambiato in questa sessione

Riorganizzazione (D-046), senza toccare il contenuto di nessuna evidenza:
- i 126 elementi di `reports/` sono in otto categorie, con i nomi invariati, e un README per categoria
  con data, nocciolo, validità e peso di ogni cartella; `reports/README.md` dice che cosa leggere per
  primo e quale codice di ricerca altri importano;
- le otto analisi dell'11–15/09, le sezioni storiche del README e il vecchio §3–§4 di PROGETTO sono in
  `docs/storico/`; il report della radice è in `reports/analisi/sintesi_stato_2026-09-24/`;
- i percorsi vecchi scritti in checkpoint e report si seguono con una regola sola (il nome della
  cartella un livello più giù), nel controllo documentale e in `config.repo_file`, usato dallo stadio
  100 per le ricette; un test lo verifica per ogni ricetta;
- negli script di ricerca sono cambiate solo le righe che calcolano la radice del repository e i
  percorsi fra cartelle: i 95 script che rispondevano a `--help` prima rispondono anche dopo;
- PROGETTO ha un §3 e un §4 nuovi e un §5 con le criticità; stati delle decisioni e delle schede
  corretti; il controllo documentale copre schede, indici e storico.

## 6. Proposte in ordine, fino al set finale

Da decidere con il proprietario; nessuna è avviata.

1. **Non spendere invii su differenze sotto 0,005.** Le quote vanno a cambi grandi o a informazione che
   solo il server dà (per esempio una seconda replica di seme, se il proprietario vuole restringere il
   rumore).
2. **Tarare il proxy sulle differenze ufficiali già misurate** (§2.1). Non spende invii: usa file
   di effetti già nella radice dati.
3. **Banco con lo scorer vero su bersagli non essenziali** (§2.5), con più semi del generatore: serve a
   decidere ampiezza, esclusione dei geni e riscalatura sui sei membri.
4. **Prova generale del 22/10 (F8)**, su A/B/C trattati come nuovi: dal bundle al `.vcc`, con la scelta
   scritta su γ e sulla cache (pannello o universi).
5. **Impronte di A/B/C contro DepMap/CCLE** e percorso «stessa linea» pronto per la decisione del
   proprietario (§3.3); verifica delle regole della gara e della licenza di Orion (§3.5).
6. **Misura decisiva per la rete relazionale** (§3.2) prima di altre architetture; tre semi per
   qualunque regola di un modello appreso.
7. **Recuperare l'evidenza mancante** (§4.1) e **portare in un pacchetto testato** il codice di ricerca
   che altri banchi importano (§4.2).
8. **Profili basali sull'asse comune** (§2.6), prima di altri modelli che leggono il contesto.

## 7. Limiti

- Nessun dato letto: ogni numero viene da un file del repository, citato; dove non c'è un file, lo dice.
- I calcoli sul rumore del §2.4 assumono differenze gaussiane fra invii; la seconda stima tratta come
  nulli cambi che possono non esserlo, e usa differenze non indipendenti.
- Il conteggio di banchi e bracci del §2.3 è approssimato dai report; non è stato ricostruito un
  registro completo delle regole.
- Revisione di un agente, senza revisione umana. Andrebbe controllata da un agente di un'altra famiglia,
  come chiede la scheda R-V2 per ogni affermazione diretta al proprietario.
