# R-REV — agire sulla revisione critica del 28 settembre

- **Stato:** in corso.
- **Aggiornato:** 29 settembre 2026, 11:35 (ora italiana), dalla sessione Claude `f2abd9a6`. Scritta alle 12:40
  dalla sessione cloud che ha fatto la revisione.
- **Assegnazione:** Claude (app desktop, sessione `f4f38e58`, sul portatile con la radice dati), dal 28/09
  alle 12:42 (ora italiana), su richiesta del proprietario in chat: §0 e le azioni in ordine, una alla volta.
  File di lavoro: questa scheda, il registro (R-020), gli indici dei report; output nelle categorie di D-046.
  Dal 28/09 alle 19:22 prosegue la sessione Claude `f2abd9a6` (app desktop, stesso portatile), perché la `f4f38e58` si
  è fermata al limite di spesa. Il proprietario ha chiesto in chat di procedere **in parallelo**: azione 2 (in corso),
  azione 3 sul portatile e azione 6 su Kaggle insieme, per arrivare prima a un modello (scheda [R-V2](modello-v2.md),
  ripresa alla stessa ora).
- **Mandato del proprietario**, in chat alla sessione cloud il 28/09 verso le 12:30: «ok ora devo passare
  ad un'altra sessione in locale, fai in modo che ci siano informazioni in repo in evidenza per farlo
  agire basandosi sulle tue analisi». Vale come via a lavorare su questa scheda. **Non** vale come via a
  invii, download, calcolo in cloud o push: quelli si chiedono in chat come sempre (LAVORO §2 e §3,
  CLAUDE.md).
- **Fonti:** la [revisione](../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md) (le
  criticità, con le fonti e il tipo di ogni affermazione) e la
  [valutazione delle critiche di Alfredo](../../reports/analisi/revisione_criticita_2026-09-28/ALFREDO_VCC_MINI.md).
  Qui non si ripetono gli argomenti: ogni azione rimanda al suo paragrafo. La revisione è di un agente,
  senza revisione umana, e non ha letto dati: la radice dati non era raggiungibile dalla sessione cloud.

## 0. Prima di tutto: portare questo lavoro nel `main` del portatile

La revisione, la riorganizzazione dei report (D-046) e questa scheda stanno sul branch
`claude/compassionate-babbage-gpgzyt` di GitHub, sopra il `main` delle 10:44 del 28/09 (`517c49e`). Il
`main` del portatile può avere commit e file non tracciati più recenti: sono lavoro di altri agenti, e
restano.

1. Guardare che cosa c'è di locale: `git status --short` e `git log --oneline origin/main..main`.
   Se ci sono modifiche non committate a file che il merge tocca, git rifiuta il merge. In quel caso si
   mettono da parte con `git stash push` e si riapplicano dopo con `git stash pop`, perché sono di altri
   agenti.
2. Unire:

   ```bash
   git fetch origin
   git -c merge.renameLimit=10000 merge origin/claude/compassionate-babbage-gpgzyt
   ```

   - Senza commit locali è un avanzamento veloce, senza conflitti.
   - Con commit locali, i conflitti possibili sono nei documenti vivi (PROGETTO, PIANI, REGISTRO,
     schede, INDICE): si tengono tutte e due le parti.
   - «CONFLICT (file location)» vuol dire un file aggiunto in locale dentro una cartella che D-046 ha
     spostato. Git lo mette già nella posizione nuova, nella categoria: si accetta con `git add` del
     percorso nuovo.
3. `ls reports/` deve mostrare solo le otto categorie, `README.md` e `CLAUDE.md`.
   - Una cartella rimasta fuori contiene file non tracciati scritti in una cartella che si è spostata
     (per esempio uscite di Kaggle scaricate dopo le 10:44). I file si spostano nella gemella, che
     `ls -d reports/*/<cartella>` trova, senza sovrascrivere quelli che ci sono già.
   - Una cartella nuova va nella sua categoria, con una riga nel README della categoria
     ([reports/CLAUDE.md](../../reports/CLAUDE.md)).
4. Uno script fuori dalla repo (agent hub, aiuti per scaricare da Kaggle) che scrive in
   `reports/<cartella>/` ora deve scrivere in `reports/<categoria>/<cartella>/`. Gli script dentro la repo
   sono già aggiornati.
