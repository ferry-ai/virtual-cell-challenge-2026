# La modalità `scientific_research` — come funziona, e che cosa è stato davvero provato

Aggiornato il 2026-09-14. Prima versione.

Questo documento descrive una modalità **nuova, provata solo a secco**. La distinzione
va tenuta stretta: al 14 settembre 2026 nessun messaggio di una campagna di ricerca è
stato inviato a DeepSeek o a Kimi.

| Parte | Stato | Evidenza |
|---|---|---|
| Contratto di risposta, livelli di provenienza, deduplicazione delle fonti | **provato**, 65 test | `tests/test_orchestrator_research.py` |
| Motore a tre fasi, budget, esiti, dossier, rapporto | **provato end-to-end**, con risposte finte | `reports/orchestrator/prova-a-secco-ricerca-2026-09-14/` |
| Ripresa senza doppi invii su una campagna di ricerca | **misurata**: 7 invii su due esecuzioni complete dello stesso run | come sopra, `events.jsonl` |
| Scelta deterministica delle piste | **provata**: 2 selezionate su 5 proposte, regola scritta in `leads.json` | come sopra |
| Accensione dell'interruttore di ricerca su un'interfaccia vera | **mai eseguita** | l'adattatore scriptato non impone nessuna modalità |
| Invio di un prompt di ricerca a DeepSeek o Kimi | **mai eseguito**: serve il tuo avvio | — |
| Che le distinzioni reggano su risposte vere | **non dimostrato** | reggono su risposte costruite apposta, che è meno |

## 1. Che cos'è, e in che cosa differisce dal ciclo di debug

Il ciclo esistente (`deep_kimi`, [ORCHESTRATORE.md](ORCHESTRATORE.md)) chiede a due
modelli di convergere su una proposta. Questa modalità chiede loro di **cercare**, e ciò
che deve sopravvivere fino alla fine non è un accordo ma un resoconto tracciabile: che
cosa è stato cercato, che cosa è stato trovato, che cosa sostiene o contraddice le
ipotesi, e che cosa resta da verificare.

Le due modalità convivono. Un incarico sceglie la propria con `mode:`; un incarico che
non lo dichiara vale `debug` e si comporta esattamente come prima.

```yaml
mode: scientific_research     # oppure debug, che è il valore predefinito
route: scientific_research
```

Il codice sta in `src/orchestrator/research/` e riusa il motore esistente per tutto ciò
che era già costato dei bug: un passo scritto prima di essere inviato, un identificatore
derivato dal prompt perché una ripresa riconosca il lavoro già fatto, una domanda
consegnata mai rispedita, una sola riparazione di formato, il codice dei modelli messo in
quarantena, pausa e arresto raccolti fra un passo e l'altro.

## 2. Le tre fasi

| Fase | Chi vede cosa | Che cosa produce |
|---|---|---|
| **1 — Ricerca indipendente** | nessuno vede l'altro | ricerche svolte, fonti trovate e consultate, evidenze pertinenti, limiti e domande aperte |
| **2 — Confronto e piste** | ciascuno vede i risultati **completi** della fase 1 | accordi, contributi complementari, contraddizioni, assunzioni non sostenute, lacune, e poche piste di approfondimento |
| **3 — Ricerca mirata e sintesi** | ciascuno vede le fasi 1 e 2 e le piste assegnate | evidenze aggiornate e una sintesi autonoma |

L'incarico può assegnare **prospettive complementari** — per esempio metodi e archivi a
uno, evidenze biologiche e limiti all'altro. È un modo di dividere il lavoro, non un
divieto di guardare altrove.

**L'ordine tecnico degli invii non conta.** La vista di ogni fase è costruita *una volta
sola*, prima di interrogare chiunque, a partire dalle fasi precedenti: chi viene
contattato per secondo non riceve niente in più. Due test lo verificano
(`test_the_send_order_gives_the_second_worker_nothing_extra`,
`test_a_worker_only_ever_sees_earlier_phases`).

Una risposta illeggibile **non viaggia**: all'altro worker viene detto che una risposta
utilizzabile non è arrivata, mai il testo a metà e mai il silenzio spacciato per accordo.

## 3. I cinque livelli di provenienza, e perché il codice non li promuove mai

È il cuore della modalità. Queste cose si assomigliano e valgono quantità molto diverse:

| Livello | Che cosa significa | Chi può assegnarlo |
|---|---|---|
| `proposed` | una query che nessuno ha eseguito | il programma, da `status: not_executed` |
| `declared_by_worker` | il worker dice di averla eseguita | il programma, da `status: executed \| failed \| blocked` |
| `observed_in_channel` | un artefatto della sessione mostra che è stata eseguita | **nessuno, in questa versione** |

E per le fonti, quattro livelli di consultazione: `found` (vista in un elenco di
risultati e nient'altro), `abstract`, `full_text_or_section`, `not_accessible`.

Tre regole, e ciascuna esiste perché l'opposto è l'errore facile:

1. **Il livello lo assegna il programma, non la risposta.** Una risposta che scrive
   `"provenance": "observed_in_channel"` chiede di essere creduta sulla propria onestà: il
   campo viene ignorato e l'ignoramento registrato.
2. **Il canale non espone le query.** Possiamo sapere che l'interruttore di ricerca era
   acceso; non sappiamo che cosa sia stato cercato. Quindi `observed_in_channel` esiste nel
   vocabolario e non è raggiungibile da nessun percorso di codice — c'è un test che
   fallisce il giorno in cui qualcuno ne aggiunge uno senza l'artefatto che lo
   giustifichi (`test_nothing_in_the_package_can_produce_an_observed_search`).
3. **Il livello di consultazione è *dichiarato*.** Non abbiamo guardato nessuno leggere.
   Il rapporto lo scrive in ogni tabella che li mostra.

## 4. Che cosa si conserva, e con quali identificatori

| Cosa | Campi | Identificatore |
|---|---|---|
| Ricerche | query, servizio, filtri, stato, provenienza, worker, fase | `Q-` + hash di query, servizio, filtri **e worker** |
| Fonti | titolo, autori, anno, DOI/URL, livello consultato, accessibilità, passo d'origine | `F-` + hash della **chiave del documento** |
| Affermazioni | testo, fonti a sostegno e contrarie, localizzatore, limiti, natura | `C-` + hash di testo **e worker** |
| Ipotesi | enunciato, evidenze iniziali, alternative, verifiche proposte, stato | l'id dell'incarico (`H1`), o derivato |
| Lacune | cosa manca, quale ricerca la colmerebbe | `G-` + hash |

La stessa query fatta da entrambi resta **due ricerche**: chi ha cercato è parte di cosa
è successo. Lo stesso paper trovato da entrambi è **una fonte**: l'identità è del
documento.

### La deduplicazione delle fonti, e la regola che non c'è

Due record sono lo stesso documento quando condividono un **DOI normalizzato** (senza
prefisso `https://doi.org/`, minuscolo) oppure un **URL normalizzato** (schema e host
minuscoli, `www.` via, frammento via, parametri di tracciamento via, barra finale via).
Mancando entrambi, la chiave è la corrispondenza **esatta** di titolo, autori e anno
normalizzati.

**Niente si fonde per somiglianza.** Due titoli che si assomigliano sono, di regola, due
articoli diversi, e una fusione sbagliata distrugge il record di chi ha trovato cosa. C'è
un test che lo impone (`test_two_similar_titles_without_an_identifier_stay_two_sources`).

Quando due record si fondono, i livelli di consultazione **restano separati per worker**:
se uno ha letto il testo completo e l'altro ha visto solo il titolo, il record utile è
che entrambe le cose sono vere, attribuite. Un livello unico «migliore» lascerebbe
l'affermazione più forte valere per tutti e due.

### Le tre nature di un'affermazione, e i segnali strutturali

`reported_by_authors` (risultato riferito dagli autori), `worker_interpretation`,
`new_hypothesis`. Quando la natura dichiarata non è riconosciuta, il record la **indebolisce**
a interpretazione: nel dubbio si scende, mai si sale.

Il parser **non sa se un'affermazione è vera**, e non ci prova. Sa riconoscere tre forme
in cui un'attribuzione sbagliata arriva di solito, e le segnala:

- un risultato attribuito agli autori di una fonte che la risposta non ha mai elencato;
- un risultato attribuito a una fonte che il worker dichiara solo `found` o
  `not_accessible` — cioè nessuno ha letto la frase che sta attribuendo;
- un risultato attribuito agli autori senza `locator`, cioè senza dire dove nel documento
  si trovi.

Una segnalazione è **un punto dove guardare, non un verdetto**, e il rapporto lo scrive
per esteso. L'identificazione semantica di un'affermazione falsa non è garantita dal
parser e non lo sarà: per stabilirlo bisogna leggere il paper.

## 5. La scelta delle piste: una regola, non un giudizio

Al massimo **due piste complessive**, scelte da codice deterministico. Nessun modello
decide come si spende il budget residuo — e Claude non è raggiungibile da questo processo
in nessun momento.

1. Da ogni worker si prende la **prima pista ben formata** nell'ordine in cui l'ha
   scritta. Ben formata vuol dire tutte e quattro le parti: *ipotesi → evidenze di
   partenza → spiegazione alternativa → ricerca che sappia distinguerle*. Una pista senza
   spiegazione alternativa è una cosa da credere, non da controllare.
2. Le candidate si ordinano per nome del ruolo, così l'ordine dei contatti non conta.
3. Si deduplicano sull'ipotesi: uguaglianza esatta sempre, somiglianza ≥ 0,85 **solo sopra
   i 60 caratteri**. Sotto quella soglia la somiglianza misura l'ortografia, non il
   significato: «pista di A» e «pista di B» danno 0,90 e sono opposte.
4. Si tronca a due.

**Non c'è ripescaggio.** Se i due propongono la stessa pista, la pista è una sola, e il
fatto che coincidano è un'informazione, non un posto vuoto da riempire con la seconda
scelta di qualcuno.

La selezione viene **congelata** in `leads.json` alla prima esecuzione: una ripresa la
rilegge invece di ricalcolarla, perché un prompt costruito da una selezione nuova potrebbe
avere un hash diverso e rifare una domanda già fatta.

Nella fase 3 **entrambi approfondiscono entrambe le piste** (`lead_assignment: both`). È
l'unica assegnazione che produce due letture confrontabili della stessa pista, e quindi
l'unica in cui un disaccordo di fase 3 può diventare visibile. Le alternative `cross` e
`own` esistono in configurazione e sono documentate come tali.

## 6. Ricerca reale: che cosa gli adattatori permettono davvero

Verificato sulla configurazione che spediamo, non assunto:

| Servizio | Ricerca sul web | Come lo sappiamo |
|---|---|---|
| **DeepSeek** | **disponibile** | il profilo descrive `ricerca_intelligente` con selettore e `aria-pressed`, misurato il 2026-09-13 ([ORCHESTRATORE.md](ORCHESTRATORE.md) §9-quater). L'adattatore lo imposta e ne **rilegge lo stato** prima del primo messaggio; se non ci riesce non invia niente |
| **Kimi** | **non dichiarata** | nessun controllo di ricerca è mai stato osservato su questa interfaccia. Probabilmente ne ha uno; un selettore che nessuno ha visto è un'ipotesi, non una configurazione |

Il che compra meno di quanto sembri, ed è scritto nel rapporto ogni volta: **sapere che
l'interruttore era acceso non è sapere quali query siano state eseguite.** Le ricerche
restano dichiarazioni dei worker.

Quando la ricerca manca su qualche canale, `research.search.on_unavailable` decide:

- **`halt`** — non parte niente. È il valore giusto quando una rassegna scritta a memoria
  sarebbe peggio di una campagna non avviata, ed è il default.
- **`plan_only`** — la campagna gira, e **ciascun worker viene informato del proprio
  canale, non di una media**: chi può cercare cerca, chi non può produce un piano di query
  dichiarate `not_executed` e ha il divieto esplicito di presentare conoscenza pregressa
  come risultato di una ricerca. Il prezzo è che le due metà non sono confrontabili alla
  pari, e il rapporto lo ripete sotto la sezione 6.

## 7. Budget, esiti, arresto

Ogni campagna parte a mano con domanda, perimetro, criteri di pertinenza e budget.

```yaml
budget:
  max_phases: 3                  # fisso: cambiarlo cambia i prompt, e il caricatore lo rifiuta
  max_main_responses: 6          # 3 fasi × 2 worker
  max_repairs_per_response: 1    # più di 1 è rifiutato dal caricatore
  max_leads: 2
  max_total_interactions: 12     # include riparazioni e tentativi
  max_wall_clock_minutes: 90
```

Il conteggio effettivo **include riparazioni e tentativi**, ed è riletto dai passi
registrati invece che da un contatore in memoria, così una campagna interrotta si addebita
gli invii già fatti. Un posto già risposto non costa nulla a rivisitarlo: `_ask` restituisce
ciò che è su disco senza contattare nessuno.

Nessuna creazione ricorsiva di nuovi incarichi: non esiste un percorso di codice che ne
crei uno.

I sei esiti, in ordine di precedenza:

| Esito | Quando |
|---|---|
| `human_stop` | l'operatore ha fermato |
| `service_unavailable` | un servizio non ha risposto, o la ricerca richiesta non è disponibile e la politica è `halt` |
| `limit_reached` | budget di risposte, interazioni o tempo; oppure meno di tre fasi eseguite |
| `unresolved_disagreement` | resta almeno una contraddizione aperta |
| `deepening_needed` | ricerche non eseguite, lacune aperte, piste oltre il tetto, posti senza risposta |
| `plan_completed` | tre fasi eseguite, ricerche delle piste dichiarate eseguite, nessuna lacuna |

**Il programma non chiude mai una contraddizione.** Non è in grado di leggere la fonte che
ne deciderebbe una, e una contraddizione archiviata senza evidenza è peggio di una
contraddizione aperta. Chiuderla è una decisione dell'operatore, con gli artefatti davanti.

Le dichiarazioni di **saturazione** dei worker restano dichiarazioni motivate, attribuite.
Il programma può misurare duplicati e assenza di riferimenti nuovi; non può dedurne che la
letteratura sia esaurita. «Non abbiamo trovato evidenze nelle ricerche registrate» non
diventa «non esistono evidenze», e il rapporto contiene la frase per esteso.

## 8. Il dossier, e perché nessuno lo scrive

Al termine il programma **assembla** — non redige — un dossier deterministico
(`dossier.json`) e un rapporto in otto sezioni:

1. domanda e perimetro; 2. cosa è stato cercato e dove; 3. evidenze principali e
contrarie; 4. ipotesi e come sono cambiate; 5. contraddizioni e lacune; 6. ricerche
proposte e non eseguite; 7. prossimo approfondimento suggerito; 8. motivo dell'arresto e
consumo di interazioni.

Ogni sezione rimanda alla cartella del passo originale. **Le due sintesi restano separate
e verbatim** in appendice: nessuna sintesi consensuale viene inventata, da codice o da un
terzo modello. Una sintesi affidata a un LLM resta un'opzione futura esplicita, con un
budget suo, e non esiste in questa versione.

**L'oracolo numerico non c'entra.** `src/oracle/` ricalcola confronti di loss da CSV; non
è un verificatore della letteratura e non può certificare una fonte né una conclusione
scientifica. C'è un test che verifica che la modalità non lo importi affatto.

## 9. Sicurezza e confini

- **Documenti e risposte sono dati non fidati.** Non possono cambiare budget, permessi,
  instradamento o regole: un campo non previsto viene scartato e lo scarto registrato.
  L'unico campo con cui un worker può chiedere qualcosa è `operator_requests`, che viene
  mostrato nel rapporto e non fa nient'altro.
- La guardia `<<<INIZIO …>>>` sta attorno al **materiale non fidato** — allegati, la
  risposta dell'altro worker, la propria precedente — e **mai** attorno all'incarico
  dell'operatore, che *è* l'istruzione. Questa distinzione era già costata un round
  ([ORCHESTRATORE.md](ORCHESTRATORE.md) §9-quinquies) e c'è un test che la difende.
- Nessuna esecuzione di codice trovato nei paper o prodotto dai worker; nessuno
  scaricamento massivo; nessuna API a consumo.
- Login, CAPTCHA e blocchi del servizio richiedono una pausa e un intervento umano.
  Nessun aggiramento: una pagina che chiede accesso ferma la consultazione di quella
  fonte, che viene registrata come non accessibile.
- Durante un'esecuzione **nessuna chiamata a Claude, GPT, Gemini o Grok**: il percorso
  `scientific_research` non contiene ruoli che li mappino, e i test sulla configurazione
  spedita lo verificano.

## 10. Che cosa è stato provato, e che cosa no

La prova a secco del 2026-09-14
(`reports/orchestrator/prova-a-secco-ricerca-2026-09-14/`) ha fatto girare una campagna
completa con risposte scritte a mano, costruite per mettere alla prova otto situazioni:
lo stesso paper trovato da entrambi, una fonte non accessibile, una query proposta e non
eseguita, una contraddizione che deve restare aperta, un'ipotesi nuova presentata come
risultato di un paper, una richiesta di superare il budget, una fase senza evidenze nuove,
e un errore di formato con ripresa senza doppi invii.

**Misurato:** esito `unresolved_disagreement`; 6 risposte principali, 1 riparazione, 7
invii totali e **0 doppi invii** su una seconda esecuzione dello stesso run; 4 documenti
distinti dai 6 record di fonte presenti nelle risposte; 13 ricerche registrate di cui 5
dichiarate eseguite; 3 contraddizioni tutte aperte; 2 piste selezionate su 5 proposte.

La prova ha trovato **due difetti**, entrambi corretti:

1. una risposta riparata non veniva riconosciuta alla ripresa — il motore trovava il primo
   tentativo illeggibile, smetteva di cercare, e proseguiva come se quel modello non avesse
   mai risposto. **Riguardava anche il ciclo di debug**;
2. due piste con ipotesi corte si fondevano per somiglianza testuale, dimezzando in
   silenzio la fase 3.

**Non dimostrato:** che DeepSeek o Kimi rispondano a un prompt di ricerca; che
l'interruttore di ricerca si accenda su un'interfaccia reale (l'adattatore scriptato non
impone nessuna modalità); che le distinzioni di provenienza reggano su risposte vere.
Reggono su risposte costruite apposta, il che è meno.

## 11. Come si avvia una campagna reale

Il primo incarico scientifico è pronto e **non è stato avviato**:
`configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml`. Chiede se esista un
Perturb-seq CRISPRi pubblico in linea T matura o epiteliale squamosa con la matrice RNA
ottenibile — l'incertezza numero 7 di [PROGETTO.md](PROGETTO.md) §4.

Prima di avviarlo, nell'ordine:

```bash
.\scripts\orch.cmd doctor
.\scripts\orch.cmd brief configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml
```

`brief` stampa perimetro, criteri, ipotesi, budget e — riga per riga — **che cosa ogni
canale può davvero fare**. Va letto: è la schermata su cui si decide se far partire la
campagna.

Poi, e solo dopo che l'hai letto:

```bash
.\scripts\orch.cmd start --brief configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml
```

Da un secondo terminale `.\scripts\orch.cmd watch` mostra fase, worker e decisione mentre
succede; `pause` e `stop` intervengono fra un passo e l'altro. Alla fine il rapporto e il
dossier stanno nella cartella del run.

Restano prerequisiti quelli del ciclo a due
([ORCHESTRATORE.md](ORCHESTRATORE.md) §10): accesso fatto a mano su entrambi i servizi e
profili verificati. Lo sono dal 13 settembre.

Per rendere **simmetrica** la campagna serve osservare il controllo di ricerca di Kimi:

```bash
.\scripts\orch.cmd probe kimi
```

poi descrivere la modalità in `configs/orchestrator/services/kimi.yaml` e dichiararla con
un blocco `search:` in `configs/orchestrator/orchestrator.yaml`. Finché non succede, la
campagna gira con DeepSeek che cerca e Kimi che pianifica, e il rapporto lo dice.

## 12. Limiti noti

- **Nessuna sessione di riserva** in questa modalità: consumerebbe una delle sei risposte,
  e una seconda sessione dello stesso modello che «approfondisce» una pista porterebbe gli
  stessi punti ciechi in una fase in cui contano le fonti. Se un worker non consegna, la
  fase prosegue con una voce sola e il rapporto dice quale fase era dimezzata.
- **Tre fasi fisse.** `max_phases` diverso da 3 è rifiutato dal caricatore, perché
  cambiarlo cambia i prompt e non solo un contatore.
- **Il parser non giudica la verità.** Segnala forme sospette; leggere il paper resta da
  fare.
- **La contraddizione derivata è strutturale**: due worker che puntano la stessa fonte in
  direzioni opposte. Due worker che si contraddicono senza citare la stessa fonte vengono
  colti solo se uno dei due lo dichiara.
- **Il canale non espone le query.** È il limite che tutto il resto del documento gira
  attorno, e non si chiude senza un artefatto del browser che oggi non esiste.
