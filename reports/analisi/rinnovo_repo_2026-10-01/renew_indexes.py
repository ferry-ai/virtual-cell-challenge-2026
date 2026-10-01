"""Reconcile live indexes with the post-t29 plan; preserve dated evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8-sig")


def write(name, text):
    (ROOT / name).write_text(text, encoding="utf-8", newline="\n")


def replace(name, old, new):
    text = read(name)
    if old not in text:
        raise ValueError(f"Missing expected text in {name}: {old[:80]}")
    write(name, text.replace(old, new, 1))


def main():
    old = read("README.md")
    write("README.md", """# Virtual Cell Challenge 2026

**Start here:** agents read [CLAUDE.md](CLAUDE.md), then
[current state](docs/PROGETTO.md) §0 and the [plan index](docs/PIANI.md) §2–3.
There is one implementation plan: [R-LEAD](docs/piani/strategia-scientifica.md),
with a [ready-to-use Claude prompt](docs/PROMPT_CLAUDE.md).
On another machine, also read the [environment handoff](docs/CONSEGNA_TEAMMATE.md).

After t29, no neural model is promoted. The current reference and observed scores
are maintained in PROGETTO and the [submission ledger](reports/invii/README.md).
The earlier training queues and instructions are [preserved as history](docs/storico/rinnovo_2026-10-01/INDICE.md).

This README covers the challenge and setup. Use [PROCEDURE](docs/PROCEDURE.md) for
execution, [AMBITI](docs/AMBITI.md) for one area's evidence, and
[reports](reports/README.md) for dated results. The final test set D/E/F arrives
on **22 October 2026**; submissions close on **5 November 2026**.

""" + old[old.index("## The task"):])

    old = read("docs/PROGETTO.md")
    start, end = old.index("## 0."), old.index("## 1.")
    current = """## 0. Oggi — dopo t29 e il rinnovo del 1–2 ottobre 2026

**La rete r2 `desc` non è promossa.** Il t29 cade nel ramo c della sua regola:
nessun altro invio neurale prima di un banco locale a sei membri almeno al livello del
transfer ([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)). La causa dello
score non è ancora isolata; il collasso identity di r3 non la dimostra.

**Il riferimento resta la ricetta t22**, quattro sorgenti a peso uguale; t22/t24 danno
una media osservata di **0,14207**. Il massimo è t28, **0,144845**, con incremento sul
t25 inferiore alla soglia registrata: non conclusivo ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
La correzione dello stimatore t25 si conserva; l'emissione t28 è un confronto distinto.
Ricette, cache, generatore e seed si ricostruiscono dai manifest, non dal numero del trial.
La fonte completa dei punteggi è l'[indice degli invii](../reports/invii/README.md).

**Un solo piano eseguibile: [R-LEAD](piani/strategia-scientifica.md).** Prima verificare
input/esposizioni, split, export, controlli e pesi; correggere i difetti riprodotti; confrontare
transfer, generico addestrato, bilineare e rete sui sei membri. Solo dopo valutare residuo,
dati aggiuntivi e distribuzioni. [Prompt per Claude](PROMPT_CLAUDE.md), [indice dei ruoli](PIANI.md).

Il corpus, le ingestioni e r1–r3 restano disponibili attraverso [R-LAB](piani/piano-giorno-2026-09-30.md).
I loro risultati sono tecnici o esplorativi: più cellule non dimostrano un modello migliore.
Il quarto training non è un lancio automatico al rinnovo della quota.
**K562 è già visto dalle reti r2/r3; H1 train/val è nel corpus, H1 test resta chiusa.**
La riserva non si usa per debug né si rinomina «nuovo contesto».

La consegna finale D/E/F resta il traguardo. La prova generale a forma piena è ancora
da completare, anche se si conserva il transfer ([R-REV](piani/revisione-critica.md)).
Risorse, spazio e accessi si misurano alla ripresa; i valori del 30/09 sono storia.

