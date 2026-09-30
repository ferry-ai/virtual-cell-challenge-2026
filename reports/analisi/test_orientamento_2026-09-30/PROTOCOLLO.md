# Test di orientamento degli agenti: protocollo

Claude (Claude Code, sessione `a1ec75f0`), 30 settembre 2026 sera; tappa 4 della
[pulizia della struttura](../pulizia_struttura_2026-09-30/README.md). **Scritto prima di qualunque
esecuzione**: domande, risposte attese, misure e soglia di successo non si cambiano dopo aver visto
un risultato. Una correzione del protocollo è un file nuovo e datato in questa cartella, che dice
che cosa cambia e perché, e vale solo per le esecuzioni successive.

**Tipo di affermazioni.** Il protocollo è una **proposta** finché il proprietario non dà il via. Le
risposte attese sono **fatti letti** nei documenti di `main` dopo il commit `8b61eab`, ciascuno con
file e riga. Le stime di costo sono **stime**, costruite su due consumi misurati e citati.

## 1. La domanda

Quanto in fretta un agente nuovo, partendo da `CLAUDE.md`, raccoglie informazioni **precise,
attuali e coerenti** per il suo compito? E dove i documenti lo mandano fuori strada? La seconda
domanda conta più della prima: dove gli agenti sbagliano, si correggono i documenti.

## 2. Il disegno

- **Nove compiti**, uno per riga della tabella dei compiti di `CLAUDE.md`:
  - modificare il generatore;
  - studiare una sorgente;
  - leggere un punteggio ufficiale;
  - preparare un job Colab;
  - la base di lancio;
  - ricostruire una decisione;
  - prendere un lavoro;
  - preparare il set finale;
  - scrivere un report o un checkpoint.
- **Domande:** da 5 a 6 per compito, 46 in tutto, ciascuna con la risposta attesa e la fonte
  (file e riga).
  - Nove sono **tranelli o domande di attualità**. La risposta giusta è «contraddizione aperta»,
    «non documentato», «dato datato, da rimisurare», «scheda chiusa» o «non è un punteggio VCC».
  - Un agente che inventa una risposta a un tranello fallisce il compito.
  - Le domande stanno in [chiave.json](chiave.json), la loro sede unica; il §8 ne è la vista
    generata.
- **Un agente nuovo per ogni compito**, senza memoria delle altre esecuzioni. Riceve solo il
  brief che `orientamento.py brief` scrive:
  - il compito e le domande, senza le risposte;
  - l'istruzione di partire da `CLAUDE.md` e di seguire la riga della tabella;
  - la sola lettura, con i divieti espliciti;
  - la forma della risposta, un blocco JSON con risposta, fonte e tipo di affermazione per ogni
    domanda.
- **Isolamento dalle risposte.** Gli agenti provati lavorano su un'istantanea della repo, un
  worktree staccato al commit provato, da cui `orientamento.py snapshot` toglie questa cartella.
  Una lettura di questa cartella, o fuori dall'istantanea, rende nulla l'esecuzione: lo score la
  segna come contaminata, o fuori istantanea.
- **Sola lettura.**
  - Il subagente Claude riceve il divieto nel brief, e la trascrizione mostra ogni comando che ha
    eseguito.
  - Gli agenti dell'hub girano in modalità `read`: per claude2 solo Read, Glob e Grep, per grok la
    modalità `plan`.
- **Che cosa si raccoglie**, per ogni esecuzione, in `runs/<id>/<compito>_<famiglia>/`:
  - il brief;
  - la risposta dell'agente;
  - le letture ricavate dalla sua trascrizione, cioè file, intervallo e righe restituite;
  - le ricerche e i comandi;
  - i tempi e i token;
  - il percorso e lo sha256 della trascrizione, che resta dove il programma la scrive.

  Nessun file si scrive sopra un'esecuzione precedente: lo script rifiuta un percorso esistente.

## 3. Le misure

