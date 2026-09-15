# L'orchestratore locale — architettura, stato, e che cosa è stato davvero provato

Aggiornato il 2026-09-15.

Questo documento descrive un sottosistema **nuovo e in gran parte non ancora provato sul
campo**. La distinzione va tenuta stretta, perché è il modo in cui questo repository ha
già sbagliato una volta:

| Parte | Stato | Evidenza |
|---|---|---|
| Motore: round, obiezioni, controlli, convergenza, arresto, ripresa, rapporto | **provato end-to-end**, con risposte finte | `reports/orchestrator/prova-a-secco-2026-09-13/` |
| Prevenzione dei doppi invii su ripresa | **misurata**: 5 passi, 5 invii totali su due esecuzioni complete | come sopra, `events.jsonl` |
| 95 test sui modi di sbagliare in silenzio | **eseguiti**, verdi | `tests/test_orchestrator.py` |
| Adattatore Gemini CLI | **implementato, mai eseguito**: la CLI non è installata su questa macchina | `orch doctor` dice «gemini is not on PATH» |
| Canale browser: Playwright guida il Chrome installato con un profilo dedicato | **misurato**: Chrome 152.0.7977.83, apertura in 2,9 s, scrittura e lettura in pagina locale, nessun Chromium scaricato | `reports/orchestrator/canale-browser-2026-09-13.json` |
| Ciclo a due DeepSeek-Kimi (percorso `deep_kimi`): 3 round, simmetria, convergenza senza verifica | **provato end-to-end**, con risposte finte | `reports/orchestrator/prova-a-secco-deep-kimi-2026-09-13/` |
| Apertura di DeepSeek e Kimi nel browser reale, lettura della pagina | **eseguito il 2026-09-13**: entrambe raggiunte, entrambe disconnesse, nessun messaggio inviato | `reports/orchestrator/sonde-2026-09-13/` |
| Invio e lettura di una risposta su DeepSeek o Kimi | **eseguito il 2026-09-13** su entrambi, con una riparazione di formato su Kimi | §9-quinquies; i profili sono `verified: true` dal 13 settembre, ciascuno citando il run che lo giustifica |
| Modalità `scientific_research`: tre fasi, provenienza, dossier | **provata end-to-end**, con risposte finte; 65 test | `reports/orchestrator/prova-a-secco-ricerca-2026-09-14/`, [RICERCA_SCIENTIFICA.md](RICERCA_SCIENTIFICA.md) |
| Invio di un prompt di ricerca a DeepSeek o Kimi | **avviato il 2026-09-15** | run `20260915T115742Z-vcc2026-jiang-audit-v1-a81104`, incarico `vcc2026-jiang-audit`; non concluso al momento di CP-0016 |
| Prima campagna reale con materiale allegato (`critica-prospetto-modello`, 14 KB fuori dalla macchina) | **eseguita il 2026-09-14**: round 1 con entrambi i worker e criterio automatico verde su entrambi; Kimi caduta al round 2 e al round 3; fermata `service_unavailable` | `<VCC2026_DATA_ROOT>/orchestrator/runs/20260914T115438Z-critica-prospetto-modell-v1-ef7fa1/`, rapporto `report-20260914T121125Z.md` |
| Riserva come seconda conversazione nella sessione attiva; riserva raggiunta anche da un canale rotto prima dell'invio | **eseguito il 2026-09-14** sulla ripresa dello stesso run: round 4, Kimi fallisce tre volte con `navigation` **senza skip dell'operatore**, DeepSeek risponde nel posto `solver_b` e il posto passa stabilmente (`seat_reassigned`, assenze 1 + rinunce 1). Con il codice precedente quel round avrebbe chiuso il run | `runs/20260914T115438Z-…/events.jsonl` (4 `stand_in_used`, 1 `seat_reassigned`), tabella `steps` del run |
| Assenza distinta da controllo fallito | **implementato, mai eseguito su un run reale** | 181 test verdi; nel run del 14 settembre nessun round è finito senza una voce, quindi nessuna riga `absent` è stata prodotta |
| Un thread per posto che **sopravvive ai round** | **non raggiunto**: la chiave per posto funziona (le voci non si mescolano mai), ma l'URL memorizzato è la home del servizio, perché è quello che la pagina espone subito dopo l'apertura di una chat nuova. Tornare su un posto riapre quindi una chat nuova invece di rientrare nella sua | `runs/20260914T115438Z-…/steps/*/transport.json`: `conversation_url` è sempre `https://chat.deepseek.com/`, mentre `url` cambia a ogni round dal terzo in poi |

Che il codice esista non dimostra che giri; che giri non dimostra che il risultato sia
giusto. Le due righe «implementato, mai eseguito» restano tali finché non esiste un run
reale con la sua cartella di passi: nessuna prova locale può sostituirle.

## 0. Che cos'è, e cosa non è

È un programma locale che porta una domanda a più modelli, in un ordine deciso da
configurazione, conserva tutto quello che è stato chiesto e risposto, decide con codice
deterministico quando fermarsi, e produce un rapporto.

Non è un agente. **Non esiste alcun percorso di codice che avvii una campagna da solo**:
niente scheduler, niente demone, niente ripartenza automatica. Un run comincia solo
quando una persona scrive `orch start`, e quando finisce non ne comincia un altro.

## 1. Confini

| Chi | Ruolo | Nel ciclo? |
|---|---|---|
| Tu (e GPT) | Definite l'obiettivo, preparate e controllate l'input, avviate, valutate | **fuori**: solo agli estremi |
| Claude | Ha progettato e implementato l'orchestratore | **fuori**: non viene interrogato dal sistema |
| Gemini, Grok | Inquadramento iniziale, checkpoint facoltativi, revisione finale | poche iterazioni |
| DeepSeek, Kimi | Ciclo di proposta, critica e revisione fino a un criterio di arresto | molte iterazioni, entro limiti |