5. Controllo documentale e suite, verdi prima di andare avanti. Un file non tracciato fuori posto lo
   nomina il controllo documentale, perché nessuna riga del registro lo copre; una cartella tracciata fuori
   categoria la nomina `test_live_tree`:

   ```bash
   python scripts/31_check_docs.py
   .\scripts\py.cmd -m unittest discover -s tests
   ```

6. Il push su GitHub solo con il via del proprietario.

### Esito del §0 (28/09, 12:42–12:59, Claude, sessione `f4f38e58`)

- **Stato locale prima dell'unione:** nessun commit locale oltre `origin/main`. Lavoro non committato di un altro agente
  (codex): in stage CP-0040, `biologia_architetture_2026-09-25` e righe di PROGETTO, REGISTRO, INDICE e di tre schede;
  non tracciato `audit_piani_dati_2026-09-26`. Copia di sicurezza fuori dalla repo, poi `git stash push`.
- **Unione:** avanzamento veloce su `81379a4`, poi `git stash apply`. Conflitti in PROGETTO, REGISTRO, `reports/CLAUDE.md`
  e nella scheda R-MODELLI, risolti tenendo le due parti: il testo di questo branch, più le righe e le sezioni
  dell'altro agente con i percorsi spostati nelle categorie. Le sue righe per il vecchio indice di `reports/CLAUDE.md`
  sono diventate righe di `reports/analisi/README.md`.
- **Cartelle rimaste fuori dalle categorie:** 124 cartelle. Contenevano 51 file ignorati o non tracciati (`__pycache__`,
  grandi `.npz` e `.h5ad` dello storico, lo zip di grok), spostati nelle gemelle senza sovrascrivere nulla; poi le
  cartelle vuote sono state tolte. `ls reports/` mostra solo le otto categorie, `README.md` e `CLAUDE.md`.
- **Script fuori dalla repo:** quelli dello scratchpad di questa sessione scrivevano in `reports/<cartella>/`; da ora
  scrivono in `reports/<categoria>/<cartella>/`.

## 1. Le azioni, in ordine

L'ordine differisce dal §6 della revisione per una ragione sola: la sessione locale legge la radice dati e
i worktree, che la sessione cloud non vedeva, e alcune cose rischiano di andare perse.

| # | Azione | Revisione | Serve | Uscita |
|---|---|---|---|---|
| 1 | Recuperare l'evidenza citata ma mai committata | §4.1, registro R-020 | il portatile | i file originali, committati; R-020 aggiornata |
| 2 | Tarare il proxy dei banchi sulle differenze ufficiali | §2.1, §2.3 | radice dati | `reports/trasferimento/taratura_proxy_<data>/` |
| 3 | Prova generale del 22 ottobre (F8 di R-V2) | §3.4 | radice dati; nessun invio | `reports/invii/prova_generale_<data>/` |
| 4 | Banco con lo scorer vero sui bersagli del pannello (non essenziali) | §2.5, §2.4, §2.7 | Colab, avviato dal proprietario | `reports/generatore_e_banchi/banco_k562_pannello_<data>/` |
| 5 | Profili basali sull'asse comune | §2.6 | radice dati | `reports/sorgenti/basali_asse_<data>/` |
| 6 | Misura decisiva per la rete relazionale | §3.2 | universi nella radice dati | `reports/modelli/covariazione_<data>/` |
| 7 | Percorso «stessa linea» e licenza di Orion | §3.3, §3.5 | decisioni del proprietario | identità solo nella radice dati |
| 8 | Codice di ricerca in un pacchetto testato | §4.2 | una decisione in DECISIONI | `src/vcc2026/` |

**Regola per chi propone un invio** (revisione §2.4 e §6, punto 1; proposta, da confermare con il
proprietario): se la differenza attesa sul riferimento sta sotto 0,005, il rumore del seme non permette di
leggerla. Un invio così si propone solo per un'informazione che solo il server dà, e lo si dice.

Ogni banco registra la regola di lettura **prima** di girare, in un file della sua cartella (CP-0030), e
riporta il tipo di ogni affermazione. Un «passa» su un proxy resta un'ipotesi finché non lo conferma lo
scorer vero o una replica (revisione §2.3).

### Azione 1 — l'evidenza mancante

Il registro, [scheda R-020](../REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository), elenca che
cosa manca e chi lo cita: l'audit di codex del 26/09, le schede R-018 e R-019, CP-0040, la previsione del
t21, il report `biologia_architetture_2026-09-25`.

