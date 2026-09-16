# Catena di cicli: piano, revisione, implementazione, controllo

**Stato:** riscritta il 16 settembre 2026 e provata con agenti simulati
(`tests/test_daily_cycle.py`, 42 test). **Nessun ciclo è stato eseguito dal vivo.** Dei
servizi veri sono state provate solo due cose: una chiamata di Grok in sola lettura, per
leggere il formato della sua risposta, e la validazione di un incarico generato con la
console dell'orchestratore, che non contatta nessun servizio. La versione precedente,
con un solo giro al giorno, è nella cronologia di git (commit `4272b3b`).

## 1. Che cosa fa

Un **ciclo** passa per quattro fasi. Ogni fase parte solo se trova il segnale della
precedente, e lascia il proprio. Il proprietario del progetto non avvia mai niente a
mano: il ciclo 01 lo apre la routine delle 8, gli altri li apre ChatGPT (Codex) quando
lui glielo chiede.

| Fase | Chi | Parte se | Produce | Segnale |
|---|---|---|---|---|
| 1. Piano, solo ciclo 01 | Claude, routine dell'app alle 08:00, skill `piano-mattutino` | — | i due piani, la fotografia della classifica | `01_piano.json`, scritto da `seal` |
| 2. Revisione | Codex. Ciclo 01: `codex exec` con la skill `$revisione-piano`. Cicli successivi: l'app Codex con la skill `avvia-ciclo`, al termine di un dialogo | ciclo 01: sigillo integro; altri: bozza valida | `02_revisione.md` o `02_dialogo.md`, il foglio `03_prompt_claude.md`, i test in `collaudo/` | `02_codex.json` |
| 3. Implementazione | Claude, `claude -p` | foglio e test identici a quelli validati, Claude autenticato | codice e test nel worktree, `04_esito_claude.md`, commit locale | `03_claude.json` |
| 4. Controllo | Grok, `grok -p` in sola lettura; campagne dell'orchestratore (DeepSeek e Kimi) se Grok le chiede | fase 3 conclusa | `05_analisi_grok.md`, fino a 3 campagne, `05_sintesi_grok.md`, `05_resoconto.md` | `04_grok.json`: il ciclo è chiuso |

Una giornata tipo:

1. Alle 8 Claude scrive il piano e lo sigilla: si apre il ciclo 01. Codex lo rivede e
   scrive foglio e test, Claude implementa, Grok controlla. Nella cartella del ciclo
   compare il resoconto; tutti dormono.
2. Più tardi il proprietario parla con ChatGPT nell'app Codex. Quando dice «avvia il
   ciclo», o ha detto «avvialo tu quando il piano è pronto», Codex scrive foglio, test e
   riassunto del dialogo e apre il ciclo 02. Il guardiano sveglia Claude, poi Grok; arriva
   il resoconto.
3. Si ripete quante volte si vuole: 03, 04, … Non c'è una chiusura automatica della
   giornata.

## 2. La casella

```
reports/ciclo_giornaliero/<giornata>/
  ciclo-01/   01_piano.json → 02_codex.json → 03_claude.json → 04_grok.json
  ciclo-02/                   02_codex.json → 03_claude.json → 04_grok.json
  bozza-…/    una bozza di Codex non ancora avviata
```

- **Giornata:** va dalle 08:00 alle 08:00 (`day_start`). Un ciclo aperto alle 3 di notte
  appartiene al giorno prima. Serve solo a nominare le cartelle.
- **Numeri:** 01 è sempre il ciclo del piano; i cicli aperti dal dialogo partono da 02 e
  il numero lo assegna lo script.
- **Segnali:** si scrivono una volta sola, a fase finita, e portano lo sha256 di ciò che
  la fase successiva può leggere. Un file scritto a metà non è JSON valido e il guardiano
  lo legge come assente. Un segnale non si sovrascrive mai.
- **Cartelle vecchie:** `reports/ciclo_giornaliero/2026-09-16/` ha la forma piatta della
  versione precedente e viene ignorata. Il suo sigillo delle 13:43Z non corrisponde più
  ai due piani, modificati dopo su richiesta del proprietario
  ([CP-0018](checkpoints/0018-drive-storage-confermato.md)).

## 3. Il guardiano

Un solo processo, `scripts\ciclo.cmd guardiano`, controlla la casella ogni 60 secondi
(`poll_seconds`) e fa avanzare di una fase il ciclo aperto più vecchio.

- **Uno alla volta.** I cicli aperti formano una coda, nell'ordine in cui sono entrati
  (sigillo o avvio). Un ciclo avviato mentre un altro lavora aspetta il suo turno; il
  suo resoconto dice che è stato pianificato senza conoscere l'esito del precedente.
