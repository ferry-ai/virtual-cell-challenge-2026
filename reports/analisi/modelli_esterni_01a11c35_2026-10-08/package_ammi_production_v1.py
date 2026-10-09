"""Package an authorized private AMMI runtime; emit no URLs and launch no job."""
import argparse
import base64
import io
import json
from pathlib import Path
import zipfile
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def pin(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha256(p))

def package(runtime,access,mounts,out,receipt):
    runtime=Path(runtime);out=Path(out)
    if out.exists() or out.resolve().is_relative_to(ROOT):raise ValueError('fresh private external package required')
    prepared=json.loads((runtime/'prepared.json').read_text())
    checked(prepared['template'])
    spec=json.loads((runtime/'runtime_template.json').read_text())
    if prepared['fold']!='production' or prepared['mode']!='cells' or spec['mode']!='production':
        raise ValueError('dedicated production package required')
    readout=json.loads(checked(spec['production_readout']).read_text())
    if (set(readout['folds'])!={'C-K562','C-iPSC'}
            or any(not readout['folds'][f].get('cells_minus_T0_read') or not readout['folds'][f].get('cells_minus_none_read') for f in readout['folds'])
            or readout.get('production_technical_fit_decision')!='proceed'):
        raise ValueError('actual comparative readout and explicit decision required before packaging')
    locators=json.loads(Path(access).read_text())
    if locators.get('status')!='authorized' or not locators.get('authorization'):
        raise ValueError('explicit private transfer authorization required')
    mount=json.loads(Path(mounts).read_text())
    if mount['owner']!='davideferrante11' or not mount.get('all_sources_verified_admissible'):
        raise ValueError('verified destination mount plan required')
    slug='ammi-production-cells-17-01a11c35-r1'
    for name,digest in spec['code'].items():
        if sha256(runtime/name)!=digest:raise ValueError('runtime code changed after template')
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(runtime.rglob('*')):
            if path.is_file():
                if path.suffix not in ('.py','.json') and path.parent.name!='assets':
                    raise ValueError('unexpected runtime package member')
                z.writestr(path.relative_to(runtime).as_posix(),path.read_bytes())
        z.writestr('private_locators.json',Path(access).read_bytes())
    raw=archive.getvalue();digest=__import__('hashlib').sha256(raw).hexdigest()
    source='''import base64,hashlib,io,json,sys,zipfile
from pathlib import Path
raw=base64.b64decode(PAYLOAD)
assert hashlib.sha256(raw).hexdigest()==DIGEST
root=Path('/kaggle/temp')/BUNDLE
root.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in archive.namelist())
    archive.extractall(root)
sys.path.insert(0,str(root))
spec=json.loads((root/'runtime_template.json').read_text())
for name,digest in spec['code'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
from ammi_bootstrap_v4 import execute
try:
    execute(root/'runtime_template.json',TEMPLATE,MODE,OUTPUT,root/'private_locators.json')
except Exception as error:
    # Resolver strips signed URLs from transport failures before reaching here.
    Path('/kaggle/working/ammi_failure.json').write_text(json.dumps(dict(type=type(error).__name__,error=str(error))))
    raise
'''
    values=dict(PAYLOAD=base64.b64encode(raw).decode(),DIGEST=digest,BUNDLE=slug+'-bundle',
        TEMPLATE=prepared['template']['sha256'],MODE=prepared['mode'],OUTPUT='/kaggle/working/'+slug)
    source='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+source
    out.mkdir(parents=True);(out/'run.py').write_text(source,encoding='utf-8')
    meta=dict(id=mount['owner']+'/'+slug,title=slug,code_file='run.py',language='python',kernel_type='script',
        is_private=True,enable_gpu=True,enable_internet=True,dataset_sources=mount['dataset_sources'],
        kernel_sources=mount['kernel_sources'],competition_sources=[])
    write(out/'kernel-metadata.json',meta)
    report=dict(slug=meta['id'],stage=str(out),private=True,actual_CUDA_required=True,
        code=pin(out/'run.py'),metadata=pin(out/'kernel-metadata.json'),template=prepared['template'],
        private_locator_manifest_sha256=sha256(access),mount_plan=pin(Path(mounts)),
        fold=prepared['fold'],mode=prepared['mode'],seed=17,launch_pending=True)
    write(receipt,report)
    print(json.dumps(dict(slug=meta['id'],launch_pending=True,code_bytes=report['code']['bytes'])))

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('runtime','access','mounts','out','receipt'):p.add_argument('--'+name,required=True)
    a=p.parse_args();package(a.runtime,a.access,a.mounts,a.out,a.receipt)