Canali: Gemini via CLI ufficiale autenticata con l'account Google; Grok, DeepSeek e Kimi
via interfaccia web, nel browser, con le tue sessioni. **Nessuna API a pagamento e nessuna
estrazione di token**: l'adattatore web guida la pagina visibile, non chiama endpoint
privati. Una pagina che possiamo guardare fallisce in modo visibile; un endpoint copiato
fallisce in silenzio.

## 2. Architettura

```
configs/orchestrator/orchestrator.yaml     servizi, ruoli, percorsi, limiti, guardie
configs/orchestrator/services/*.yaml       un profilo per interfaccia web (selettori)
configs/orchestrator/briefs/*.yaml         gli incarichi
        │
        ▼   scripts/orch.cmd  →  python -m orchestrator.cli
src/orchestrator/
  cli.py           i comandi: doctor, brief, start, resume, status, watch, show,
                   events, pause, unpause, stop, approve-plan, reconcile, report,
                   login, probe
  settings.py      carica e valida la configurazione; rifiuta ciò che non è ammesso
  briefs.py        l'incarico: versione per contenuto, e guardia su cosa può uscire
  protocol.py      come si chiede e cosa si accetta di leggere  ← confine con i dati
  engine.py        il ciclo: chi viene interrogato, quando, e con quale prompt
  convergence.py   i cinque modi di fermarsi, e i numeri che li producono
  checks.py        i controlli di accettazione (contains, regex, numeric, human)
  store.py         SQLite (indice e controllo) + file (evidenza, scritti una volta sola)
  report.py        il rapporto finale, verbatim e con i percorsi
  adapters/        gemini_cli · web (Playwright) · manual · scripted (offline)
        │
        ▼
<VCC2026_DATA_ROOT>/orchestrator/          fuori dal repository (D-001: il Desktop è OneDrive)
  orchestrator.sqlite3                     stato, controllo, eventi
  runs/<run>/run.json                      istantanea di com'era configurato quel run
  runs/<run>/events.jsonl                  registro append-only
  runs/<run>/steps/<fase-round-ruolo-id>/  prompt.txt, response.raw.txt,
                                           response.parsed.json, quarantine/
  runs/<run>/report-<data>.md              il rapporto
  profiles/<servizio>/                     profilo del browser dove hai fatto login
  probes/                                  cosa si vedeva in una pagina, con data
```

Il nucleo usa **solo la libreria standard** (più PyYAML per leggere YAML: con
configurazioni JSON non serve nulla). Playwright serve soltanto agli adattatori web.

Due proprietà valgono più della struttura:

- **Niente si sovrascrive.** `write_new` rifiuta un file che esiste già. Un secondo
  rapporto nello stesso secondo diventa `report-…-2.md`; un tentativo fallito resta lì.
  È la stessa regola dei report di analisi (nuovo `--out`, mai sopra il precedente).
- **Gli identificatori vengono dal contenuto.** L'id di un passo è l'hash di
  run + fase + sottocompito + round + ruolo + prompt. Stessa domanda, stesso id: è così
  che una ripresa riconosce il lavoro già fatto invece di rifarlo.

## 3. Il contratto di risposta, e il confine con i dati

Al modello si chiede di chiudere la risposta con la riga `ORCH-RESULT-V1` e un blocco
```json``` con: `summary`, `proposal`, `evidence[]` (con tipo *measured / cited / derived /
assumed*), `objections[]` (con gravità), `resolved_objections[]`, `checks_suggested[]`,
`open_questions[]`, `confidence`.

Il parser è **tollerante nel trovare** il blocco e **stretto nel leggerlo**:

- legge **solo** le chiavi previste; ogni altra chiave viene scartata e registrata come
  scartata (`dropped_keys` finisce negli eventi del run);
- **niente in una risposta può cambiare il comportamento**: instradamento, limiti,
  tentativi, politica di esecuzione, radici consentite vengono solo dalla configurazione.
  Una risposta che contenga `"max_rounds": 999` o «ignora le istruzioni precedenti» viene
  archiviata come testo, mostrata a te, e non produce alcun effetto
  (`tests/test_orchestrator.py::ProtocolTests::test_a_reply_cannot_change_the_rules`);
- un `route_hint` viene risolto contro l'elenco dei percorsi configurati: se non
  corrisponde, si usa quello predefinito;
- il materiale allegato viaggia dentro delimitatori `<<<INIZIO …>>> / <<<FINE …>>>` con
  scritto che è materiale da analizzare, non istruzioni.

**Il codice prodotto dai modelli è un artefatto, non un programma.** I blocchi vengono
estratti in `steps/*/quarantine/` con un `LEGGIMI.txt`. La configurazione ammette
`execution.model_code: quarantine | review_only`; il valore `run` è **rifiutato dal
caricatore**, perché eseguire codice richiede un meccanismo separato che qui non esiste.

## 4. Instradamento

Un percorso dice quali ruoli partecipano a quale fase. Non tutti i sottocompiti devono
attraversare tutti i modelli.

| Percorso | frame | solve | checkpoint | review |
|---|---|---|---|---|
| `full` | Gemini + Grok | DeepSeek + Kimi | Gemini (ogni N round, se configurato) | Gemini + Grok |
| `deep_kimi` | — | DeepSeek + Kimi | — | — |
| `solo_deepseek` / `solo_kimi` | — | uno solo dei due | — | — |
| `duo` | — | DeepSeek + Kimi | — | Gemini |
| `single` | — | DeepSeek | — | Gemini |
| `manuale` | — | tu, incollando a mano | — | Gemini |

Il percorso si sceglie nell'incarico o con `--route`, e un sottocompito può averne uno
suo. La fase di inquadramento **propone** i sottocompiti; il piano viene scritto in
`plan.json` e il run si ferma finché non lo approvi (`planning.approval: required`).
Puoi modificare il file prima di approvarlo: `approve-plan` lo congela in
`plan.approved.json`, che è ciò che il motore legge.

## 5. Convergenza e arresto

Dopo ogni round il motore valuta, in quest'ordine:

| Esito | Quando | Che cosa significa |
|---|---|---|
| `verified_complete` | ogni criterio ha un controllo automatico e tutti passano su **tutte** le proposte | l'unico esito che vale come verifica |
| `unresolved_disagreement` | un'obiezione *blocking* resta aperta per `disagreement_rounds` | serve una tua decisione |
| `proposals_converged` | le proposte sono stabili e testualmente vicine per `convergence_rounds` | soluzione stabile, **validazione ancora da fare** |
| `stagnation` | nessuna nuova evidenza, obiezione o correzione per `stagnation_rounds` | il ciclo non sta più producendo |
| `limit_reached` | `max_rounds` o `max_wall_clock_minutes` | vale **anche** per i cicli «a convergenza» |
| `service_unavailable` | un servizio non risponde | il modello manca e si vede; nessuna sostituzione |

L'accordo fra DeepSeek e Kimi **non** è una prova di correttezza, e il codice lo tratta
così: un criterio diventa verde solo se lo dice un controllo il cui valore atteso stava
nell'incarico **prima** che qualcuno rispondesse. Con criteri solo umani, il massimo
raggiungibile è `proposals_converged`, che nel rapporto è scritto per esteso come
«convergenza delle proposte (validazione mancante)».

Dal 13 settembre la convergenza **non** si misura piu' sulla somiglianza dei testi. Nel
primo run reale i due modelli concordavano su ogni punto sostanziale e la somiglianza era
**0,345**, perche' scrivono in modo diverso: una regola che aspetta 0,92 fra due modelli
diversi aspetta per sempre, e «fino a convergenza» diventerebbe in silenzio «fino al
tetto». Adesso, quando per N round nessuno porta evidenze, obiezioni o correzioni nuove e
ciascuno ha smesso di riscriversi, l'esito dipende da una cosa sola:

* **nessuna obiezione aperta fra i due** → `proposals_converged`;
* **qualcosa ancora conteso** → `stagnation`.

Resta valida anche la vecchia scorciatoia: due testi quasi identici sono convergenza senza
bisogno d'altro.

Due avvertenze oneste:

1. La somiglianza fra proposte è **testuale** (`difflib`), non semantica. Due risposte
   giuste scritte in modo diverso danno un valore basso: nella prova a secco entrambe
   dicevano 24 con somiglianza 0,393. Serve a rilevare «ha smesso di cambiare», non
   «vogliono dire la stessa cosa». Per questo `verified_complete` viene prima.
2. Un'obiezione rivolta al materiale in esame non e' un disaccordo fra i due modelli.
   Il primo run reale si e' fermato per «disaccordo irrisolto» mentre i due erano
   d'accordo su tutto: le cinque obiezioni bloccanti rimaste aperte erano le loro
   critiche **condivise** al codice sotto esame, che nessuno avrebbe mai risolto perche'
   nessuno le contestava. Ora contano solo le obiezioni rivolte a un partecipante.
3. L'età di un'obiezione si conta in **occasioni reali di risolverla**, non in round
   trascorsi. Non conta il round che l'ha sollevata — i round sono sincroni, l'altro non
   poteva ancora averla vista — e non conta un round in cui è mancata una voce: chiudere
   un'obiezione richiede che il bersaglio risponda *e* che chi l'ha sollevata accetti, e
   con qualcuno assente non c'era nessuna occasione. Trovato sul run delle 00:24 del 14
   settembre, fermato per «disaccordo irrisolto» al round 4: le due obiezioni erano nate
   al round 2, e nei round 3 e 4 mancava ogni volta un modello. Con la vecchia regola
   valevano 3 round di età, con quella nuova ne valgono 0.
4. La verifica ha la precedenza su un'obiezione aperta. Se i controlli passano su
   entrambe le proposte mentre un'obiezione resta formalmente aperta, il run si chiude
   come verificato **e l'obiezione compare comunque** nella sezione 4 del rapporto.

Un'obiezione la chiude solo chi l'ha sollevata: se è l'altro a dire «risolta», lo stato
diventa `resolved_claimed`, che continua a contare come aperta.

## 6. Controllo umano

```bash
.\scripts\orch.cmd doctor                          # ambiente, canali, permessi
.\scripts\orch.cmd brief configs/orchestrator/briefs/prova-fattoriale.yaml
.\scripts\orch.cmd start --brief <incarico> [--route duo]
.\scripts\orch.cmd status | watch | show --diff | events
.\scripts\orch.cmd pause | unpause | stop | resume
.\scripts\orch.cmd approve-plan <run>
.\scripts\orch.cmd reconcile <run> --step <id> [--abandon | --reply-file <file>]
.\scripts\orch.cmd report <run>
```

Durante l'esecuzione, da un secondo terminale, `watch` mostra: run e stato, sottocompito
attivo, ruolo e servizio del passo in corso, round, conteggio dei passi per stato,
obiezioni aperte, e l'ultima decisione con i suoi numeri. `show --diff` mostra, per ogni
ruolo, il confronto riga per riga con il proprio round precedente e quante evidenze e
obiezioni sono nuove. `show --prompt --raw` mostra input e output **originali**.

`pause` e `stop` vengono raccolti fra un passo e l'altro. Un `Ctrl+C` non perde niente: lo
stato è su disco e `resume` riparte da lì. Un run attivo è protetto da un lock con
heartbeat, perché due processi sullo stesso run invierebbero le stesse domande due volte.

**Ripresa dopo un crash.** Un passo che risulta `dispatched` ma senza risposta è
ambiguo: la domanda può essere arrivata o no. Il motore **non lo reinvia da solo**, si
ferma e chiede una riconciliazione: guardi la conversazione nel servizio e dichiari se la
risposta va acquisita (`--reply-file`) o se il passo va rifatto (`--abandon`).

## 7. Versioni dell'incarico

L'hash di un incarico copre i suoi campi **e i byte dei materiali allegati**. Se modifichi
un incarico già registrato senza cambiare `version`, l'avvio viene rifiutato con un
messaggio che dice cosa fare; `--bump-version` registra la versione successiva. Ogni run
porta con sé `brief_id`, versione e hash, quindi un risultato prodotto con il testo
precedente resta riconoscibile.

## 8. Errori del canale contro problemi del contenuto

