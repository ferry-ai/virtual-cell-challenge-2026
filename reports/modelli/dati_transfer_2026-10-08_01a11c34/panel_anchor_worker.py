"""Cloud CPU construction of the frozen T0 requests, using stage 100 unchanged."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from ntc_cells import sha, checked
from run_ntc_extraction import available_memory


def main():
    work=Path('/kaggle/working'); temp=Path('/kaggle/temp/ammi_anchors_r1')
    contract=json.loads((work/'anchor_requests.json').read_text())
    resources=dict(cpu_count=os.cpu_count(),available_RAM=available_memory(),
                   disk_free=shutil.disk_usage(work).free)
    (work/'initial_resources.json').write_text(json.dumps(resources))
    if resources['available_RAM'] < 1<<30 or resources['disk_free'] < 1<<30:
        raise RuntimeError('anchors require at least 1 GiB free RAM and disk')
    all_requests=contract['parity_requests']+contract['requests']
    all_pins={s:p for request in all_requests for s,p in request['source_pins'].items()}
    files=[p for p in Path('/kaggle/input').rglob('*') if p.is_file() and p.name.endswith(('.npz','.npz.bin'))]
    resolved={}
    for name,spec in all_pins.items():
        hits=[p for p in files if p.stat().st_size==spec['bytes'] and sha(p)==spec['sha256']]
        if not hits:raise ValueError('pinned anchor source absent: '+name)
        resolved[name]=sorted(hits)[0]
    # Coordinates are mounted, not silently downloaded or replaced.
    coords=[p for p in Path('/kaggle/input').rglob('gene_coordinates_gencode_v50.tsv')
            if sha(p)==contract['coordinates']['sha256']]
    if not coords:raise ValueError('pinned coordinates missing')
    coords=sorted(coords)
    out=work/'anchors';out.mkdir(exist_ok=False)
    results=[]
    env=dict(os.environ,VCC2026_DATA_ROOT=str(work/'data'),VCC2026_ARTIFACT_ROOT=str(temp/'artifacts'),
             PYTHONPATH=str(work/'repo/src'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for request in all_requests:
        ident=request['id'];folder=temp/ident;cache=folder/'cache';cache.mkdir(parents=True,exist_ok=False)
        for source in request['sources']:os.symlink(resolved[source],cache/(source+'.npz'))
        recipe=work/'recipes'/(ident+'.json');checked(recipe,request['recipe'])
        subprocess.run([sys.executable,str(work/'repo/scripts/100_build_context_effects.py'),
            '--recipe',str(recipe),'--cache',str(cache),'--targets-csv',str(work/'data/raw/controls/pert_counts.csv'),
            '--coords',str(coords[0]),'--contexts',','.join(json.loads(recipe.read_text())['contexts']),
            '--out',str(folder/'out')],env=env,check=True)
        receipt=json.loads((folder/'out/manifest.json').read_text())
        if receipt['cache_npz_sha256']!=request['expected_cache_sha256']:
            raise ValueError('stage100 source consumption differs')
        destination=out/ident;shutil.copytree(folder/'out',destination)
        digest=sha(destination/('effects_'+ident+'.npz'))
        if request.get('expected_effects_sha256') and digest!=request['expected_effects_sha256']:
            raise ValueError('outer-only T0 parity failed')
        results.append(dict(id=ident,excluded_lineages=request['excluded_lineages'],
            consumed=receipt['cache_npz_sha256'],effects_sha256=digest,
            parity_verified=bool(request.get('expected_effects_sha256'))))
    digests={r['id']:r['effects_sha256'] for r in results}
    pairs=contract.get('parity_pairs',[])
    for left,right in pairs:
        if digests[left]!=digests[right]:raise ValueError('frozen production T0 parity failed')
    (out/'complete.json').write_text(json.dumps(dict(status='COMPLETE',requests=results,
        protocol=contract.get('execution_protocol','T0 panel centering; no final refit; inner always excluded'),
        outer_only_reference_parity_verified=any(r.get('expected_effects_sha256') for r in all_requests),
        production_parity_pairs_verified=pairs,complete_D053=False),indent=2))


if __name__=='__main__':main()
