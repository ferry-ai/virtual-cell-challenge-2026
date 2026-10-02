"""Which local copies could be deleted, how many GiB that frees, and the proof of the remote copy.

A local file is "proven remote" when an independent environment read a remote copy with the same sha256:
the Colab verification of the Drive mirror (verify_receipts.jsonl of job 130/131, status "verified") or the
Kaggle-side kernel (compare_full.json, status "match"). A group (two path levels) is proposed for deletion only
when every file in it is proven remote and the group is not an active dependency. Freed bytes count each
physical file once and only when all its hard links are in deletable groups. Nothing is deleted here.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Active local dependencies (2-3 October 2026): what running work or the submission path reads from the laptop.
ACTIVE = {
    "processed/universe_": "R-LEAD (sessione 22d21f) legge tutti gli universi; produzione D/E/F: stadio 106, preset me1",
    "processed/multisource_2026-09-27_r9": "R-LEAD; cache delle ricette t25 e t28",
    "processed/multisource_2026-09-23_r5": "cache della ricetta di riferimento t22",
    "processed/generalizzazione_contesti_2026-10-02": "R-LEAD, cartella attiva",
    "processed/basal_sources_2026-09-28.csv": "R-LEAD (cubo del banco)",
    "processed/corpus_basale_2026-09-28": "R-LEAD (cubo del banco)",
    "processed/archivio_cloud_2026-10-02": "stato di questa migrazione",
    "raw/controls/": "produzione e R-LEAD: controlli ufficiali A/B/C e asse genico",
    "raw/nadig_hepg2": "R-LEAD (universo HepG2) e banchi HepG2",
    "external/annotation": "produzione (termini cis) e R-LEAD",
    "external/vcc2025": "R-LEAD (metadati H1)",
    # Named by live stages (dipendenze.py, 3 October): small, they stay so the stages run as documented.
    "external/K562_gwps_raw_bulk_01.h5ad": "codice vivo: scripts/98_multisource_effects.py",
    "external/cd4/": "codice vivo: scripts/97_extract_cd4_rows.py",
    "interim/orion_hct116": "codice vivo: scripts/102_extract_orion_panel.py",
}
SMALL = 100 << 20  # groups below this stay local: small results are part of a light laptop


def group(rel: str) -> str:
    parts = rel.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else rel


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", required=True, type=Path, help="processed/archivio_cloud_2026-10-02/r1")
    p.add_argument("--colab", nargs="*", default=[], type=Path, help="verify_receipts.jsonl files of jobs 130/131")
    p.add_argument("--kaggle", nargs="*", default=[], type=Path, help="compare_full.json of the Kaggle check")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    inv = {r["rel"]: r for r in csv.DictReader((a.run / "local_inventory.tsv").open(encoding="utf-8"), delimiter="\t")
           if not r["rel"].startswith(("ERROR:", "SPECIAL:"))}
    sha = {r["rel"]: r["sha256"] for r in csv.DictReader((a.run / "local_hashes.tsv").open(encoding="utf-8"),
                                                          delimiter="\t") if r["sha256"]}
    proven: dict[str, set[str]] = defaultdict(set)  # sha256 -> proofs
    for f in a.colab:
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("status") == "verified":
                proven[r["sha256"]].add(f"Drive, letto da Colab ({f.parent.name}): data/{r['rel']}")
    for f in a.kaggle:
        for r in json.loads(f.read_text(encoding="utf-8"))["results"]:
            if r.get("status") == "match":
                proven[r["sha256_kaggle"]].add(f"Kaggle, letto sul server: {r['dataset']}/{r['file']}")
    by_group: dict[str, list[str]] = defaultdict(list)
    for rel in inv:
        by_group[group(rel)].append(rel)
    rows = []
    for g, rels in sorted(by_group.items()):
        active = next((why for pre, why in ACTIVE.items() if g.startswith(pre) or (g + "/").startswith(pre)), None)
        ids = {}
        for rel in rels:
            ids.setdefault(inv[rel]["file_id"], int(inv[rel]["bytes"]))
        size = sum(ids.values())
        unproven = [rel for rel in rels if not proven.get(sha.get(rel, ""), set())]
        kinds = sorted({k.split(",")[0] for rel in rels for k in proven.get(sha.get(rel, ""), set())})
        if active:
            status = "tenere: dipendenza attiva"
        elif size < SMALL:
            status = "tenere: piccolo"
        elif unproven:
            status = "in attesa della prova remota"
        else:
            status = "eliminabile col via"
        rows.append({"group": g, "files": len(rels), "unique_bytes": size, "status": status, "why": active,
                     "proof_kinds": kinds, "files_without_proof": len(unproven)})
    deletable = {r["group"] for r in rows if r["status"] == "eliminabile col via"}
    # Freed bytes: a physical file is freed only if all its paths are in deletable groups.
    paths_by_id = defaultdict(list)
    for rel, r in inv.items():
        paths_by_id[r["file_id"]].append(rel)
    freed = defaultdict(int)
    for fid, rels in paths_by_id.items():
        gs = {group(x) for x in rels}
        if gs <= deletable:
            freed[sorted(gs)[0]] += int(inv[rels[0]]["bytes"])
    for r in rows:
        r["freed_bytes_if_deleted"] = freed.get(r["group"], 0) if r["group"] in deletable else 0
    pending = [r for r in rows if r["status"] == "in attesa della prova remota"]
    doc = {"rows": rows, "deletable_GiB": round(sum(r["freed_bytes_if_deleted"] for r in rows) / 2**30, 3),
           "pending_GiB": round(sum(r["unique_bytes"] for r in pending) / 2**30, 3),
           "kept_active_GiB": round(sum(r["unique_bytes"] for r in rows if r["status"] == "tenere: dipendenza attiva") / 2**30, 3),
           "kept_small_GiB": round(sum(r["unique_bytes"] for r in rows if r["status"] == "tenere: piccolo") / 2**30, 3),
           "colab_receipts": [str(x) for x in a.colab], "kaggle_compares": [str(x) for x in a.kaggle]}
    a.out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in doc.items() if k != "rows"}, indent=1))
    for r in rows:
        if r["status"] in ("eliminabile col via", "in attesa della prova remota"):
            print(f"{r['unique_bytes'] / 2**30:8.2f} GiB  {r['status']:30s} {r['group']}  proofs={r['proof_kinds']} "
                  f"without={r['files_without_proof']}")


if __name__ == "__main__":
    main()
