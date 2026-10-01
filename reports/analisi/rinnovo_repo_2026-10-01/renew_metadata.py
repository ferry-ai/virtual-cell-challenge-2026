"""Register the renewal and reconcile source/index lifecycle metadata."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8-sig")


def write(name, text):
    (ROOT / name).write_text(text, encoding="utf-8", newline="\n")


def main():
    name = "docs/REGISTRO.md"
    text = read(name)
    a, b = text.index("Aggiornato il 2026-09-30 sera"), text.index("## Stati")
    text = text[:a] + """Il rinnovo richiesto il 1 ottobre e completato nelle verifiche del 2 ottobre riallinea
le guide a t29: R-LEAD è il piano operativo unico; le code datate restano evidenza storica.
Le revisioni aperte sotto conservano numeri e ancore. La cronologia del registro si recupera
in Git; [rapporto del rinnovo](../reports/analisi/rinnovo_repo_2026-10-01/README.md).

""" + text[b:]
    notes = {
        "docs/CONSEGNA_TEAMMATE.md": "Addendum portabile: Git, runtime, input esterni e accessi sulla macchina del teammate. Strategia e sequenza soltanto in R-LEAD; t29 concluso",
        "docs/PROMPT_CLAUDE_TEAMMATE.md": "Rimando al prompt unico PROMPT_CLAUDE.md con addendum per macchina esterna; vecchio prompt integrale nello storico del rinnovo",
        "docs/piani/strategia-scientifica.md": "R-LEAD: unico piano implementativo P0–P6 dopo t29, da prendere in carico da Claude. Manifest di esposizione, diagnosi/export, correzioni con test, banco a sei membri, estensioni condizionate e finale. Non eseguito dal rinnovo",
        "docs/piani/piano-giorno-2026-09-30.md": "R-LAB: inventario corrente di corpus, codice e r1–r3; in attesa del nuovo protocollo R-LEAD per un training. Quarto training storico non in coda automatica; cronologia conservata nello storico",
        "docs/piani/": "Schede correnti e guida: R-LEAD unico percorso eseguibile; R-COMP scopo, R-LAB mezzi, R-REV/S-INVII requisiti; R-DATI/R-SWITCH/R-V2 in attesa di una motivazione. R-MODELLI chiusa dal 30/09. Versioni precedenti nel rinnovo storico, agenti confermati fermi dal proprietario",
        "reports/sorgenti/corpus_cellulare_2026-09-30/": "Inventari successivi, contratti, QC, shard, adattatori e job; sorgenti usate nei training cellulari r1–r3. Le vecchie code Colab sono fotografie datate; catalogo, presenza e uso dopo QC sono distinti. Leggere README e manifest della versione effettiva, disponibilità sul destinatario da verificare",
        "reports/modelli/cellnet_terza_ondata_2026-10-01/": "Protocollo tecnico del quarto training, terza ondata e floor pi. Nessun esito registrato; il prossimo job si decide tramite R-LEAD dopo t29, non automaticamente alla riapertura della quota. Non contiene il banco a sei membri richiesto per un altro invio neurale",
        "reports/modelli/cellnet_completo_2026-10-01/": "R3: protocollo, lanci ed ESITO.md con misure tecniche/esplorative; identity collassato, diagnosi AGGIORNAMENTO_R3 nell'audit del 1/10. Split diversi da r2; nessuna promozione scientifica",
        "reports/modelli/cellnet_esteso_2026-10-01/": "R2: training e parte tecnica misurati, ESITO.md e ricevute; braccio desc usato in t29, non promosso (CP-0055). Correzioni del disegno in NOTA_TRAINING; non confondere il completamento con il successo competitivo",
        "reports/modelli/cellnet_tecnico_2026-10-01/": "R1: primo training reale, protocollo/lanci/esiti conservati. ESITO.md: parte A non interamente passata, incidente E-20261001-001. Misura tecnica, nessuna promozione",
        "reports/modelli/risposta_biologica_2026-09-30/": "Codice originale cellnet, prepass, descrittori, export e registri usati dai training r1–r3; non più solo una miniatura. H1 train/val ammesse al fit, test riserva chiusa. Diagnosi in lead_audit_2026-10-01: split, controlli, pesi, baseline e gate; nuove correzioni in copie distinte, nessuna promozione implicita",
    }
    lines = text.splitlines()
    for key, note in notes.items():
        matches = [i for i, line in enumerate(lines) if line.startswith(f"| `{key}` |")]
        if len(matches) != 1:
            raise ValueError((key, matches))
        i = matches[0]
        cells = lines[i].split("|")
        cells[4] = f" {note} "
        lines[i] = "|".join(cells)
    first = next(i for i, line in enumerate(lines) if line.startswith("| `docs/CONSEGNA_TEAMMATE.md`"))
    additions = [
        "| `docs/PROMPT_CLAUDE.md` | attuale | — | Prompt unico per implementare R-LEAD dopo t29; richiama piano, prima consegna, limiti delle evidenze e autorizzazioni della sessione | — |",
        "| `docs/storico/rinnovo_2026-10-01/` | storico | `docs/PIANI.md`, `docs/piani/strategia-scientifica.md` | Copie di 18 documenti prima del rinnovo, prose invariate salvo link relativi e fine riga; manifest con hash e commit 3de6cd0. Nessuna coda o assegnazione vigente si ricava dalle copie | — |",
        "| `reports/analisi/rinnovo_repo_2026-10-01/` | attuale | — | Rinnovo richiesto dal proprietario dopo t29: inventario dei depistaggi corretti, script applicati, snapshot/hash e verifiche. Nessun nuovo risultato biologico o training | — |",
    ]
    lines[first:first] = additions
    write(name, "\n".join(lines) + "\n")

    name = "docs/DECISIONI.md"
    text = read(name)
    row = "| D-051 | Un solo piano implementativo R-LEAD dopo t29; mappe correnti riscritte, code e incarichi datati nello storico recuperabile. R-COMP/R-LAB sono scopo e inventario, le alternative hanno dipendenze esplicite | attiva | 2026-10-01 | Richiesta del proprietario di rinnovare la repo e preparare il piano per Claude; `reports/analisi/rinnovo_repo_2026-10-01/README.md` |\n"
    text = text.replace("| D-050 |", row + "| D-050 |", 1)
    section = """### D-051 — Una sola sequenza operativa dopo t29