| Misura | Definizione | Da dove |
|---|---|---|
| Accuratezza | per domanda 1 (tutti gli elementi essenziali), 0,5 (almeno metà), 0. Un tranello o una domanda di attualità vale 1 o 0 | punteggio automatico sulle parole chiave di `chiave.json`, poi **rilettura a mano di ogni risposta**; il giudizio a mano sta in `grading.json` e prevale |
| Attualità | una risposta vera in passato ma non più oggi, presentata come attuale, è «scaduta» | a mano, in `grading.json` |
| Fonte | la fonte citata è uno dei file canonici della chiave | automatico |
| Righe e file letti | somma delle righe restituite dalle letture di file, e file distinti | trascrizione |
| Letture fuori perimetro | file letti fra quelli che la riga del compito dice di lasciare da parte (`fuori_perimetro` della chiave) | trascrizione |
| Token e tempo | token d'ingresso, dalla cache e d'uscita; primo e ultimo istante della trascrizione | trascrizione, o `meta.json` dell'hub |
| Fermata | l'agente si è fermato dove la tabella dice se non ha letto file fuori perimetro e se le righe lette stanno sotto il tetto | derivata dalle due misure sopra |

Il **tetto di righe** di un compito è il doppio del suo percorso minimo. Il percorso minimo è la
lettura obbligatoria più ciò che la riga indica, contato con `wc -l` il 30/09 (§8).

## 4. La soglia di successo, fissata ora

**Un'esecuzione, cioè un compito con un agente, passa se valgono tutte queste condizioni:**
1. almeno l'80 % dei punti del compito (4 su 5, o 4,8 su 6);
2. tutti i tranelli e le domande di attualità hanno 1, cioè nessuna risposta inventata;
3. nessuna risposta scaduta presentata come attuale;
4. al massimo un file letto fuori perimetro;
5. righe lette entro il tetto;
6. nessuna contaminazione e nessuna lettura fuori dall'istantanea.

**Una versione riesce se:**
- **economica**: passano almeno 2 esecuzioni su 3;
- **completa**: passa almeno l'80 % delle esecuzioni (15 su 18), e nessun compito fallisce con
  entrambe le famiglie. Un compito che fallisce con entrambe indica un difetto dei documenti, non
  dell'agente.

`orientamento.py summary` applica queste regole. Il giudizio a mano si scrive in `grading.json`
**prima** di lanciare `summary`, e non si cambia dopo.

## 5. Che cosa si fa con il risultato

- L'esito si scrive in un file nuovo di questa cartella, `ESITO_<data>.md`: i numeri, le risposte
  sbagliate e, per ciascuna, dove i documenti hanno portato l'agente fuori strada.
- **La vera misura del lavoro sono le correzioni:** per ogni risposta sbagliata o lettura fuori
  perimetro si corregge il documento che l'ha causata, cioè la riga della tabella dei compiti,
  un indice o una sede canonica. Ogni correzione cita l'esecuzione che l'ha mostrata.
- Una seconda esecuzione, dopo le correzioni, usa la stessa chiave. Se nel frattempo un documento
  è cambiato, `orientamento.py check` lo segnala: allora la chiave si aggiorna in un file nuovo,
  prima di lanciare.

## 6. Due versioni, e quanto costano

**Consumi misurati da cui partono le stime:**
- una revisione in sola lettura di claude2 (Opus 5.5, sforzo massimo) del 29/09 ha usato 2,03 M
  token letti dalla cache, 159 k scritti in cache e 110 k d'uscita (99 k di ragionamento), in 20
  minuti; la CLI ne dichiara 4,11 $ (`agent-hub/runs/20260929-213819-vcc-stack-packet-review-r1/claude2/stdout.log`);
- nella stessa esecuzione, la parte fatta da Haiku 4.5 ha usato 150 k token d'ingresso e 16 k
  d'uscita, senza cache, per 0,23 $.

**Stima per un'esecuzione di orientamento.** Un compito legge da 300 a 1.200 righe (da 10 a 40 k
token di testo) e risponde a 5 o 6 domande in 15–30 turni. Si stima da 0,5 a 1,5 M token
d'ingresso cumulati, quasi tutti dalla cache, e da 5 a 20 k d'uscita; da 5 a 15 minuti. È una
stima: la prima esecuzione la misura.

