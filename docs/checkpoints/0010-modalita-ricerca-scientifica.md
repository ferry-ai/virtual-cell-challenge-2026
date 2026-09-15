# CP-0010 — Modalita di ricerca scientifica a tre fasi nell'orchestratore

- **Data:** 2026-09-14
- **Tipo:** osservazione
- **Redatto da:** agente
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

L'orchestratore sa far discutere due modelli fino a una proposta stabile. Serviva una
cosa diversa: fargli **cercare in letteratura** e produrre non un accordo ma un resoconto
tracciabile — che cosa è stato cercato, che cosa trovato, che cosa sostiene o contraddice
le ipotesi, che cosa resta da verificare. La domanda operativa era se si potesse
costruirla **senza** che il programma promuovesse in silenzio ciò che un modello dichiara
a ciò che è stato osservato.

## 2. Cosa è stato fatto

Aggiunta una modalità `scientific_research` in `src/orchestrator/research/`, scelta
dall'incarico con `mode:`, che riusa il motore esistente (passi, ripresa, riparazione
unica, quarantena del codice, pausa e arresto) e cambia la forma della campagna: tre fasi
— ricerca indipendente, confronto e piste, ricerca mirata e sintesi.

Prova a secco completa, senza contattare nessun servizio, con sei risposte scritte a mano
in `configs/orchestrator/rehearsal/ricerca-collaudo/`, costruite per mettere alla prova
otto situazioni che devono restare distinguibili:

```bash
set VCC2026_ORCH_ROOT=%TEMP%\orch-ricerca-prova
.\scripts\orch.cmd --config configs/orchestrator/offline-ricerca.yaml ^
    start --brief configs/orchestrator/briefs/ricerca-collaudo.yaml
```

Poi lo stesso run ripreso una seconda volta, per contare gli invii.

```bash
.\scripts\py.cmd -m unittest tests.test_orchestrator tests.test_orchestrator_research tests.test_oracle_pairwise_loss
```

## 3. Cosa si è osservato

Tutti i numeri di questa sezione si rileggono da
`reports/orchestrator/prova-a-secco-ricerca-2026-09-14/dossier.json` e da `events.jsonl`
nella stessa cartella.

| Osservazione | Valore | Evidenza |
|---|---|---|
| Esito della campagna di prova | `unresolved_disagreement` | `dossier.json`, campo `outcome` |
| Risposte principali, riparazioni, invii totali | 6, 1, 7 | `dossier.json` `ledger`; `events.jsonl` conta 7 `step_dispatched` |
| Invii dopo una seconda esecuzione dello stesso run | ancora 7: **nessun doppio invio** | `events.jsonl` |
| Documenti distinti dai 6 record di fonte nelle risposte | 4 | `dossier.json` `sources` |
| Lo stesso paper trovato da entrambi, con titoli diversi e DOI scritto in due modi | 1 fonte, `key_kind: doi`, `found_by: [solver_a, solver_b]`, livelli dichiarati separati | come sopra |
| Ricerche registrate, di cui dichiarate eseguite / mai eseguite | 13, 5 / 4 | `dossier.json` `searches` |
| Contraddizioni, tutte aperte | 3 (2 dichiarate, 1 derivata) | `dossier.json` `contradictions`, tutte `status: open` |
| Piste selezionate su proposte | 2 su 5 | `leads.json` |
| Affermazioni segnalate per forma sospetta | 2 | `dossier.json`, `claims[].flags` |
| Chiavi di risposta scartate senza effetto | `budget`, `max_rounds` | `dossier.json` `dropped_keys` |
| Test verdi, fra motore preesistente, ricerca e oracolo | 203 | esecuzione del comando in §2 |

**Due difetti trovati dalla prova, entrambi corretti:**

1. Una **risposta riparata non veniva riconosciuta alla ripresa**. Il motore trovava il
   primo tentativo illeggibile, smetteva di cercare, e proseguiva come se quel modello non
   avesse mai risposto: la risposta riparata restava su disco, ignorata, e al compagno
   veniva detto che una voce mancava. **Riguardava anche il ciclo di debug**, non solo la
   modalità nuova.
2. Due piste con ipotesi corte si fondevano per **somiglianza testuale** — «pista di A» e
   «pista di B» danno 0,90 — dimezzando in silenzio la fase 3. Ora sotto i 60 caratteri
   si fondono solo per uguaglianza esatta.

**Capacità di ricerca dei canali**, letta dalla configurazione spedita e non assunta:
DeepSeek dichiara `ricerca_intelligente`, descritta nel suo profilo con selettore e
`aria-pressed` (misurata il 2026-09-13); **Kimi non dichiara nessun controllo di ricerca**,
perché nessuno ne ha mai osservato uno su quell'interfaccia.

