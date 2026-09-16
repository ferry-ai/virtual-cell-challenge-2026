# Ciclo giornaliero: piano, revisione, implementazione

**Stato:** implementato e provato il 16 settembre 2026 con agenti simulati
(`tests/test_daily_cycle.py`). **Non ancora eseguito dal vivo**: la prima esecuzione
reale è prevista per il 17 settembre.

## 1. Che cosa fa

Ogni mattina tre fasi girano in sequenza fissa, una sola volta. Ogni fase parte solo se
trova il segnale della precedente, e lascia il proprio.

| Fase | Chi | Quando | Parte se | Produce | Segnale |
|---|---|---|---|---|---|
| 1. Piano | Claude, routine dell'app con la skill `piano-mattutino` | 08:00 | — | i due piani, la fotografia della classifica, la pagina per il team | `01_piano.json`, scritto dal comando `seal` |
| 2. Revisione | Codex, `codex exec` con la skill `$revisione-piano` | dalle 08:30, appena c'è il segnale; attesa fino alle 12:00 | sigillo presente e piani identici a quelli sigillati | `02_revisione.md` e il foglio-prompt `03_prompt_claude.md` | `02_codex.json`, scritto dallo script |
| 3. Implementazione | Claude, `claude -p` | subito dopo la fase 2 | foglio valido e Claude autenticato da riga di comando | codice e test nel worktree, `04_esito_claude.md`, commit locale sul branch `ciclo/<data>` | `03_claude.json`, scritto dallo script |
| 4. Integrazione | da definire | — | — | — | — |

La fase 1 parte dall'attività pianificata dell'app Claude. Le fasi 2 e 3 le avvia
`scripts/ciclo.cmd run` dall'Utilità di pianificazione di Windows, che richiama
`scripts/32_daily_cycle.py`.

## 2. Perché segnali e non un osservatore di file

Un osservatore di file scatta su un file scritto a metà, e può scattare due volte. Un
segnale si scrive una volta sola, a fase finita, e contiene lo sha256 di ciò che la
fase successiva può leggere. Se un piano viene modificato dopo il sigillo, la
revisione non parte: legge solo ciò che è stato consegnato.

## 3. Una sola iterazione al giorno

- Un segnale non si sovrascrive mai. Se esiste, la sua fase non riparte.
- Un lucchetto (`.lock` nella cartella del giorno) impedisce due esecuzioni insieme. Un
  lucchetto più vecchio di 8 ore è considerato un'esecuzione interrotta.
- Anche un giorno saltato si chiude con i suoi segnali. Per esempio, senza piano alle
  12:00 la fase 2 è `saltato` e la fase 3 `non_avviato`.
- **Per rifare una fase** si rinomina il suo segnale, per esempio in
  `02_codex.json.annullato-1030`, e si lancia `scripts\ciclo.cmd fase2` o `fase3`. Non
  si cancella niente: il segnale annullato resta come prova.

## 4. I controlli dello script

Lo script è deterministico. Gli agenti scelgono che cosa fare; lo script decide se
possono farlo.

- **Integrità:** lo sha256 di ogni piano deve coincidere con il sigillo, e quello del
  foglio con quello validato alla fine della fase 2.
- **Forma della risposta:**
  - Codex deve rispondere con il JSON di `configs/ciclo_giornaliero/codex_output.schema.json`;
  - Claude con quello di `configs/ciclo_giornaliero/claude_output.schema.json`.
- **Il foglio-prompt:**
  - deve avere le sei sezioni Obiettivo, Contesto, Passi, Regola di accettazione,
    Vincoli e Consegna;
  - non deve superare i 15 KB;
  - non deve contenere comandi di invio alla gara, di push o di aggiramento dei
    permessi, nemmeno per vietarli. I divieti li aggiunge il preambolo fisso
    `configs/ciclo_giornaliero/preambolo_claude.md`, che prevale sul foglio.
- **Tempi massimi:** 45 minuti per Codex, 90 per Claude. I registri completi stanno fuori
  dal repository.