### Coordinamento e decisioni realmente aperte

Il proprietario ha confermato Claude e teammate **fermi** durante il rinnovo; la prossima
sessione prende R-LEAD registrando macchina, commit, file e output. Gli incarichi datati
sono conservati nello [storico del rinnovo](storico/rinnovo_2026-10-01/INDICE.md).

- Ogni accesso mancante si presenta con file necessario e passo impedito. H1 train/val
  non è un download ancora da proporre sulla base della vecchia lista.
- Nuovo cloud, download, invii e push seguono CLAUDE.md e la chat pertinente. Resta aperto
  il perimetro delle autorizzazioni cloud annotate in modo diverso nelle vecchie schede.
- Uso di ulteriori dati della stessa linea e verifica esterna della licenza Orion restano
  decisioni distinte dall'autorizzazione già data per gli invii; identità fuori dalla repo pubblica.
- La preregistrazione t21 citata ma assente resta [R-020](REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository),
  non va ricostruita dopo il risultato.

La pubblicazione si verifica confrontando commit locale e remoto aggiornato: nessuna lista
statica di commit «mai pubblicati» è autorevole. Worktree, scratchpad e infrastruttura hanno
il proprio stato in [AGENTI](AGENTI.md); il rinnovo non ne modifica la sorte.

"""
    write("docs/PROGETTO.md", old[:start] + current + old[end:])
    replace("docs/PROGETTO.md", "- **Misurato.** Nessun modello appreso passa la sua regola; dove batte la versione cieca non batte\n  quella con il contesto scambiato; la perdita sulla famiglia tenuta fuori sale dopo 50–100 passi\n  ([modelli](../reports/modelli/README.md)).", "- **Misurato nei modelli del 27–28/09.** Dove battono il contesto cieco non battono quello\n  scambiato; in quelle corse la perdita sulla famiglia esclusa sale dopo 50–100 passi.\n  Non estendere quella curva a r2/r3 cellulari: hanno [esiti e diagnosi propri](../reports/modelli/README.md).\n  Nessuna rete è stata promossa; t29 aggiunge un esito ufficiale negativo (CP-0055).")
    replace("docs/PROGETTO.md", "sono risolte, la `mse` resta stimata dalla classifica;", "non sono identificate per contesto: le ancore aggregate del 17/09 non convertono esattamente\ni grezzi ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md));")
    replace("docs/PROGETTO.md", "2. **Le decisioni di ricerca si prendono su un proxy di due membri su sei**", "2. **Le decisioni precedenti sono state prese anche su un proxy di due membri su sei**")

    old = read("docs/PIANI.md")
    shared = old[old.index("## 3. Lavorare"):old.index("## 4. Piani")]
    write("docs/PIANI.md", """# Piani — un incarico operativo, supporti e alternative

**Per lavorare adesso:** [R-LEAD](piani/strategia-scientifica.md), con il
[prompt per Claude](PROMPT_CLAUDE.md). Dopo t29 la prima consegna è un esperimento
interpretabile e un confronto completo, non l'espansione automatica del corpus.
Stato generale e riferimento in [PROGETTO §0](PROGETTO.md).

Questo indice mantiene priorità e dipendenze; stato e presa in carico stanno nelle schede.
Il rinnovo del 1–2 ottobre conserva [le versioni precedenti](storico/rinnovo_2026-10-01/INDICE.md).
Non sono incarichi da riprendere dai loro vecchi «prossimi passi».

## 1. Dove leggere che cosa

[CLAUDE.md](../CLAUDE.md) instrada per compito; [AMBITI](AMBITI.md) per area;
[docs/CLAUDE.md](CLAUDE.md) indica la sede canonica di ogni informazione.
Un report contiene evidenza datata, una scheda il lavoro attuale. L'esistenza di codice,
un protocollo o una riga «in corso» non prova che un job sia attivo o concluso.

## 2. Ordine dei piani aperti

