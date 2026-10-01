# CP-0054 — Lo scorer funziona fuori dal sandbox: consegna verificata al teammate

- **Data:** 2026-10-01
- **Tipo:** correzione
- **Redatto da:** Codex su richiesta del proprietario
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Come trasferire il programma R-LEAD al teammate senza dipendenze locali implicite?
I tre errori dello scorer nell'audit dimostrano davvero un ambiente incompleto sulla macchina?

## 2. Cosa è stato fatto

Preparati [brief e mappa](../CONSEGNA_TEAMMATE.md), [prompt autonomo](../PROMPT_CLAUDE_TEAMMATE.md)
e [preflight portabile](../../reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py).
Confrontati inventari nel sandbox e fuori dal sandbox con lo stesso Python e la stessa radice
dati. Provati import dello scorer e suite completa fuori dal sandbox, senza installazioni.
Controllati gli oggetti Git da pubblicare e il dry run del push, su richiesta del proprietario.
La sequenza e gli esiti sono nelle [verifiche nuove](../../reports/analisi/handoff_teammate_2026-10-01/VERIFICHE.md).

## 3. Cosa si è osservato

`source_machine_r2.json` non individua `cell_eval2.config` nel sandbox;
`source_machine_r3_native.json` lo individua fuori dal sandbox, con lo stesso eseguibile
Python 3.12.3. La suite nativa passa **287 test in 232,940 secondi**; dettagli e confronto
dei percorsi del modulo nelle [verifiche](../../reports/analisi/handoff_teammate_2026-10-01/VERIFICHE.md#correzione-scorer).
I tre controlli di portabilità del preflight sono passati (`preflight_checks_r1.json`).

Il controllo dei blob Git (`publication_check_r1.json`) copre 101 commit non ancora remoti,
2.316 blob nuovi, 83.590.833 byte; massimo 5.351.609 byte, nessun blob oltre 100 MB e nessun
formato riconoscibile di credenziale individuato. Non certifica ogni possibile dato privato.
Manifest e risultati sono nella [cartella della consegna](../../reports/analisi/handoff_teammate_2026-10-01/README.md).

## 4. Interpretazione e incertezza

Misurata una differenza di visibilità fra contesti di esecuzione. I precedenti errori
non dimostrano un pacchetto assente dal computer; non è isolata la causa precisa del sandbox.
Il clone trasferisce il programma, non dataset, pesi, credenziali o processi attivi.
Il superamento dei test di origine non dimostra readiness del teammate né qualità del modello.

## 5. Spiegazione semplice

Una finestra dell'agente non riusciva a vedere un file che il terminale della stessa macchina
vede. Prima di reinstallare bisogna controllare da quale finestra e con quale Python si lavora.
Per riprendere il progetto servono anche un inventario dei propri dati e prove sul proprio sistema.

## 6. Conseguenze

R-LEAD passa al teammate; prima consegna: ambiente verificato, diagnosi applicabili riprodotte
e fase A corretta e provata. Il prompt richiede inventario per A–F, test CPU, scorer e verifiche
di applicabilità prima di training pesante. Incarichi R-LAB preservati. Nessuna nuova decisione
scientifica, nessuna promozione del modello, nessun cambio delle metriche.

## 7. Cosa corregge

Precisa soltanto la diagnosi ambientale delle verifiche citate da
[CP-0053](0053-audit-cellnet-e-strategia.md):
`reports/analisi/lead_audit_2026-10-01/VERIFICHE.md` osservava tre errori di import nel sandbox,
da cui si era inferito un ambiente incompleto. I test nativi mostrano che tale inferenza non
vale per la macchina. Il report originale resta una fotografia storica, con scheda di correzione
e stato nel registro; misure scientifiche, confronto r2/r3 e piano dell'audit restano invariati.

## 8. Domanda di comprensione

Perché lo stesso errore di import deve essere confrontato fra agente e terminale prima di
reinstallare, e perché 287 test passati qui non confermano che il teammate possa addestrare?
