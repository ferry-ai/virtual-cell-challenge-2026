"""Audit all recovered aggregate hashes, axes, recipes and actual source exclusions."""
import csv
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np
from percorso import HERE, ROOT, DATA, now, read, pin, sha, write_new


def main():
    p=argparse.ArgumentParser(__doc__)
    for name,default in [('retrieval','ammi_anchors_retrieval_r1.json'),('prepared','neural_inputs_cloud_prepared_r4.json'),
                         ('contract','panel_anchor_requests_r1.json'),('out','ammi_anchors_verified_r1.json')]:
        p.add_argument('--'+name,type=Path,default=HERE/default)
    a=p.parse_args()
    retrieval=read(a.retrieval);root=Path(retrieval['out'])
    prepared=read(a.prepared)
    job=next(j for j in prepared['jobs'] if j['slug']==retrieval['slug'])
    remote=subprocess.run([sys.executable,str(HERE/'remote_identity.py'),'davideferrante11',job['slug']],
                          capture_output=True,text=True,timeout=120)
    if remote.returncode:raise RuntimeError('saved code identity query failed')
    identity=json.loads(remote.stdout)
    if identity!={'source_sha256':job['code']['sha256'],'version':1,'is_private':True}:
        raise ValueError('saved code identity differs')
    contract=read(a.contract);done=read(root/'anchors/complete.json')
    requested={r['id']:r for r in contract['requests']+contract.get('parity_requests',[])}
    completed={r['id']:r for r in done['requests']}
    production='production' in contract['folds']
    expected=set(requested) if production else set(requested)|{'parity_k562','parity_ipsc'}
    if set(completed)!=expected:raise ValueError('anchor coverage differs')
    if production:
        if done['production_parity_pairs_verified']!=contract['parity_pairs']:raise ValueError('production parity missing')
        for left,right in contract['parity_pairs']:
            if completed[left]['effects_sha256']!=completed[right]['effects_sha256']:raise ValueError('production parity differs')
    elif not done['outer_only_reference_parity_verified']:raise ValueError('missing parity')
    refs={}
    for tag in (() if production else ('k562','ipsc')):
        ref=read(ROOT/('reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_'+tag+'_r1/effetti.json'))
        refs['parity_'+tag]=ref['files']['T0']['sha256']
    with Path(contract['panel']['path']).open(newline='') as f:targets=[r['target_gene'] for r in csv.DictReader(f)]
    with (DATA/'raw/controls/gene_names.csv').open(newline='') as f:genes=[r[0] for r in list(csv.reader(f))[1:]]
    records={}
    for ident,record in sorted(completed.items()):
        path=root/'anchors'/ident/('effects_'+ident+'.npz');manifest=read(path.parent/'manifest.json')
        if sha(path)!=record['effects_sha256']:raise ValueError('anchor hash differs')
        if ident in refs:
            if record['effects_sha256']!=refs[ident] or not record['parity_verified']:raise ValueError('T0 parity differs')
        else:
            req=requested[ident]
            if record['excluded_lineages']!=req['excluded_lineages'] or record['consumed']!=req['expected_cache_sha256']:
                raise ValueError('actual source exclusions differ')
            if manifest['cache_npz_sha256']!=req['expected_cache_sha256'] or manifest['recipe']!=read(req['recipe']['path']):
                raise ValueError('stage100 recipe/source receipt differs')
        with np.load(path,allow_pickle=False) as z:
            if z['genes'].tolist()!=genes or z['targets'].tolist()!=targets:raise ValueError('aggregate axes differ')
        headers={}
        with zipfile.ZipFile(path) as archive:
            for name in ('lfc','observed'):
                with archive.open(name+'.npy') as f:
                    version=np.lib.format.read_magic(f)
                    header_reader={(1,0):np.lib.format.read_array_header_1_0,
                                   (2,0):np.lib.format.read_array_header_2_0}.get(version)
                    if header_reader is None:raise ValueError('unsupported NPY header version')
                    shape,order,dtype=header_reader(f)
                if shape!=(300,18533) or dtype!=np.dtype('float32' if name=='lfc' else 'bool'):
                    raise ValueError('aggregate matrix schema differs')
                headers[name]=dict(shape=list(shape),dtype=str(dtype))
        records[ident]=dict(effects=pin(path),manifest=pin(path.parent/'manifest.json'),
            excluded_lineages=record['excluded_lineages'],schema=headers,
            remote_path='anchors/'+ident+'/'+path.name)
    out=dict(utc=now(),status='PASS',slug=job['slug'],remote_identity=identity,
        contract=pin(a.contract),completion=pin(root/'anchors/complete.json'),
        retrieval=pin(a.retrieval),anchors=records,
        actual_source_exclusions_verified=True,all_effect_hashes_verified=True,axes_verified=True,
        parity_against_independent_T0=refs,production_parity_pairs=contract.get('parity_pairs',[]),full_numeric_matrices_loaded_locally=False,
        private_access_from_davidmaisterx=False,training_executed=False,complete_D053=False)
    write_new(a.out,out)
    print(json.dumps(dict(status='PASS',anchors=len(records),parity=len(refs)+len(contract.get('parity_pairs',[])),source_consumption_verified=True)))


if __name__=='__main__':main()