## 4. Interpretazione e incertezza

**Misura:** il motore a tre fasi gira, non rispedisce domande, e conserva le otto
distinzioni su risposte costruite per metterle alla prova.

**Interpretazione:** la forma del dossier regge. Che regga su risposte vere è un'altra
cosa, e non è stata osservata.

**Quello che la prova non dimostra**, ed è la parte che conta:

- **che le distinzioni di provenienza sopravvivano a risposte reali.** Le sei risposte
  della prova sono state scritte da me sapendo quali distinzioni dovevano mettere alla
  prova. Un modello vero scriverà `consulted: full_text_or_section` con più disinvoltura
  di quanto abbia fatto il mio fixture, e il programma non ha modo di contraddirlo;
- **che l'interruttore di ricerca si accenda su un'interfaccia vera.** L'adattatore
  scriptato non impone e non verifica nessuna modalità: quel percorso di codice esiste
  (`apply_modes`) ed è stato provato sul ciclo di debug, mai in una campagna di ricerca;
- **che DeepSeek o Kimi rispondano a un prompt di ricerca.** Nessun messaggio di questa
  modalità è mai partito.

**Il limite strutturale, che non si chiude con più lavoro sui prompt:** il canale mostra
che l'interruttore era acceso, non quali query siano state eseguite. Per questo il livello
`observed_in_channel` esiste nel vocabolario e **non è raggiungibile da nessun percorso di
codice**. Tutto ciò che un worker dice di aver cercato resta una sua dichiarazione. Una
campagna che producesse cento fonti verificabili non renderebbe le sue ricerche osservate.

## 5. Spiegazione semplice

Se chiedo a due assistenti di cercarmi degli articoli, torneranno con un elenco. Il
problema è che l'elenco ha la stessa forma sia che li abbiano davvero cercati e letti, sia
che li abbiano ricordati. Un riferimento scritto bene non dimostra che l'articolo esista,
e tantomeno che dica quello che gli viene attribuito.

Questa modalità tiene separate le cose che si assomigliano: una ricerca *proposta*, una
ricerca che il worker *dice* di aver fatto, e una ricerca che abbiamo *visto* fare — e
l'ultima, oggi, non è ottenibile, quindi nessuna riga la porta mai. Per le fonti: vista in
un elenco, abstract letto, testo letto, non accessibile. E per le affermazioni: risultato
riferito dagli autori, interpretazione del worker, ipotesi nuova.

Lo stesso paper trovato da entrambi conta una volta, ma solo se condividono un DOI o un
indirizzo: due titoli che si assomigliano restano due articoli, perché di solito lo sono.
E quando i due si contraddicono, il programma **non decide chi ha ragione**: non ha letto
il paper, e una contraddizione archiviata senza prove è peggio di una lasciata aperta.

## 6. Conseguenze

- Nuova decisione **D-023** in `docs/DECISIONI.md`: la modalità di ricerca separa i
  livelli di provenienza e non li promuove; sceglie le piste con una regola e non con un
  modello; non chiude contraddizioni; non inventa una sintesi consensuale.
- Nuovo documento `docs/RICERCA_SCIENTIFICA.md`, con lo stato riga per riga di che cosa è
  provato e che cosa no.
- Un incarico scientifico reale è pronto e **non è stato avviato**:
  `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml`. Riguarda l'incertezza
  numero 7 di `docs/PROGETTO.md` §4 — se esista Perturb-seq CRISPRi pubblico in linea T
  matura o squamosa. Se la risposta fosse positiva sbloccherebbe il passo 3 di
  `docs/PROGETTO.md` §5, che è il collo di bottiglia del progetto.
- Il prossimo passo che chiuderebbe la parte non dimostrata è una campagna reale avviata
  dall'operatore. Il secondo, indipendente, è osservare il controllo di ricerca di Kimi
  con `orch probe kimi`, senza il quale metà campagna gira senza ricerca.

## 7. Cosa corregge

**Nessuna conclusione di un checkpoint precedente.** Corregge invece un difetto del codice
descritto in [CP-0004](0004-primo-trial-locale-e-pacchetti.md)? No: il difetto della
risposta riparata non compare in nessun checkpoint, perché non era mai stato osservato. È
un difetto del ciclo di debug documentato in `docs/ORCHESTRATORE.md` §8, che diceva «parte
un unico prompt di riparazione» senza dire che alla ripresa quella riparazione veniva
persa. Quel paragrafo resta vero su un run che non viene ripreso.

## 8. Domanda di comprensione

Un worker restituisce dieci fonti con DOI ben formati e dichiara `consulted: abstract` per
tutte. Il programma segnala qualcosa? E che cosa cambierebbe se per due di quelle dieci
scrivesse invece che gli autori riportano un certo risultato?
