"""Skip cell-generation imports for effects-only; pin missing generation dependencies."""
import base64,hashlib,io,json,shutil,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build(pkg,vendor,install=False):
    params=json.loads((pkg/'params.json').read_text());params['embedded_sha256']['driver.py']=sha(pkg/'driver.py');(pkg/'params.json').write_text(json.dumps(params,indent=2))
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(pkg.rglob('*')):
            if f.is_file() and f.name not in ('run.py','kernel-metadata.json','gene_coordinates_gencode_v50.tsv') and '__pycache__' not in f.parts and (vendor or 'vendor' not in f.relative_to(pkg).parts):z.write(f,f.relative_to(pkg).as_posix())
    code="import base64,io,os,zipfile,runpy,sys\nos.chdir('/kaggle/working')\nzipfile.ZipFile(io.BytesIO(base64.b64decode("+repr(base64.b64encode(b.getvalue()).decode())+"))).extractall('/kaggle/working')\nsys.path.insert(0,'/kaggle/working')\n"
    if install:
        code+="""import subprocess,importlib.metadata as md,json
from pathlib import Path
core={n:md.version(n) for n in ('numpy','scipy','pandas','h5py')}
Path('core_constraints.txt').write_text(''.join(n+'=='+v+'\\n' for n,v in core.items()))
subprocess.check_call([sys.executable,'-m','pip','install','--disable-pip-version-check','--constraint','core_constraints.txt','anndata==0.13.3.post0','zstandard==0.25.0'])
assert {n:md.version(n) for n in core}==core
Path('runtime_versions.json').write_text(json.dumps({n:md.version(n) for n in (*core,'anndata','zstandard')},indent=2))
"""
    code+="runpy.run_path('/kaggle/working/driver.py',run_name='__main__')\n"
    compile(code,'run.py','exec');(pkg/'run.py').write_text(code)
    assert (pkg/'run.py').stat().st_size<1000000
def main():
    k=S/'k562_reuse_r1';old=json.loads((k/'ready_fix1.json').read_text());pkg=k/'effects_fix2_package';shutil.copytree(Path(old['package']),pkg)
    d=pkg/'driver.py';code=d.read_text();code=code.replace('        import anndata  # noqa: F401',"        if not params.get('effects_only'):\n            import anndata  # noqa: F401").replace('        import zstandard  # noqa: F401',"        if not params.get('effects_only'):\n            import zstandard  # noqa: F401");compile(code,'driver.py','exec');d.write_text(code)
    m=json.loads((pkg/'kernel-metadata.json').read_text());m['id']='davideferrante11/vcc-refit-t28-bank-k562-reuse-r1-fix2';m['title']='vcc-refit-t28-bank-k562-reuse-r1-fix2';(pkg/'kernel-metadata.json').write_text(json.dumps(m,indent=2));build(pkg,False)
    (k/'ready_fix2.json').write_text(json.dumps({**old,'package':str(pkg),'metadata':m,'code_sha256':sha(pkg/'run.py'),'params_sha256':sha(pkg/'params.json'),'supersedes_failed':old['metadata']['id'],'diagnosis':'effects-only unnecessarily imported missing anndata; imports deferred, estimators unchanged'},indent=2))
    g=S/'generation_parent_r1';old=json.loads((g/'ready_fixed.json').read_text());pkg=g/'package_deps';shutil.copytree(Path(old['package']),pkg)
    m=json.loads((pkg/'kernel-metadata.json').read_text());m['enable_internet']=True;(pkg/'kernel-metadata.json').write_text(json.dumps(m,indent=2));build(pkg,True,True)
    (g/'ready_deps.json').write_text(json.dumps({**old,'package':str(pkg),'metadata':m,'code_sha256':sha(pkg/'run.py'),'params_sha256':sha(pkg/'params.json'),'dependency_installation':'pinned anndata0.13.3.post0/zstandard0.25.0, no core upgrades, runtime versions recorded'},indent=2))
if __name__=='__main__':main()
