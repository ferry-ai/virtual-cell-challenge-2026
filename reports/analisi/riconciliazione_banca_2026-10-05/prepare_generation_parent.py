"""Prepare the authorized full t28 generation from frozen sources plus exact K562.

Preserves Grok originals; one self-contained Kaggle code file, no raw controls embedded.
"""
import base64,hashlib,io,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[3]
S=R/'reports/modelli/percorso_riusabile_2026-10-05'
OUT=S/'generation_parent_r1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    OUT.mkdir(exist_ok=False)
    pkg=OUT/'package';shutil.copytree(S/'k562_reuse_r1/effects_package_r3',pkg)
    params=json.loads((pkg/'params.json').read_text());params['effects_only']=False
    params['kind']='t28_generation_with_explicit_original_k562_reuse';params['controls_private_authorized']=True
    params['embedded_sha256'].update({p.relative_to(pkg).as_posix():sha(p) for p in (pkg/'vendor').rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    write(pkg/'params.json',params)
    meta=json.loads((pkg/'kernel-metadata.json').read_text());meta['id']='davideferrante11/vcc-generate-t28-bank-k562-reuse-r1';meta['title']='vcc-generate-t28-bank-k562-reuse-r1'
    meta['dataset_sources'].append('davideferrante11/vcc-official-controls-r1');write(pkg/'kernel-metadata.json',meta)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(pkg.rglob('*')):
            if p.is_file() and p.name not in ('run.py','kernel-metadata.json','gene_coordinates_gencode_v50.tsv') and '__pycache__' not in p.parts:z.write(p,p.relative_to(pkg).as_posix())
    bootstrap="import base64,io,os,zipfile,runpy\nos.chdir('/kaggle/working')\nzipfile.ZipFile(io.BytesIO(base64.b64decode("+repr(base64.b64encode(buffer.getvalue()).decode())+"))).extractall('/kaggle/working')\nrunpy.run_path('/kaggle/working/driver.py',run_name='__main__')\n"
    compile(bootstrap,'run.py','exec');(pkg/'run.py').write_text(bootstrap)
    assert (pkg/'run.py').stat().st_size<1000000
    write(OUT/'ready.json',{'package':str(pkg),'slug':meta['id'],'metadata':meta,'code_sha256':sha(pkg/'run.py'),'params_sha256':sha(pkg/'params.json'),
      'controls_upload_authorized':True,'needs_ready_inputs_and_preflight':True,'fit_bank_complete':False,'generation_launched':False,
      'corrections':['unique source names across A/B/C','producer checkpoint and every matrix hash','explicit historical K562 vote','self-contained code_file']})
    print(json.dumps({'generation_prepared':True,'code_bytes':(pkg/'run.py').stat().st_size}))
if __name__=='__main__':main()