- **Continuità.** Il worktree di un ciclo parte dal commit dell'ultimo ciclo
  implementato. Se quel lavoro è già integrato nel checkout principale, parte da `HEAD`.
  Il motivo è scritto in `03_claude.json`, campo `base_motivo`.
- **PC sveglio.** Mentre un agente lavora, il guardiano chiede a Windows di non
  sospendere il computer.
- **Un solo processo.** Il lucchetto `<data root>/ciclo/guardiano.lock` contiene il pid;
  un lucchetto il cui processo non esiste più viene rimosso.
- **`run`**, il comando di riserva, fa lo stesso lavoro ma aspetta il piano fino alle
  12:00 (`seal_deadline`) e si ferma quando il ciclo 01 del giorno è chiuso. Se il
  guardiano è già attivo, esce senza fare niente.

## 4. Avviare un ciclo dal dialogo

1. Il proprietario apre l'app Codex sulla cartella del progetto e ne parla. La skill
   `avvia-ciclo` parte dall'ultimo resoconto.
2. Quando c'è il via, Codex esegue `python scripts/32_daily_cycle.py bozza` e scrive
   nella bozza `03_prompt_claude.md`, `02_dialogo.md`, `passo.json`, i test in
   `collaudo/` e, se c'è, `02_revisione.md`.
3. Codex esegue `python scripts/32_daily_cycle.py avvia --bozza <cartella>`. Lo script
   controlla la bozza; se va bene, la rinomina in `ciclo-NN` e scrive `02_codex.json`
   con `origine: dialogo` e chi l'ha avviata. Se non va bene, non crea niente e dice
   perché.

## 5. Il collaudo

I test di collaudo sono la specifica del passo, scritti da Codex **prima** di Claude.

- Lo script li esegue due volte, prima e dopo il lavoro di Claude, sempre da una copia
  presa dalla cartella del ciclo e verificata con lo sha256. Claude ne vede un'altra
  copia in `.ciclo/collaudo/`: se la modifica, non cambia niente.
- Girano con il Python del progetto, con `src/` del worktree nel percorso e senza
  scrivere bytecode. Non finiscono mai nel commit.
- Esiti: un `completato` di Claude diventa `parziale` se il collaudo fallisce dopo il
  lavoro, se passava già prima (non informativo), o se falliscono le verifiche.
- Regole per chi li scrive: nelle due skill di Codex. Nello stesso controllo del foglio
  rientrano anche i test: niente comandi di invio, push o cancellazione ricorsiva,
  nemmeno nei commenti; al massimo 200 KB.

## 6. Grok e l'orchestratore

- **Analisi indipendente.** Grok legge foglio, esito, diff e collaudo, in sola lettura e
  senza web, e risponde con il JSON di `configs/ciclo_giornaliero/grok_output.schema.json`.
  La sua analisi è scritta prima di qualunque campagna.
- **Campagne.** Se Grok ne chiede una, lo script la costruisce su un modello fisso: Grok
  scrive titolo, domanda, contesto, risultato atteso e criteri; percorso (`deep_kimi`),
  limiti e regole li mette lo script. Gli allegati si scelgono da un elenco fisso di
  estratti preparati dallo script, sotto i 150 KB. Lo script valida l'incarico con
  `orch brief`, lo avvia con `orch start` e poi risveglia Grok con il rapporto. Al
  massimo **3 campagne per ciclo** (`max_campagne`); una richiesta oltre il tetto è
  registrata e ignorata.
- **Che cosa vale un esito.** I criteri delle campagne sono umani: l'orchestratore può
  arrivare al più a «convergenza delle proposte, validazione mancante». Uno stato
  `finished` non è una verifica.
- **Ripresa.** Ogni chiamata a Grok e ogni campagna lasciano un record scritto una volta
  (`grok/chiamata-NN.json`, `orch/campagna-N.json`): se il guardiano si ferma a metà, al
  riavvio non ripete né l'una né l'altra.
- **Decisione.** L'avvio delle campagne da parte del ciclo è la modifica di D-021 del 16
  settembre, voluta dal proprietario: Grok decide, lo script avvia.
- **Costo.** Il CLI di Grok riporta un costo nominale per chiamata (0,0097 USD nella
  prova del 16 settembre). Che con il login dell'abbonamento non venga addebitato va
  verificato nell'account.

## 7. I controlli dello script

Gli agenti scelgono che cosa fare; lo script decide se possono farlo.

- **Integrità:** sha256 dei piani contro il sigillo, del foglio e dei test contro
  `02_codex.json`.
- **Forma delle risposte:** gli schemi JSON di Codex, Claude e Grok in
  `configs/ciclo_giornaliero/`.