- **Mandato:** il 1 ottobre il proprietario chiede un rinnovo della repo per togliere i
  depistaggi e un piano implementativo da affidare a Claude; conferma gli agenti fermi.
- **Decisione:** R-LEAD contiene P0–P6 e i criteri di avanzamento; il prompt lo richiama.
  R-COMP mantiene lo scopo, R-LAB l'inventario; verifiche e alternative non sono programmi
  concorrenti. Le schede lunghe diventano brevi, salvo la specifica implementativa R-LEAD.
- **Conservazione:** 18 versioni precedenti nello storico con hash; tag locale
  `archivio/pre-rinnovo-2026-10-01` su `3de6cd0`. Evidenze, protocolli, dati e pesi invariati.
- **Limite:** è una correzione della navigazione, non una validazione della rete né una
  nuova autorizzazione a job, download, invii o push. Le soglie congelate restano invariate.
- **Si riapre:** quando un risultato o una nuova istruzione cambia le dipendenze; aggiornare
  la scheda canonica, non aggiungere un piano parallelo in un prompt o in un report.
- **Verifiche:** [rapporto del rinnovo](../reports/analisi/rinnovo_repo_2026-10-01/README.md).

"""
    text = text.replace("### D-050 —", section + "### D-050 —", 1)
    text = text.replace("Le misure si confrontano con le ancore ufficiali risolte, e non si sottomette senza sapere in quale regime della fedeltà siamo | attiva", "Le misure si confrontano con lo scorer e il regime della fedeltà; CP-0050 limita l'uso delle ancore aggregate, che non identificano la scala ufficiale per contesto | attiva", 1)
    write(name, text)

    name = "docs/ARCHIVIO.md"
    text = read(name) + """

