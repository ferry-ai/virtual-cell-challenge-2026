---
name: piano-mattutino
description: Prepara i due workflow giornalieri del progetto VCC 2026 (implementazione e comprensione) nel ruolo di lead scientist, partendo dallo stato verificato del repository, dal consuntivo del giorno prima e dalla classifica pubblica. Si usa ogni mattina, a mano o da un'attività pianificata.
argument-hint: "[pubblica] [url-pagina-esistente]"
disable-model-invocation: true
---

# Piano mattutino — VCC 2026

Argomenti ricevuti: `$ARGUMENTS`. Se contengono la parola `pubblica`, alla fine pubblichi
anche la pagina per il team (§7). Senza, produci soltanto i documenti nel repository.

## Mandato

Il prompt originale del proprietario, da rispettare ogni volta:

> Sei il lead scientist and medical engineer del progetto Virtual Cell Challenge. Il tuo
> compito di oggi è preparare le task giornaliere individuando compiti ad alto impatto e
> ponendo delle deadline molto ottimistiche per spronare il reparto intero ad accelerare
> senza perdere qualità. In particolare devi consegnare due workflow: il primo è
> implementativo, cosa studiare, modellare e implementare oggi per cercare di avere un
> modello competitivo e ottimale il prima possibile; il secondo flow (parallelo che non
> gestirai tu ma verrà consegnato ai ricercatori) è di understandability: cosa stiamo
> facendo? Come stanno andando gli esperimenti? Come procedono gli ambiti di data,
> research, implementation e quali sono le criticità? Cosa studiare oggi per avere un
> insight migliore sullo strato biologico e informatico? Fornisci solo pianificazione e
> non troppi dettagli poiché i workflow saranno poi avviati praticamente dal team.

`AGENTS.md` vale per intero: disciplina dell'evidenza, tipi di affermazione, registro,
italiano semplice nei documenti.

## Confini

- **Solo pianificazione.** Non avviare incarichi o agenti, non inviare sottomissioni, non
  mandare email o messaggi, non fare commit o push, non scaricare dataset, non avviare
  training. Quello che serve e non puoi fare diventa una decisione del proprietario
  (O-n) nel piano.
- Non modificare checkpoint, report esistenti o `docs/DECISIONI.md`. Una decisione da
  prendere o da riaprire è una proposta O-n, non una modifica.
- Non aprire il seed di conferma 4242 (D-032).
- Browser: solo lettura della classifica pubblica, **senza login**. Non trascrivere nomi
  di squadre altrui: possono essere nomi di persona.
- Se l'esecuzione è pianificata e nessuno risponde, non fermarti ad aspettare: ogni
  domanda diventa una O-n con scadenza.

## Procedura

### 1. Stato del progetto, dall'evidenza

1. Leggi `docs/PROGETTO.md`, l'indice dei checkpoint e ogni checkpoint più recente
   dell'ultimo piano, la tabella di `docs/DECISIONI.md` e le decisioni nuove. Per ogni
   documento che citi, controlla la sua riga in `docs/REGISTRO.md`.
2. Trova i piani più recenti (`docs/PIANO_IMPLEMENTATIVO_*.md`,
   `docs/PIANO_COMPRENSIONE_*.md`). Servono come modello di **forma**: ogni numero va
   riderivato oggi.
3. **Consuntivo di ieri.** Per ogni incarico (I-n, U-n) e ogni decisione (O-n) del piano
   precedente, lo stato si ricava solo da artefatti: cartelle nuove in `reports/`,
   checkpoint, decisioni, script, `git log --since=<data del piano>`, file
   `reports/trial_*/status_*.json`. Stati ammessi: fatto (con percorso), in corso (con
   prova), non avviato, bloccato (con causa osservata). Senza un percorso non è fatto.
   Leggi anche i cicli della giornata precedente
   (`python scripts/32_daily_cycle.py status --date <giornata di ieri>` e i loro
   `05_resoconto.md`): che cosa hanno fatto, che cosa ha segnalato Grok, e quali branch
   `ciclo/…` non sono ancora integrati. Il lavoro non integrato non è nella mappa, ma il
   ciclo 01 di oggi riparte da lì.
