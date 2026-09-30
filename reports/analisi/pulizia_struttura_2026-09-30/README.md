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
| 1 | inventario e proposta (16:25); eseguita dopo il via (17:29–17:35) | `581f264`, poi il commit che aggiunge questa riga | da 19 worktree e uno stash a 2 worktree di Codex tenuti dal proprietario, nessuno stash: §1.4 |

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