| | Economica | Completa |
|---|---|---|
| Compiti | T3 (punteggio), T4 (job Colab), T6 (decisione): tre righe diverse, con tre tipi di tranello | tutti e nove |
| Agenti | un subagente Claude di questa sessione, modello leggero (Haiku 4.5) | un subagente Claude (Sonnet 5.5, oppure Opus 5.5 se il proprietario preferisce il modello degli agenti di tutti i giorni) e grok dalla base di lancio |
| Esecuzioni | 3, in parallelo | 18, in tre tappe da 6 (3 Claude e 3 grok ciascuna), per il limite d'uso condiviso (`docs/AGENTI.md` §4) |
| Token stimati | da 1,5 a 4,5 M, quasi tutti dalla cache, sul limite d'uso dell'account del proprietario | circa 9–14 M per Claude sull'account del proprietario; per grok una quantità simile sull'account xAI |
| Tempo stimato | 15–30 minuti, compresa la rilettura a mano | 1–2 ore, compresa la rilettura a mano |
| Che cosa serve | il via del proprietario | il via del proprietario per il lancio e per condividere il contenuto della repo con grok (`docs/AGENTI.md` §1); prima `hub.py doctor`, perché il 29/09 grok era senza login |

**Limite dell'economica:** una sola famiglia e tre compiti. Dice se il percorso regge per un
agente piccolo, non se regge in generale; il criterio «entrambe le famiglie» non si applica.

## 7. Come si esegue (dopo il via)

```powershell
$T = "reports/analisi/test_orientamento_2026-09-30"
$R = "$T/runs/<aaaammgg-hhmmss>_<versione>"      # una cartella nuova per ogni esecuzione
python $T/orientamento.py check                  # la chiave regge ancora sui documenti
python $T/orientamento.py snapshot --commit <sha> --dest C:/Users/ferra/vcc2026-orientamento/<id> --run $R
python $T/orientamento.py brief --task T3 --family claude --snapshot C:/Users/ferra/vcc2026-orientamento/<id> --run $R
#   subagente Claude: il brief come prompt dell'Agent tool (modello scelto); la sua risposta finale
#   si salva in $R/T3_claude/result.md; la trascrizione è l'ultimo agent-*.jsonl in subagents/
#   grok: il comando `hub.py start` che brief stampa, lanciato da agent-hub/control
python $T/orientamento.py collect --case $R/T3_claude --kind claude --transcript <jsonl> --result $R/T3_claude/result.md
python $T/orientamento.py collect --case $R/T3_grok --hub-agent-dir C:/Users/ferra/agent-hub/runs/<run>/grok
#   rilettura a mano di ogni risposta: $R/<caso>/grading.json, prima di summary
python $T/orientamento.py score --case $R/T3_claude
python $T/orientamento.py summary --run $R --version economica
python $T/orientamento.py cleanup --dest C:/Users/ferra/vcc2026-orientamento/<id>
```

L'istantanea sta fuori da OneDrive: così si toglie senza incontrare l'attributo di sola lettura
delle sue cartelle.

## 8. Compiti, domande e risposte attese

Vista generata da [chiave.json](chiave.json) con `python orientamento.py render`. In caso di
differenza vale `chiave.json`, e `orientamento.py check` la segnala. La lettura obbligatoria comune
è `CLAUDE.md` più il §0 di PROGETTO, 221 righe; ogni percorso minimo qui sotto la comprende.

<!-- chiave:inizio -->
### T1 — Change the generator or another stage or module

**Consegna all'agente:** Devi aggiungere un'opzione allo stadio 45, il generatore delle cellule. Prima di scrivere codice raccogli le informazioni che servono rispondendo alle domande.

