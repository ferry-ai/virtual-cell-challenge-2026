# Pulizia della struttura, 30 settembre 2026

Claude (Claude Code, sessione `a1ec75f0`), dalle 16:05 del 30/09; orari letti con `date`. Il
proprietario ha chiesto in chat quattro tappe: unificare worktree e branch; nomi più esplicativi e
una struttura a indice; togliere l'obsoleto; progettare i test di orientamento degli agenti. Via
fino all'implementazione, con commit locali e **senza push**; il via esplicito serve prima di
agire nella tappa 1 e prima di lanciare agenti nella tappa 4.

**Tipo di affermazioni.** Inventari, conteggi, hash e date sono **misurati** con i comandi citati,
in sola lettura. Le classi e le azioni sono **proposte** finché la riga «Esito» di una tappa non
dice che sono state eseguite.

## Registro delle tappe

Una riga a fine tappa, con il commit che la chiude.

| Tappa | Stato | Commit | Che cosa |
|---|---|---|---|
| 1 | inventario e proposta (16:25); eseguita dopo il via (17:29–17:35) | `581f264`, `9f0f2ea` | da 19 worktree e uno stash a 2 worktree di Codex tenuti dal proprietario, nessuno stash: §1.4 |
| 2 | fatta dopo la tappa 1; ora dei commit in `git log` | `b254929`, `bc54bbf` | `LAVORO` → `PROCEDURE` con un reindirizzamento testato; nove righe di indice corrette sulle fonti: §2 |
| 3 | fatta; il punto 4 secondo la scelta del proprietario | `6c7814f`, poi il commit che aggiunge questa riga | sei script di job archiviati; 25 voci del registro a `storico` e 7 con la riserva; una regola per i checkpoint corretti; R-MODELLI chiusa: §3 |

## 1. Worktree, branch e stash

### 1.1 Inventario (misurato il 30/09 alle 16:23)

Comandi: `git worktree list --porcelain`, `git branch -a`, `git stash list`, e per ogni worktree
`git status`, `git log main..HEAD`, `git ls-files --others` (con e senza gli ignorati), date di
modifica; per ogni file non committato l'hash del contenuto (`git hash-object`, senza scrivere)
confrontato con tutti gli oggetti raggiungibili da `main` e con il file allo stesso percorso,
anche un livello più giù per le categorie del 28/09. Per i worktree dell'hub, il confronto blob per
blob con il `diff.patch` che l'hub salva a fine esecuzione. Il risultato completo è
[inventario_worktree.json](inventario_worktree.json), prodotto da
[inventario_worktree.py](inventario_worktree.py).

`main` è a `9e4408d`, 26 commit avanti a `origin/main`. Classi: **(a)** niente di unico rispetto a
`main`; **(b)** commit unici; **(c)** modifiche non committate o file non tracciati unici.

