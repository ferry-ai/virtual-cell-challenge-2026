"""The catalogue of the cell-level corpus (R-LAB, priority 3 of the handoff of 30/09): one row per dataset with modality,
cells, matrix format, adapter, state and the reason for every exclusion; the sources available only as aggregates
declared apart.

Measured columns come from the remote inventory (p1_r4/remote/*.json: format, shape, integer counts, labels) and from
the jobs (complete.json on Drive, publication receipts); the state and the reasons are written below by hand, each with
the evidence it rests on. Nothing is read from memory: a dataset whose file was not measured says so.

    python catalogo.py --out catalogo_r1          (refuses an existing folder)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REMOTE = HERE / "p1_r4" / "remote"
REMOTE_LATER = [HERE / "p1_r5" / "remote_kolf"]          # measured again with the corrected reader (1/10)

# state of the ingested datasets (1/10, 02:10): cells from complete.json of each job (Drive), publication from the
# receipts, admission from the prepass r3 of reports/modelli/cellnet_tecnico_2026-10-01
INGESTED = {
    "hepg2_nadig": ("J01 (job 086), pubblicato come rlab-hepg2-nadig", 145473,
                    "nei due training, come contesto tenuto fuori (classi C e J)"),
    "jurkat_nadig": ("J05 (job 103), rlab-jurkat-nadig", 262956, "nei due training"),
    "h1_vcc2025_trainval": ("J04 (job 108), rlab-h1-vcc2025-trainval", 320200,
                            "nei due training, train e validation letti come un esperimento: 38.176 controlli sono gli "
                            "stessi nei due file e contano una volta (il test è la riserva)"),
    "hipsci_targeted_19": ("J02 (job 088), rlab-hipsci-targeted19", 1161865,
                           "nei due training (526.843 cellule senza guida assegnata restano fuori dalla supervisione)"),
    "hipsci_gw_fitness": ("J02 (job 088), rlab-hipsci-gwfit", 322746,
                          "fuori dal training: 36 NTC in tutto, da 1 a 5 per linea, sotto il minimo di 30 per chiave; "
                          "rientra solo con controlli dichiarati (le cellule non assegnate come controlli chiedono prima "
                          "un'analisi)"),
    "hipsci_gw_nonfitness": ("J02 (job 088), rlab-hipsci-gwnonfit", 396458,
                             "fuori dal training: 12 NTC in tutto, come per il fitness"),
    "replogle_k562_gwps": ("J06 r2 (job 115), rlab-k562-gwps-r2", 1989578,
                           "nel secondo training; il dataset del 30/09, rlab-k562-gwps, ha codici al posto dei bersagli "
                           "(E-20260930-003) e non entra in nessun training"),
    "replogle_k562_essential": ("J07 r7 (job 114), rlab-k562-essential", 310385, "nel secondo training"),
    "replogle_rpe1": ("J07 r7 (job 114), rlab-rpe1", 247914, "nel secondo training"),
    "jurkat_gse249595": ("J03 (job 087), rlab-jurkat-gse249595", None,
                         "fuori: nessuna chiamata delle guide nel rilascio; si supervisiona dopo un'assegnazione provata"),
}

# scPerturb copies of experiments ingested from their original releases: declared republications, not a second copy
REPUBLISHED = {
    "scp_NadigOConner2024_hepg2": "hepg2_nadig", "scp_NadigOConner2024_jurkat": "jurkat_nadig",
    "scp_ReplogleWeissman2022_K562_essential": "replogle_k562_essential",
    "scp_ReplogleWeissman2022_K562_gwps": "replogle_k562_gwps", "scp_ReplogleWeissman2022_rpe1": "replogle_rpe1",
}

AGGREGATE_ONLY = [
    ("dld1_gse337988", "DLD-1, GSE337988", "effetti (LFC e SE su un pannello di risposte)", "file per cellula da verificare"),
    ("mixscale (parte DE)", "Mixscale, Zenodo 14518762", "espressione differenziale per linea e stimolo",
     "le cellule esistono come oggetti Seurat (IFNG, IFNB, INS, TGFB, TNFA): servono R e un adattatore"),
    ("southard_*_mean_pop", "Southard 2025, medie per popolazione", "medie con p e p aggiustati (matrici dense non intere)",
     "le cellule sono nei file final_pop dello stesso studio"),
    ("depmap_24q4", "DepMap 24Q4", "bulk basale (espressione e dipendenza)", "covariate ausiliarie, mai supervisione"),
    ("catalogo_accessioni", "77 accessioni del catalogo del 26/09", "solo menzioni", "da riconciliare una per una"),
]


def row_for(d: dict) -> dict:
    x = d.get("X") or {}
    obs = d["obs"]["describe"] if isinstance(d.get("obs"), dict) and "describe" in d["obs"] else {}
    pt = (obs.get("perturbation_type") or {}).get("top") or {}
    return {"id": d["id"], "bytes": d.get("bytes"), "format": x.get("format"), "cells": (x.get("shape") or [None])[0],
            "features": (x.get("shape") or [None, None])[1],
            "integer": x.get("sample_integer", x.get("first_rows_integer")),
            "layers": {k: (v or {}).get("format") for k, v in (d.get("layers") or {}).items()},
            "layer_integer": {k: (v or {}).get("sample_integer", (v or {}).get("first_rows_integer"))
                              for k, v in (d.get("layers") or {}).items()},
            "perturbation_type": pt, "error": d.get("error")}


def classify(r: dict) -> tuple[str, str, str]:
    """(modality, adapter, state with the reason) of one measured remote file."""
    i, pt = r["id"], r["perturbation_type"]
    kinds = set(pt)
    modality = ", ".join(sorted(kinds)) or {"cd4": "CRISPRi", "h1": "CRISPRi", "a549": "KO (Cas9)",
                                            "southard": "CRISPRa", "kolf": "CRISPRi"}.get(i.split("_")[0], "da leggere")
    if r["error"]:
        return modality, "h5rows (a intervalli)", ("da rimisurare: misura fallita con il lettore del 30/09 "
                                                   f"({r['error'][:40]}); lettore corretto il 1/10")
    if i in REPUBLISHED:
        return modality, "—", f"fuori: ripubblicazione scPerturb di {REPUBLISHED[i]}, ingerito dal rilascio originale"
    if r["features"] is not None and r["features"] <= 30:
        return "proteine (ADT)", "—", ("fuori dalla supervisione RNA: matrice di proteine di superficie "
                                       f"({r['features']} feature), altro saggio; vista ausiliaria possibile")
    if i.startswith("h1_"):
        return modality, "h5rows", "ingerito (J04)"
    if "mean_pop" in i:
        return modality, "—", "solo aggregati: medie per popolazione (vedi sorgenti solo aggregate)"
    counts_layer = next((k for k in ("counts", "raw_counts") if k in r["layers"] and r["layer_integer"].get(k)), None)
    if r["integer"] is not True and counts_layer:
        fmt = r["layers"][counts_layer]
        adapter = f"h5rows, layer {counts_layer}" if fmt in ("csr_matrix", "dense") else f"CSC da scrivere, layer {counts_layer}"
        return modality, adapter, f"da ingerire: X non è di conteggi, i conteggi interi sono nel layer {counts_layer}"
    if r["integer"] is False:
        return modality, "—", "fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi"
    if kinds and kinds <= {"drug", "cytokines", "cytokine"}:
        return modality, "h5rows" if r["format"] in ("csr_matrix", "dense") else "CSC da scrivere", \
            "da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario)"
    if r["format"] == "csc_matrix":
        return modality, "CSC da scrivere", "da ingerire: serve l'adattatore per matrici ordinate per gene"
    return modality, "h5rows", "da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP)"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    out = HERE / a.out if not a.out.is_absolute() else a.out
    if out.exists():
        sys.exit(f"refusing: {out} exists")
    out.mkdir(parents=True)
    later = {f.name: f for d in REMOTE_LATER for f in d.glob("*.json") if f.name != "index.json"}
    rows = []
    for f in sorted(REMOTE.glob("*.json")):
        if f.name == "index.json":
            continue
        f = later.get(f.name, f)
        r = row_for(json.loads(f.read_text(encoding="utf-8")))
        r["modality"], r["adapter"], r["state"] = classify(r)
        r["evidence"] = f.relative_to(HERE).as_posix()
        rows.append(r)
    ingested = [{"id": k, "job": v[0], "cells": v[1], "state": v[2]} for k, v in INGESTED.items()]
    (out / "catalogo.json").write_text(json.dumps({"remote": rows, "ingested": ingested,
                                                   "aggregate_only": AGGREGATE_ONLY}, indent=1), encoding="utf-8")
    lines = ["# Catalogo del corpus cellulare (R-LAB)", "",
             "Generato da `catalogo.py` il 1/10 dalle misure remote (`p1_r4/remote/`), dai `complete.json` dei job e "
             "dalle ricevute di pubblicazione. Stato: **misurato** dove c'è un file di prova, **scritto a mano con la "
             "sua evidenza** negli altri casi. Le cellule che entrano davvero nel training (dopo QC e identità) sono nel "
             "pre-passo di [cellnet_tecnico_2026-10-01](../../../modelli/cellnet_tecnico_2026-10-01/README.md).", "",
             "## 1. Ingeriti (shard nel contratto, su Drive e su Kaggle)", "",
             "| Dataset | Job e dataset Kaggle | Cellule | Stato |", "|---|---|---|---|"]
    for r in ingested:
        lines.append(f"| {r['id']} | {r['job']} | {r['cells'] if r['cells'] else 'n.d.'} | {r['state']} |")
    tot = sum(r["cells"] for r in ingested if r["cells"] and "nei due training" in r["state"])
    tot2 = tot + sum(r["cells"] for r in ingested if r["cells"] and r["state"].startswith("nel secondo training"))
    lines += ["", f"Nel primo training: **{tot:,} cellule** prima di QC e identità; nel secondo **{tot2:,}**. Le "
              "cellule di training ammesse e quelle viste stanno nel pre-passo e nella copertura di ciascun "
              "training.".replace(",", "."), "",
              "## 2. Misurati in remoto, non ancora ingeriti", "",
              "| File | Modalità | Cellule | Formato | Adattatore | Stato e motivo |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['modality']} | {r['cells'] if r['cells'] else '—'} | {r['format'] or '—'} | "
                     f"{r['adapter']} | {r['state']} |")
    counts = {}
    for r in rows:
        key = r["state"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    lines += ["", "Per stato: " + "; ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + ".", "",
              "## 3. Sorgenti solo aggregate (dichiarate a parte)", "",
              "| Sorgente | Studio | Che cosa c'è | Nota |", "|---|---|---|---|"]
    for s in AGGREGATE_ONLY:
        lines.append("| " + " | ".join(s) + " |")
    lines += ["", "## 4. Sorgenti note senza misura remota", "",
              "Orion (HCT116, HEK293T: parquet su Hugging Face, licenza non commerciale), Tahoe-100M (parquet; farmaci, "
              "con la cautela del proprietario), VIPerturb-seq (RDS prefiltrato: serve R), microglia GSE335887 e "
              "PerturbFate GSE291147 (non acquisiti), scBaseCount (a pagamento per chi legge): i loro dati per cellula "
              "esistono ma serve un lettore o un via, come scritto in `sources.yaml`.", ""]
    (out / "CATALOGO.md").write_text("\n".join(lines), encoding="utf-8")
    print(out / "CATALOGO.md", len(rows), "remote files", tot, tot2, "cells in the two trainings")


if __name__ == "__main__":
    main()