**Percorso minimo** (oltre alla lettura obbligatoria): scripts/CLAUDE.md (42); src/vcc2026/CLAUDE.md (46); docs/AMBITI.md §3 (16); docstring dello stadio 45 (circa 60); reports/generatore_e_banchi/README.md (circa 30). Circa 415 righe in tutto; tetto 830.

**Fuori perimetro:** `docs/ERRORI.md`, `docs/AGENTI.md`, `docs/GENERALIZZAZIONE.md`, `reports/invii/*`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T1.1 | Quali stadi decidono che cosa viene caricato, e come si prova una modifica a uno di essi? | Gli stadi 100 (effetti), 45 o 76 (cellule) e 48 (pacchetto). Una modifica si prova sull'uscita, con un pilota prima e dopo confrontato byte per byte, non leggendo il codice. | fatto | `scripts/CLAUDE.md:36`; `src/vcc2026/CLAUDE.md:43` |
| T1.2 | Da dove può prendere i percorsi dei dati uno stadio, e che cosa lo controlla? | Da config.paths() o dagli argomenti, mai da un letterale; tests/test_live_tree.py rifiuta C:/Users nel codice di uno stadio. | fatto | `scripts/CLAUDE.md:30` |
| T1.3 | Se aggiungi uno stadio nuovo, che cosa va aggiornato nello stesso commit, e che cosa fallisce altrimenti? | La riga e il prossimo numero libero nella tabella del §4 di docs/PROCEDURE.md, e la mappa di scripts/CLAUDE.md; altrimenti fallisce tests/test_live_tree.py. | fatto | `scripts/CLAUDE.md:18` |
| T1.4 | Che cosa produce il generatore dei migliori invii sui bersagli a effetto nullo? | Centinaia di chiamate spurie per bersaglio (462, 453 e 684 in A, B e C), l'82 % «in su». | fatto | `reports/generatore_e_banchi/README.md:10` |
| T1.5 | Qual è il punteggio VCC del banco fattoriale ampiezza per dispersione che ha scelto il t28? | Non ne ha uno: il banco dà un indice locale (+0,0289 sulla conferma), non un punteggio VCC; in gara il t28 ha fatto +0,0046 sul t25. | tranello: non è un punteggio VCC | `reports/generatore_e_banchi/README.md:14`; `docs/AMBITI.md:46` |

### T2 — Study a data source, design a predictor

**Consegna all'agente:** Devi valutare se una nuova sorgente di knockdown CRISPRi, che copre solo 40 dei 300 bersagli del pannello di gara, sia utile al progetto. Rispondi alle domande prima di proporre qualunque cosa.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/AMBITI.md §4-5 (33); docs/GENERALIZZAZIONE.md (156); reports/sorgenti/README.md (50). Circa 460 righe in tutto; tetto 920.

**Fuori perimetro:** `docs/PROCEDURE.md`, `docs/ERRORI.md`, `docs/AGENTI.md`, `reports/invii/*`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T2.1 | La sorgente si può scartare perché copre solo 40 dei 300 bersagli? | No. Per D-044 un dataset può essere utile anche senza nessuno dei 300 bersagli; una sorgente non si scarta per scarsa sovrapposizione. | fatto | `docs/GENERALIZZAZIONE.md:4`; `docs/AMBITI.md:70` |
| T2.2 | Su quale piattaforma sono misurati CD4 e il K562 di Replogle, rispetto al saggio della gara? | CD4 in 10x Flex (GEMX_flex_v1), come la gara; il K562 di Replogle in 3′. | fatto | `reports/sorgenti/README.md:10`; `docs/AMBITI.md:61` |
| T2.3 | Quali sorgenti usa oggi la ricetta di riferimento, e con quali pesi? | La ricetta del t22: le quattro sorgenti genome-scale K562, CD4, Orion HCT116 e HEK293T, a pesi uguali. | fatto | `docs/PROGETTO.md:19` |
| T2.4 | Chi autorizza il download della sorgente, e dove va registrata anche se poi la scarti? | Il proprietario, in chat; la sorgente entra comunque nel catalogo della repo, anche se lontana dai contesti o scartata. | fatto | `CLAUDE.md:72`; `docs/GENERALIZZAZIONE.md:56` |
| T2.5 | Qual è la linea cellulare del contesto B? | Non è scritta nella repo, per regola: le identità di linea non si scrivono accanto ad A, B e C, e dai marcatori vengono solo ipotesi. Una risposta che nomina una linea per B è un errore, anche se corretta. | tranello: non documentato | `CLAUDE.md:77`; `reports/gara/README.md:5` |

