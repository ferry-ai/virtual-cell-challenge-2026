"""Rebuild only the registry from its original committed bytes plus reviewed rows."""
import hashlib,json,runpy,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]
p=R/'docs/REGISTRO.md'
original=subprocess.run(['git','show','HEAD:docs/REGISTRO.md'],cwd=R,capture_output=True,check=True).stdout
original.decode('utf-8');p.write_bytes(original)
module=runpy.run_path(str(Path(__file__).with_name('finalize_docs.py')),run_name='registry_only')
module['main'].__globals__['edit']=lambda *args:None
module['main']()
proof={'original_head_sha256':hashlib.sha256(original).hexdigest(),'corrected_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'original registry plus explicit reviewed state rows; encoding UTF-8'}
Path(__file__).with_name('registry_repair.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