| Ruolo | Scheda | Quando usarla |
|---|---|---|
| **Implementazione principale** | [R-LEAD — P0–P6](piani/strategia-scientifica.md) | Presa in carico unica: input/esposizione, diagnosi, correzioni, banco, estensioni condizionate e finale |
| Obiettivo del programma | [R-COMP](piani/modello-competitivo.md) | Perimetro e criterio competitivo; nessun secondo percorso da avviare |
| Inventario dell'esecuzione | [R-LAB](piani/piano-giorno-2026-09-30.md) | Corpus, training e artefatti disponibili; nuovi job scelti attraverso R-LEAD |
| Verifiche residue | [R-REV](piani/revisione-critica.md) | Forma piena, banco K562, basali e residui; la tabella distingue concluso e da fare |
| Consegna finale | [S-INVII](piani/invii-finale.md) | Manifest, pacchetto e lettura ufficiale; preparazione indipendente dal successo neurale |
| Supporto condizionato | [R-DATI](piani/dati-affidabilita.md) | Una lacuna di dati misurata nel banco, non una nuova raccolta indiscriminata |
| Ipotesi condizionata | [R-SWITCH](piani/switch-distribuzioni.md) | Limite di popolazione misurato e guide/repliche indipendenti |
| Catalogo precedente | [R-V2](piani/modello-v2.md) | Ritrovare filoni ed esiti; riapertura motivata attraverso R-LEAD |

R-COMP e R-LAB descrivono scopo e mezzi dello stesso lavoro. Le alternative conservano
valore come ipotesi, senza diventare otto piani da eseguire insieme. Ogni nuovo confronto
ha una regola scritta prima dei numeri. Nessuna voce dell'indice autorizza quota o invii.

""" + shared + """## 4. Piani chiusi e risultati precedenti

| Scheda | Esito | Riapertura |
|---|---|---|
| [R-MODELLI](piani/trasferimento-modelli.md) | Chiuso dal proprietario il 30/09; i confronti sono registrati nella scheda e nello storico | Nuovo protocollo motivato da R-LEAD; nessuna riapertura implicita nel rinnovo |

Le ipotesi H1–H10 del 24/09 sono nel [report di ricerca](../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md).
I loro esiti e le successive correzioni si trovano tramite AMBITI e gli indici dei report.
Una bocciatura di candidato non chiude automaticamente la famiglia di modelli.
""")

    old = read("docs/piani/trasferimento-modelli.md")
    closure = old[old.index("## Chiusura"):old.index("### Sottoattività documentale")]
    write("docs/piani/trasferimento-modelli.md", """# R-MODELLI — programmi, stato cellulare e bersagli nuovi

- **Stato:** chiuso il 30 settembre 2026 per scelta del proprietario; il rinnovo non lo riapre.
- **Aggiornato:** testo operativo ridotto nel rinnovo del 1–2 ottobre.
- **Assegnazione:** nessun training preso in carico qui; consegna documentale Codex del 25/09.
- **Prossimo passo:** nessuno senza riapertura esplicita e protocollo di [R-LEAD](strategia-scientifica.md).
- **Dipendenze:** nuovo limite misurato e input adeguati per la condizione di riapertura sotto.

La sezione seguente registra l'esito **al 30/09**. I successivi training cellulari e t29 sono
in [R-LAB](piano-giorno-2026-09-30.md); il lavoro corrente è R-LEAD. Le vecchie istruzioni
eseguibili sono [conservate nello storico](../storico/rinnovo_2026-10-01/docs/piani/trasferimento-modelli.md).

""" + closure)

    old = read("reports/README.md")
    suffix = old[old.index("## Come si leggono le colonne"):]
    write("reports/README.md", """# reports — evidenze datate, indicizzate per argomento

Le cartelle conservano misure, protocolli, uscite e codice delle esecuzioni. I report non
si riscrivono dopo un risultato: una correzione ha una nuova evidenza e un rimando nel
registro. Le regole sono in [CLAUDE.md](CLAUDE.md). Gli indici di categoria si aggiornano.