- **Verifiche dopo Claude, eseguite dallo script e non dall'agente:** il controllo
  documentale e l'intera suite di test nel worktree. Se una verifica fallisce, un esito
  `completato` diventa `parziale`.
- **Commit:** solo nel worktree, solo sul branch del giorno, escludendo la cartella
  `.ciclo/` con i materiali copiati. Niente push.

## 5. Che cosa possono fare gli agenti

**Codex (fase 2)**
- Sandbox `workspace-write`, con la cartella del giorno come unica cartella scrivibile e
  la rete chiusa.
- Legge il repository ma non lo modifica.
- Il file `.agents/skills/revisione-piano/agents/openai.yaml` impedisce che la skill si
  attivi da sola in altre conversazioni.

**Claude (fase 3)**
- Lavora nel worktree con `--permission-mode acceptEdits`.
- Con `--permission-prompts none`, tutto ciò che richiederebbe un'approvazione viene
  negato, senza fermare l'esecuzione.
- Comandi ammessi: lettura e modifica dei file, controllo documentale, test tramite
  `scripts\py.cmd`, e comandi git di sola lettura.
- Esclusi: web, push, commit, reset e checkout.
- L'elenco completo sta in `configs/ciclo_giornaliero/ciclo.json`.

## 6. Dove stanno le cose

| Che cosa | Dove |
|---|---|
| Segnali e documenti del giorno | `reports/ciclo_giornaliero/<data>/` |
| Registri dei comandi | `<data root>/ciclo/<data>/`, più `<data root>/ciclo/scheduler.log` |
| Worktree dell'implementazione | `<data root>/worktrees/ciclo-<data>`, branch `ciclo/<data>` |
| Impostazioni, schemi, testi fissi | `configs/ciclo_giornaliero/` |
| Skill | `.claude/skills/piano-mattutino/` (Claude), `.agents/skills/revisione-piano/` (Codex) |
| Istruzioni di progetto per Codex | `AGENTS.md`, che rimanda a `CLAUDE.md` |

## 7. Comandi

```bash
python scripts/32_daily_cycle.py status
```

```bash
python scripts/32_daily_cycle.py run --dry-run
```

```bash
scripts\ciclo.cmd run
```

Registrata il 16 settembre nell'Utilità di pianificazione come «VCC2026 Ciclo
giornaliero»: ogni giorno alle 08:30, solo con l'utente connesso. Per rifarla da capo:

```bash
schtasks /Create /TN "VCC2026 Ciclo giornaliero" /TR "\"C:\Users\ferra\OneDrive\Desktop\vcc2026\scripts\ciclo.cmd\" run" /SC DAILY /ST 08:30 /F
```

`schtasks` non imposta tre opzioni, che sono state aggiunte da PowerShell: avvio appena
possibile se l'orario è stato perso, nessuna seconda istanza in parallelo, limite di sei
ore.

```powershell
Set-ScheduledTask -TaskName 'VCC2026 Ciclo giornaliero' -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 6))
```

Per rimuoverla:

```bash
schtasks /Delete /TN "VCC2026 Ciclo giornaliero" /F
```

## 8. Prerequisiti e limiti

- **Claude da riga di comando deve essere autenticato.** Il 16 settembre
  `claude auth status` risponde `loggedIn: false`: l'app usa credenziali proprie, che non
  passano agli script. Finché non si esegue una volta `claude auth login` in un
  terminale, la fase 3 si chiude come `bloccato`. Codex risulta autenticato con ChatGPT.
- **Computer acceso e utente connesso** alle 08:30; app Claude aperta alle 08:00 per la
  fase 1.
- **Il worktree parte dall'ultimo commit.** Il lavoro non versionato non esiste per la
  fase 3; un passo che ne dipende va escluso già in fase 2.
- **L'integrazione non è automatica.** I branch `ciclo/<data>` si accumulano finché
  l'integratore non li unisce: è la fase 4, da definire.
- **Ogni giorno girano due sessioni di agenti**, con il loro consumo.