| # | Worktree | HEAD | Ultima modifica | Classe | Che cosa ha di unico |
|---|---|---|---|---|---|
| 1–3 | hub `20260927-143643-v2-gated-model` (claude2), `-145651-v2-gated-bench` (codex), `-181506-v2-hipsci-sums` (claude2) | staccato, in `main` | 27/09 | (a) | niente: esecuzioni fallite senza modifiche |
| 4–11 | hub `-142516-v2-kolf-ingest`, `-144723-v2-gated-model-codex`, `-165427-v2-kolf-effects`, `-183334-v2-hipsci-codex`, `-193129-v2-rsums-pack`, `-204227-v2-network-design-r2`, `20260928-003503-v2-tahoe-dmso`, `-032819-v2-tahoe-arms` | staccato, in `main` | 27–28/09 | (c) solo di forma | 1–8 file non committati ciascuno, ma **ogni contenuto è in un commit di `main`**: identico oggi, o in una versione poi corretta dalla sessione che ha lanciato il worker |
| 12 | hub `20260926-001005-v2-f3-ctj` (codex, fallita) | staccato, in `main` | 26/09 | (c) | `src/vcc2026/ctj.py`, prima bozza (13 KB), sostituita da quella del run 13 |
| 13 | hub `20260927-135336-v2-ctj-frozen` (codex) | staccato, in `main` | 27/09 | (c) | cinque versioni intermedie mai committate: il `result.md` del worker, `scripts/105_ctj_bench.py` e `tests/test_ctj.py` (in `main` più lunghi), due righe di `scripts/CLAUDE.md` e `src/vcc2026/CLAUDE.md` |
| 14 | hub `20260927-181528-v2-network-design` (claude2, fallita) | staccato, in `main` | 27/09 | (c) | una bozza di `contesti.csv`, poi rifatta nel run 11 |
| 15 | hub `20260928-014223-v2-context-encoder` (claude2, fallita) | staccato, in `main` | 28/09 | (c) | due righe di indice e registro per `encoder_contesto_2026-09-28/`, entrate in `main` in altra forma |
| 16 | `~/.codex/worktrees/atlas-transfer-pilot` | branch `codex/atlas-transfer-pilot`, `a0ab5fb`, in `main` | 19/09 15:51 | (c) | il pilota non committato di Codex del 19/09: stadio 96, `atlas_transfer.py`, due test, 16 file di report e log (20 file, 1,9 MB) e 72 `.npz` ignorati (124 MB). Mai in `main`; `docs/ARCHIVIO.md` lo lascia al proprietario dal 24/09 |
| 17 | `~/.codex/worktrees/ipsc-transfer` | staccato, `e4edcd9`, in `main` | 29/09 17:37 | (c) | **il lavoro R-IPSC di Codex del 29/09, mai in `main`**: la scheda `docs/piani/replica-ipsc.md`, la cartella `reports/trasferimento/ipsc_replica_2026-09-29/` (protocollo, esecuzione, validazione, consenso all'upload di un pacchetto da 945 MB su un dataset Kaggle privato, codice r1–r3, log del job r1 fallito) e le sue righe in PIANI, REGISTRO, `docs/piani/CLAUDE.md` e nell'indice di `trasferimento/`; 20 file in stage e 5 non tracciati |
| 18 | `vcc2026-refactor` | branch `refactor/pulizia`, `51a9c60` | 19/09 12:52 | (b) già archiviata | 22 commit fuori da `main`, **tutti sotto il tag `archivio/refactor-pulizia-2026-09-19`** (stesso commit). Ignorato: un `.h5ad` di 1,6 MB con lo stesso sha256 della copia in `reports/storico/candidate_verification/pilot/`. `docs/ARCHIVIO.md` dà il branch per ritirato dal 24/09, ma resta perché il worktree lo tiene |
| 19 | `C:/Users/ferra/wt8` | staccato, `14015fd`, in `main` | 28/09 00:15 | (a) | niente; creato il 27/09 alle 01:45 |

Oltre ai worktree:
- **Stash** `stash@{0}`, 28/09 12:44, «local work of other agents before merging the cloud branch»:
  20 file. I 12 nuovi (CP-0040 e `biologia_architetture_2026-09-25/`) sono in `main` identici; delle
  righe aggiunte ai sette documenti condivisi, le sole mai entrate in `main` differiscono per il
  prefisso di categoria del 28/09 (verificato riga per riga su REGISTRO, schede e indici). **(a)
  nel contenuto**, ma il commit dello stash non ha altro riferimento.
- **Branch remoti** `origin/alfredo` (24/09) e `origin/claude/compassionate-babbage-gpgzyt` (28/09):
  0 commit fuori da `main`. Toglierli su GitHub richiede un push, fuori da questo mandato.
- **Nove cartelle di metadati orfane** in `.git/worktrees/` (`wt_check`…`wt_check3`, `wt_f19e447`,
  `wtc`…`wtf`, 26–27/09, circa 5 KB ciascuna, senza `gitdir`): ereditano un permesso di negazione
  in scrittura e cancellazione (letto con `icacls`), per questo `git worktree prune` non le toglie.
  Innocue.
- **Sessioni attive** fra le 16:05 e le 16:25: tre sessioni Claude, tutte inattive (`ListAgents`); l'app Codex è
  in esecuzione (processi dal 28–29/09). L'ultimo file scritto nel worktree 17 è del 29/09 alle
  17:37, ma **non posso stabilire se la chat Codex `01a0ec7c` sia chiusa**: decide il proprietario.

**I worktree dell'hub hanno già una copia del loro lavoro.** A fine esecuzione l'hub salva in
`runs/<run>/<agente>/diff.patch` tutte le modifiche, file nuovi compresi (`git add -A`, poi
`git diff --cached --binary`), e `hub.py clean` toglie solo i worktree, lasciando rapporti e patch.
Per tutti i 15 lo stato attuale coincide con il `diff.patch`: nessuna modifica dopo la fine.

### 1.2 Proposta

In quest'ordine; ogni passo si verifica prima del successivo.

1. **Radice dati, prima di togliere qualunque cosa**, in
   `C:/Users/ferra/vcc2026-data/archivio_repo/2026-09-30/worktree/`, come fatto la notte del 30/09
   per ciò che è uscito dall'albero; manifest con sha256 nel commit di chiusura, hash riletti a
   destinazione:
   - worktree 16: i 20 file non tracciati e i 72 ignorati (126 MB), ai loro percorsi relativi;
   - worktree 12–15: `diff.patch`, `result.md`, `meta.json` e `prompt.md` dei quattro run con
     bozze uniche (circa 0,5 MB), perché la cartella `runs/` dell'hub si può ripulire.
2. **Worktree 1–15**, con la procedura dell'hub (`control/CLAUDE.md`, «Commands»):
   `py -3 hub.py clean <run>` da `C:/Users/ferra/agent-hub/control`, uno per run. Il comando esegue
   `git worktree remove --force` e `git worktree prune`; rapporti e `diff.patch` restano.
3. **Worktree 16**, dopo il passo 1: `git worktree remove --force` (i file sono nella radice dati)
   e `git branch -d codex/atlas-transfer-pilot` (già tutto in `main`, `-d` basta).
4. **Worktree 18**: `git worktree remove`, poi `git branch -D refactor/pulizia`; il tag
   `archivio/refactor-pulizia-2026-09-19` punta allo stesso commit, e l'`.h5ad` ignorato ha una
   copia identica nell'albero principale.
5. **Worktree 19**: `git worktree remove C:/Users/ferra/wt8`.
6. **Stash**: tag annotato `archivio/stash-altri-agenti-2026-09-28` sul suo commit `8a8bbef`, poi
   `git stash drop`. Il contenuto è già in `main`; il tag costa nulla e lo tiene raggiungibile.
7. **Worktree 17, R-IPSC di Codex: lo decide il proprietario.** Tre strade:
   - **(A, se la chat Codex è chiusa)** committare in `main` il lavoro com'è, a nome di Codex
     (D-048): la cartella del report al suo posto, la scheda, e solo le sue righe riportate a mano
     su PIANI, REGISTRO, `docs/piani/CLAUDE.md` e l'indice di `trasferimento/`, che nel frattempo
     sono cambiati; controllo di privacy come la notte del 30/09; poi togliere il worktree;
   - **(B)** salvarlo come patch nella radice dati e togliere il worktree: il lavoro esce dalla
     repo;
   - **(C, se la chat è attiva o nel dubbio)** lasciarlo com'è.
8. **Registrazione**: una sezione in [ARCHIVIO](../../../docs/ARCHIVIO.md) con le righe di ciò che
   esce (tag, branch, worktree, dove stanno i file); l'elenco misurato di
   [AGENTI](../../../docs/AGENTI.md) §3 sostituito dal risultato; la voce sui worktree in PROGETTO §0,
   «Che cosa aspetta una decisione del proprietario», aggiornata.

**Non si toccano:** i branch remoti (push), le nove cartelle orfane di `.git/worktrees/` (permesso
di negazione; se il proprietario vuole, le toglie a mano), le cartelle `runs/` dell'hub e ogni
altro file dell'hub.

### 1.3 Le due attività pianificate della catena ritirata

Rilette il 30/09 fra le 16:05 e le 16:25 (orari di `date` prima e dopo) con `Get-ScheduledTask`,
in sola lettura: «VCC2026 Ciclo giornaliero», pronta,
ultima esecuzione il 30/09 alle 15:02 con esito 1, prossima l'1/10 alle 08:30; «VCC2026 Guardiano»,
pronta, ultima il 28/09 alle 07:13 con esito 1. Entrambe lanciano `scripts/ciclo.cmd`, che non è
nell'albero ([AGENTI](../../../docs/AGENTI.md) §2). Toglierle spetta al proprietario; il comando,
con una copia delle definizioni prima di toglierle:

```powershell
$d = 'C:\Users\ferra\vcc2026-data\archivio_repo\2026-09-30\attivita_pianificate'
New-Item -ItemType Directory -Force $d | Out-Null
foreach ($n in 'VCC2026 Ciclo giornaliero', 'VCC2026 Guardiano') {
    Export-ScheduledTask -TaskName $n | Out-File -Encoding utf8 (Join-Path $d "$n.xml")
    Unregister-ScheduledTask -TaskName $n -Confirm:$false
}
```

### 1.4 Esito

**Le scelte del proprietario**, in chat, prima delle 17:29: via ai passi 1–6, **tenendo il
worktree 16** (atlas) con il suo branch; il worktree 17 (R-IPSC) **resta** com'è; le due attività
pianificate **restano**. Il passo 1 si è quindi ridotto ai quattro run dell'hub.

**Eseguito** (misurato; hash, conteggi e comandi in
[archiviato_worktree.json](archiviato_worktree.json)):
1. Copiati nella radice dati `diff.patch`, `result.md`, `meta.json` e `prompt.md` dei run 12–15,
   16 file per 375 KB; `sha256sum -c` a destinazione: 16 su 16 corretti. Un `LEGGIMI.txt` accanto.
2. Alle 17:29, ricontrollati i 15 worktree dell'hub (identici al loro `diff.patch`, nessun run in
   esecuzione), poi `hub.py clean` per ciascuno: 15 rimossi; rapporti e patch restano in `runs/`.