Sono tenuti separati perché richiedono cose diverse.

- **`TransportError`** (browser morto, sessione scaduta, timeout, CLI assente, quota):
  ritentato fino a `transport_retries`, poi il run si ferma con `service_unavailable`.
  Su fallimento l'adattatore web salva screenshot e HTML nella cartella del passo.
- **`ContentProblem`** (nessun blocco, JSON non valido, `proposal` mancante): **non** si
  ritenta la stessa domanda. Parte un unico prompt di riparazione che chiede solo il
  blocco; se fallisce anche quello, la risposta grezza resta agli atti, il passo è
  `unparsed` e viene registrata un'obiezione automatica che lo segnala.

**Una riparazione riuscita sopravvive alla ripresa.** Corretto il 14 settembre 2026,
trovato dalla prova a secco della modalità di ricerca. Alla ripresa il motore trovava il
primo tentativo illeggibile, smetteva di cercare, e proseguiva come se quel modello non
avesse mai risposto: la risposta riparata restava sul disco, ignorata, e al compagno
veniva detto che una voce mancava. Ora, quando il passo principale di un posto risulta
`unparsed`, il motore cerca nello stesso posto un passo `answered` con un prompt diverso —
che per costruzione può essere solo la sua riparazione — e usa quello
(`_existing_repair`). Riguardava anche questo ciclo, non solo la modalità nuova.

## 9. Che cosa è stato provato

Il 13 settembre 2026, con l'orchestratore appena scritto, è stata eseguita una prova a
secco su un compito innocuo — «quanti zeri finali ha 100!» — con risposte preparate a mano
in `configs/orchestrator/rehearsal/prova-fattoriale/`, senza contattare nessun servizio e
senza inviare nulla del progetto.

Lo scenario e ciò che il motore ha fatto (`reports/orchestrator/prova-a-secco-2026-09-13/`):

- round 1: una proposta dice 24 (corretta), l'altra 20 (dimentica i multipli di 25). Due
  criteri su tre falliscono, il ciclo continua;
- round 2: la prima solleva un'obiezione *blocking* specifica, la seconda la accetta e si
  corregge. I tre controlli passano su entrambe le proposte → `verified_complete`;
- revisione finale, poi rapporto con esito, evidenze, controlli eseguiti round per round,
  disaccordi, motivo dell'arresto e decisioni che restano all'operatore;
- rieseguito l'intero run: **5 passi, 5 invii totali**, tutti riconosciuti come già fatti.

Questo dimostra il motore. **Non dimostra nulla sugli adattatori reali**: né la CLI di
Gemini né alcuna interfaccia web sono state contattate.

## 9-bis. Il ciclo a due: percorso `deep_kimi`

Aggiunto il 2026-09-13. È il percorso in cui lavorano **solo** DeepSeek e Kimi:
`solve: [solver_a, solver_b]`, nessun inquadramento, nessun checkpoint, nessuna revisione
affidata ad altri. Gemini, Grok, GPT e Claude non vengono interpellati in nessun momento —
non per convenzione, ma perché il percorso non contiene ruoli che li mappino, e c'è un test
che lo verifica sulla configurazione che spediamo davvero
(`RealConfigurationTests::test_deep_kimi_calls_nobody_but_deepseek_and_kimi`).

Come gira:

1. Prepari l'incarico e lo avvii tu. Il percorso non ha fase di inquadramento, quindi non
   c'è nessun piano da approvare: il sottocompito è l'incarico stesso.
2. **Round 1 alla cieca.** I due ricevono lo stesso problema e non vedono nulla l'uno
   dell'altro. Il prompt lo dice esplicitamente.
3. **Dal round 2** ciascuno riceve la proposta completa dell'altro, le modifiche che
   l'altro dichiara di aver fatto, le sue questioni irrisolte e le obiezioni aperte; e deve
   produrre, in quest'ordine: obiezioni precise, risposte alle obiezioni che lo riguardano,
   `changes` (che cosa ha cambiato rispetto a sé stesso), `open_questions`, e la proposta
   riscritta per intero.
4. **L'ordine tecnico degli invii non conta.** La vista del round è costruita *una volta
   sola*, prima di interrogare chiunque, a partire dal round precedente: chi viene
   contattato per secondo non riceve niente in più. È verificato da un test che confronta i
   due prompt del round 2 e controlla che nessuno dei due contenga materiale del round 2
   (`TwoModelLoopTests::test_the_send_order_gives_the_second_model_nothing_extra`).
5. **Una risposta incompleta non viaggia.** Prima di inoltrare, la risposta deve rispettare
   il contratto; l'adattatore concede tempo extra a un blocco ancora aperto invece di
   accettarlo, e se resta illeggibile all'altro modello viene detto che una risposta
   utilizzabile non è arrivata — mai il testo a metà, e mai il silenzio spacciato per
   accordo.
6. **Una conversazione per esecuzione.** Ogni run apre una chat nuova nel servizio e ci
   resta per tutti i round, così la sessione è leggibile anche dal lato del servizio. Non è
   una dipendenza: ogni prompt porta con sé tutto lo stato che gli serve.
7. Si ferma per limite, stagnazione, stabilità delle proposte, problema del servizio o tuo
   arresto. Con criteri solo umani — come nell'incarico di collaudo — **il completamento
   verificato non è raggiungibile per costruzione**: il massimo è
   `proposals_converged`, che il rapporto scrive «convergenza delle proposte (validazione
   mancante)».
8. Il rapporto ti dà: le due proposte finali verbatim, **il diff fra le due** con la loro
   somiglianza testuale, le modifiche dichiarate nell'ultimo round, le obiezioni ancora
   aperte, il motivo dell'arresto con i numeri, e i criteri che restano da verificare a
   mano.

Prova a secco del percorso, con risposte preparate a mano
(`reports/orchestrator/prova-a-secco-deep-kimi-2026-09-13/`): round 1 con due proposte
indipendenti e distanti (somiglianza 0,110), round 2 con due obiezioni precise, una accolta
e una lasciata aperta, round 3 senza novità → **convergenza delle proposte** a somiglianza
0,954, con i tre criteri ancora da verificare a mano. Nessun servizio esterno contattato.

