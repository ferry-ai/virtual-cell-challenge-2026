"""Does stage 102's download() leak committed memory? Downloads the smallest HEK293T file repeatedly."""
import gc
import importlib.util
import sys
from pathlib import Path

REPO = Path(r"C:\Users\ferra\OneDrive\Desktop\vcc2026")
spec = importlib.util.spec_from_file_location("ou", REPO / "reports/universo_2026-09-26/orion_universe.py")
ou = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ou)

files = sorted(ou.stage102.list_files("HEK293T"), key=lambda ps: ps[1])
path, size = files[0]
print("smallest", path, size, flush=True)
dest = Path(sys.argv[1])
print("start", ou.memory(), flush=True)
for i in range(6):
    # force 8 spans on 8 threads, like a large file: chunk = size / 8
    ou.stage102.download(path, size, dest, threads=8, chunk=max(1, size // 8 + 1))
    print(i, "after download", ou.memory(), flush=True)
    gc.collect()
    print(i, "after gc", ou.memory(), flush=True)
    dest.unlink()
