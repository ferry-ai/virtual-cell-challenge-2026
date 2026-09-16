# CP-0019 — Catena di cicli: guardiano, collaudo scritto prima e controllo di Grok

- **Data:** 2026-09-16
- **Tipo:** cambio-di-strategia
- **Redatto da:** agente Claude (Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il proprietario vuole che la catena giri tutto il giorno senza che nessuno la avvii a
mano. Il ciclo 01 lo apre la routine delle 8; i cicli successivi li apre ChatGPT alla
fine di un dialogo, anche su delega; ogni ciclo lo controlla Grok, che può far lavorare
DeepSeek e Kimi. Come renderlo meccanico senza perdere le garanzie della versione a un
giro: segnali scritti una volta sola, integrità degli input, niente invii né push?

## 2. Cosa è stato fatto

**Scelte del proprietario**, espresse in chat il 16 settembre. Sono decisioni, non misure:

- nessun avvio manuale;
- i cicli dopo il primo partono da ChatGPT, anche su delega;
- Gemini serve allo studio del proprietario, fuori dalla catena;
- il resoconto resta nella cartella del ciclo, e l'email è facoltativa;
- Claude, ChatGPT e Grok lavorano con i CLI degli abbonamenti, solo DeepSeek e Kimi sul
  web;
- Grok decide le campagne e lo script le avvia, al massimo 3 per ciclo;
- il lavoro della giornata va salvato in un commit sul branch attuale.

**Implementazione.**

- Commit di base `4272b3b`, senza push, con il lavoro del 16 settembre, escluso il file
  spurio nella radice.
- Riscritto `scripts/32_daily_cycle.py`: cartelle `ciclo-NN`, coda, guardiano con
  lucchetto sul pid, comandi `bozza` e `avvia`, collaudo prima e dopo, fase 4 con Grok e
  campagne, resoconto.
- Nuovi `configs/ciclo_giornaliero/grok_output.schema.json`,
  `configs/ciclo_giornaliero/prompt_grok.md` e
  `configs/ciclo_giornaliero/prompt_grok_seguito.md`.
- Nuova skill di Codex `avvia-ciclo`.
- Aggiornati:
  - le skill `revisione-piano` e `piano-mattutino`, e `AGENTS.md`;
  - `configs/ciclo_giornaliero/ciclo.json`, `configs/ciclo_giornaliero/prompt_codex.md`
    e `configs/ciclo_giornaliero/preambolo_claude.md`;
  - `scripts/ciclo.cmd`;
  - D-021, e `docs/CICLO_GIORNALIERO.md` riscritto.

**Prove.**

```bash
python -m unittest tests.test_daily_cycle
python scripts/31_check_docs.py
.\scripts\py.cmd -m unittest discover -s tests
```

Sui servizi veri sono state fatte due sole prove, entrambe trascritte in
`reports/catena_2026-09-16/`:

- una chiamata a Grok in sola lettura, fuori dal repository;
- la validazione con `orch brief` di un incarico nel formato che lo script genera. La
  validazione non contatta nessun servizio.

## 3. Cosa si è osservato

### 3.1 Grok Build (misura)

- **Il CLI.** La pagina ufficiale lo presenta come «early beta» dal 25 maggio 2026, per
  gli abbonati SuperGrok e X Premium Plus, con una modalità non interattiva (`-p`).
  Fonte: x.ai/news/grok-build-cli, letta il 16 settembre.
- **Su questa macchina.** È installato `grok 1.0.30` in `~/.grok/bin`, con un file di
  login presente. Legge da solo `AGENTS.md` e `CLAUDE.md` come istruzioni di progetto
  (`grok inspect`).
- **La chiamata di prova.** Uscita 0 in 12,7 s. La risposta è JSON con
  `structuredOutput` conforme allo schema passato; il modello è `grok-4.6-build`, e
  `total_cost_usd` vale 0,00973284. Quel valore è un costo **nominale**: se venga
  addebitato con il login dell'abbonamento non è verificato.
  Fonte: `reports/catena_2026-09-16/grok_probe.json`.

### 3.2 Orchestratore (misura)

- **Formato dell'incarico.** Un incarico JSON con percorso `deep_kimi`, criteri umani e
  un allegato nella stessa cartella passa `orch brief` con uscita 0.
  Fonte: `reports/catena_2026-09-16/orch_brief_probe.txt`.
- **Allegati.** Il caricatore degli incarichi rifiuta allegati fuori dalla cartella
  dell'incarico o sopra i 200 KB (`src/orchestrator/briefs.py`).
- **Esecuzione.** `orch start` gira fino alla fine. Stampa l'id del run, lo stato finale
  e il percorso del rapporto, ed esce con 0, 1 o 2 (`src/orchestrator/cli.py`).

### 3.3 Prove con agenti simulati (misura)

Sono 42 test in `tests/test_daily_cycle.py`, tutti verdi. Coprono:

- **ciclo del mattino:** il ciclo 01 intero, e nessun lavoro ripetuto al secondo
  passaggio;
- **cicli dal dialogo:** il ciclo 02 aspetta il suo turno e parte dal commit del 01; un
  lavoro già integrato riparte da `HEAD`;
- **campagne:** il tetto di tre; l'avvio spento; un incarico non valido registrato e non
  avviato; la ripresa dopo un'interruzione senza ripetere campagne né chiamate;
- **collaudo:** i test modificati dopo la revisione fermano il ciclo; una copia
  manomessa da Claude non cambia l'esito; un collaudo che passava già rende il ciclo
  `parziale`;
- **controlli di ingresso e di stato:** foglio e bozza non validi, Claude non
  autenticato, cartella del 16 settembre ignorata, secondo guardiano rifiutato.

L'intera suite del progetto: 565 test verdi, uno saltato, in 375 s. Il controllo dei
documenti è verde. Fonte: `reports/catena_2026-09-16/verifiche.txt`.

### 3.4 Un difetto trovato dalle prove e corretto (misura)

Il primo giro dei test ne ha fatto fallire uno. Eseguire il collaudo scriveva file `.pyc`
in una cartella `__pycache__` sotto `src` del worktree, e quel file finiva nel commit del
ciclo. Ora il
collaudo gira con `PYTHONDONTWRITEBYTECODE=1`. Il `.gitignore` del progetto esclude
comunque `__pycache__/`; il repository dei test no.

### 3.5 Questa macchina (misura, 16 settembre)

- Lo script trova Codex, Claude, Grok e il Python di `orch-venv`.
- `claude auth status` risponde `loggedIn: false`.
- L'attività «VCC2026 Ciclo giornaliero» è `Ready`.
- Il sigillo di `reports/ciclo_giornaliero/2026-09-16/01_piano.json` non corrisponde più
  ai due piani, modificati dopo il sigillo per CP-0018. Nel sigillo gli sha256 iniziano
  per `259ac498` e `a611557c`, sui file per `e5f927bd` e `4935a921`.

## 4. Interpretazione e incertezza

- **Il comportamento con gli agenti veri è un'ipotesi.** Nessun ciclo è girato dal vivo.
  Gli agenti simulati rispettano le righe di comando documentate e osservate, ma non
  dicono come si comporteranno quelli veri. Per esempio:
  - se Codex scriverà test che falliscono davvero prima del lavoro;
  - se Grok, in modalità `plan`, leggerà i file del worktree: la prova non gli ha fatto
    usare strumenti.
- **Il collaudo protegge solo in parte (interpretazione).** Il controllo «deve fallire
  prima» ferma i test banali, non quelli deboli: la qualità del collaudo resta di
  Codex. Il collaudo impedisce però che sia Claude a scriversi l'esame.
- **Le campagne non possono verificare niente (interpretazione).** Con criteri solo
  umani, l'orchestratore arriva al più a «convergenza, validazione mancante». Il
  resoconto riporta lo stato così com'è.
- **Rischi operativi (ipotesi).**
  - Le sessioni web di DeepSeek e Kimi possono scadere di notte, e Kimi è caduto il 14 e
    il 15 settembre.
  - Grok Build è in beta.
  - Il costo reale delle chiamate a Grok non è verificato.
  - Il consumo delle quote con molti cicli al giorno non è misurato.
- **Mappa indietro rispetto al lavoro (interpretazione).** Senza integrazione, i branch
  dei cicli si impilano e la mappa resta indietro. Il piano del mattino ora legge i
  resoconti per compensare, ma è una toppa, non una fase.
- **Processi rimasti vivi (limite noto).** Un timeout sul comando di verifica
  `cmd /c scripts\py.cmd` può lasciare vivo il processo figlio. Orchestratore e collaudo
  sono invece chiamati direttamente sul loro Python.

## 5. Spiegazione semplice

È una staffetta con una cassetta delle lettere. Ogni corridore, finito il suo tratto,
lascia un biglietto sigillato nella cassetta; il successivo parte solo quando lo trova.
Un guardiano guarda la cassetta ogni minuto. L'esame del tratto di Claude lo scrive
Codex prima che Claude parta: Claude può leggerlo, ma si corregge una copia che lui non
può toccare. Alla fine arriva Grok, l'ispettore. Scrive la sua relazione prima di
sentire due consulenti esterni, DeepSeek e Kimi, e può chiamarli al massimo tre volte.
Poi lascia il resoconto nella cassetta del proprietario, e tutti dormono fino al
prossimo biglietto.

## 6. Conseguenze

- **D-021 aggiornata:** Grok decide le campagne, lo script le avvia, al massimo tre per
  ciclo; `orch start` a mano resta possibile.
- **Utilità di pianificazione:** l'attività delle 08:30 (`ciclo.cmd run`) funziona con
  il nuovo script e ora arriva fino al controllo di Grok. Il guardiano all'accesso non è
  registrato: serve il consenso del proprietario (`docs/CICLO_GIORNALIERO.md` §10).
- **Prima del primo ciclo reale:**
  - `claude auth login`;
  - verificare che Grok non addebiti a consumo;
  - sessioni di DeepSeek e Kimi attive nel profilo dell'orchestratore.
- **Ancora da definire:** l'integrazione (merge dei branch, mappa, registro). L'email è
  facoltativa e non implementata.
- **Prima misura vera:** i segnali e i resoconti del primo ciclo reale. Il piano
  successivo dovrebbe citarli.

## 7. Cosa corregge

Nessun checkpoint. Supera due materiali:

- **`docs/CICLO_GIORNALIERO.md` a un giro al giorno** (versione nel commit `4272b3b`).
  Diceva «una sola iterazione al giorno» e lasciava «da definire» la fase dopo
  l'implementazione. Ora i cicli sono ripetibili e la fase 4 è il controllo di Grok.
  L'integrazione resta da definire.
- **D-021 nella versione del 13 settembre.** L'orchestratore si avviava solo a mano, e
  un agente che decide da sé quando ripartire era un'alternativa scartata. Ora è
  ammesso, con i paletti scritti nella scheda.

## 8. Domanda di comprensione

Se Claude modifica i test che vede in `.ciclo/collaudo/`, perché l'esito del collaudo non
cambia? E perché un collaudo che passa già prima del lavoro rende il ciclo `parziale`
invece che `completato`?