## 9-ter. Che cosa è stato eseguito sui servizi reali

Il 13 settembre 2026, con `orch probe`, che **legge la pagina e non invia niente**
(`reports/orchestrator/sonde-2026-09-13/`):

| Servizio | Esito | Dettaglio |
|---|---|---|
| DeepSeek | raggiunto, **non autenticato** | reindirizza a `/sign_in`, pagina resa in 3,3 s, interfaccia in italiano, banner cookie. Della chat non si vede nulla |
| Kimi | raggiunto, **non autenticato** | pagina resa in 10,4 s, interfaccia in cinese; il compositore `div.chat-input-editor[role=textbox]` è visibile anche senza login, i contenitori dei messaggi sono vuoti |

Nessun CAPTCHA e nessun blocco anti-bot durante le due aperture. Il guardiano
`logged_out_url_fragments` è confermato su DeepSeek: l'URL finale è davvero `/sign_in`.

La prima sonda ha trovato **una pagina bianca**, e non era colpa del sito: aspettava
`domcontentloaded`, che su queste interfacce scatta sul guscio vuoto. Corretto con
`WebChatAdapter.settle()`, che attende la comparsa di elementi interattivi e registra
quanti secondi ha atteso; la sonda cieca è conservata come evidenza del difetto. È il tipo
di errore che sarebbe passato per «il servizio non ha un compositore».

**Quello che resta non dimostrato sui canali reali:** scrivere nel compositore, inviare,
leggere una risposta completa, riconoscere la fine dello streaming, e far passare una
risposta da un modello all'altro. Tutto questo richiede il login, che è tuo.

## 9-ter-bis. Quando un modello non risponde

Deciso dall'operatore il 13 settembre, dopo che Kimi ha risposto «troppo traffico» e il
run ha aspettato dieci minuti prima di fermarsi.

**Il round prosegue senza quella voce.** Il passo viene chiuso come `abandoned`, all'altro
modello viene detto per esteso che il compagno non ha consegnato — «non dedurne che sia
d'accordo con te» — e il rapporto elenca quali round sono stati dimezzati. La domanda
**non viene mai rimandata**: era gia' partita, e ripeterla significherebbe farla due volte
nella stessa conversazione.

Se lo stesso servizio manca `absence_tolerance` round di fila (due, di default) il run si
ferma con `service_unavailable`, a meno che la route non dichiari una riserva (§9-ter-ter):
a quel punto non e' piu' un ciclo a due, e' un monologo. Un servizio che risponde azzera il
contatore.

**Nemmeno la ripresa rimanda la domanda.** Trovato il 14 settembre guardando il run delle
21:55, messo in pausa dopo un timeout di Kimi al round 1: il passo era chiuso come
`abandoned`, ma la domanda era gia' partita, e alla ripresa il motore ne apriva un secondo
tentativo — cioe' incollava lo stesso prompt nella stessa conversazione. Ora un passo
abbandonato **dopo l'invio** non viene riaperto. L'unica cosa che lo riapre e' `orch
reconcile --abandon`, con cui sei tu a dichiarare, avendo guardato la chat, che la domanda
non e' mai arrivata.

Tre cose accorciano l'attesa, invece di consumare tutto il timeout:

* **Il rifiuto del servizio si riconosce dal testo della pagina.** `service_refusals` nel
  profilo elenca le frasi che significano «non ti servo adesso»; il controllo scatta solo
  finche' non e' arrivato alcun messaggio, cosi' un modello che scrive «traffico» nella
  propria risposta non lo fa scattare. Le frasi di Kimi sono quelle riferite
  dall'operatore, non ancora viste da qui.
* **A meta' attesa il terminale lo dice**, con l'ora in cui rinuncera' e i comandi per non
  aspettare.
* **`orch skip` rinuncia al passo in corso** da un secondo terminale. Non e' una domanda
  bloccante di proposito: un run non presidiato non deve fermarsi ad aspettare una
  risposta umana. Uno `skip` chiesto quando nulla e' in attesa viene scartato come vecchio.
  **Se il posto ha una riserva, lo skip la chiama**: «non aspetto questo» vuol dire
  «chiedi all'altra», non «perdi il round». Corretto il 14 settembre: la prima versione
  faceva proseguire il round a una voce sola, che non e' quello che uno si aspetta
  premendo skip. Una rinuncia non ferma mai un run — quello lo fanno solo le assenze vere —
  ma concorre a far passare il posto alla riserva, perche' in un modo o nell'altro quel
  servizio non sta producendo.

Il 13 settembre questa sezione diceva «nessuna sostituzione». Il 14 settembre, dopo una
serata in cui Kimi ha risposto «troppo traffico» a ripetizione, l'operatore ha deciso
diversamente: la sostituzione si fa, ma dichiarata prima e visibile dopo. Il paragrafo
seguente sostituisce quella posizione; il motivo per cui era stata presa resta valido ed
è il motivo per cui la riserva è marcata ovunque (D-022).

## 9-ter-ter. La sessione di riserva

Deciso il 14 settembre 2026. Serve a un caso solo: **un servizio smette di rispondere
mentre l'altro funziona.**

**La riserva è una seconda sessione del servizio ancora attivo, mai di quello caduto.**
Se Kimi è sovraccarica, una seconda Kimi trova lo stesso sovraccarico; quello che serve è
una seconda DeepSeek, e viceversa. Non è una raccomandazione: il caricatore della
configurazione **rifiuta** una riserva della stessa famiglia del titolare.

```yaml
deep_kimi:
  solve: [solver_a, solver_b]
  stand_in:
    solver_b: deepseek      # se Kimi non consegna, risponde DeepSeek in un'altra chat
    solver_a: kimi          # se DeepSeek non consegna, risponde Kimi in un'altra chat
