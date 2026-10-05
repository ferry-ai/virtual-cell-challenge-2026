"""Pin the original t25 K562 cache and package an effects-only cloud refit.

No ingestion, cloud calls or competition-control upload. Original Grok files remain intact.
"""
import base64,hashlib,io,json,shutil,sys,zipfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
STUDY=REPO/'reports/modelli/percorso_riusabile_2026-10-05'
OUT=STUDY/'k562_reuse_r1'
REF='davideferrante11/vcc-k562-t25-cache-r1'
PIN='a37c78ce1f7c13a3fc145e75e64f2ccead555ec8e38a656d671903ed4fd7218f'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    sys.path.insert(0,str(REPO/'src'))
    from vcc2026.config import paths
    import numpy as np
    src=paths().processed/'multisource_2026-09-27_r9/k562.npz'
    assert sha(src)==PIN
    prior=(REPO/'reports/sorgenti/pseudoconteggio_2026-09-27/parita_sha256.txt').read_text()
    assert 'k562.npz r5='+PIN+' ricostruita='+PIN+' identici' in prior
    with np.load(src,allow_pickle=False) as z:
        assert z['raw'].shape==z['shrunk'].shape==z['se'].shape==(272,18533)
        assert len(set(z['targets']))==272
        assert np.isfinite(z['se'][np.isfinite(z['raw'])]).all()
        meta=json.loads(str(z['meta']))
    if (OUT/'ready_r3.json').exists():raise FileExistsError('package already prepared')
    OUT.mkdir(exist_ok=True)
    stage=REPO/'data/cloud_inputs/vcc-k562-t25-cache-r1';stage.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,stage/'k562.npz.bin');assert sha(stage/'k562.npz.bin')==PIN
    proof={'source':'k562 GWPS bulk, exact original stage98 t25/t28 cache; NOT K562 essential',
      'source_path':str(src),'sha256':PIN,'bytes':src.stat().st_size,'shape':[272,18533],
      'historical_proof':'reports/sorgenti/pseudoconteggio_2026-09-27/parita_sha256.txt',
      'meta':meta,'dataset':REF,'private':True,'new_ingestion':False,
      'current_singlecell_bank_job_untouched':True,'scope':'production only; not held-out C/J',
      'axis_sha256':'25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201'}
    write(stage/'lineage.json',proof);write(OUT/'preparation.json',proof)
    write(stage/'dataset-metadata.json',{'id':REF,'title':'VCC K562 original t25 cache r1',
      'licenses':[{'name':'other'}],'description':'Private byte-identical original K562 GWPS stage98 source table. Explicit historical provenance; no competition controls, no prediction.'})
    original=STUDY/'agenti/grok_transfer_esteso_r8/packages/vcc-generate-t28-extbank-r1'
    pkg=OUT/'effects_package_r3';shutil.copytree(original,pkg,dirs_exist_ok=True)
    driver=(pkg/'driver.py').read_text()
    driver=driver.replace("voted = sorted(name for ctx in recipe['contexts'].values() for name in ctx['weights'])", "voted = sorted({name for ctx in recipe['contexts'].values() for name in ctx['weights']})")
    driver=driver.replace("linked = _link_controls(params)","linked = {} if params.get('effects_only') else _link_controls(params)")
    driver=driver.replace("recipe = contract.accept_source_model(document)","recipe = contract.accept_source_model(document)\n        for context in recipe['contexts'].values():\n            context['weights']['k562'] = 1.0")
    driver=driver.replace("'k562_in_recipe': False", "'k562_in_recipe': True")
    driver=driver.replace("path = cache / (name + '.npz')", "path = cache / (name + '.npz')\n        if name == 'k562':\n            hits = list(INPUTS.rglob('k562.npz.bin'))\n            if len(hits) != 1 or _sha256(hits[0]) != "+repr(PIN)+":\n                _fail('blocked_k562_historical_identity')\n            path = hits[0]")
    driver=driver.replace("os.symlink(path, dest / path.name)","os.symlink(path, dest / (name + '.npz'))")
    driver=driver.replace("document = json.loads((model_dir / 'source_model.json').read_text(encoding='utf-8'))", "_verify_mix_checkpoint(model_dir)\n    document = json.loads((model_dir / 'source_model.json').read_text(encoding='utf-8'))")
    checkpoint=STUDY/'extended_mix_completion_r1/model/checkpoint.json'
    guard="""\ndef _verify_mix_checkpoint(model_dir):
    checkpoint = model_dir / 'checkpoint.json'
    if _sha256(checkpoint) != CHECKPOINT_PIN:
        _fail('blocked_producer_checkpoint_identity')
    receipt = json.loads(checkpoint.read_text())
    for item in receipt['files']:
        rel = Path(item['path'])
        if rel.is_absolute() or '..' in rel.parts:
            _fail('blocked_producer_relative_path')
        path = model_dir / rel
        if not path.is_file() or path.stat().st_size != item['bytes'] or _sha256(path) != item['sha256']:
            _fail('blocked_producer_file_hash', file=item['path'])
\n""".replace('CHECKPOINT_PIN',repr(sha(checkpoint)))
    driver=driver.replace('def main():',guard+'def main():')
    coords=original/'data/external/annotation/gene_coordinates_gencode_v50.tsv'
    shutil.copy2(coords,stage/coords.name)
    driver=driver.replace('    _verify_embedded(params)', "    coords_hits = list(INPUTS.rglob('gene_coordinates_gencode_v50.tsv'))\n    if len(coords_hits) != 1 or _sha256(coords_hits[0]) != "+repr(sha(coords))+":\n        _fail('blocked_coordinates_identity')\n    (WORKING / 'data/external/annotation').mkdir(parents=True, exist_ok=True)\n    (WORKING / 'data/external/annotation/gene_coordinates_gencode_v50.tsv').write_bytes(coords_hits[0].read_bytes())\n    _verify_embedded(params)")
    marker="    _run_script(WORKING / 'repo' / 'scripts' / '45_generate_prediction.py', ["
    fast="""    if params.get('effects_only'):
        destination = WORKING / 'effects'
        shutil.copytree(effects, destination)
        _write(WORKING / 'status.json', {'status': 'effects_ready', 'usable_export': True,
          'registered_sources': voted, 'k562_historical_sha256': K562_PIN,
          'catalogue_complete': False, 'controls_h5ad_uploaded': False,
          'recipe_sha256': recipe_sha, 'scope': 'production; not held-out C/J'})
        return
""".replace('K562_PIN',repr(PIN))
    assert marker in driver
    driver=driver.replace(marker,fast+marker)
    driver=driver.replace('import os,','import os,')
    driver=driver.replace('from __future__ import annotations','from __future__ import annotations\nimport shutil')
    (pkg/'driver.py').write_text(driver,encoding='utf-8')
    compile(driver,'driver.py','exec')
    params=json.loads((pkg/'params.json').read_text());params['effects_only']=True
    params['k562_reuse']=proof;params['claims_complete_training']=False
    params['embedded_sha256']={p.relative_to(pkg).as_posix():sha(p) for p in pkg.rglob('*') if p.is_file() and p.name not in ('params.json','run.py','kernel-metadata.json','gene_coordinates_gencode_v50.tsv') and '__pycache__' not in p.parts and 'vendor' not in p.relative_to(pkg).parts}
    params['coordinates_mount_sha256']=sha(coords)
    write(pkg/'params.json',params)
    metadata=json.loads((pkg/'kernel-metadata.json').read_text());metadata['id']='davideferrante11/vcc-refit-t28-bank-k562-reuse-r1';metadata['title']='vcc-refit-t28-bank-k562-reuse-r1'
    metadata['dataset_sources'].append(REF);write(pkg/'kernel-metadata.json',metadata)
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(pkg.rglob('*')):
            if p.is_file() and p.name not in ('run.py','kernel-metadata.json','gene_coordinates_gencode_v50.tsv') and '__pycache__' not in p.parts and 'vendor' not in p.relative_to(pkg).parts:z.write(p,p.relative_to(pkg).as_posix())
    bootstrap="import base64,io,os,zipfile,runpy\nfrom pathlib import Path\nos.chdir('/kaggle/working')\nzipfile.ZipFile(io.BytesIO(base64.b64decode(PAYLOAD))).extractall('/kaggle/working')\nrunpy.run_path('/kaggle/working/driver.py',run_name='__main__')\n"
    bootstrap=bootstrap.replace('PAYLOAD',repr(base64.b64encode(payload.getvalue()).decode()))
    (pkg/'run.py').write_text(bootstrap,encoding='utf-8');compile(bootstrap,'run.py','exec')
    write(OUT/'ready_r3.json',{'package':str(pkg),'metadata':metadata,'code_sha256':sha(pkg/'run.py'),
      'params_sha256':sha(pkg/'params.json'),'code_bytes':(pkg/'run.py').stat().st_size,
      'state':'prepared_not_launched','no_control_h5ad_in_payload':True,'new_ingestion':False})
    print(json.dumps({'cache_bytes':src.stat().st_size,'code_bytes':(pkg/'run.py').stat().st_size,'prepared':True}))
if __name__=='__main__':main()