3. `wt8` rimosso con `git worktree remove`.
4. `vcc2026-refactor`: `git worktree remove` lo ha tolto dalla lista, ma si è fermato con
   «Permission denied» dopo aver cancellato un solo file. Il resto della cartella, cioè l'albero
   del tag confrontato per nome, il duplicato `.h5ad` e le cache, è andato nel Cestino. Poi
   `git branch -D refactor/pulizia`: il tag punta allo stesso commit, verificato prima.
5. Stash: tag annotato `archivio/stash-altri-agenti-2026-09-28` sul commit `8a8bbef`, verificato,
   poi `git stash drop`.
6. Registrati: una sezione in [ARCHIVIO](../../../docs/ARCHIVIO.md), l'elenco e la procedura in
   [AGENTI](../../../docs/AGENTI.md) §3, la scelta sulle attività pianificate in AGENTI §2, e la
   voce del proprietario in PROGETTO §0.

**Due scostamenti dalla proposta**, entrambi dovuti a una causa che la proposta non conosceva:
- **La causa del «Permission denied»** non sono i permessi di negazione letti con `icacls`, che
  riguardano le identità della sandbox di Codex e non questo utente. È l'attributo di sola lettura
  di Windows, presente su ogni cartella sotto OneDrive (84 in `.git/worktrees/`, 178 in
  `vcc2026-refactor`), con cui git per Windows non riesce a rimuovere una cartella. Per questo
  anche i 15 `git worktree remove` dell'hub avevano lasciato 17 cartelle di metadati a metà.