- **Foglio:** le sei sezioni Obiettivo, Contesto, Passi, Regola di accettazione, Vincoli
  e Consegna; al massimo 15 KB; nessuna espressione vietata. Lo stesso divieto vale per
  il riassunto del dialogo e per i test. I divieti li aggiunge il preambolo fisso
  `configs/ciclo_giornaliero/preambolo_claude.md`, che prevale sul foglio.
- **Tempi massimi:** 45 minuti per Codex, 90 per Claude, 30 per ogni chiamata a Grok,
  45 per ogni campagna, 20 per il collaudo.
- **Dopo Claude, a cura dello script:** collaudo, controllo documentale e intera suite
  di test nel worktree.
- **Commit:** solo nel worktree, solo sul branch del ciclo, esclusa `.ciclo/`. Niente
  push.

## 8. Che cosa possono fare gli agenti

- **Codex, fase 2 del ciclo 01:** sandbox `workspace-write` con la cartella del ciclo
  come unica cartella scrivibile, rete chiusa.
- **Codex nell'app:** dialogo, bozza e comando `avvia`. Non scrive segnali e non avvia
  a mano Claude, Grok o l'orchestratore (`AGENTS.md`).
- **Claude, fase 3:** worktree, `--permission-mode acceptEdits`, `--permission-prompts
  none`; comandi ammessi e vietati in `configs/ciclo_giornaliero/ciclo.json`. Niente
  web, push, commit, reset e checkout.
- **Grok, fase 4:** `--permission-mode plan`, `--disable-web-search`, nessuna scrittura.
  Legge `AGENTS.md` e `CLAUDE.md` come istruzioni di progetto.

## 9. Dove stanno le cose

| Che cosa | Dove |
|---|---|
| Segnali, foglio, test, analisi, resoconti | `reports/ciclo_giornaliero/<giornata>/ciclo-NN/` |
| Incarichi e rapporti delle campagne | `ciclo-NN/orch/` |
| Registri dei comandi e lucchetto | `<data root>/ciclo/`, più `<data root>/ciclo/scheduler.log` |
| Worktree | `<data root>/worktrees/ciclo-<giornata>-NN`, branch `ciclo/<giornata>-NN` |
| Impostazioni, schemi, testi fissi | `configs/ciclo_giornaliero/` |
| Skill | `.claude/skills/piano-mattutino/`, `.agents/skills/revisione-piano/`, `.agents/skills/avvia-ciclo/` |
| Istruzioni per Codex e Grok | `AGENTS.md`, che rimanda a `CLAUDE.md` |

## 10. Comandi

```bash
python scripts/32_daily_cycle.py status
```

```bash
python scripts/32_daily_cycle.py guardiano --una-volta
```

```bash
python scripts/32_daily_cycle.py run --dry-run
```

`guardiano` senza opzioni gira finché non lo si ferma; `--una-volta` si ferma quando non
c'è niente da fare. `bozza` e `avvia` li usa Codex.

**Utilità di pianificazione.** Due attività, entrambe solo con l'utente connesso.

| Attività | Quando | Che cosa | Impostazioni |
|---|---|---|---|
| «VCC2026 Guardiano» | all'accesso a Windows; registrata e avviata il 16 settembre alle 23:54, su consenso del proprietario | `ciclo.cmd guardiano`, dentro un PowerShell con finestra nascosta | nessun limite di durata, anche a batteria, una sola istanza, fino a tre riavvii a 5 minuti di distanza |
| «VCC2026 Ciclo giornaliero» | ogni giorno alle 08:30 | `ciclo.cmd run`, la riserva: se il guardiano è attivo esce subito | limite di 6 ore, anche a batteria (dal 16 settembre), avvio appena possibile se l'orario è stato perso |

Per fermare il guardiano: `Stop-ScheduledTask -TaskName 'VCC2026 Guardiano'` in
PowerShell; per toglierlo del tutto: `Unregister-ScheduledTask`, con lo stesso nome.

## 11. Prerequisiti e limiti

- **Claude da riga di comando deve essere autenticato.** Il 16 settembre
  `claude auth status` risponde `loggedIn: false`: finché non si esegue una volta
  `claude auth login`, ogni fase 3 si chiude `bloccato` e il ciclo si chiude senza
  controllo di Grok.
- **Computer acceso e utente connesso.** Per il ciclo 01, app Claude aperta alle 08:00.
- **L'integrazione non è automatica.** I branch `ciclo/<giornata>-NN` si accumulano uno
  sopra l'altro finché qualcuno non li unisce e aggiorna mappa e registro, in una
  sessione supervisionata dal proprietario. Questa fase va ancora definita.
- **Email:** non implementata; il resoconto resta nella cartella del ciclo.
- **Quote:** ogni ciclo consuma quote degli abbonamenti Claude, ChatGPT e SuperGrok, più
  le sessioni web di DeepSeek e Kimi per ogni campagna.
