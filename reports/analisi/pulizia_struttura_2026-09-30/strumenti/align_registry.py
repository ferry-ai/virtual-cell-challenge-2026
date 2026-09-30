"""Align docs/REGISTRO.md with the folder indexes where they plainly disagreed (tappa 3).

Group A: attuale -> storico, where the index calls the entry storico or chiuso, or the entry sits
in reports/storico/, whose index says everything there is a dated photograph, not a guide.
Group B: attuale stays, the note gets the caveat of the index, with its verified source.
Each row is matched by its first cell and must be found exactly once with the expected state.
"""
from pathlib import Path

P = Path(r"C:/Users/ferra/OneDrive/Desktop/vcc2026/docs/REGISTRO.md")
A = [
    "reports/analisi/direzione_2026-09-19/", "reports/generatore_e_banchi/bench_2026-09-17/",
    "reports/generatore_e_banchi/call_budget_2026-09-17/",
    "reports/generatore_e_banchi/call_budget_2026-09-17/c001/",
    "reports/invii/prediction_t19_2026-09-25/", "reports/invii/prediction_t18_2026-09-25/",
    "reports/invii/trial_2026-09-25/", "reports/invii/prediction_t12_2026-09-23/",
    "reports/invii/trial_2026-09-19/", "reports/invii/trial02_decision_2026-09-17/",
    "reports/storico/gpu_2026-09-15/", "reports/storico/runtime_2026-09-15/",
    "reports/storico/eval_protocol_2026-09-15/", "reports/storico/pipeline/",
    "reports/storico/remote_catalog_2026-09-15/", "reports/storico/source_cards_2026-09-15/",
    "reports/storico/jiang_2026-09-15/", "reports/storico/primeflow_2026-09-15/",
    "reports/storico/ricerca_dataset_20260915.md", "reports/storico/candidate_verification/",
    "reports/storico/grok_verification/", "reports/storico/orchestrator/",
    "reports/storico/orchestrator/prova-a-secco-ricerca-2026-09-14/", "reports/storico/oracle/",
    "docs/storico/BENCHMARK_MODULARE.md", "docs/storico/BENCHMARK_TRE_CONTESTI.md",
    "docs/storico/SVD_E_RANGO.md",
]
B = {
    "reports/analisi/analisi_2026-09-24/":
        " **Vale in parte:** il confronto delle precisioni di segno va letto contro il controllo a bersagli "
        "scambiati, perché il 50 % non basta come riferimento (`reports/analisi/audit_stato_2026-09-24/ANALISI.md`, "
        "§1; CP-0034).",
    "reports/analisi/ipotesi_trasferimento_2026-09-24/":
        " **Vale in parte:** H1 (programmi) e H6 (pesi per somiglianza) sono state provate e sono cadute "
        "(`reports/trasferimento/programmi_2026-09-26/`, `reports/trasferimento/contesti_2026-09-26/`); le altre "
        "restano aperte.",
    "reports/gara/context_identity/":
        " **Vale in parte:** la lettura «occhio» di B è un'ipotesi debole (R-001, punto 3).",
    "reports/invii/lezioni_invii_2026-09-28/":
        " **Vale in parte:** l'audit del 29/09 ne corregge il rumore stimato da una sola coppia di semi e il peso "
        "della risposta comune sull'MSE (`reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md`, §2.2 e §2.4).",
    "reports/sorgenti/universo_hipsci_2026-09-27/":
        " **Vale in parte** secondo l'indice di `reports/sorgenti/`: le linee con silenziamento debole vanno trattate "
        "a parte, e gli universi `_ua1`, che usano come controlli anche le cellule senza guida assegnata, possono "
        "tirare gli effetti verso zero (interpretazione).",
    "reports/sorgenti/universo_2026-09-26/":
        " **Vale in parte:** gli universi di CD4 e delle due Orion sono sostituiti da quelli ricostruiti con lo "
        "stimatore corretto (`reports/sorgenti/universo_corretto_2026-09-27/`); K562, K562 essential e RPE1 valgono.",
    "reports/trasferimento/quota_condivisa_2026-09-27/":
        " **Vale in parte:** l'ablazione del t23 attribuisce il guadagno all'esclusione dei geni, non alla quota "
        "(`reports/trasferimento/ablazione_t23_2026-09-27/`).",
}
HEADER_OLD = "Aggiornato il 2026-09-30 con il riordino dell'ingresso degli agenti (D-049):"
HEADER_NEW = ("Aggiornato il 2026-09-30 sera con la pulizia della struttura "
              "(`reports/analisi/pulizia_struttura_2026-09-30/`, §3): 25 voci e due loro righe interne passano "
              "da `attuale` a `storico`, perché l'indice della loro cartella le dà per storiche o chiuse, o perché "
              "stanno in `reports/storico/`; sette voci che l'indice dà per valide in parte hanno la riserva nella "
              "nota. " + HEADER_OLD)

lines = P.read_text(encoding="utf-8").split("\n")
done_a, done_b = set(), set()
for i, line in enumerate(lines):
    if not line.startswith("| `"):
        continue
    cells = line.split("|")
    first = cells[1].strip()
    for path in A:
        if first == f"`{path}`":
            assert cells[2].strip() == "attuale", (path, cells[2])
            cells[2] = " storico "
            lines[i] = "|".join(cells)
            done_a.add(path)
    for path, add in B.items():
        if first == f"`{path}`":
            assert cells[2].strip() == "attuale", (path, cells[2])
            cells[4] = cells[4].rstrip() + add + " "
            lines[i] = "|".join(cells)
            done_b.add(path)
assert done_a == set(A), set(A) - done_a
assert done_b == set(B), set(B) - done_b
text = "\n".join(lines)
assert text.count(HEADER_OLD) == 1
text = text.replace(HEADER_OLD, HEADER_NEW)
P.write_text(text, encoding="utf-8", newline="")
print("storico:", len(done_a), "caveats:", len(done_b))
