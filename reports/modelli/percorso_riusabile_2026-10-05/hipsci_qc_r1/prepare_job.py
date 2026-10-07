"""Self-contained QC job; no models, matrices or raw data are uploaded."""
import ast,base64,hashlib,json,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
S=HERE.parent
stage=HERE/'package';stage.mkdir(exist_ok=False)
source=S/'hipsci_adapter_r3'
p=json.loads((source/'package_r2/params.json').read_text())
p['kind']='diagnostic_own_gene_not_fit_or_selection'
p['diagnostic_policy']=dict(no_auto_admission=True,no_context_exclusion=True,no_weights_changed=True,
    purpose='Quantify own-transcript knockdown on all native labels per clone; not predictive selection',
    historical_p2='two nonempty archive pools; all 19 manifests use pseudo0.5')
(stage/'params.json').write_text(json.dumps(p,indent=1)+'\n')
(HERE/'estimator.py').write_bytes((source/'estimator.py').read_bytes())
files={n:(HERE/n).read_bytes() for n in ('qc.py','runtime.py','estimator.py')}
data=Path('C:/Users/ferra/vcc2026-data/raw/controls')
for n in ('gene_names.csv','pert_counts.csv'):
    b=(data/n).read_bytes()
    assert hashlib.sha256(b).hexdigest()==p['embedded_inputs'][n]['sha256']
    files[n]=b
files['params.json']=(stage/'params.json').read_bytes()
payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in files.items()}
code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
code+='runpy.run_path("runtime.py",run_name="__main__")\n'
ast.parse(code);assert len(code.encode())<900000
(stage/'run.py').write_text(code)
slug='davideferante/vcc-qc-hipsci-targeted19-countsum-r1'
meta=json.loads((source/'package_r2/kernel-metadata.json').read_text())
meta.update(id=slug,title=slug.split('/')[1])
(stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1)+'\n')
def pin(path):return dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
proof=dict(slug=slug,stage=str(stage),code=pin(stage/'run.py'),params=pin(stage/'params.json'),
    input_producer=p['producer'],full_training=False,diagnostic_only=True,automatic_admission=False,
    modules={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in files.items()})
(HERE/'prepared.json').write_text(json.dumps(proof,indent=1)+'\n')
# Copy proven launch/preflight mechanics without mutating previous evidence.
dispatch=(source/'dispatch.py').read_text().replace("'prepared_r2.json'","'prepared.json'")
(HERE/'dispatch.py').write_text(dispatch)
pre=(source/'preflight.py').read_text()
pre=pre.replace("pairs={(owner,ref)","pairs={(owner,ref)")
pre=pre.replace("if ref not in terminal","if ref not in terminal")
(HERE/'preflight.py').write_text(pre)
print(json.dumps(dict(slug=slug,code_bytes=len(code.encode()),compute_started=False)))