- **Le nove cartelle orfane dei giorni 26–27/09**, che la proposta lasciava stare, sono state tolte
  insieme alle 17 nuove. Per le 26 si è prima controllato che ogni `ORIG_HEAD` puntasse a un commit
  di `main` o del tag del refactor. Poi si è tolto l'attributo solo a quelle cartelle e si è
  eseguito `git worktree prune -v`.

**Dopo** (misurato fra le 17:29 e le 17:35): `git worktree list` dà `main` e i due worktree di Codex tenuti;
`git branch` dà `main` e `codex/atlas-transfer-pilot`; `git stash list` è vuoto; in
`.git/worktrees/` restano solo le due cartelle registrate. Nel Cestino c'è `vcc2026-refactor`, 930
file, fino a quando il proprietario non lo svuota.

**Resta aperto:**
- il lavoro R-IPSC di Codex, fuori da `main` finché il proprietario non decide;
- i due branch remoti, da togliere con un push;
- le attività pianificate, lasciate per scelta del proprietario: rimettere `scripts/ciclo.cmd`
  nell'albero riattiverebbe la catena.

## 2. Nomi più esplicativi e struttura a indice

### 2.1 I nomi: proposta e scelta

Valutati tutti i documenti vivi di `docs/` e le guide. Il conteggio delle citazioni è misurato
con `git grep`: «vivi» sono i documenti che si aggiornano, «immutabili» checkpoint, report e
`docs/storico/`.