## 1–2 ottobre 2026 — rinnovo delle guide dopo t29

Il tag annotato **locale** `archivio/pre-rinnovo-2026-10-01` conserva `3de6cd0`, prima del
rinnovo D-051. Nessun file di codice o evidenza è rimosso dall'albero; le guide correnti
sono riscritte, con le versioni precedenti in [docs/storico/rinnovo_2026-10-01](storico/rinnovo_2026-10-01/INDICE.md).
Il manifest elenca ogni originale, copia e hash. Non si esegue `git rm`: nessun percorso
originale lascia l'albero. I file pesanti, worktree e protocolli restano dove erano.

| Versione precedente | Dove si recupera | Sede attuale |
|---|---|---|
| README, PROGETTO, PIANI e nove schede | [Indice delle 18 copie](storico/rinnovo_2026-10-01/INDICE.md), una riga per file | Stessi percorsi, con R-LEAD come sequenza unica |
| Consegna e prompt teammate | Copie nello stesso indice | Addendum portabile e rimando a `docs/PROMPT_CLAUDE.md` |
| PROCEDURE e tre indici dei report | Copie nello stesso indice | Stessi percorsi, metadata riallineati agli esiti |

Recupero byte originali, senza modificare il checkout:

```bash
git show archivio/pre-rinnovo-2026-10-01:docs/piani/strategia-scientifica.md
```

[Perimetro, correzioni e verifiche](../reports/analisi/rinnovo_repo_2026-10-01/README.md).
"""
    write(name, text)

    name = "docs/storico/README.md"
    text = read(name).replace("fra l'11 e il 30 settembre", "prima del rinnovo corrente", 1)
    row = "| 01/10 | [rinnovo_2026-10-01/INDICE.md](rinnovo_2026-10-01/INDICE.md) | Diciotto copie pre-rinnovo: piani, mappe, prompt e indici; incarichi e code datati | storico; per agire usare PIANI e R-LEAD correnti |\n"
    text = text.replace("| 30/09 |", row + "| 30/09 |", 1)
    write(name, text)
    name = "reports/analisi/README.md"
    text = read(name)
    row = "| 01–02/10 | [rinnovo_repo_2026-10-01/](rinnovo_repo_2026-10-01/) | Rinnovo post-t29: 18 copie storiche con hash, schede operative ridotte, piano unico P0–P6 per Claude, metadata corretti e verifiche | sì, manutenzione documentale; nessun nuovo training o risultato biologico | ★★ |\n"
    text = text.replace("| 01/10 |", row + "| 01/10 |", 1)
    write(name, text)

    name = "docs/CLAUDE.md"
    text = read(name)
    text = text.replace("| Procedures: submission path", "| Initial implementation prompt | `docs/PROMPT_CLAUDE.md`, pointing to R-LEAD; `docs/CONSEGNA_TEAMMATE.md` only adds portable environment checks | when the entry path changes; do not duplicate the plan in the prompt |\n| Procedures: submission path", 1)
    write(name, text)
    name = "docs/piani/CLAUDE.md"
    text = read(name).replace("## Regole delle schede", "Keep only the current mandate, next step, dependencies and closure in a live card.\nDated execution instructions go to `docs/storico/`, with provenance and registry metadata.\nR-LEAD owns the implementation sequence; other cards and prompts link to it.\n\n## Regole delle schede", 1)
    write(name, text)
    name = "CLAUDE.md"
    text = read(name).replace("On cloud compute two records disagree, and the contradiction is open: card R-V2 (F7)\nnotes Colab and Kaggle as authorised on 27/09, while the mandate of card R-REV (28/09) and PIANI\n§2 ask for it in chat.", "On cloud compute two historical records disagree, and the contradiction is open: R-V2 (F7)\nnotes Colab and Kaggle as authorised on 27/09, while R-REV (28/09) asks for it in chat.\nThose original cards are preserved in `docs/storico/rinnovo_2026-10-01/docs/piani/`.")
    write(name, text)


if __name__ == "__main__":
    main()