- **Dove cercare:**
  - `git status --short`, `git stash list` e `git worktree list`;
  - `git log --all -- <percorso>` per ogni voce;
  - le cartelle di lavoro degli agenti (agent hub, sessioni di codex);
  - la radice dati.
- **Come committare:**
  - i file come sono stati trovati, con la data in cui sono stati scritti, nel messaggio;
  - nella categoria: l'audit e la biologia in `reports/analisi/`, la previsione del t21 in `reports/invii/`,
    con il nome di cartella citato;
  - CP-0040 in `docs/checkpoints/` con la sua riga nell'indice (il numero è riservato);
  - R-018 e R-019 nel registro;
  - poi le righe nei README delle categorie e nel registro.
- **Se una voce non si trova,** R-020 dice dove si è cercato. Non si ricostruisce.

**Esito (28/09, Claude, sessione `f4f38e58`):** quattro voci su cinque trovate sul portatile e committate come
trovate. La previsione del t21 non esiste: lo script che doveva scriverla non risulta eseguito. Dettagli e dove si è
cercato nella scheda [R-020](../REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository), che resta aperta solo
per quella citazione.

### Azione 2 — il proxy contro le differenze ufficiali

**Domanda:** il proxy su cui si leggono i banchi dal 25/09 (Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen, contro una
sorgente pubblica tenuta fuori) prevede il segno delle differenze ufficiali già misurate?

- **Materiale:**
  - le coppie a un fattore sono in `reports/invii/lezioni_invii_2026-09-28/coppie.csv` e nella sua
    [tabella](../../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md). Sopra il rumore del seme ce ne
    sono quattro: via CD4 (t10 − t08), più HCT116 (t11 − t08), e i due raddoppi d'ampiezza (t15 − t11,
    t16 − t15). Le altre stanno dentro il rumore. Il t11 cambia anche i pesi di K562 e CD4 rispetto al t08
    ([CP-0031](../checkpoints/0031-t11-punteggio-orion.md)): sul banco si ricostruiscono le ricette esatte,
    non «t08 più HCT116»;
  - le ricette in `configs/recipes/`;
  - il banco da cui partire, `reports/trasferimento/quattro_sorgenti_2026-09-26/four_sources_bench.py`,
    con i proxy fissati dai test in `tests/test_proxy_banchi.py`.
- **Disegno:**
  - le due ricette di ogni coppia si ricostruiscono sul banco;
  - una coppia che toglie o aggiunge una sorgente si legge solo con una verità diversa da quella sorgente.
    HEK293T non entra in nessuna delle ricette dal t08 al t16, quindi fa da verità per tutte e quattro le
    coppie sopra il rumore; le altre sorgenti danno letture in più dove non sono la sorgente che cambia;
  - si riportano anche i due membri da soli, contro `pds` e `nmae` ufficiali, perché il proxy non vede
    gli altri quattro.
- **Regola di lettura (proposta).** Se il proxy sbaglia il segno anche su una sola delle quattro coppie
  sopra il rumore, nessun candidato si propone più al proprietario sul solo proxy: serve il banco
  dell'azione 4. Si fissa, eventualmente diversa, nel protocollo prima di girare.
- **Chiusura:** report e checkpoint.

**Presa in carico (28/09, 18:45, Claude, sessione `f4f38e58`):** protocollo e regola scritti prima di girare in
[taratura_proxy_2026-09-28](../../reports/trasferimento/taratura_proxy_2026-09-28/RISULTATI.md), codice
`taratura_proxy.py` nella stessa cartella.