| Nome | Proposta | Citato da: vivi / immutabili | Perché |
|---|---|---|---|
| `docs/LAVORO.md` («Come si lavora») | `docs/PROCEDURE.md` | 20 file, 47 occorrenze, compresi il test degli stadi e il controllo documentale / 14 file | il nome non diceva che cosa contiene, cioè le procedure del perimetro di esecuzione; chi cercava come inviare apriva `SOTTOMISSIONE.md` |
| `docs/SOTTOMISSIONE.md` | nessun rinomino; lo stato si valuta nella tappa 3 | 9 / 7 | resoconto del 13/09 con il contratto nel §1 |
| `docs/AMBITI.md` | resta | 8 / 4 | il nome dice già «per area» |
| `docs/REGISTRO.md` | resta | 13 / 28, ed è il cuore del controllo | costo alto, guadagno modesto |
| PROGETTO, PIANI, ERRORI, GENERALIZZAZIONE, DECISIONI, ARCHIVIO, AGENTI | restano | — | nomi già espliciti |
| le guide `CLAUDE.md`, `AGENTS.md`, le schede, i checkpoint, le cartelle dei report | restano | — | caricate per nome dagli agenti, o citate per ID e percorso ovunque |

**Scelta del proprietario** (in chat, prima delle 17:57): `LAVORO → PROCEDURE`; gli altri nomi
restano.

### 2.2 Il rinomino e il reindirizzamento (commit `b254929`)

- `git mv docs/LAVORO.md docs/PROCEDURE.md`, con il titolo «Procedure — il percorso vivo» e una
  riga sul nome vecchio.
- **Rimandi aggiornati:** 59 occorrenze in 23 file vivi, fra cui `CLAUDE.md` (perimetri, tabella dei
  compiti e mappa verificata da `tests/test_live_tree.py`), le guide di cartella, le schede, gli
  indici di `reports/` e il test degli stadi. **Lasciati col nome vecchio**, perché registrano che
  cosa è successo allora: le due citazioni in DECISIONI, la sezione del 23/09 di ARCHIVIO, la riga
  storica in testa al registro e la scheda R-022.
- **Il meccanismo:** una tabella «Nomi cambiati» in ARCHIVIO, l'unico elenco. La leggono
  `scripts/31_check_docs.py` e `config.repo_file`:
  - `renamed_paths` e `renamed` nel controllo, che segue il nome vecchio per percorsi e link
    e verifica le ancore nel file rinominato;
  - `--status docs/LAVORO.md` risponde «renamed: now docs/PROCEDURE.md» con la riga di registro;
  - un nome rinominato non conta più come archiviato.
- **Test:** uno per il controllo (`tests/test_doc_workflow.py`), uno per `repo_file` e uno che
  confronta i due lettori sulla tabella vera (`tests/test_pipeline_contracts.py`).
- **Verifiche** (misurato):
  - senza la tabella il controllo trova 5 citazioni rotte, con la tabella 0;
  - `repo_file` dà gli stessi percorsi della versione precedente su tutti i file della repo che
    le ricette nominano, più tre casi di controllo: 7 su 7. Lo stadio 100, che lo usa per le
    ricette, legge gli stessi ingressi.

### 2.3 Gli indici

Ogni riga corretta è stata verificata sulla sua fonte prima di scriverla.