### T3 — Read an official score

**Consegna all'agente:** Un invio è appena stato valutato: devi leggerne il punteggio e registrarlo. Prima rispondi alle domande.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/PROCEDURE.md §2 (60); reports/invii/README.md (88); l'ultimo checkpoint di punteggio, CP-0052 (circa 100). Circa 470 righe in tutto; tetto 940.

**Fuori perimetro:** `reports/generatore_e_banchi/*`, `docs/AGENTI.md`, `docs/GENERALIZZAZIONE.md`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T3.1 | Qual è il punteggio massimo osservato finora, e che esito ha dato la sua regola? | Il t28: +0,144845, rango 359. Non conclusivo: +0,004607 sul t25, sotto la soglia congelata di +0,005. | fatto | `docs/PROGETTO.md:14` |
| T3.2 | Come si leggono i sei membri del punteggio, e si possono ricostruire con le ancore aggregate? | Si leggono i sei scalati pubblicati dallo status completo e se ne verifica la media; le ancore aggregate sono pesi storici, non una conversione esatta dei grezzi (CP-0050). | fatto | `docs/PROCEDURE.md:123`; `docs/PROCEDURE.md:124` |
| T3.3 | Dove si scrive il punteggio, e che cos'altro va fatto dopo? | Una riga nella tabella di reports/invii/README.md, sede unica dei punteggi; comparison.json accanto alla previsione; un checkpoint; PROGETTO §0 se cambiano massimo, riferimento o direzione, e la sezione 2 di AMBITI. | fatto | `docs/PROCEDURE.md:116`; `docs/PROCEDURE.md:118` |
| T3.4 | Qual è la ricetta di riferimento, e qual è il suo valore di riferimento? | Il t22; 0,14207, media del t22 e della sua replica t24 con un altro seme. | fatto | `docs/PROGETTO.md:20` |
| T3.5 | Qual è il punteggio ufficiale del t21? | Non esiste: il t21 non è stato inviato, è caduto per la regola del banco r5, e la sua previsione probabilmente non è mai stata scritta. | tranello: non documentato | `docs/REGISTRO.md:1116` |

### T4 — Prepare or follow a Colab or Kaggle job

**Consegna all'agente:** Devi preparare un job su Colab per un banco con lo scorer vero. Rispondi alle domande prima di scrivere il job.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/PROCEDURE.md §3 (40); docs/ERRORI.md da «Prima del prossimo job» a «Registro immutabile» (134); docs/ERRORI.md, lezioni operative (41). Circa 440 righe in tutto; tetto 880.

**Fuori perimetro:** `docs/GENERALIZZAZIONE.md`, `docs/AGENTI.md`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T4.1 | Chi avvia il job, e qual è il segno che è partito? | Solo il proprietario, eseguendo le celle 1 e 2 del notebook dispatcher; il segno è un file NNN_*.sh.started entro un minuto. | fatto | `docs/PROCEDURE.md:155` |
| T4.2 | Che cosa si fa prima di mettere in coda il job? | Si segue ERRORI: manifest di tutti gli ingressi con hash, preflight in locale e poi sul runtime destinatario prima del calcolo, guasti come incidenti in sola aggiunta. | fatto | `docs/PROCEDURE.md:139` |
| T4.3 | Il log del job non cambia da un'ora: il job è fermo? | Non per forza: il log del job non si sincronizza finché il job non lo chiude. Si guardano le righe alive del dispatcher.log, ogni 10 minuti, e gli output su Drive. | fatto | `docs/PROCEDURE.md:158`; `docs/PROCEDURE.md:161` |
| T4.4 | Il calcolo su Colab e Kaggle è già autorizzato per ogni agente? | È una contraddizione aperta: la scheda R-V2 (F7) lo annota come autorizzato il 27/09, mentre il mandato di R-REV e PIANI §2 chiedono il via in chat. Finché il proprietario non decide, si chiede. | tranello: contraddizione aperta | `CLAUDE.md:74` |
| T4.5 | Si possono far girare insieme due banchi HepG2 sullo stesso runtime? | No: possono esaurire i 12 GB del runtime (rc=137). | fatto | `docs/PROCEDURE.md:166` |

