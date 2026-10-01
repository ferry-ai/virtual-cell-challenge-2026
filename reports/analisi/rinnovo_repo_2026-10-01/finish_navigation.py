"""Give the snapshot its own index without replacing the original root README."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "snapshot_manifest.json").read_text(encoding="utf-8"))
lines = [
    "# Guide prima del rinnovo post-t29", "",
    "**Storico, non istruzioni correnti.** Queste sono le 18 versioni del commit `3de6cd0`,",
    "conservate prima del rinnovo richiesto il 1 ottobre 2026. Per lavorare usare",
    "[PIANI corrente](../../PIANI.md) e [R-LEAD corrente](../../piani/strategia-scientifica.md).", "",
    "Testo invariato salvo link relativi e fine riga; gli originali Git sono anche nel tag",
    "locale `archivio/pre-rinnovo-2026-10-01`. I collegamenti fra due guide copiate restano",
    "nella fotografia storica. [Manifest e hash](../../../reports/analisi/rinnovo_repo_2026-10-01/snapshot_manifest.json).", "",
    "| Originale | Copia storica |", "|---|---|",
]
for row in manifest["files"]:
    local = row["snapshot"].split("docs/storico/rinnovo_2026-10-01/", 1)[1]
    lines.append(f"| `{row['source']}` | [Testo precedente]({local}) |")
(ROOT / "docs/storico/rinnovo_2026-10-01/INDICE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

files = [ROOT / "README.md", *list((ROOT / "docs").glob("*.md")), HERE / "README.md", HERE / "renew_indexes.py", HERE / "renew_metadata.py"]
for file in files:
    original = file.read_text(encoding="utf-8-sig")
    text = original.replace("rinnovo_2026-10-01/README.md", "rinnovo_2026-10-01/INDICE.md")
    if text != original:
        file.write_text(text, encoding="utf-8", newline="\n")
for name in ("docs/piani/revisione-critica.md", "reports/analisi/rinnovo_repo_2026-10-01/renew_navigation.py"):
    file = ROOT / name
    text = file.read_text(encoding="utf-8").replace("#7-il-set-finale-il-22-ottobre", "#7-il-set-finale-22-ottobre")
    file.write_text(text, encoding="utf-8", newline="\n")