**Esito (28/09, 19:28, Claude, sessione `f2abd9a6`): non passa.** Sulla verità HEK293T il proxy legge con il segno
giusto t11 − t08 e t15 − t11; non legge t10 − t08 (la stima punta dall'altra parte) né t16 − t15. Per la regola:
nessun candidato si propone più al proprietario sul solo proxy, serve il banco dell'azione 4. Report
([Esito](../../reports/trasferimento/taratura_proxy_2026-09-28/RISULTATI.md)) e
[CP-0041](../checkpoints/0041-proxy-contro-ufficiale.md): l'azione 2 è chiusa.

### Azione 3 — la prova generale del 22 ottobre

È il filone F8 della [scheda R-V2](modello-v2.md), libero: la presa in carico si annota anche lì.

- **I passi** sono quelli di LAVORO §7, «Il giorno del rilascio», su A/B/C trattati come nuovi:
  - una copia dei controlli in una cartella a parte (`raw/controls/` non si tocca);
  - 300 bersagli finti, scelti con un seme. Una parte ha effetti negli universi, una parte in nessuna
    sorgente, per provare i ripieghi dello stadio 100;
  - si arriva al `.vcc` verificato dallo stadio 48. Nessun invio.
- **Scritto prima di girare:**
  - che cosa fa γ = 1 con un pannello nuovo, e quale cache si usa, pannello o universi (revisione §3.4);
  - come si fissa l'ampiezza per D/E/F: una regola calcolabile dai soli controlli (revisione §2.4), non
    l'1,576 di A/B/C.
- **Si misura:**
  - la durata di ogni stadio;
  - il disco al picco;
  - quanti bersagli hanno effetti in almeno una sorgente;
  - ogni punto in cui la pipeline dipende ancora dal pannello di A/B/C.
- **Chiusura:** il `.vcc` e l'elenco dei difetti trovati, ciascuno corretto con il suo test; checkpoint.

**Presa in carico (28/09, 19:22, Claude, sessione `f2abd9a6`):** piano e preregistrazione in
`reports/invii/prova_generale_2026-09-28/`, scritti prima di girare; gli stadi girano sul portatile dopo la lettura di
r1, che occupa la CPU.

### Azione 4 — il banco con lo scorer vero sui bersagli del pannello

L'unico banco a sei membri fatto finora (HepG2) usa bersagli dello schermo essenziale, che trasferiscono
più di quelli di gara (revisione §2.5).

- **Verità e sorgenti:**
  - la verità sono le cellule K562 genome-wide dei bersagli del pannello, dall'uscita dello stadio 71
    (272 dei 300 coperti; nessuno nei pannelli *essential*);
  - le sorgenti sono CD4, HCT116 e HEK293T. K562 resta fuori, perché è la verità;
  - i bracci si costruiscono con il codice di produzione, come
    `reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/build_effects.py`.
- **Il generatore (verificato nel codice):** lo stadio 73 genera i bracci solo con `ControlModel`. Lo
  stadio 75 ha il prefisso `g0:` per il generatore di trial-01, che è quello degli invii. Si porta `g0:` nel
  73, con il suo test, oppure si usa il 75 con le cellule K562 come verità, leggendo il codice.
- **I bracci:**
  - la forma del t22 senza K562, a 1,576, a metà e al doppio;
  - un'ampiezza per contesto che porta il numero di geni rilevabili a quello di un riferimento, con la
    soglia calcolata dai controlli del contesto (`match_detectable` dello stadio 100);
  - l'esclusione dei geni stimati da meno di due universi, cioè la parte del t23 che conta
    ([ablazione](../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md));
  - il generatore con e senza `--gene-dispersion` (revisione §2.7).
- **Semi:** almeno tre semi del generatore. Si riporta la varianza fra semi accanto al bootstrap sui
  bersagli.
- **Colab:** il job lo avvia il proprietario (LAVORO §3).
- **Chiusura:** report e checkpoint. L'esito decide ampiezza ed esclusione per D/E/F, nella prova
  dell'azione 3.

### Azione 5 — i profili basali sull'asse comune

Verificato nel codice: `reports/trasferimento/trasferimento_appreso_2026-09-26/basal_profiles.py` calcola i
CPM delle sorgenti su tutti i geni di ogni file, prima di restringerli all'asse; quelli di A/B/C sono
sull'asse Flex.

- **Chi li legge:**
  - la ricetta del t23 (`gene_share`) e il blocco `pooling` dello stadio 100, tramite
    `processed/basal_sources_2026-09-26.csv`;
  - i banchi con `--basal`;
  - i modelli che leggono il contesto.

  La ricetta del t22 non legge profili basali (`configs/recipes/t22.json`).
- **Da fare:**
  - ricalcolare i CPM sui soli geni dell'asse, in un file nuovo accanto al vecchio;
  - misurare il fattore per sorgente;
  - misurare di quanto cambiano le soglie (≥ 5 CPM, `detectable_threshold`).
- **Chiusura:** report. Se i modelli che leggono il contesto debbano cambiare file si decide con il
  proprietario.

### Azione 6 — la misura decisiva per la rete relazionale

È la proposta 1 della scheda R-V2 per quando si riparte, e la revisione (§3.2) la mette prima di ogni rete
nuova.

- **Domanda:** chi si muove con chi, cioè la correlazione fra geni delle risposte su molti bersagli, è più
  conservato fra linee dell'effetto del singolo bersaglio?
- **Dati:** gli universi nella radice dati, bersagli del pannello esclusi.
- **Controlli:**
  - coppie di linee dello stesso laboratorio contro laboratori diversi, perché laboratorio e linea
    coincidono (Alfredo, P18);
  - bersagli permutati come nullo;
  - metà contro metà come tetto.
- **Prima di girare:** la regola, cioè quale valore dice «sì, c'è una base».
- **Chiusura:** report. R-V2 è in pausa per scelta del proprietario: l'esito si porta a lui.

**Presa in carico (28/09, 19:22, Claude, sessione `f2abd9a6`):** R-V2 è ripresa dal proprietario alla stessa ora.
Protocollo e regola in `reports/modelli/covariazione_2026-09-28/`, scritti prima di girare; il calcolo va su Kaggle.

**Esito (29/09, 11:22): inconclusivo per W1; lettura «uso» no** ([CP-0043](../checkpoints/0043-misura-decisiva-relazioni.md)).
La via delle relazioni non prevede la risposta a un knockdown né fra linee né nella stessa linea; l'effetto dello
stesso bersaglio sì. Portato al proprietario alle 11:25: la rete relazionale non parte, si punta sulle azioni 3 e 4.
L'azione 6 è chiusa.

### Azione 7 — la stessa linea e la licenza di Orion

Serve prima la decisione del proprietario: R-V2, «Domanda strategica aperta».

- **Se dice sì:**
  - le impronte di A/B/C (stadio 99, `reports/gara/context_fingerprints_2026-09-22/`) si confrontano con
    DepMap/CCLE. L'espressione DepMap 24Q4 è già in locale; dati di genotipo sarebbero un download, e
    serve il via;
  - le identità e i confronti restano nella radice dati, mai nella repo pubblica;
  - prima, si leggono le regole della gara sull'uso di linee identificate.
- **Orion** (CC-BY-NC-SA, due sorgenti su quattro della ricetta):
  - chiedere agli organizzatori tocca al proprietario;
  - intanto si può registrare una ricetta di riserva senza Orion, con la sua previsione;
  - l'invio consuma quota e ha bisogno del via.

### Azione 8 — il codice di ricerca in un pacchetto testato

- **Proposta (revisione §4.2):**
  - proxy, bootstrap e lettore degli universi in `src/vcc2026/`, con test di parità contro i file di oggi;
  - i report restano la registrazione di come hanno girato.
- **Prima:** una decisione in DECISIONI, perché D-040 tiene nell'albero solo il codice che produce o
  valuta un invio.

## 2. Per il proprietario

- **Il branch:** portare questo branch in `main` e dare il via al push (§0).
- **Il branch `alfredo`:** su GitHub c'è ancora un branch `alfredo`, fermo al 24/09 e già contenuto in
  `main`. La regola «un solo branch» vorrebbe cancellarlo o archiviarlo come tag.
- **Alfredo:**
  - la [valutazione](../../reports/analisi/revisione_criticita_2026-09-28/ALFREDO_VCC_MINI.md) si può
    girare ad Alfredo; il suo §4 risponde alle sue domande;
  - condividere con lui gli universi (P17) è una decisione del proprietario; i dati restano comunque
    fuori dalla repo pubblica.
- **Le azioni 7 e 8** e la regola sugli invii sotto 0,005.

## 3. Rapporto con le altre schede

- **[R-V2](modello-v2.md)** (in pausa dalle 10:40 del 28/09 per scelta del proprietario):
  - l'azione 3 è il suo F8;
  - l'azione 6 è la sua proposta 1;
  - gli esiti in attesa su Kaggle si leggono là, con le loro regole. Un «passa» va replicato prima di
    crederci (revisione §3.2).
- **[S-INVII](invii-finale.md):**
  - la regola sulle differenze sotto 0,005;
  - l'esito delle azioni 3 e 4, che alimenta LAVORO §7.
- **[R-DATI](dati-affidabilita.md):** le azioni 1 e 5 toccano il suo ambito.

## 4. Criterio di chiusura

Ogni azione si chiude da sola, con la sua evidenza. La scheda si chiude quando le azioni 1–4 hanno report e
checkpoint e le azioni 5–8 sono fatte oppure rinviate dal proprietario, con la data scritta qui.
