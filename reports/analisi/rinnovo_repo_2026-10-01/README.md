# Rinnovo della repo dopo t29

**Mandato:** il proprietario chiede il 1 ottobre 2026 di rinnovare la repo per togliere i
depistaggi e preparare un piano implementativo per Claude. Conferma che Claude e teammate
sono fermi. Esecuzione Codex, chat `01a0f949-2230-7703-b5c2-7d467397b431`, iniziata il
1/10 e proseguita dopo mezzanotte del 2/10, Europe/Rome.

**Tipo:** manutenzione documentale, ricostruzione e proposta implementativa. Nessun nuovo
training, download, calcolo cloud, invio o risultato biologico prodotto da questo lavoro.
La causa del fallimento t29 resta da isolare.

## Risultato della manutenzione

Un solo percorso operativo: CLAUDE → PROGETTO §0 → PIANI §2–3 → R-LEAD.
Il [piano P0–P6](../../../docs/piani/strategia-scientifica.md) è la specifica canonica;
il [prompt per Claude](../../../docs/PROMPT_CLAUDE.md) la richiama. R-COMP mantiene
l'obiettivo, R-LAB gli artefatti, R-REV e S-INVII i requisiti residui; R-DATI, R-SWITCH
e R-V2 aspettano una motivazione sperimentale. R-MODELLI resta chiusa.

| Depistaggio osservato prima del rinnovo | Correzione | Fonte che la giustifica |
|---|---|---|
| README propone espansione del corpus come piano del giorno | Ingresso unico su R-LEAD; nessun prossimo training automatico | CP-0055 e richiesta del proprietario |
| Schede con incarichi, merge e code di giorni diversi ancora eseguibili | Schede correnti riscritte; copie integrali nello storico | Conferma degli agenti fermi; cronologie preservate |
| R4 «parte quando si rinnova la quota» | Protocollo tecnico conservato, nuovo lancio subordinato alla scelta R-LEAD | Protocollo R4 non include il banco a sei membri richiesto da t29 |
| Indici descrivono r1–r3 come se non avessero esiti e cellnet come mai addestrata | Esiti tecnici/esplorativi distinti dalla promozione | ESITO.md di ciascuna corsa; CP-0055 |
| HIPSCI mai usata, H1 ancora da acquisire, vecchi job tutti in coda | Stato per versione e modello; uso successivo distinto da disponibilità attuale | Corpus, registri di holdout e training cellulari R-LAB |
| K562 proposto implicitamente come contesto indipendente anche per le reti | Esposizione dei checkpoint obbligatoria; K562 già vista da r2/r3 | Corpus r2/r3 e protocollo K562 con proprie esclusioni/limiti |
| Gate identity r3 trattabile come spiegazione del t29 | Bracci e corse distinti; causa ufficiale non isolata | AGGIORNAMENTO_R3 e manifest t29 r2 desc |
| T11 copiabile con percorsi occupati; ultima ricetta suggerita come migliore | Manifest del riferimento e destinazioni nuove; help degli stadi | Ricevute di generazione, immutabilità delle ricette |
| Stadi 82/84 descritti come conversione alla scala ufficiale | Diagnostica storica approssimata; docstring/guide corrette, logica invariata | CP-0050 e R-022 |
| Vecchio spazio disco e lista di commit non pubblicati presentati come blocchi attuali | Preflight e confronto Git al momento dell'azione | Valori datati non attestano stato corrente |
| Prompt teammate contiene una seconda strategia estesa | Rimando al prompt unico; consegna mantiene soltanto portabilità | D-051 |

Le curve dei modelli del 27–28/09 e i limiti dei proxy restano qualificati per esperimento;
non si estendono a tutte le reti cellulari. Il t29 boccia il candidato provato secondo la
sua regola. Non prova che ogni architettura neurale sia inutile.

## Conservazione e perimetro

Base **`3de6cd08528574fa033ea0d2855c734b530c2222`**; tag annotato locale
`archivio/pre-rinnovo-2026-10-01`. [Manifest](snapshot_manifest.json) con hash degli
originali e delle 18 copie in [docs/storico](../../../docs/storico/rinnovo_2026-10-01/INDICE.md).
Prose invariate, soltanto link relativi ribasati e fine riga normalizzati nelle copie;
il tag conserva i contenuti Git originali. Nessun percorso originale è rimosso.

Report di esperimenti, checkpoint, ricette, pesi e dati non vengono riscritti.
Il codice runtime non cambia: l'unica modifica Python fuori da questa cartella è
la docstring dello stadio 84. Gli script qui registrano la manutenzione, non una nuova pipeline.

`.claude/` è configurazione personale, ora ignorata per intero; non viene cancellata o
trasferita come parte del progetto. Le due ricevute `t29_keep_awake*_stop.json` già non
tracciate restano sul disco. Non sono esiti scientifici prodotti dal rinnovo.
Worktree, scratchpad, infrastruttura cloud e dati esterni non vengono ripuliti alla cieca.
Il lavoro copre la navigazione corrente e i depistaggi riscontrati: non certifica ogni
affermazione di ogni documento storico o lo stato attuale di account remoti.

## File di questa consegna

| File | Ruolo |
|---|---|
| `snapshot_docs.py`, `snapshot_manifest.json` | Copie di 18 guide prima della modifica e relativi hash |
| `renew_navigation.py` | Testi delle schede e dei prompt applicati nel rinnovo |
| `renew_indexes.py` | Riscrittura degli ingressi e correzioni delle guide |
| `renew_metadata.py` | Allineamento del registro, D-051, indici e archivio |
| `finish_navigation.py` | Indice delle copie storiche e rifinitura dei collegamenti |
| `prepare_validation.py`, `stage_paths.json` | File del rinnovo enumerati per lo staging nominativo |
| `verify_renewal.py` | Controlli di conservazione e perimetro; esito in `verification.json` |
| `VERIFICHE.md` | Stato e risultati dei controlli strutturali e della suite |
| `unittest_native.log` | Suite completa: 287 test passati nel runtime nativo, 438,159 secondi |

Gli script di modifica sono una registrazione della sessione, **non comandi da rilanciare**
su una repo che avrà altri cambiamenti. Per recuperare una versione usare lo storico o Git.
I passi eseguibili da Claude sono soltanto quelli della scheda R-LEAD corrente.