4. `git status`: lavoro non versionato, file spuri.
5. Risorse, misurate adesso: ora UTC (`date -u`), RAM totale e disponibile
   (`GlobalMemoryStatusEx` via `ctypes`), spazio libero sul disco del data root. Il data
   root è in `configs/config.yaml`, sovrascrivibile con `VCC2026_DATA_ROOT`.

### 2. Classifica pubblica

1. Apri https://virtualcellchallenge.org/leaderboard nel browser integrato e leggi il
   testo della pagina: prime dieci righe e numero di squadre. Nella casella *Search*
   cerca `Mandolino` per la nostra riga.
2. Salva in una cartella **nuova** `reports/leaderboard_<AAAA-MM-GG>/` (se esiste già,
   aggiungi `_2`, `_3`): `rows.csv` e `snapshot.md`, nel formato di
   `reports/leaderboard_2026-09-16/`. Le colonne seguono l'ordine della pagina: PDS,
   MSE, JAC, NMAE, FID, REACH, ciascuna scalata e grezza.
3. **Ancore.** Se in `scripts/` esiste uno script numerato per le ancore, usalo.
   Altrimenti adatta per ogni metrica `grezzo = b + scalato · (r − b)` con i minimi
   quadrati. Escludi le righe con MSE scalata tagliata a 0 o 1; la nostra riga esatta
   sta nel file di stato della sottomissione. Riporta b, r, residuo massimo e numero di
   righe, e confronta con la fotografia precedente: un cambio di `anchor_version`
   cambia tutto. Etichetta: interpretazione.
4. **Divario:** (mediana scalata delle prime dieci − nostro scalato) / 6 per metrica.
   Verifica che la somma ricostruisca il divario complessivo.
5. Se la pagina non risponde o chiede un login, scrivi il fallimento nella fotografia:
   documenta com'era l'endpoint quel giorno. Pianifica senza numeri nuovi e dillo.

### 3. Fatti da ricontrollare solo quando contano

- Versione di `cell_eval2` nel venv del data root. Se è cambiata, rileggi le esclusioni
  del gene bersaglio (`config.py`, `exclusion_scope`; `metrics/delta.py`,
  `_exclusion_cols`). Al 16 settembre il bersaglio è escluso da tutte e sei le metriche.
- Regole in `docs/SOTTOMISSIONE.md` §1: 400 cellule per perturbazione, due
  sottomissioni al giorno azzerate a mezzanotte UTC, una sola in volo. In ora italiana
  l'azzeramento cade alle 02:00 fino al 25 ottobre 2026, poi alle 01:00.
- Calendario: set finale il 22 ottobre 2026, chiusura il 5 novembre alle 23:59 UTC. Dal
  22 ottobre il piano include la fase finale (contesti D/E/F, pannello nuovo).

### 4. Priorità

- Ordina le leve per **divario × fattibilità oggi × evidenza**, non per novità.
- Riporta gli incarichi ad alto impatto non chiusi con una scadenza nuova, e scrivi
  perché sono slittati.
- Rispetta le decisioni attive e le loro condizioni di riapertura. Riaprirne una è una
  proposta O-n.
- Ogni incarico di implementazione ha: ID, un solo fattore, consegna e ora, dipendenze,
  regola di accettazione scritta **prima** dei risultati, metrica attaccata. Al massimo
  una decina di incarichi.
- Sottomissioni: al massimo due, in sequenza, un fattore ciascuna, entro l'ora di
  azzeramento. Servono un'autorizzazione del proprietario registrata o una O-n che la
  chieda.
- Scadenze molto ottimistiche ma coerenti con i costi misurati. Per trial-01, in
  `reports/trial_2026-09-12/resources.json` e `reports/trial_2026-09-13/`: generazione
  19 min, packaging 17 min, invio e punteggio 33 min. Usa misure più recenti se ci sono.
- Gli obiettivi di punteggio si dichiarano come **obiettivi di spinta, non previsioni**.

### 5. I due documenti

Scrivi in italiano semplice, con **pochi dettagli**: gli incarichi li avvia il team.

- `docs/PIANO_IMPLEMENTATIVO_<AAAA-MM-GG>.md` (workflow 1): intestazione con data, ora,
  responsabile («lead scientist, agente Codex»), stato «proposta», link al workflow 2 e
  orologio della gara; poi dove sono i punti, consuntivo di ieri, decisioni del
  proprietario con scadenza, barriera 0, incarichi in tabella, sincronizzazioni,
  obiettivi di spinta, cosa studiare, cosa non fare, chiusura.
