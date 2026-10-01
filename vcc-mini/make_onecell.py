"""Write onecell.py: one Colab cell that carries the code (zip, base64, sha256-checked), mounts
Drive, fetches the chosen tiers and runs the read-only inspection. Paste it into an empty notebook.
"""
import base64
import hashlib
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = ["drive_fetch.py", "build_mini.py", "sources.json", "catalog.json", "data.py", "model.py", "train.py"]

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in FILES:
        z.write(ROOT / f, f)
raw = buf.getvalue()
b64 = base64.b64encode(raw).decode()
sha = hashlib.sha256(raw).hexdigest()
lines = "\n".join(b64[i: i + 100] for i in range(0, len(b64), 100))

cell = f'''# vcc-data: dati pubblici su Google Drive, verificati. Premi Shift+Invio e autorizza Drive.
TIERS = ["mini"]                       # 5 file, 2,69 GB; gli altri tier solo dopo averli decisi
DRIVE_DIR = "/content/drive/MyDrive/vcc-data"

import base64, glob, hashlib, io, os, shutil, time, zipfile
from google.colab import drive
drive.mount("/content/drive")
PAYLOAD = """
{lines}
"""
raw = base64.b64decode("".join(PAYLOAD.split()))
assert hashlib.sha256(raw).hexdigest() == "{sha}", "codice corrotto nel copia-incolla"
zipfile.ZipFile(io.BytesIO(raw)).extractall("/content/vcc-code")
os.makedirs(f"{{DRIVE_DIR}}/code", exist_ok=True)
for f in os.listdir("/content/vcc-code"):
    shutil.copyfile(f"/content/vcc-code/{{f}}", f"{{DRIVE_DIR}}/code/{{f}}")
print("VM libera:", round(shutil.disk_usage("/content").free / 1e9, 1), "GB | Drive libero (dal mount):",
      round(shutil.disk_usage("/content/drive/MyDrive").free / 1e9, 1), "GB")

ip = get_ipython()
ip.system(f'python /content/vcc-code/drive_fetch.py --catalog /content/vcc-code/catalog.json '
          f'--dest "{{DRIVE_DIR}}" --tiers {{" ".join(TIERS)}}')

# Ispezione in sola lettura dei file mini: l'output va incollato a Claude.
os.makedirs("/content/work/raw", exist_ok=True)
for p in glob.glob(f"{{DRIVE_DIR}}/raw/mini/*"):
    shutil.copyfile(p, "/content/work/raw/" + os.path.basename(p))
ip.system("pip -q install anndata")
os.makedirs(f"{{DRIVE_DIR}}/logs", exist_ok=True)
log = f"{{DRIVE_DIR}}/logs/inspect_{{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}}.txt"
ip.system(f'cd /content/vcc-code && VCC_MINI_DATA=/content/work python build_mini.py --inspect 2>&1 | tee "{{log}}"')
drive.flush_and_unmount()
print("FINITO. Ispezione salvata in", log)
'''
(ROOT / "onecell.py").write_text(cell, encoding="utf-8")
print(f"onecell.py: {len(cell) / 1e3:.0f} kB, zip sha256 {sha[:16]}")
