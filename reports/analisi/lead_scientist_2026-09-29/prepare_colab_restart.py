"""Create the r2 development job after the audited NPZ string-dtype repair."""
from pathlib import Path
here = Path(__file__).resolve().parent
text = (here / "colab_generator_r1.sh").read_text(encoding="utf-8").replace("_r1", "_r2")
text = text.replace('tar -xzf "$ARCHIVE"',
                    'echo "634f228e1c358a1f1d4474d59a0dcac2f3a501921d68795ca9acd4b371db1033  $ARCHIVE" | sha256sum -c -\ntar -xzf "$ARCHIVE"')
insert = '''python - "$OUT" <<'PY'
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import json, sys
packages = ['numpy','scipy','pandas','h5py','scanpy','anndata','scikit-learn','polars','pyarrow','PyYAML','numba','cell-eval2']
versions = {}
for package in packages:
    try: versions[package] = version(package)
    except PackageNotFoundError: versions[package] = None
with (Path(sys.argv[1]) / 'development_environment.json').open('x') as handle:
    json.dump({'python': sys.version, 'versions': versions}, handle, indent=2)
PY
'''
needle = 'python -u "$BENCH" --phase run'
text = text.replace(needle, insert + needle)
with (here / "colab_generator_r2.sh").open("x", encoding="utf-8", newline="\n") as handle:
    handle.write(text)
