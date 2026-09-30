# Infrastruttura degli agenti

**Perimetro.** I sistemi che lanciano e coordinano gli agenti: la base di lancio attuale,
l'orchestratore e la catena di cicli ritirati il 23 settembre, il coordinamento fra sessioni nella
stessa cartella. Non riguarda la ricerca, i dati, i modelli o gli invii: **chi lavora lì non ha
bisogno di questa pagina**, salvo il §3 se deve coordinarsi con un'altra sessione.
**Fonti:** il README e le istruzioni della base di lancio (fuori dalla repo, lette il 30/09 senza
modificarle), D-040 in [DECISIONI](DECISIONI.md), [ARCHIVIO](ARCHIVIO.md),
[PIANI §3](PIANI.md#3-lavorare-in-una-cartella-condivisa), la revisione esterna del 29/09 in
`reports/analisi/lead_scientist_2026-09-29/external_reviews/STATO.md`; i fatti misurati il 30/09
sono detti tali. **Si aggiorna** quando cambia l'interfaccia fra la base di lancio e il progetto, o
quando un sistema viene ritirato o riattivato (D-049). Scritta il 30/09.

## 1. La base di lancio attuale: agent-hub, fuori dalla repo

- **Dove:** `C:/Users/ferra/agent-hub`, cartella separata dal progetto, creata il 24/09; la radice e
  `control/` non sono sotto git. Non si modifica da una sessione che lavora sul progetto.
- **Che cosa fa:** una sessione di regia (nelle istruzioni dell'hub è Claude nell'app, aperta su
  `agent-hub/control`) affida compiti ad altri agenti a riga di comando (Claude Code con un secondo
  account, Codex, Grok, Antigravity), raccoglie i loro rapporti e li verifica. Chi sono gli agenti,
  i login, i permessi, i modelli fissati in `control/agents.toml` e i comandi stanno nelle
  istruzioni dell'hub: `README.md` per il proprietario, `control/CLAUDE.md` per la regia,
  `runs/CLAUDE.md` per i worker. **Leggile solo se il tuo compito è la base di lancio.**
- **Non è l'orchestratore ritirato** (§2), anche se le istruzioni dell'hub chiamano la regia
  «orchestrator»: niente cicli, guardiano o piano del mattino; ogni lancio è un compito singolo,
  deciso da una sessione. Non è registrata come decisione in [DECISIONI](DECISIONI.md): la sua
  documentazione è la sua.

**L'interfaccia con il progetto**, cioè tutto ciò che il progetto ne deve sapere:
- **Autorizzazione.** Ogni lancio consuma la quota dell'account di quell'agente, e condividere con
  un agente contenuti della repo è una scelta del proprietario: lo autorizza lui in chat, come ogni
  altro uso di quota ([CLAUDE.md](../CLAUDE.md)).
- **Regole del worker.** Un worker lavora su vcc2026 solo se la regia gli passa la repo come
  cartella di lavoro (`--cwd`) o una sua copia isolata. Allora vale per lui l'accordo della repo,
  [CLAUDE.md](../CLAUDE.md) (per Codex attraverso `AGENTS.md`), con le regole del worker che l'hub
  ripete nel prompt. Dove le due si scontrano valgono quelle del worker, che sono più strette: non
  committa, non fa push, non cambia branch, non lancia altri agenti. Verifica, commit e registro
  spettano alla sessione che l'ha lanciato.
- **Rapporti.** I rapporti integrali degli agenti usati per uno studio si copiano nella cartella del
  report, in una sottocartella `agenti/` (la regola è in `reports/CLAUDE.md`): lo ha chiesto il
  proprietario il 25/09, perché le cartelle `runs/` dell'hub si possono ripulire e un risultato
  detto solo a voce si perde.
- **Un rapporto non è evidenza** finché la sessione che lo riceve non lo verifica sulle fonti. La
  verifica incrociata serve anche al contrario: il 25/09 la revisione di claude2 e grok ha trovato
  in un banco un difetto che ha evitato un invio sbagliato
  ([CP-0039](checkpoints/0039-banco-varianti-restrizione.md), §6).

## 2. Ritirati il 23 settembre: orchestratore, oracolo, catena di cicli

- **Che cosa:** l'orchestratore locale delle consultazioni multi-modello, l'oracolo numerico
  pairwise e la catena di cicli giornalieri Codex → Claude → Grok, con guardiano e piano del
  mattino (D-020, D-021, D-022, D-023, tutte superate).
- **Quando e perché:** D-040, 23 settembre: nell'albero resta solo il codice che produce o valuta
  un invio.
- **Dove sono:** il codice e i documenti nel tag `archivio/pre-pulizia-2026-09-23`, elencati file
  per file in [ARCHIVIO](ARCHIVIO.md), sezione «Agenti e orchestrazione»; le loro prove in
  `reports/storico/` (`orchestrator/`, `catena_2026-09-16/`, `ciclo_giornaliero/`, `oracle/`,
  `grok_verification/`), indicizzate in [storico](../reports/storico/README.md).
- **Due attività pianificate di Windows sono ancora registrate** (misurato il 30/09 con
  `Get-ScheduledTask`, in sola lettura): «VCC2026 Ciclo giornaliero», pronta, ogni giorno alle
  08:30, ultima esecuzione il 30/09 alle 15:02 con esito 1; «VCC2026 Guardiano», pronta, ultima
  esecuzione il 28/09 con esito 1. Lanciano `scripts/ciclo.cmd`, che non è più nell'albero, e per
  questo oggi falliscono senza effetti. **Rimettere nell'albero `scripts/ciclo.cmd` dal tag
  riattiverebbe la catena alla prossima esecuzione.** Toglierle spetta al proprietario.
- **Non si riattivano.** Riportarne uno in vita è una decisione da scrivere in DECISIONI prima,
  con il codice ripreso dal tag e il suo test.

## 3. Coordinamento fra sessioni nella stessa cartella

Claude e Codex lavorano spesso in parallelo sulla stessa copia della repo, senza alcun lock. Le
regole minime sono in [CLAUDE.md](../CLAUDE.md), «Shared checkout»; qui il resto, per chi deve
committare file condivisi o coordinarsi:

- **Prima di ogni commit** `git log -3`, `git status` e `git diff --cached --stat`; si aggiungono
  solo i propri file, per nome, mai `git add -A` sulla radice. Codex lascia segnaposto nell'indice
  con `git add -N`: un commit senza percorsi li includerebbe.
- **Un file che anche altri stanno modificando** (REGISTRO, PROGETTO, un README, una scheda,
  `src/vcc2026/CLAUDE.md`): `git commit -- <file>` prende il file intero, righe altrui comprese
  (e7c933b, corretto da db32204). Si committa un blob con le sole proprie righe: `git hash-object -w`
  più `git update-index --cacheinfo`, oppure un indice temporaneo (`GIT_INDEX_FILE`) e
  `git commit-tree`.
- **I file di una sessione attiva non si toccano**: né modifiche né stash né commit; si segnalano
  al proprietario. Il lavoro lasciato da una sessione finita si committa com'è (D-048).
- **Per parlare con un'altra sessione Claude:** `ListAgents` e `SendMessage`. Per prendere un lavoro
  assegnato a un'altra sessione: [PIANI §3](PIANI.md#3-lavorare-in-una-cartella-condivisa).
- **Un job Colab o Kaggle** di un'altra sessione: come sapere se è vivo è in
  [LAVORO §3](LAVORO.md#3-job-su-colab-e-kaggle).
- **Worktree e branch lasciati dagli agenti** (misurato il 30/09 con `git worktree list`): oltre a
  `main`, 15 worktree staccati sotto `agent-hub/runs/`, dalle esecuzioni in modifica isolata del
  26–28/09; 2 di Codex sotto `~/.codex/worktrees/`, uno sul branch locale
  `codex/atlas-transfer-pilot`; `vcc2026-refactor` sul branch locale `refactor/pulizia`; `wt8`. Non
  sono materiale del progetto e non si usano come fonte senza verificarne l'origine; ripulirli spetta
  al proprietario (per quelli dell'hub c'è il comando di pulizia delle sue esecuzioni).

Non sono materiale del progetto neanche la cartella `.claude/` nella radice, configurazione locale
di Claude Code (permessi, un workflow), non tracciata, e la memoria privata di ciascun agente. Una
lezione che serve a tutti va in [ERRORI](ERRORI.md) o qui, non solo in una memoria privata (D-048).

## 4. Lezioni della base di lancio

- **Il controllo automatico dei permessi** ha bloccato lanci in modalità auto il 24/09 e, il 29/09,
  un lancio per cui il consenso sull'account non valeva come consenso a condividere contenuti della
  repo. Non si aggira: si chiede il via esplicito, oppure il proprietario lancia il comando
  (`external_reviews/STATO.md`; istruzioni della regia dell'hub).
- **Il limite d'uso è condiviso** fra le sessioni Claude sul progetto e gli agenti dell'hub: il 29/09
  claude2 si è fermato al limite di sessione senza produrre la revisione (`STATO.md`). Il 25/09 due
  workflow da 8 e 6 indagini con le loro verifiche hanno esaurito il limite in circa mezz'ora, e 21
  agenti su 22 si sono fermati a metà; con tappe da 3–6 agenti il 26/09 tutto è arrivato in fondo
  (fino al 30/09 scritto solo nella memoria privata di un agente).
- **`hub.py doctor`** controlla installazione e login senza chiamare modelli; il 29/09 segnalava Grok
  senza login e un account di claude2 diverso da quello atteso (`STATO.md`).
