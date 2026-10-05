"""Repair the diagnosed Python import path; no estimator or source bytes change."""
import hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fix(pkg):
    p=pkg/'run.py';s=p.read_text();assert s.count("runpy.run_path('/kaggle/working/driver.py'")==1
    s=s.replace('import base64,io,os,zipfile,runpy','import base64,io,os,zipfile,runpy,sys')
    s=s.replace("runpy.run_path('/kaggle/working/driver.py'", "sys.path.insert(0,'/kaggle/working')\nrunpy.run_path('/kaggle/working/driver.py'")
    compile(s,'run.py','exec');p.write_text(s)
def main():
    k=S/'k562_reuse_r1';old=json.loads((k/'ready_r3.json').read_text());pkg=k/'effects_retry_package';shutil.copytree(Path(old['package']),pkg)
    fix(pkg);m=json.loads((pkg/'kernel-metadata.json').read_text());m['id']='davideferrante11/vcc-refit-t28-bank-k562-reuse-r1-fix1';m['title']='vcc-refit-t28-bank-k562-reuse-r1-fix1';(pkg/'kernel-metadata.json').write_text(json.dumps(m,indent=2))
    (k/'ready_fix1.json').write_text(json.dumps({**old,'package':str(pkg),'metadata':m,'code_sha256':sha(pkg/'run.py'),'supersedes_failed':old['metadata']['id'],'diagnosis':'ModuleNotFoundError generate_contract; bootstrap lacked working dir on sys.path; data/formulas unchanged'},indent=2))
    g=S/'generation_parent_r1';ready=json.loads((g/'ready.json').read_text());fix(Path(ready['package']));ready['code_sha256']=sha(Path(ready['package'])/'run.py');ready['bootstrap_import_path_repaired']=True;(g/'ready_fixed.json').write_text(json.dumps(ready,indent=2))
if __name__=='__main__':main()