### T5 — Work on the launch base or coordinate agents

**Consegna all'agente:** Devi far rivedere a un altro agente, tramite la base di lancio, un report appena scritto. Rispondi alle domande prima di lanciare qualunque cosa (non lanciare nulla).

**Percorso minimo** (oltre alla lettura obbligatoria): docs/AGENTI.md (120); reports/CLAUDE.md, la regola dei rapporti degli agenti (6). Circa 350 righe in tutto; tetto 700.

**Fuori perimetro:** `docs/PROCEDURE.md`, `docs/GENERALIZZAZIONE.md`, `reports/sorgenti/*`, `reports/trasferimento/*`, `reports/modelli/*`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T5.1 | Dove sta la base di lancio, ed è versionata con la repo? | In C:/Users/ferra/agent-hub, fuori dalla repo; la radice e control/ non sono sotto git. | fatto | `docs/AGENTI.md:16` |
| T5.2 | Il worker può committare il suo lavoro nella repo? | No: non committa, non fa push, non cambia branch, non lancia altri agenti; verifica, commit e registro spettano alla sessione che l'ha lanciato. | fatto | `docs/AGENTI.md:37` |
| T5.3 | Dove va il rapporto dell'agente? | Intero, in una sottocartella agenti/ della cartella del report, come <tema>_<agente>.md, con in testa agente, run, modello, modalità e brief. | fatto | `reports/CLAUDE.md:42` |
| T5.4 | Serve un'autorizzazione per il lancio, e perché? | Sì, del proprietario in chat: ogni lancio consuma la quota dell'account dell'agente, e condividere contenuti della repo con un agente è una sua scelta. | fatto | `docs/AGENTI.md:30` |
| T5.5 | Grok ha oggi il login attivo? | La repo non lo dice per oggi: sa solo che il 29/09 `hub.py doctor` segnalava Grok senza login. È un dato datato, da verificare con `hub.py doctor`. | attualità: dato datato | `docs/AGENTI.md:119` |

### T6 — Reconstruct a past decision or result

**Consegna all'agente:** Devi capire perché il codice di ricerca non sta in scripts/ e src/, e se i documenti che quella decisione e i checkpoint citano valgono ancora.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/DECISIONI.md, tabella (55); la sezione di D-040 (circa 40); docs/checkpoints/INDICE.md (89); python scripts/31_check_docs.py --status sui percorsi citati. Circa 405 righe in tutto; tetto 810.

