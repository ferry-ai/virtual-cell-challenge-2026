"""Generate colab_drive_loader.ipynb, with the current code files embedded as %%writefile cells.

Rerun after any change to the embedded files: the notebook prints their sha256 in Colab, so
what ran there can be matched to the files here.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EMBED = ["drive_fetch.py", "build_mini.py", "sources.json", "catalog.json", "data.py", "model.py", "train.py"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


def main():
    cat = json.loads((ROOT / "catalog.json").read_text())
    rows = "\n".join(
        f"| `{t}` | {v['files']} | {v['bytes'] / 1e9:.2f} GB | "
        f"{next(e['license'] for e in cat['files'] if e['tier'] == t)} |"
        for t, v in cat["tiers"].items())
    # Hash of the text without trailing newlines: independent of CRLF here and of how %%writefile ends the file.
    text = {f: (ROOT / f).read_text(encoding="utf-8").rstrip("\n") for f in EMBED}
    shas = {f: hashlib.sha256(t.encode()).hexdigest() for f, t in text.items()}
    cells = [md(f"""
# vcc-data: dati pubblici su Google Drive, verificati

Scarica i file del catalogo **dalla macchina Colab** (non dal tuo PC) e li salva in Google Drive,
uno alla volta: download sul disco della VM, controllo di dimensione e checksum, copia su Drive,
nuovo controllo della dimensione, file `.verified.json` accanto a ogni file. Se la sessione cade,
si rilancia la stessa cella: i file giÃ  verificati si saltano.

Catalogo congelato il {cat['frozen_utc']} dalle API di Figshare, Zenodo, Hugging Face e S3.

| tier | file | dimensione | licenza |
|---|---|---|---|
{rows}

**Di default scarica solo `mini`.** Gli altri tier si aggiungono a `TIERS` solo dopo averli decisi:
`cd4` non dichiara una licenza, Orion Ã¨ non commerciale.

Limiti da conoscere: Google Drive accetta circa 750 GB di upload al giorno (lo script si ferma a 700);
il disco della VM deve contenere il file piÃ¹ grande (65,8 GB per `sc_k562_gw`); una sessione Colab
gratuita puÃ² chiudersi dopo alcune ore, e in quel caso si rilancia.
"""),
        code('''
# Impostazioni: l'unica cella da modificare
TIERS = ["mini"]                     # aggiungere: "sc_replogle", "sc_k562_gw", "cd4", "orion_hct116", "orion_hek293t"
DRIVE_DIR = "/content/drive/MyDrive/vcc-data"
LIMIT = 0                            # 0 = tutti i file dei tier scelti; un numero piccolo per una prova
'''),
        code('''
from google.colab import drive
drive.mount("/content/drive")
import json, os, shutil, subprocess
os.makedirs(DRIVE_DIR, exist_ok=True)
gb = lambda b: f"{b / 1e9:.1f} GB"
vm, dr = shutil.disk_usage("/content"), shutil.disk_usage("/content/drive/MyDrive")
print("VM disk free:", gb(vm.free), "| Drive free (as reported by the mount):", gb(dr.free))
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"],
                     capture_output=True, text=True).stdout or "no GPU")
'''),
        md("## Codice\nOgni cella scrive un file in `/content/vcc-code/`. L'ultima ne controlla lo sha256 e li copia anche in `DRIVE_DIR/code/`."),
    ]
    for f in EMBED:
        cells.append(code(f"%%writefile /content/vcc-code/{f}\n" + text[f] + "\n"))
    cells.insert(len(cells) - len(EMBED), code("!mkdir -p /content/vcc-code"))
    cells += [
        code(f'''
import hashlib
EXPECTED = {json.dumps(shas, indent=1)}
for f, want in EXPECTED.items():
    got = hashlib.sha256(open(f"/content/vcc-code/{{f}}", encoding="utf-8").read().rstrip("\\n").encode()).hexdigest()
    assert got == want, (f, got, want)
os.makedirs(f"{{DRIVE_DIR}}/code", exist_ok=True)
for f in EXPECTED:
    shutil.copyfile(f"/content/vcc-code/{{f}}", f"{{DRIVE_DIR}}/code/{{f}}")
print("code verified and copied to", f"{{DRIVE_DIR}}/code")
'''),
        md("## Download verso Drive\nRilanciabile: salta ciÃ² che Ã¨ giÃ  verificato."),
        code('!python /content/vcc-code/drive_fetch.py --catalog /content/vcc-code/catalog.json --dest "{DRIVE_DIR}" --tiers {" ".join(TIERS)} --limit {LIMIT}'),
        md("""
## Ispezione dei file `mini` (sola lettura)

Copia i cinque file sul disco della VM e stampa colonne, etichette e un campione dei conteggi.
Non costruisce nulla: l'output serve a correggere `SPEC` in `build_mini.py` (punto P6 della revisione).
Il testo finisce anche in `DRIVE_DIR/logs/`.
"""),
        code('''
import glob, time
os.makedirs("/content/work/raw", exist_ok=True)
for p in glob.glob(f"{DRIVE_DIR}/raw/mini/*"):
    shutil.copyfile(p, "/content/work/raw/" + os.path.basename(p))
!pip -q install anndata
stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
!cd /content/vcc-code && VCC_MINI_DATA=/content/work python build_mini.py --inspect 2>&1 | tee "{DRIVE_DIR}/logs/inspect_{stamp}.txt"
'''),
        md("""
## Costruzione del dataset (spenta)

Da accendere solo dopo aver controllato l'ispezione e corretto `SPEC`. Scrive in una cartella
nuova su Drive, `mini_<data>`, senza sovrascrivere quelle precedenti.
"""),
        code('''
BUILD = False
if BUILD:
    !cd /content/vcc-code && VCC_MINI_DATA=/content/work python build_mini.py
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    shutil.copytree("/content/work/mini", f"{DRIVE_DIR}/mini_{stamp}")
    print("written", f"{DRIVE_DIR}/mini_{stamp}")
'''),
        code('drive.flush_and_unmount()  # scrive su Drive tutto ciÃ² che Ã¨ ancora in coda'),
    ]
    nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                                       "kernelspec": {"display_name": "Python 3", "name": "python3"}},
          "nbformat": 4, "nbformat_minor": 0}
    out = ROOT / "colab_drive_loader.ipynb"
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print("written", out, f"{out.stat().st_size / 1e3:.0f} kB,", len(cells), "cells")
    for f, s in shas.items():
        print(f"  {f:16s} {s[:16]}")


if __name__ == "__main__":
    main()