```

**Una seconda conversazione, non un secondo profilo.** Corretto il 14 settembre 2026,
dopo che la prima riserva reale è caduta. La versione precedente dava alla riserva una
`profile_dir` propria: cartella di profilo separata, quindi un secondo accesso da fare a
mano. Il vincolo che ci aveva portati lì è vero — Chrome non apre due volte la stessa
cartella di profilo — ma la conclusione no: non serve un secondo processo, serve un
secondo *thread*. Una cartella separata è una **seconda identità di browser**: eredita la
mappa di selettori verificata e non l'ambiente in cui quei selettori erano stati
verificati (lingua dell'interfaccia, dialoghi già chiusi, preferenze), e se ci si accede
con lo stesso account non compra niente. Nel run delle 11:54 è caduta sul primo controllo
di modalità: `Pensiero Profondo` non è un'etichetta che esiste in un'interfaccia in
un'altra lingua.

Oggi l'adattatore web apre **una conversazione per posto**, non una per run
(`WebChatAdapter.conversation_key`, chiave `run:ruolo`). La riserva è quindi il servizio
che sta ancora rispondendo, in una chat sua, nella sessione già autenticata: niente
secondo accesso, niente seconda cartella, stessa lingua e stessi selettori del canale che
funziona. La chat separata non è comodità: se la riserva rispondesse nel thread del
titolare si porterebbe in contesto le risposte precedenti del titolare, e le due voci che
il ciclo esiste per tenere separate diventerebbero una conversazione sola
(`ConversationThreadTests`).

Resta vero, e va detto ogni volta, che account e quota sono condivisi: se il servizio
limita, limita entrambe le chat. I blocchi `deepseek_b` e `kimi_b` in configurazione
restano definiti per il caso in cui esista un **secondo account vero**, che è l'unica cosa
che una cartella di profilo separata compri davvero.

Che cosa succede, in ordine:

1. Il titolare non consegna. Il passo resta `abandoned` con la sua cartella e la sua prova.
2. La riserva riceve **lo stesso round**, in una conversazione sua, con scritto in testa
   che sta subentrando e che non ha visto i round precedenti. La proposta lasciata nel
   ruolo le arriva come materiale — `PROPOSTA-LASCIATA-NEL-RUOLO`, non
   `TUA-PROPOSTA-PRECEDENTE` — perché non è sua e non deve difenderla.
3. Il compagno, al round dopo, legge in chiaro che quella risposta viene da una riserva e
   che **è un'altra istanza del suo stesso modello**, con l'istruzione di valutarla con
   più severità, non con meno.
4. Se il titolare tace per `absence_tolerance` round di fila, il posto **passa** alla
   riserva per il resto del run (evento `seat_reassigned`) invece di far fallire il run.
   Senza questo, ogni round successivo pagherebbe di nuovo il timeout intero.
5. Se la riserva stessa non è raggiungibile — mai autenticata, browser che non parte — il
   round torna a proseguire con una voce sola. Aggiungere una riserva non deve poter
   peggiorare le cose rispetto al non averla.
6. **Anche un canale che si rompe prima di inviare arriva alla riserva.** Corretto il 14
   settembre 2026. Da `_ask` si esce per tre strade — lo skip dell'operatore, la domanda
   consegnata e rimasta senza risposta, l'errore di canale prima dell'invio — e solo le
   prime due passavano dalla riserva: la terza sollevava, e il sollevamento scavalcava
   proprio la riserva che il chiamante avrebbe interrogato subito dopo. Un servizio troppo
   rotto per scrivergli era coperto **peggio** di uno che taceva e basta. Ora quell'errore
   conta come un'assenza, concorre al passaggio del posto, e il round prosegue con la
   riserva; senza riserva l'esito resta `service_unavailable`, invariato.

**Che cosa questo non è.** Due sessioni dello stesso modello non sono due modelli. Un
accordo fra loro è un modello che concorda con sé stesso, e vale meno di un accordo fra
modelli diversi: condividono gli stessi punti ciechi. Perciò la convergenza decisa su un
round coperto da una riserva esce con il motivo `..._same_model`, la frase mostrata a
schermo lo dice, e il rapporto lo ripete in due punti — sotto le proposte finali e fra le
decisioni che restano all'operatore. La scelta se accontentarsene o rifare il ciclo quando
il servizio manca torna disponibile è dell'operatore, non del sistema.

## 9-ter-quater. La modalita' di ricerca scientifica

Aggiunta il 2026-09-14. E' una **modalita'**, non un percorso: la sceglie l'incarico con
`mode: scientific_research`, e un incarico che non la dichiara vale `debug` e si comporta
esattamente come prima. Il ciclo di debug descritto qui sopra non cambia in nulla.

In breve, perche' il documento completo e' [RICERCA_SCIENTIFICA.md](RICERCA_SCIENTIFICA.md):

- tre fasi al posto dei round a convergenza — ricerca indipendente, confronto e piste,
  ricerca mirata e sintesi — e la vista di ogni fase e' costruita una volta sola prima di
  interrogare chiunque;
- il contratto di risposta e' diverso (`ORCH-RESEARCH-V1`) e chiede **il registro delle
  ricerche svolte** e **il livello a cui ogni fonte e' stata consultata**, separati da
  cio' che il worker conclude;
- il programma **non promuove** una ricerca dichiarata a una ricerca osservata: il canale
  mostra che l'interruttore era acceso, non quali query siano state eseguite;
- le piste di approfondimento le sceglie una regola deterministica, non un modello;
- il dossier finale e' assemblato da codice: due sintesi separate e verbatim, nessuna
  sintesi consensuale, nessuna contraddizione chiusa.

Al 14 settembre 2026 e' stata **provata solo a secco**. Un incarico scientifico reale e'
pronto in `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml` e **non e' stato
avviato**.

## 9-quater. Le modalita' del compositore

Aggiunto il 2026-09-13. Interfacce come DeepSeek hanno interruttori accanto alla casella di
testo — «Pensiero Profondo», «Ricerca intelligente» — che cambiano il comportamento del
modello. Lasciarli a quello che l'interfaccia si ricorda significa poter confrontare due
round eseguiti in condizioni diverse senza saperlo.

Quindi la configurazione li dichiara e l'adattatore li **impone e verifica**, una volta per
conversazione, prima del primo messaggio:

```yaml
# configs/orchestrator/orchestrator.yaml
deepseek:
  modes:
    pensiero_profondo: true