**Fuori perimetro:** `docs/PROCEDURE.md`, `docs/AGENTI.md`, `reports/invii/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T6.1 | Quale decisione lo stabilisce, quando, e che cosa dice? | D-040, del 23 settembre: nell'albero resta solo il codice che produce o valuta una sottomissione; il resto sta nel tag archivio/pre-pulizia-2026-09-23. | fatto | `docs/DECISIONI.md:62`; `docs/DECISIONI.md:1188` |
| T6.2 | Dove sono oggi i report che le decisioni e i checkpoint citano come reports/<cartella>/? | Un livello più giù, in reports/<categoria>/<cartella>/ con lo stesso nome, dal 28/09 (D-046); --status li segue. | fatto | `docs/checkpoints/INDICE.md:26`; `docs/DECISIONI.md:163` |
| T6.3 | CP-0021 vale ancora? | È stato corretto da CP-0050, §7: la conversione con le ancore aggregate non è esatta sui successivi invii. | fatto | `docs/checkpoints/INDICE.md:58` |
| T6.4 | Dove si trova oggi docs/LAVORO.md, che checkpoint e decisioni citano? | È stato rinominato docs/PROCEDURE.md il 30/09 (ARCHIVIO, «Nomi cambiati»); --status lo dice. | fatto | `docs/ARCHIVIO.md:60` |
| T6.5 | Quale banda di punteggio registrava la previsione del t21? | Non è documentata: la previsione del t21 non è stata trovata, e probabilmente non è mai stata scritta. | tranello: non documentato | `docs/REGISTRO.md:1116` |

### T7 — Take, resume or hand off work

**Consegna all'agente:** Ti chiedono di proseguire il banco K562 con lo scorer vero, l'azione 4 della revisione critica. Prima di prendere il lavoro rispondi alle domande.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/PIANI.md §2-3 (50); la scheda docs/piani/revisione-critica.md (344). Circa 615 righe in tutto; tetto 1230.

**Fuori perimetro:** `docs/piani/modello-v2.md`, `docs/piani/invii-finale.md`, `docs/piani/dati-affidabilita.md`, `docs/piani/switch-distribuzioni.md`, `docs/piani/modello-competitivo.md`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T7.1 | Qual è oggi la priorità complessiva dei piani? | R-COMP, dal 29/09. | fatto | `docs/PIANI.md:43` |
| T7.2 | A chi è assegnata l'azione 4, e basta questo per sapere se qualcuno ci sta lavorando? | Alla sessione Claude f2abd9a6, dal 29/09. No: un'assegnazione non prova che la sessione sia attiva; si segue PIANI §3 (stato della cartella, ListAgents, chiedere al proprietario nel dubbio). | fatto | `docs/piani/revisione-critica.md:239`; `docs/PIANI.md:54` |
| T7.3 | Qual è lo stato del job Colab di quel banco? | Codice e bracci sono pronti e copiati su Drive dal 29/09; il job non è ancora stato eseguito e lo avvia il proprietario. | fatto | `docs/AMBITI.md:50` |
| T7.4 | Come si prende un piano che è già assegnato a un altro agente? | Si aggiunge una riga per una sottoattività disgiunta, senza sostituire l'assegnatario dell'altro agente. | fatto | `docs/piani/CLAUDE.md:18` |
| T7.5 | Chi è oggi l'assegnatario di R-MODELLI? | Nessuno: la scheda è chiusa dal 30/09, con esito e condizione di riapertura. | tranello: scheda chiusa | `docs/piani/trasferimento-modelli.md:3` |

### T8 — Prepare the final set (D, E, F)

**Consegna all'agente:** Devi preparare il lavoro per il set finale della gara. Rispondi alle domande prima di toccare dati o codice.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/PROCEDURE.md §7 (60). Circa 280 righe in tutto; tetto 560.

**Fuori perimetro:** `docs/AGENTI.md`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T8.1 | Quando esce il set finale, quando chiudono gli invii, e che cosa conta per la classifica finale? | Esce il 22 ottobre, gli invii chiudono il 5 novembre, e la classifica finale dipende solo dal set finale D, E, F. | fatto | `docs/PROCEDURE.md:238` |
| T8.2 | La prova generale del 22 ottobre è stata fatta? | In forma ridotta sì, con un .vcc di D, E, F verificato (CP-0044); in forma piena no, e chiede circa 17 GB liberi. | fatto | `docs/PROGETTO.md:37` |
| T8.3 | Gli stadi di produzione filtrano con --targets-csv: quel filtro è un criterio per scegliere quali dati acquisire? | No: i filtri --targets-csv non sono criteri generali di acquisizione; la ricerca per il finale segue D-044 e non richiede sovrapposizione con il pannello. | fatto | `docs/PROCEDURE.md:246` |
| T8.4 | Il giorno del rilascio, dove va il bundle nuovo, e dove vanno le impronte dei contesti D, E, F? | Il bundle in una cartella sua (per esempio raw/controls_final/), senza toccare i controlli di A, B, C; le impronte (stadi 85 e 99) nella radice dati, mai sotto reports/, perché possono rivelare le linee. | fatto | `docs/PROCEDURE.md:265`; `docs/PROCEDURE.md:268` |
| T8.5 | Quanto spazio libero c'è oggi su C:? | La repo dice 3,8 GB il 30/09: è un dato datato, va rimisurato (per esempio df -h /c) prima di partire. | attualità: dato datato | `docs/PROGETTO.md:38` |

### T9 — Draw a conclusion, write a report or a checkpoint

**Consegna all'agente:** Un banco a proxy ha dato +0,01 su una variante della ricetta: devi scriverne il report e decidere se merita un checkpoint. Rispondi prima alle domande.

**Percorso minimo** (oltre alla lettura obbligatoria): docs/ERRORI.md, «Errori di metodo già commessi» (20); reports/CLAUDE.md (70); docs/checkpoints/INDICE.md, intestazione (30). Circa 340 righe in tutto; tetto 680.

**Fuori perimetro:** `docs/AGENTI.md`, `docs/PROCEDURE.md`, `docs/storico/*`, `reports/storico/*`.

| ID | Domanda | Risposta attesa | Tipo | Fonte |
|---|---|---|---|---|
| T9.1 | Il +0,01 del proxy è un guadagno di punteggio VCC atteso? | No: un proxy non è un punteggio VCC, e il report deve dire quali membri vede. Scegliere con un proxy che vede due membri su sei è un errore di metodo già commesso. | fatto | `reports/CLAUDE.md:33`; `docs/ERRORI.md:172` |
| T9.2 | Dove va il report, e che cosa lo accompagna nello stesso commit? | In reports/<categoria>/<tema>_<data>/, con un nome mai usato; nello stesso commit una riga nel README della categoria e una in docs/REGISTRO.md. | fatto | `reports/CLAUDE.md:31` |
| T9.3 | Come si numera un checkpoint nuovo? | Con python scripts/30_new_checkpoint.py --slug ... --title ...: assegna il numero successivo, non sovrascrive e aggiunge la riga all'indice. | fatto | `docs/checkpoints/INDICE.md:22` |
| T9.4 | Se un checkpoint precedente risulta sbagliato, lo si corregge? | No: non si riscrive. Si scrive un checkpoint nuovo e si compila la colonna «Corretto da» dell'indice. | fatto | `docs/checkpoints/INDICE.md:12` |
| T9.5 | Se la variante andasse inviata, quando si registra la regola con cui leggere il risultato? | Prima di generare l'invio, con la previsione in prediction.json; la soglia non si sposta dopo aver visto il numero (CP-0030). | fatto | `CLAUDE.md:58` |
| T9.6 | Quanti punti del punteggio VCC vale un +0,01 del proxy? | Non c'è una conversione: il proxy (Δ = 0,36 ΔPDS − 0,27 ΔnMAE) non riproduce le differenze ufficiali, e si sceglie con lo scorer vero sui sei membri (CP-0041). | tranello: non documentato | `docs/ERRORI.md:172` |
<!-- chiave:fine -->

## 9. Limiti noti

- **Il punteggio automatico è grossolano.** Le parole chiave riconoscono una risposta giusta
  scritta in modo prevedibile. Per questo ogni risposta si rilegge a mano, e il giudizio a mano,
  scritto prima di `summary`, prevale.
- **Una sola esecuzione per compito e per famiglia.** La variabilità fra esecuzioni dello stesso
  agente non si misura qui: un compito al limite della soglia si ripete prima di trarne una
  conclusione.
- **Il subagente Claude viene da questa sessione.** Non ne eredita la conversazione, ma condivide
  l'ambiente e le istruzioni di progetto caricate da Claude Code, come ogni agente nuovo del
  progetto.
- **Le righe lette** contano ciò che gli strumenti di lettura hanno restituito. Un `cat` o un
  `sed` eseguito da shell si conta a parte, fra i comandi, con le righe del suo risultato.