| Indice | Prima | Dopo | Fonte |
|---|---|---|---|
| `analisi/lead_scientist_2026-09-29/README.md` | cinque sottocartelle non nominate | `audit_scientifico/`, `score_credibility_r1/`, `score_bias_dati_r1/`, `training_copertura_r1/` e `neural_plan_k562/` accanto al documento che le usa | i documenti stessi, che le citano |
| `invii/README.md`, prova generale | D4 e D9 «da correggere» | corretti il 29/09 pomeriggio con i loro test; resta la forma piena | scheda R-REV, «Correzioni (29/09 pomeriggio)»; RISULTATI, «Correzioni dei difetti»; commit `117b2a8` |
| `invii/README.md`, `lezioni_invii` | «sì; il rumore viene da una sola coppia di semi» | «in parte»: l'audit del 29/09 ne corregge il rumore stimato da una coppia di semi e il peso della risposta comune sull'MSE | `AUDIT_SCIENTIFICO.md`, §2.2 e §2.4 |
| `trasferimento/README.md` | il t23 «pronto e non inviato» | inviato il 28/09, +0,141868, non conclusivo | tabella dei punteggi di `invii/README.md`, CP-0042 |
| `trasferimento/README.md`, trasferimento appreso | l'audit di codex «non è nel repository» | è in `analisi/audit_piani_dati_2026-09-26/`, recuperato il 28/09 | registro, R-019 e R-020 |
| `modelli/README.md`, rischi | le sorgenti «quasi tutte in 3'» | K562 in 3′, CD4 in Flex, Orion in GEM-X 5′ secondo le schede, da riverificare | `AUDIT_DATI.md`, §1 |
| `sorgenti/README.md`, `basali_asse` | «in corso nella sessione Claude» | la sessione si è chiusa senza eseguire il protocollo, `r1/` è vuota | la cartella; il riordino della notte del 30/09 dà la sessione `f4f38e58` per chiusa |
| `generatore_e_banchi/README.md`, banco K562 | «protocollo» | protocollo, bracci costruiti e copiati su Drive il 29/09 sera, job non eseguito | la cartella, senza `r1/`; commit `e7c933b` |
| `docs/storico/README.md` | mancava `PROGETTO_sezioni_0_6_7_2026-09-30.md`; «fra l'11 e il 28 settembre» | riga aggiunta; date e provenienza corrette; il rimando a `--status` | la cartella; la riga di registro del file |

Gli altri indici non hanno richiesto correzioni: ogni categoria ha un README con che cosa sapere
prima e una tabella con «Vale?» e peso. Le cartelle grandi senza README sono le `trial_*` degli
invii, che hanno la struttura fissa descritta in `reports/CLAUDE.md`, e quelle di `storico/`,
indicizzate dal suo README.