```

```yaml
# configs/orchestrator/services/deepseek.yaml
modes:
  pensiero_profondo:
    selector: "div.ds-toggle-button:has-text('Pensiero Profondo')"
    state_attribute: "aria-pressed"
    on_value: "true"
```

Se l'interruttore non si trova, non risponde al clic o resta nello stato sbagliato,
**non viene inviato niente**: e' un errore di canale con screenshot e HTML nella cartella
del passo. Lo stato applicato finisce nei metadati di ogni passo, quindi il rapporto dice
in che condizioni e' stata prodotta ogni risposta.

Misurato il 2026-09-13 nel profilo dell'operatore: `aria-pressed` e' l'attributo che porta
lo stato, e **entrambe** le modalita' risultavano gia' attive, «Pensiero Profondo»
compreso. Il selettore dipende dalla lingua dell'interfaccia: se cambia, il fallimento e'
rumoroso, perche' lo stato viene riletto dopo il clic.

## 9-quinquies. Collaudo assistito contro esecuzione autonoma

Claude serve a implementare e collaudare il sistema. **Durante un'esecuzione operativa non
deve leggere, sintetizzare, inoltrare risposte o decidere il passo successivo.** Tutta
l'intermediazione — template, invio, acquisizione, sincronizzazione dei round, persistenza,
arresto — e' codice deterministico.

La regola e' verificata, non promessa. Nel pacchetto non esiste alcun riferimento ad
Anthropic, Claude, OpenAI, nessun client HTTP: le uniche uscite dal processo sono
`subprocess` (la CLI di Gemini) e Playwright (il browser). Tre test lo impongono
(`NoModelInTheLoopTests`), e falliscono se un'aggiunta futura importa un SDK o chiama un
endpoint.

Restano allora tre categorie, e vanno tenute distinte nel registro:

| Categoria | Che cosa significa | Stato al 2026-09-13 |
|---|---|---|
| **Esecuzione autonoma** | un processo `orch` avviato da una persona porta a termine il lavoro da solo | provata **solo a secco**, con risposte da file |
| **Collaudo assistito** | Claude usa i propri strumenti per far girare codice dell'orchestratore a scopo diagnostico, fuori da un run | sonde, scoperta dei selettori e delle modalita', prova del canale browser |
| **Automazione incompleta** | un passaggio che in un run non presidiato richiederebbe ancora un intervento | elencata qui sotto |

**Criterio di completamento**, nelle parole dell'operatore: il comando parte da un
terminale esterno, senza un turno di Claude attivo, DeepSeek e Kimi completano almeno due
round e viene prodotto il report. Finche' non succede, l'automazione del canale web resta
**non dimostrata**, e nessuna prova assistita puo' sostituirla.

### Il primo invio reale, e i tre difetti che ha scoperto

Il 13 settembre 2026 l'operatore ha avviato il ciclo `deep_kimi` da un terminale esterno,
senza turno di Claude attivo. **DeepSeek ha risposto davvero**: modalita' «Pensiero
Profondo» applicata e verificata, 47,5 s di attesa, 7.241 caratteri ricevuti, non troncati,
proposta di 4.429 caratteri conforme al contratto, con quattro evidenze dichiarate. Anche
l'apertura di una conversazione nuova dall'indirizzo base ha funzionato.

Poi il processo e' morto aprendo Kimi, e ha scoperto tre difetti diversi
(`reports/orchestrator/primo-invio-reale-2026-09-13/`):

1. **Un solo runtime per processo.** L'API sincrona di Playwright ne tiene uno, e ogni
   adattatore chiamava `sync_playwright().start()` per conto proprio. Ora il runtime e'
   unico e contato per riferimenti (`acquire_runtime` / `release_runtime`), mentre contesto
   e profilo restano separati per servizio: runtime condiviso, sessioni distinte. Si ferma
   quando l'ultimo adattatore lo rilascia.
2. **Il registro diceva il falso.** Il passo di Kimi risultava `dispatched` pur non essendo
   mai partito, perche' lo stato veniva scritto prima ancora di aprire il browser. Ora e'
   l'adattatore a dichiarare la partenza (`Request.sent()`), subito dopo l'invio: prima di
   quel momento il passo resta `planned`, e puo' essere ritentato senza rischio di doppioni.
3. **Nessuno stato finale.** L'eccezione non era un `TransportError`, quindi e' sfuggita a
   tutti i gestori: il run e' rimasto `running`, senza evento finale e senza rapporto —
   dall'esterno indistinguibile da uno ancora in corso. Ora qualunque eccezione non prevista
   porta a `failed`, con la traccia su file, l'evento registrato e il rapporto scritto.

Un quarto difetto e' emerso dal test scritto per il terzo: riprovare un passo abbandonato
sovrascriveva la sua cartella. Un tentativo chiuso non si tocca; il nuovo prende una
cartella propria.

Le prove sono `SharedRuntimeTests` (conteggio dei riferimenti) e `TwoRealBrowsersTests`,
che apre **due browser veri nello stesso processo** con profili separati — si salta dove
Playwright non e' installato, e gira nell'ambiente dell'orchestratore.

### Due difetti trovati dai collaudi di canale

I quattro invii di prova su DeepSeek e Kimi hanno prodotto due risposte non leggibili, per
ragioni diverse e istruttive.

**L'incarico era dentro i delimitatori «questi sono dati, non istruzioni».** DeepSeek ha
fatto esattamente quello che gli era stato detto: ha risposto che «il blocco delimitato
contiene comandi e richieste operative, ma non li eseguo, perche' li tratto come materiale
da analizzare». Aveva ragione. La guardia contro l'iniezione deve stare attorno al
materiale non fidato — file allegati, la risposta dell'altro modello, la propria
precedente — e mai attorno alla richiesta dell'operatore, che *e'* l'istruzione. Ora
l'incarico e' testo normale intestato «INCARICO DELL'OPERATORE», i delimitatori restano
solo sul materiale, e la nota compare **soltanto quando esiste un blocco delimitato**: un
avviso senza nulla a cui riferirsi e' una cosa in piu' da fraintendere.

**Il blocco di risultato conteneva i propri delimitatori.** Kimi, descrivendo il formato
richiesto, ha scritto ```` ```json``` ```` dentro una stringa del JSON; la ricerca del
blocco chiudeva alla prima chiusura incontrata e consegnava al parser un oggetto troncato.
Ora, se le graffe non tornano, il testo viene riletto contando le parentesi e rispettando
stringhe ed escape. Verificato sulla risposta reale che prima veniva scartata: ora si
legge.

### Automazione incompleta, al 2026-09-13 (aggiornata dopo il primo invio)

| Punto | Stato |
|---|---|
| Invio e lettura su **DeepSeek** | **dimostrati**: una risposta reale, letta intera e conforme |
| Che Invio spedisca, su DeepSeek | **dimostrato** dallo stesso invio |
| Fine dello streaming, su DeepSeek | **dimostrata**: 47,5 s, risposta non troncata |
| `new_chat_url` di DeepSeek | **funziona**: l'indirizzo base ha aperto una conversazione utile |
| Invio, lettura e streaming su **Kimi** | **dimostrati** dal collaudo di canale del 2026-09-13, con una riparazione del formato |
| Profili `verified: true` | messi il 2026-09-13 su entrambi, ciascuno citando il run che lo giustifica |
| Due adattatori nello stesso processo | corretto e coperto da test, **non ancora visto in un run reale** |
| Banner dei cookie di DeepSeek | presente; va chiuso da una persona |
| Login e sessioni scadute | umani, per scelta |
| Manutenzione dei selettori | umana: `orch probe` osserva, l'operatore compila |

Il criterio di completamento resta quello dell'operatore, e **non e' ancora soddisfatto**:
un comando avviato da terminale esterno, senza turno di Claude, con DeepSeek e Kimi che
completano almeno due round e producono il report.

## 10. Prima di usarlo davvero

Scelte fatte con l'operatore il 13 settembre 2026: profilo di browser **dedicato** sul
Chrome gia' installato, **DeepSeek** come primo servizio da collegare, **ambiente separato**
per Playwright.

Gia' fatto:

- `C:/Users/ferra/vcc2026-data/orch-venv` (123 MB) con `playwright 1.62.0` e `PyYAML`.
  `scripts/orch.cmd` lo usa da solo se esiste, altrimenti ricade sul venv di progetto;
  `VCC2026_ORCH_PYTHON` ha comunque la precedenza. **L'ambiente di analisi non e' stato
  toccato**: nessun pacchetto aggiunto, `requirements.lock.txt` invariato.
- Nessun Chromium scaricato: `browser_channel: chrome` usa il browser gia' presente
  (~450 MB risparmiati, con 14,6 GiB liberi sul disco).
- Verificato che il canale funzioni su una pagina locale (§0).

Restano a te, in quest'ordine. Il primo collaudo riguarda **solo** DeepSeek e Kimi:
Gemini e la sua CLI non servono per il percorso `deep_kimi`, e possono aspettare.

1. `.\scripts\orch.cmd login deepseek` e `.\scripts\orch.cmd login kimi`. Si apre una
   finestra di Chrome sul profilo dedicato: accedi a mano. Il banner dei cookie lo decidi
   tu — l'orchestratore non accetta condizioni al posto tuo, e non legge né salva token.
2. Apri in ciascuno dei due una conversazione con almeno una risposta, poi
   `.\scripts\orch.cmd probe deepseek` e `... probe kimi`. Serve a vedere il selettore di
   **un** messaggio dell'assistente, che senza messaggi sullo schermo non esiste: e' il
   pezzo che manca a entrambi i profili.
3. Con quelle sonde davanti si compilano `selectors.editor`, `selectors.message`,
   `selectors.send` e `selectors.new_chat` in
   `configs/orchestrator/services/{deepseek,kimi}.yaml`. Di Kimi il compositore e' gia'
   compilato da osservazione.
4. Primo invio vero, un servizio alla volta, con i percorsi `solo_deepseek` e
   `solo_kimi` — un solo modello e nessun revisore, cosi' il collaudo di un canale non
   chiama nessun altro:

   ```
   .\scripts\orch.cmd start --brief configs/orchestrator/briefs/collaudo-deep-kimi.yaml --route solo_deepseek
   ```

   Se la risposta torna intera e leggibile, si mette
   `verified: true` con la data in quel profilo; altrimenti si guardano screenshot e HTML
   che l'adattatore ha salvato nella cartella del passo.
5. Solo quando **entrambi** i profili sono verificati:

   ```
   .\scripts\orch.cmd start --brief configs/orchestrator/briefs/collaudo-deep-kimi.yaml
   ```

   Tre round al massimo, incarico sintetico, criteri umani. Da un secondo terminale
   `.\scripts\orch.cmd watch` mostra round, servizio e decisione mentre succede;
   `pause` e `stop` intervengono fra un passo e l'altro.
6. Solo dopo quel collaudo ha senso un incarico vero — con materiale che hai controllato tu
   e `outbound.allowed_roots` allargata di proposito.

## 11. Limiti noti

- La somiglianza è testuale (§5).
- La fusione dei sottocompiti proposti dai due inquadratori è per titolo, con soglia 0,85:
  è grezza, ed è il motivo per cui il piano richiede la tua approvazione.
- Il rapporto tronca le proposte molto lunghe (6.000 caratteri) e rimanda al file: la
  cartella del passo resta la fonte.
- I checkpoint intermedi (`checkpoint_every`) sono implementati ma non provati.
- Un servizio web che risponde in streaming viene considerato finito quando il testo non
  cambia per `stable_seconds`. È un'euristica; su una risposta con pause lunghe può
  chiudere presto. Il testo resta comunque agli atti.
- Non c'è ancora una interfaccia grafica: `watch` è un terminale che si ridisegna.
