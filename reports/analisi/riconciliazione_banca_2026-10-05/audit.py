"""Metadata-only bank/release reconciliation; no cloud calls or matrix loads."""
import argparse,hashlib,json,subprocess
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

REPO=Path(__file__).resolve().parents[3]
STUDY=REPO/'reports/modelli/percorso_riusabile_2026-10-05'
STORAGE_SHA='7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf'
EXPECTED_SHA='f7edac31784e56fab3a192e74dc0b6b8ea56bc1496dbba5d5c06c753d2e66015'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def ref(path):return path.relative_to(REPO).as_posix()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--coverage',type=Path);p.add_argument('--expected-sha');a=p.parse_args()
    out=a.out.resolve();out.mkdir(exist_ok=False)
    errors=[];open_items=[];pins=[];git_mismatches=[]
    def pin(path,expected=None):
        path=path.resolve()
        if not path.is_file():
            open_items.append({'kind':'missing_local_receipt','path':str(path)});return
        actual=sha(path)
        item={'path':ref(path),'sha256':actual,'bytes':path.stat().st_size}
        if expected is not None:
            item['expected_sha256']=expected;item['matches_expected']=actual==expected
            if actual!=expected:open_items.append({'kind':'frozen_reference_changed',**item})
        pins.append(item)
        r=subprocess.run(['git','show',':'+item['path']],cwd=REPO,capture_output=True)
        if r.returncode==0 and hashlib.sha256(r.stdout).hexdigest()!=actual:
            git_mismatches.append({'path':item['path'],'working_sha256':actual,'index_sha256':hashlib.sha256(r.stdout).hexdigest()})
    storage_path=STUDY/'cloud_catalog_r10/manifest.json'
    expected_path=(a.coverage or STUDY/'training_coverage_r1/expected.json').resolve()
    expected_sha=a.expected_sha or EXPECTED_SHA
    pin(storage_path,STORAGE_SHA);pin(expected_path,expected_sha)
    storage=read(storage_path);expected=read(expected_path)
    if sha(storage_path)!=STORAGE_SHA or sha(expected_path)!=expected_sha:errors.append('top-level frozen identity differs')
    coverage=set(storage['units']);wanted=set(expected['expected_storage_units'])
    if coverage!=wanted:errors.append('storage and expected unit identities differ')
    for collection in ('catalogue_records','additional_sources'):
        values=expected[collection]
        values=[values] if isinstance(values,dict) and 'path' in values else (list(values.values()) if isinstance(values,dict) else values)
        for item in values:
            if isinstance(item,dict) and item.get('path') and item.get('sha256'):
                pin(REPO/item['path'],item['sha256'])
    duplicates=defaultdict(list);raws=[]
    for dataset,raw in storage['raw_archives'].items():
        rp=REPO/raw['files_receipt'];pin(rp,raw['files_sha256'])
        if not rp.is_file():continue
        files=read(rp)
        if sum(f['bytes'] for f in files)!=raw['bytes']:errors.append('raw byte total differs: '+dataset)
        for f in files:duplicates[f['sha256']].append({'dataset':dataset,'file':f['file'],'unit':f['unit']})
        raws.append({'dataset':dataset,'version':raw['version'],'bytes':raw['bytes'],'units':list(raw['units'])})
    receipt_path=STUDY/'extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1.json'
    launch=read(receipt_path);pin(receipt_path)
    stage=Path(launch['stage']);pin(stage/'run.py',launch['code_sha256']);pin(stage/'params.json',launch['params_sha256'])
    params=read(stage/'params.json');metadata=read(stage/'kernel-metadata.json');pin(stage/'kernel-metadata.json')
    if metadata['id']!=launch['slug']:errors.append('launched job identity differs')
    mounted=metadata['kernel_sources']
    if len(mounted)!=len(set(mounted)):errors.append('duplicate kernel mount')
    for bad in ('rlead-bench-cube-r2','vcc-effects-mix-t25-bank-r1'):
        if any(s.endswith('/'+bad) for s in mounted):errors.append('refused historical/error mount: '+bad)
    aliases=[]
    for folder in ('sourcefits_launch_r1','cd4_joint_launch_r1','extended_mix_launch_r2'):
        for path in sorted((STUDY/folder).glob('*.json')):
            data=read(path)
            if data.get('accepted') and data.get('slug') and data.get('supersedes_failed'):
                aliases.append({'old':data['supersedes_failed'],'new':data['slug'],'receipt':ref(path)})
    for alias in aliases:
        if alias['old'] in mounted:errors.append('failed predecessor still mounted: '+alias['old'])
        if alias['new'] in mounted and alias['old'] in mounted:errors.append('original/retry double vote')
    model_dir=STUDY/'extended_mix_completion_r1/model'
    model=read(model_dir/'source_model.json');manifest=read(model_dir/'manifest.json')
    inventory=read(model_dir/'panel_inventory.json');checkpoint=read(model_dir/'checkpoint.json')
    checked=[];remote=[]
    for f in checkpoint['files']:
        path=model_dir/f['path']
        if path.is_file():
            pin(path,f['sha256']);checked.append(f['path'])
            if sha(path)!=f['sha256'] or path.stat().st_size!=f['bytes']:errors.append('downloaded output identity differs: '+f['path'])
        else:remote.append(f)
    for item in manifest['joints']+manifest['fragments']:
        if item['slug'] not in mounted:errors.append('used fragment not in frozen mounts: '+item['slug'])
        if item.get('axis_sha256')!=params['axis']['sha256']:errors.append('used fragment axis differs: '+item['slug'])
    votes=model['sources']
    if len(votes)!=len(set(votes)):errors.append('duplicate source vote')
    if 'h1_train' in votes or 'h1_val' in votes:errors.append('H1 splits vote independently')
    if any(v.startswith('cd4_') and v!='cd4_mix' for v in votes):errors.append('CD4 conditions vote twice')
    panel_sources=[v for v in votes if inventory[v]['n_targets_on_panel']>0]
    baseline=read(REPO/'configs/recipes/t25.json');baseline_votes=set(baseline['contexts']['A']['weights'])
    missing=sorted(baseline_votes-set(votes))
    if missing:open_items.append({'kind':'not_baseline_superset','missing_sources':missing,'replacement_allowed':False})
    open_items.extend({'kind':'catalogue_gap','detail':gap} for gap in model['catalogue_gaps'])
    for v in votes:
        if inventory[v]['n_targets_on_panel']==0:open_items.append({'kind':'no_panel_targets_in_current_table','source':v,'scientific_exclusion':False})
    release={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),'scope':'partial production transfer; not complete catalogue or held-out validation',
      'storage':{'path':ref(storage_path),'sha256':STORAGE_SHA},'coverage':{'path':ref(expected_path),'sha256':expected_sha,'units':sorted(wanted)},
      'consumer':{'job':launch['slug'],'version':1,'launch_receipt':ref(receipt_path),'code_sha256':launch['code_sha256'],'params_sha256':launch['params_sha256'],
                  'mounted_producers':mounted,'failed_aliases':aliases},
      'model':{'registered_sources':votes,'sources_with_panel_targets':panel_sources,'panel_targets':300,'baseline_sources':sorted(baseline_votes),
               'baseline_sources_missing':missing,'strict_baseline_plus_additions':not missing,'same_algorithm_equivalence_complete':False,
               'cache_hashes_to_verify_in_consumer':remote,'usable_export':model['usable_export']},
      'raw_archives':raws,'fallback_to_legacy':False,'claims_complete_training':False,'claims_complete_corpus':False,'source_identity_rule':'version+bytes+axis+QC+code+parameters; age/title do not select inputs'}
    (out/'selection.json').write_text(json.dumps(release,indent=2),encoding='utf-8')
    summary={'utc':release['created_utc'],'hard_failures':errors,'open_items':open_items,'checked_pins':pins,'git_index_byte_differences':git_mismatches,
      'storage_units':len(coverage),'expected_units':len(wanted),'registered_sources':len(votes),'sources_with_panel_targets':len(panel_sources),
      'raw_identical_file_groups':[v for v in duplicates.values() if len(v)>1],
      'duplicate_scope':'identical archived bytes only; overlapping biological cells/studies still require reconciliation',
      'downloaded_output_files_verified':checked,'remote_matrix_files_not_downloaded':len(remote),
      'consumer_matrices_fully_reverified':False,'no_new_cloud_compute':True,'no_new_data_upload':True}
    (out/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'hard_failures':errors,'open_items':len(open_items),'git_byte_differences':len(git_mismatches),'pins':len(pins),'duplicate_byte_groups':len(summary['raw_identical_file_groups']),
                      'units':len(coverage),'sources_with_panel_targets':len(panel_sources)}))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