**Non fatto qui:** allineare le voci del registro con il «Vale?» degli indici, dove dicono cose
diverse (per esempio `docs/storico/SVD_E_RANGO.md`, `attuale` nel registro e «chiuso»
nell'indice). È il punto 3 della tappa 3.

## 3. Rimuovere l'obsoleto

### 3.1 Che cosa è obsoleto nell'albero vivo (misurato, 30/09 dalle 18:05)

Nell'albero vivo stanno `docs/` fuori da `storico/` e `checkpoints/`, `scripts/`, `src/`,
`configs/`, `tests/`, `notebooks/` e la radice. Si è cercato con `--status`, il registro, gli
indici e `git log`:
- **`notebooks/colab_jobs/`**: sei script su dieci non li cita nessun documento vivo, e nessun job
  in coda su Drive li usa. La coda è stata letta fra le 18:04 e le 18:22: i job che li nominano, 019–023, sono
  chiusi, e non c'è nessun job in attesa. Quattro sono istanze di job del 17/09 con la cartella di
  output scritta dentro. Due sono modelli a parametri. Restano gli altri quattro:
  - `common.sh`, che il job del banco K562 del 29/09 carica;
  - `generate_trial.sh` e `queue_trial.sh`, il modo documentato di generare con lo stadio 76, che
    accetta ancora quegli argomenti;
  - `sync_to_drive.ps1`.
- **Registro:** tre voci `da-verificare` nominano file dell'albero vivo, ma due sono già
  archiviate (R-013). La terza è `docs/SOTTOMISSIONE.md`, trattata al §3.4.
- **Sezioni morte:** nessuna da togliere.
  - PROGETTO §6–§7 sono rimandi, che tengono i numeri citati dai checkpoint.
  - GENERALIZZAZIONE §5 si dichiara storica e porta regole ancora valide.
- **File sparsi:** nessuno. La radice ha solo i file della mappa di `CLAUDE.md`; `configs/` le
  ricette usate, che non si modificano, `config.yaml` e `trials.yaml`. Il resto lo tiene vero
  `tests/test_live_tree.py`.

### 3.2 Uscito dall'albero (procedura di ARCHIVIO)

Tag annotato `archivio/pre-pulizia-2026-09-30` su `bc54bbf`, sezione con una riga per file in
[ARCHIVIO](../../../docs/ARCHIVIO.md), poi `git rm` dei sei script. PROCEDURE §3 e la riga di
registro di `notebooks/` dicono che cosa resta; §3 dice anche che `queue_trial.sh` mette in coda
una generazione con lo stadio 76.

### 3.3 Registro e indici allineati

Uno script, [strumenti/divergences.py](strumenti/divergences.py), ha confrontato in sola lettura lo stato del registro con il «Vale?» dell'indice della
cartella, per 149 voci indicizzate. Ne ha trovate 35 in netto disaccordo; ciascuna è stata letta
nella sua nota, nell'indice e nelle prime righe del documento. Gli stati del registro dicono come
usare un documento: `attuale` significa «è la guida valida adesso, seguilo», `storico`
«registrazione datata, non una guida».

- **25 voci, più due loro righe interne, da `attuale` a `storico`:**
  - 21 perché l'indice le dà per storiche o chiuse: i tre testi di `docs/storico/` sui banchi e
    sulla SVD, previsioni e trial fino al 25/09, i banchi del 17/09, la direzione del 19/09, e
    nove cartelle di `reports/storico/`;
  - quattro, sempre in `reports/storico/`, perché l'indice della categoria dichiara tutto ciò che
    contiene «fotografie datate, non guide». L'elenco è in [strumenti/align_registry.py](strumenti/align_registry.py)
    e nel diff del commit.
- **Sette voci «in parte» restano `attuale`,** con la riserva nella nota e la sua fonte verificata:
  `analisi_2026-09-24` (audit dei segni, CP-0034), `ipotesi_trasferimento_2026-09-24` (H1 e H6
  cadute), `context_identity` (R-001, punto 3), `lezioni_invii` (audit del 29/09),
  `universo_hipsci` (dall'indice, come interpretazione), `universo_2026-09-26` (sostituito per
  CD4 e Orion), `quota_condivisa` (l'ablazione del t23).
- **Tre voci «in parte» erano già coerenti,** perché una voce più specifica porta la riserva:
  `trial_2026-09-12` (R-011), `multisource_2026-09-22` (nella nota) e `banco_varianti` (R-017,
  R-018).
- **Dopo:** 10 voci «in parte» con stato `attuale` e la riserva scritta; 139 concordi.

Gli script della sessione, copiati dallo scratchpad così come sono girati, stanno in
[strumenti/](strumenti/): il rinomino (`rename_refs.py`, `verify_rename.py`), gli indici
(`fix_indexes.py`), il registro (`divergences.py`, `align_registry.py`). Hanno percorsi assoluti:
sono una registrazione, non strumenti da rilanciare.

**Checkpoint corretti:** 12 hanno la colonna «Corretto da» compilata. Al posto di cento righe
cambiate a mano, due regole in `scripts/31_check_docs.py`, con i loro test:
- con `--status` la correzione compare **per prima**, prima dello stato del registro;
- il controllo fallisce se un checkpoint corretto ha una riga propria `attuale` che non nomina chi
  l'ha corretto.

Il solo caso era CP-0035: la regola lo ha segnalato, e la sua nota ora nomina CP-0036, con le
parole della riga di INDICE. La regola sta anche nell'intestazione di INDICE, la sua sede.

### 3.4 Le schede e il contratto: la scelta del proprietario

Proposta in chat, con una tabella per scheda: accorciare R-REV, R-V2 e S-INVII, portando i diari
in `docs/storico/`; chiudere R-DATI, R-MODELLI e R-SWITCH con esito e condizione di riapertura;
portare il contratto del formato di `docs/SOTTOMISSIONE.md` in PROCEDURE e il file in storico.

**Scelta del proprietario** (in chat, prima delle 18:31, ora letta con `date`): nessuna scheda accorciata; si chiude solo
**R-MODELLI**; `SOTTOMISSIONE.md` resta com'è, `da-verificare` con la scheda R-015.

**Eseguito:** R-MODELLI è `chiuso`, con una sezione «Chiusura» che dà l'esito dei suoi cinque
confronti, ciascuno con la sua fonte: 1–3 e 5 eseguiti in R-V2 e R-COMP senza superare la loro
regola, il 4 mai eseguito. La condizione di riapertura è il ritorno dei descrittori dei bersagli
nuovi e dei ruoli con segno (H2–H3, filone F5 di R-V2). Il resto della scheda resta com'era.
PIANI toglie la sua riga dal §2 e la mette nel §4, i piani chiusi, e il testo del §2 la segue;
la nota del registro su `docs/piani/` annota la chiusura, come chiede la guida delle schede.
