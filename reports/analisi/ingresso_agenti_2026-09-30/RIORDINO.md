# Riordino dell'ingresso degli agenti, 30 settembre pomeriggio

Claude (app desktop, sessione `4dfcb130`), dalle 15:05 circa del 30/09; orari letti con `date`.
Il proprietario ha chiesto in chat di snellire la repo perché un agente appena arrivato capisca in
fretta progetto, direzione, stato e lavoro assegnato, legga solo ciò che serve al suo compito,
distingua le regole globali da quelle di un ambito; di separare progetto, strumenti di esecuzione,
infrastruttura degli agenti e archivio; di dare una sede a ogni informazione. Via a procedere fino
all'implementazione, senza push. Le regole che ne seguono sono la decisione D-049.

**Tipo di affermazioni.** Righe e conteggi sono **misurati** (`wc -l`, `git show 1212e2f:…`,
`git worktree list`, `Get-ScheduledTask` in sola lettura). L'analisi del percorso d'ingresso è
stata fatta da quattro agenti in sola lettura; ogni fatto che ne è entrato nei documenti è stato
riverificato sulla fonte prima di scriverlo. La verifica dei sei percorsi con agenti «appena
arrivati» è stata fermata a metà per il limite d'uso: il §5 è una verifica meccanica, non una
prova con agenti.

## 1. Prima (commit `1212e2f`)

- **Letture obbligatorie prima di qualunque compito: circa 880 righe.** CLAUDE.md 220, PROGETTO
  §0 e §5 223, AMBITI 135, PIANI 97, ERRORI 204, le ultime tre righe dell'indice dei checkpoint;
  più LAVORO (280) per chi esegue codice, e il registro (1.193 righe) prima di fidarsi di un
  documento.
- **Tre percorsi di lettura diversi** (CLAUDE.md, PROGETTO §6, AGENTS.md) e più tabelle «dove
  leggere che cosa» (CLAUDE.md, PIANI §1, AMBITI §8, docs/CLAUDE.md, PROGETTO §6).
- **Lo stato del t28 scritto a mano in sette posti**, la tabella dei punteggi in due, le regole dei
  checkpoint in cinque, il preflight dei job in quattro, il ritiro della catena di cicli in circa
  dieci. Il §0 di PROGETTO era di 203 righe, circa metà cronaca già presente nei checkpoint.
- **Copie scadute:** R-V2 «in pausa» (la scheda dice in corso dal 28/09), la prova generale «non
  fatta» (fatta in forma ridotta, CP-0044), le ancore che «reggono» (corrette da CP-0050), cinque
  evidenze «assenti» (quattro recuperate il 28/09), 22.000 righe di codice di ricerca (59.638 al
  30/09), il t23 «in attesa del via» (valutato il 28/09).
- **Perimetri mescolati:** l'accordo globale conteneva stato, lo scopo di ricerca D-044, il
  preflight dei job e l'archivio; la base di lancio `agent-hub`, attiva fuori dalla repo (84
  esecuzioni dal 24 al 29/09), non era nominata da nessun documento d'ingresso, mentre PROGETTO §2
  chiamava «chiusa» l'infrastruttura degli agenti.

## 2. Struttura risultante e sedi canoniche

| Perimetro | Ingresso | Contenuto |
|---|---|---|
| Progetto VCC | `docs/AMBITI.md`, una sezione per area | dati, modelli, valutazione, codice della pipeline |
| Strumenti di esecuzione | `docs/LAVORO.md`, per sezione; `docs/ERRORI.md` per i job | Colab e Kaggle, generazione, pacchetto, invii |
| Infrastruttura degli agenti | `docs/AGENTI.md`, nuovo | base di lancio fuori dalla repo, sistemi ritirati, coordinamento |
| Archivio e storia | DECISIONI, indice dei checkpoint, `--status` | decisioni, checkpoint, registro, archivio, `docs/storico/` |

Le sedi canoniche, una per tipo di informazione, sono la tabella di `docs/CLAUDE.md`. Le scelte
principali: lo stato solo nel §0 di PROGETTO; i punteggi ufficiali solo nella tabella di
`reports/invii/README.md`; stato e assegnazione di un piano solo nella sua scheda; le regole dei
checkpoint solo nell'intestazione del loro indice; le regole di scrittura in `docs/CLAUDE.md`; la
validità di un percorso con `python scripts/31_check_docs.py --status <percorso>`, che mette
accanto registro, correzioni dei checkpoint e giudizio dell'indice della cartella.

## 3. Duplicazioni e obblighi di lettura tolti

- `CLAUDE.md` da 220 a 131 righe: niente stato, niente D-044 (in GENERALIZZAZIONE, con la frase
  che mancava sugli assi incompatibili), niente preflight (in ERRORI e LAVORO §3), niente regole
  di scrittura (in `docs/CLAUDE.md` e `reports/CLAUDE.md`). Restano i perimetri, la tabella dei
  compiti con dove fermarsi e le regole globali, con due regole prima sparse: nessuna identità di
  linea accanto ad A/B/C, e la contraddizione aperta sull'autorizzazione del calcolo in cloud.
- `AGENTS.md` da 17 a 7 righe: rimanda all'accordo, più la guida di cartella che Codex non carica.
- PROGETTO da 449 a circa 280 righe, il §0 da 203 a 89 (59 fino alle decisioni in attesa del
  proprietario); §6 e §7 sono rimandi. Il testo tolto è in
  `docs/storico/PROGETTO_sezioni_0_6_7_2026-09-30.md`.