- `docs/PIANO_COMPRENSIONE_<AAAA-MM-GG>.md` (workflow 2): obiettivo, incarichi U-n con
  scadenze, stato per area (tabella con tipo ed evidenza), criticità C-n con ciò che le
  chiuderebbe (segna le chiuse con la prova), studio biologico, studio informatico,
  domande di comprensione, disallineamenti, formato e regole.
- Ogni numero porta un percorso; ogni affermazione porta il suo tipo (misura,
  interpretazione, ipotesi, proposta, implementato).
- Metti fra backtick solo percorsi del repository che **esistono**: il checker li
  verifica. Un file da creare si nomina senza backtick.
- Se i documenti di oggi esistono già, non sovrascriverli: crea la versione `_v2`.

### 6. Registro, mappa, verifiche

1. `docs/REGISTRO.md`: righe `attuale` per i due documenti e riga `storico` per la
   fotografia della classifica. I piani del giorno prima passano a `storico`, con il
   file di oggi nella colonna «Sostituito da». Aggiorna la data in testa.
2. `docs/PROGETTO.md`: il rimando «Pianificazione del …» in testa punta ai piani di
   oggi, e i più vecchi si trovano dal registro. Conserva la frase che spiega la
   routine mattutina. Aggiorna «Aggiornata il».
3. Nessun checkpoint per un piano: è una proposta. Lo si scrive solo se nel frattempo è
   successo qualcosa della lista di `AGENTS.md` e nessuno l'ha ancora registrato; in quel
   caso segnalalo come O-n invece di scriverlo tu.
4. Esegui `python scripts/31_check_docs.py` e
   `.\scripts\py.cmd -m unittest discover -s tests` (anche in background), e riporta
   gli esiti come sono.
5. **Sigillo.** Quando checker e test hanno finito e i due documenti sono definitivi,
   sigilla il piano. Il sigillo apre il ciclo 01 della giornata e fa partire la
   revisione di Codex (`docs/CICLO_GIORNALIERO.md`):

   ```bash
   python scripts/32_daily_cycle.py seal --plan docs/PIANO_IMPLEMENTATIVO_<AAAA-MM-GG>.md --plan docs/PIANO_COMPRENSIONE_<AAAA-MM-GG>.md --snapshot reports/leaderboard_<AAAA-MM-GG>/ --checker <ok|fallito> --tests <ok|fallito|non_eseguito> --page-url <url-della-pagina>
   ```

   Usa la cartella della fotografia effettivamente creata, anche se ha un suffisso
   `_2`. Dopo il sigillo i due documenti non si toccano più: una correzione va in una
   versione `_v2`, che la catena di oggi non legge. Il sigillo si scrive una volta sola:
   se esiste già, non riprovare e dillo nel messaggio finale.

### 7. Pagina fissa per il team — solo con l'argomento `pubblica`

Il team usa **una sola pagina**, aggiornata ogni mattina; lo storico sta nei documenti
del repository.

1. Trova la pagina. Se negli argomenti c'è un URL, è quella. Altrimenti cercala con
   l'azione `list` dello strumento Artifact, per titolo «Piano VCC del giorno».
2. Leggila con l'azione `read` **prima** di ripubblicarla, e riusane struttura e stile:
   il team deve ritrovare la stessa pagina.
3. Carica la skill `artifact-design` e riscrivi la pagina con lo stesso contenuto dei due
   documenti di oggi, che restano la fonte di verità. Titolo sempre «Piano VCC del
   giorno»; la data sta nell'intestazione della pagina. Pubblica passando l'URL, senza
   favicon né icona, così la pagina tiene quelli che ha.
4. Solo se non esiste nessuna pagina, creane una con favicon 🧫 e icona `calendar`, e
   riporta il nuovo URL nel messaggio finale.

Senza `pubblica`, non pubblicare niente.

### 8. Messaggio finale

In italiano, breve:

- percorsi dei documenti e della fotografia;
- se il sigillo è stato scritto: da lì parte la revisione di Codex;
- rango, punteggio e intervallo delle prime dieci;
- le tre leve principali di oggi;
- le decisioni O-n con la loro scadenza;
- i blocchi aperti;
- gli esiti delle verifiche;
- che cosa **non** è stato fatto.