**Per scegliere il lavoro:** [PIANI](../docs/PIANI.md) e R-LEAD. Per scegliere cosa leggere:
[AMBITI](../docs/AMBITI.md), solo la sezione pertinente. Non leggere tutti i report né
seguire i «prossimi passi» datati come ordini attuali.

## Evidenze che cambiano il prossimo passo

| Domanda | Fonte |
|---|---|
| Che cosa ha bocciato t29? | [CP-0055](../docs/checkpoints/0055-t29-rete-cellulare-punteggio.md) e [invii](invii/README.md): candidato r2 `desc`, banco a sei membri richiesto prima del prossimo invio neurale |
| Quali difetti riprodurre? | [Nota training](analisi/lead_audit_2026-10-01/NOTA_TRAINING.md) e [diagnosi r3](analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md): split, pesi, controlli, baseline e gate |
| Quali risultati e input esistono? | [Modelli](modelli/README.md) e [sorgenti](sorgenti/README.md): esiti tecnici distinti da promozioni; disponibilità pesante da verificare |
| Che cosa non si può chiamare score o conferma? | [Credibilità degli score](analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md), CP-0050: ancore aggregate e riserva già vista |
| Perché il generatore resta un confronto separato? | [t28](../docs/checkpoints/0052-t28-punteggio-ufficiale.md), esito ufficiale non conclusivo, e [banco HepG2](generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md), sviluppo su un contesto |
| Che cosa ha cambiato il rinnovo? | [Registro del rinnovo](analisi/rinnovo_repo_2026-10-01/README.md), con copie e hash della navigazione precedente |

## Le categorie

| Categoria | Domanda | Indice |
|---|---|---|
| `gara/` | Scorer, ancore, controlli e fotografie della classifica | [gara](gara/README.md) |
| `invii/` | Previsione, artefatto, punteggio ufficiale e lettura della regola | [invii](invii/README.md) |
| `sorgenti/` | Dati, estrazioni, stimatori, corpus e QC | [sorgenti](sorgenti/README.md) |
| `trasferimento/` | Ricetta per lo stesso bersaglio e sue varianti | [trasferimento](trasferimento/README.md) |
| `modelli/` | Modelli appresi, protocolli ed esiti | [modelli](modelli/README.md) |
| `generatore_e_banchi/` | Emissione delle cellule e banchi con scorer | [generatore e banchi](generatore_e_banchi/README.md) |
| `analisi/` | Audit, ipotesi, sintesi e riordini | [analisi](analisi/README.md) |
| `storico/` | Linee chiuse e infrastruttura ritirata | [storico](storico/README.md) |

""" + suffix)

    old = read("reports/modelli/README.md")
    table = old[old.index("| Data |"):old.index("## Rischi da tenere presenti")]
    lines = table.splitlines()
    descriptions = {
        "cellnet_terza_ondata_2026-10-01/": ("Quarto training: terza ondata più floor su pi; protocollo tecnico conservato, non prossimo job automatico", "protocollo; nessun esito registrato, non soddisfa da solo il banco richiesto dopo t29"),
        "cellnet_completo_2026-10-01/": ("R3: seconda ondata CRISPRi/a/KO; lettura in ESITO.md e diagnosi del gate identity nell'audit del 1/10", "misure tecniche/esplorative; nessuna promozione; split diversi da r2"),
        "cellnet_esteso_2026-10-01/": ("R2: corpus esteso, ESITO.md; braccio desc usato nel t29 ufficiale, esito negativo CP-0055", "training misurato; candidato non promosso, cause da isolare"),
        "cellnet_tecnico_2026-10-01/": ("R1: primo training reale; protocollo, lanci ed ESITO.md, con incidente E-20261001-001", "misure tecniche; parte A non interamente passata, non promozione"),
        "risposta_biologica_2026-09-30/": ("Codice cellnet, descrittori, export e registri di holdout usati nei training r1–r3; H1 test riservata, train/val ammesse nel fit", "codice ed evidenza originali; diagnosi del 1/10 da leggere prima di riusare, correggere copie nuove"),
    }
    for i, line in enumerate(lines):
        for key, (core, verdict) in descriptions.items():
            if f"]({key})" in line:
                cells = line.split("|")
                cells[3], cells[4] = f" {core} ", f" {verdict} "
                lines[i] = "|".join(cells)
    write("reports/modelli/README.md", """# modelli — protocolli, training e risultati

