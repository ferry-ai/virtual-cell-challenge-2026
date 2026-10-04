"""Builds the Kaggle code dataset of the t35 bench: code.zip (bench, route C bench, slide, src/vcc2026), its
code_manifest.json (sha256 per file and the repo commit), the cell_eval2 wheel and the per-line magnitudes.

Usage: python pacchetto_kaggle.py --out <data root>/kaggle/banco_t35_code --obiettivi <dir> --wheel <whl> --commit <sha>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FILES = {
    "banco_t35.py": "reports/generatore_e_banchi/banco_t35_2026-10-04/banco_t35.py",
    "banco_tipo.py": "reports/trasferimento/strada_c_banco_2026-10-03/banco_tipo.py",
    "arms.py": "reports/trasferimento/strada_c_banco_2026-10-03/arms.py",
    "genera_l1.py": "reports/modelli/rete_l1_2026-10-04/genera_l1.py",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--obiettivi", type=Path, required=True)
    ap.add_argument("--wheel", type=Path, required=True)
    ap.add_argument("--commit", required=True)
    a = ap.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise SystemExit(f"{a.out} is not empty")
    a.out.mkdir(parents=True, exist_ok=True)
    entries = dict(FILES)
    for p in sorted((REPO / "src" / "vcc2026").glob("*.py")):
        entries[f"src/vcc2026/{p.name}"] = str(p.relative_to(REPO)).replace("\\", "/")
    man = {"repo_commit": a.commit, "files": {}}
    with zipfile.ZipFile(a.out / "code.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for arc, rel in entries.items():
            data = (REPO / rel).read_bytes()
            z.writestr(arc, data)
            man["files"][arc] = hashlib.sha256(data).hexdigest()
    (a.out / "code_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    shutil.copy2(a.wheel, a.out / a.wheel.name)
    dst = a.out / "obiettivi"
    dst.mkdir()
    for p in sorted(a.obiettivi.glob("obiettivi_*.npz")) + [a.obiettivi / "obiettivi.json"]:
        shutil.copy2(p, dst / p.name)
    (a.out / "dataset-metadata.json").write_text(json.dumps(
        {"title": "banco t35 code", "id": "alfredo2003bit/banco-t35-code", "licenses": [{"name": "CC0-1.0"}]},
        indent=1), encoding="utf-8")
    print(f"{len(entries)} code files; {len(list(dst.iterdir()))} objective files -> {a.out}")


if __name__ == "__main__":
    main()
