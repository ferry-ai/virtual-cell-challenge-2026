"""Write runcell.py: one Colab cell that runs the whole bench from the data already on Drive.

    tests -> build mini/ (to Drive) -> training as chosen by RUN -> aggregate (full only)

The code travels inside the cell (zip, base64, sha256-checked). Data on Drive are fetched only if
missing (drive_fetch.py skips verified files). Every output goes to a new folder on Drive.
"""
import base64
import hashlib
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ["drive_fetch.py", "build_mini.py", "sources.json", "catalog.json", "data.py", "model.py", "train.py",
         "aggregate.py", "make_synthetic.py", "tests/test_leakage.py", "tests/test_build_format.py"]

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in FILES:
        z.write(ROOT / f, f)
raw = buf.getvalue()
b64 = base64.b64encode(raw).decode()
sha = hashlib.sha256(raw).hexdigest()
lines = "\n".join(b64[i: i + 100] for i in range(0, len(b64), 100))

cell = f'''# vcc-mini su Colab: test, costruzione del dataset, addestramento. Shift+Invio, poi autorizza Drive.
RUN = "smoke"      # "build": solo test e dataset | "smoke": + una prova breve (HepG2, 2 epoche)
                   # "full": + 4 linee tenute fuori x 2 semi sul fold 0, poi aggregate.py
DRIVE_DIR = "/content/drive/MyDrive/vcc-data"

import base64, glob, hashlib, io, os, shutil, time, zipfile
from google.colab import drive
drive.mount("/content/drive")
ip = get_ipython()
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
PAYLOAD = """
{lines}
"""
raw = base64.b64decode("".join(PAYLOAD.split()))
assert hashlib.sha256(raw).hexdigest() == "{sha}", "codice corrotto nel copia-incolla"
shutil.rmtree("/content/vcc-code", ignore_errors=True)
zipfile.ZipFile(io.BytesIO(raw)).extractall("/content/vcc-code")
ip.system('pip -q install anndata "pandas<3"')
ip.system("nvidia-smi --query-gpu=name,memory.total --format=csv || echo 'nessuna GPU: si addestra su CPU'")

print("\\n== 1. dati su Drive (salta i file gia verificati)")
ip.system(f'python /content/vcc-code/drive_fetch.py --catalog /content/vcc-code/catalog.json --dest "{{DRIVE_DIR}}" --tiers mini')
os.makedirs("/content/work/raw", exist_ok=True)
for p in glob.glob(f"{{DRIVE_DIR}}/raw/mini/*"):
    shutil.copyfile(p, "/content/work/raw/" + os.path.basename(p))

print("\\n== 2. test")
ip.system("cd /content/vcc-code && python -m unittest discover -s tests 2>&1 | tail -4")

print("\\n== 3. costruzione di mini/")
shutil.rmtree("/content/work/mini", ignore_errors=True)
ip.system("cd /content/vcc-code && VCC_MINI_DATA=/content/work python build_mini.py 2>&1 | tail -15")
assert os.path.exists("/content/work/mini/manifest.json"), "costruzione fallita: vedi sopra"
shutil.copytree("/content/work/mini", f"{{DRIVE_DIR}}/mini_{{STAMP}}")
print("dataset copiato in", f"{{DRIVE_DIR}}/mini_{{STAMP}}")
ip.system("cat /content/work/mini/lines.csv")

runs = f"{{DRIVE_DIR}}/runs_{{STAMP}}"
train = "cd /content/vcc-code && python train.py --data /content/work/mini"
if RUN == "smoke":
    print("\\n== 4. prova breve: verifica che giri, i numeri non si leggono")
    ip.system(f'{{train}} --held HepG2 --fold 0 --seed 0 --epochs 2 --max-train-pairs 400 --out "{{runs}}/smoke_hepg2"')
elif RUN == "full":
    print("\\n== 4. addestramenti: 4 linee x 2 semi, fold 0")
    for held in ["HepG2", "Jurkat", "RPE1", "K562"]:
        for seed in [0, 1]:
            ip.system(f'{{train}} --held {{held}} --fold 0 --seed {{seed}} --out "{{runs}}/{{held}}_f0_s{{seed}}" 2>&1 | tail -40')
    ip.system(f'cd /content/vcc-code && python aggregate.py "{{runs}}"/*_f0_s* --out "{{runs}}/aggregate.json"')
drive.flush_and_unmount()
print("FINITO", STAMP)
'''
(ROOT / "runcell.py").write_text(cell, encoding="utf-8")
print(f"runcell.py: {len(cell) / 1e3:.0f} kB, zip sha256 {sha[:16]}")