Il programma operativo è [R-LEAD](../../docs/piani/strategia-scientifica.md); gli input
cellulari sono indicizzati da [R-LAB](../../docs/piani/piano-giorno-2026-09-30.md).
Il t29 boccia il candidato r2 `desc` con generatore t22 (CP-0055), non tutte le reti.
Esito tecnico, segnale esplorativo e promozione scientifica sono distinti.

Prima di riusare cellnet leggere [NOTA_TRAINING](../analisi/lead_audit_2026-10-01/NOTA_TRAINING.md)
e [AGGIORNAMENTO_R3](../analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md).
Le comparazioni r2/r3 hanno split differenti; il collasso identity r3 non spiega da solo t29.
K562 già nel training non vale come contesto neurale nuovo; H1 train/val è nel corpus.

Le prove E1/E2, scambio di contesto e curve dei primi 50–100 passi appartengono ai
modelli del 27–28/09 sotto indicizzati. Non descrivono indistintamente le reti cellulari.
La rete sulle sorgenti e Stack hanno [esiti propri](../analisi/lead_scientist_2026-09-29/README.md#rete-sulle-sorgenti),
CP-0049 e CP-0051. [Indice generale](../README.md).

""" + "\n".join(lines) + "\n")

    replace("reports/sorgenti/README.md", "- **Quali sorgenti sono davvero entrate in un modello**, e quali sono pronte ma mai usate (per\n  esempio diciannove linee HIPSCI): [copertura del training](../analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md), 29/09.", "- **Uso nel training:** la [copertura del 29/09](../analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md)\n  riguarda i modelli di allora. HIPSCI e H1 train/val sono entrate nei training cellulari\n  successivi, indicizzati da [R-LAB](../../docs/piani/piano-giorno-2026-09-30.md).\n  Verificare i manifest e i ruoli dopo QC per ciascun checkpoint; H1 test resta riserva chiusa.")
    old = read("reports/sorgenti/README.md")
    lines = old.splitlines()
    for i, line in enumerate(lines):
        if "](corpus_cellulare_2026-09-30/)" in line:
            lines[i] = "| 30/09–01/10 | [corpus_cellulare_2026-09-30/](corpus_cellulare_2026-09-30/) | Inventari successivi, contratto degli shard, QC, adattatori e job; corpus usato nei training cellulari r1–r3 | dati e implementazione con manifest per versione; le vecchie code Colab non descrivono lo stato corrente. Disponibilità sulla macchina destinataria da verificare | ★★★ |"
    write("reports/sorgenti/README.md", "\n".join(lines) + "\n")

    replace("docs/PROCEDURE.md", "Tutto il codice che non compare qui è archiviato ([ARCHIVIO.md](ARCHIVIO.md)). Se ti serve,\nriprendilo dal tag: non riscriverlo.", "Questa pagina elenca la pipeline di produzione. Il codice di ricerca resta nelle cartelle\ndei [report](../reports/README.md#il-codice-di-ricerca-che-sta-qui), con copie congelate per\nesperimento; il codice ritirato si recupera tramite [ARCHIVIO](ARCHIVIO.md).")
    replace("docs/PROCEDURE.md", "È il percorso del t08, del t10 e del t11. Cambiano solo la ricetta e la cache delle sorgenti.", "Il percorso si ricostruisce dai manifest del riferimento scelto: ricetta, cache, effetti,\ngeneratore, scala e seed sono tutti parte del candidato. R-LEAD distingue replica t22,\nstimatore corretto t25 e variante di emissione t28; il numero più recente non è il default.")
    old = read("docs/PROCEDURE.md")
    a, b = old.index("I comandi, con i percorsi usati per il t11:"), old.index("I manifest di ogni stadio")
    write("docs/PROCEDURE.md", old[:a] + """Prima di generare scegliere una destinazione nuova e registrare i parametri nel protocollo.
Questi sono i punti d'ingresso per controllare gli argomenti correnti:

```powershell
.\\scripts\\py.cmd scripts\\100_build_context_effects.py --help
.\\scripts\\py.cmd scripts\\45_generate_prediction.py --help
.\\scripts\\py.cmd scripts\\48_package_prediction.py --help
```

Preparare poi un comando esplicito con `--recipe`, `--cache` e un `--out` nuovo per 100;
`--run-id` nuovo, `--trial trial-ext-profile`, effetti per contesto e opzioni congelate
per 45; file realmente prodotto e altro `--run-id` nuovo per 48. Per un export neurale
documentare il percorso che sostituisce 100. Il pacchetto da inviare è quello dichiarato
dal manifest di 48, non un percorso copiato da un esempio vecchio. Invio e lettura: §2.

Gli esempi t11 precedenti sono nello [storico](storico/rinnovo_2026-10-01/docs/PROCEDURE.md);
contengono destinazioni occupate e non vanno eseguiti come un nuovo trial.

""" + old[b:])
    replace("docs/PROCEDURE.md", "Ancore dagli status ufficiali; punteggio atteso di un braccio di banco", "Diagnostica storica di ancore aggregate e previsione approssimata; non score ufficiale né criterio di promozione")
    replace("docs/PROCEDURE.md", "Lo stadio 84 vale per la famiglia di modelli su cui è stato tarato, non per una famiglia\nnuova ([CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)).", "Gli stadi 82/84 conservano un metodo storico approssimato: CP-0050 smentisce la conversione\nesatta dei grezzi aggregati, anche entro la famiglia originaria. Leggere [R-022](REGISTRO.md#r-022--ancore-aggregate-e-indipendenza-della-conferma).\nPer il risultato ufficiale usare i sei scalati pubblicati; per nuovi banchi vale R-LEAD P4.")
    replace("scripts/CLAUDE.md", "official scale    82 anchors from official statuses · 84 expected official score of a bench arm", "historical fit    82 aggregate anchors · 84 approximate prediction (CP-0050: not an exact official scale)")
    replace("configs/CLAUDE.md", "the latest recipe is the best example.", "use the declared reference recipe and its generation manifests as the example; the newest\n  recipe is not necessarily adopted, and does not specify every stage-45 option.")
    replace("scripts/84_predict_official.py", '"""Stage 84: predict a submission\'s official score from a bench arm, and register it first.', '"""Stage 84: historical approximate prediction from a bench arm.\n\nCP-0050 / registry R-022: aggregate anchors do not exactly recover official scaled\nscores. Preserve this diagnostic for historical replay; do not use its output as\nan official score or as the promotion rule for a new model.')
    replace("scripts/84_predict_official.py", "3. the official anchors solved by stage 82, which turn a raw value into the scaled score.", "3. the aggregate affine fit from stage 82 (an approximation, not identified context anchors).")
    replace("docs/checkpoints/INDICE.md", "Il prossimo checkpoint nuovo è il 0041.", "Questa nota riguarda il recupero storico; il prossimo numero si ricava dall'indice corrente.")
    replace(".gitignore", "# Personal Claude Code permissions\n.claude/settings.local.json", "# Personal Claude Code configuration and workflow; not project handoff material\n.claude/")


if __name__ == "__main__":
    main()