- Tolte le tabelle di instradamento di PIANI §1 e AMBITI §8, e l'elenco delle schede in
  `docs/piani/CLAUDE.md` (resta in PIANI §2); il blocco «scoperte del 29–30/09» di AMBITI, già
  riportato nelle sue sezioni.
- In LAVORO: una sola lista di che cosa fare dopo un punteggio (§2, punto 7), un solo dato sul
  disco (dalle riserve degli stadi), le opzioni dello stadio 45 del t28, Kaggle nel §3, le regole
  degli stadi rimandate a `scripts/CLAUDE.md`.

## 4. Il percorso iniziale, prima e dopo

| Compito | Prima: righe da leggere prima di cominciare | Dopo |
|---|---|---|
| Qualunque, comune | circa 880 | CLAUDE.md 131 + PROGETTO §0 59–89 = 190–220 |
| Modificare il generatore | 880 + LAVORO 280 + guide di cartella | 190 + `scripts/CLAUDE.md` 42 + `src/vcc2026/CLAUDE.md` 46 + AMBITI §3 16, più docstring e test |
| Studiare una sorgente dati | 880 + GENERALIZZAZIONE 144 | 190 + AMBITI §4–5 33 + GENERALIZZAZIONE 156 + indice delle sorgenti 50 |
| Leggere un punteggio ufficiale | 880 + LAVORO 280 | 190 + LAVORO §2 60 + indice degli invii 88 + l'ultimo checkpoint di punteggio |
| Preparare un job Colab | 880 + LAVORO 280 (ERRORI già dentro gli 880) | 190 + LAVORO §3 40 + ERRORI, parte dei job 134 e lezioni 41 |
| Base di lancio | 880, senza trovare la base di lancio | 190 + `docs/AGENTI.md` 111, poi le istruzioni dell'hub |
| Ricostruire una decisione | 880 + REGISTRO 1.193 | 190 + tabella di DECISIONI 51 + una sezione + `--status` sui documenti citati |

## 5. I sei percorsi, verificati a mano

Per ogni percorso si sono seguite le righe della tabella dei compiti e si è controllato che la
risposta alle domande chiave sia sul percorso: generatore (prova byte per byte prima e dopo in
`src/vcc2026/CLAUDE.md`; opzioni del t28 in LAVORO §1; nessun percorso di dati nel codice in
`scripts/CLAUDE.md`); sorgente dati (niente scarto per scarso overlap, maschere, leakage T/J,
autorizzazione e catalogo in GENERALIZZAZIONE); punteggio (sei scalati pubblicati, ancore non
esatte, lista unica in LAVORO §2.7, tabella in `reports/invii/README.md`); job Colab (manifest e
preflight in ERRORI, Kaggle in LAVORO §3, autorizzazione aperta in CLAUDE.md); base di lancio
(interfaccia, regole del worker, rapporti in `agenti/`, attività pianificate in AGENTI §1–2);
decisione storica (`--status` su CP-0021 mostra «Corretto da» CP-0050; D-040 con la condizione di
riapertura). Nessun percorso passa per un perimetro estraneo, salvo PROGETTO §0 che è comune.
**Non è stata fatta** la prova con agenti che partono da zero: è il primo controllo da ripetere.

## 6. Che cosa resta aperto

- **Per il proprietario:** togliere le attività pianificate «VCC2026 Ciclo giornaliero» e «VCC2026
  Guardiano» della catena ritirata (misurato il 30/09: registrate e pronte, la prima eseguita alle
  15:02 con esito 1); decidere sui worktree lasciati dagli agenti (15 dell'hub, 2 di Codex,
  `vcc2026-refactor`, `wt8`); risolvere la contraddizione sull'autorizzazione del calcolo in cloud;
  il push.
- **Schede dei piani, non riscritte perché hanno assegnatari:** S-INVII, R-DATI, R-MODELLI e
  R-SWITCH sono ferme al 28/09; R-V2 (364 righe) e R-REV (344) sono diventate diari; molte
  assegnazioni nominano sessioni chiuse.
- **Validità divergente:** il registro dice `attuale` dove l'indice della cartella dice «in parte»
  o «chiuso» (per esempio `reports/sorgenti/universo_2026-09-26/`, `docs/storico/SVD_E_RANGO.md`), e
  dieci checkpoint corretti hanno righe `attuale`. `--status` mostra le due voci insieme; allinearle
  richiede di rileggere ogni documento, non fatto qui.
- **Righe scadute negli indici delle categorie**, segnalate dall'analisi e non corrette qui: la prova
  generale con D4 e D9 «da correggere» e `lezioni_invii` senza la correzione del 29/09
  (`invii/README.md`), il t23 «non inviato» e l'audit di codex «assente» (`trasferimento/README.md`),
  le sorgenti «quasi tutte in 3'» (`modelli/README.md`), `basali_asse` «in corso»
  (`sorgenti/README.md`), il banco K562 «protocollo» (`generatore_e_banchi/README.md`).
- **Strumenti di esecuzione nei report datati:** il preflight, il registro degli incidenti (ora
  eccezione dichiarata), i launcher con preflight, la procedura Kaggle; gli script di
  `notebooks/colab_jobs/` del 17/09 non eseguono il preflight.

## 7. Come tornare indietro

Tutto è in un commit locale, non su GitHub: `git revert` lo annulla. Il testo tolto da PROGETTO è
in `docs/storico/PROGETTO_sezioni_0_6_7_2026-09-30.md`; nessun report, checkpoint o dato è stato
spostato o cancellato.
