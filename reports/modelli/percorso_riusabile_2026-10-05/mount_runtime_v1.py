"""Runtime-only proof of unchanged cross-account mounts and original readers.

No fit, effect estimation, ingestion, statistical pooling or model promotion.
"""
import gzip,json,os,shutil,time
from pathlib import Path
import psutil
from sample_reader import SampleReader,sha
from population_reader import PopulationReader
from restore_bank_aliases_v1 import restore


def mounted(slug):
    matches=[p.parent for p in Path('/kaggle/input').rglob('complete.json')
             if slug in p.parts]
    roots=[p for p in Path('/kaggle/input').rglob('layout.json') if slug in p.parts]
    if roots:return roots[0].parent
    if len(matches)!=1:raise ValueError('dataset mount not unique: '+slug)
    return matches[0]


def main():
    started=time.monotonic();params=json.loads(Path('params.json').read_text())
    free=psutil.virtual_memory().available;disk=shutil.disk_usage('.').free
    if free<2*1024**3 or disk<2*1024**3:raise MemoryError('reader preflight capacity insufficient')
    print(json.dumps({'cpus':os.cpu_count(),'ram_available':free,'disk_free':disk}),flush=True)
    n=params['norman'];root=mounted(n['dataset'].split('/')[1])
    restored=restore(root,n['layout_sha256'],'/kaggle/working/restored_norman')
    # Reader construction verifies lineage, row identities and sampled masks.
    population=PopulationReader(restored/'bank/norman2019',n['bank_receipt_sha256'])
    sample=SampleReader(restored/'samples/norman2019',n['sample_receipt_sha256'],n['bank_receipt_sha256'])
    population.require_sample_link(sample)
    for name in population.receipt['files']:population.verify(name)
    for name in sample.receipt['files']:sample.verify(name)
    # Validate locators as gzip, preserving the exact original bytes.
    with gzip.open(restored/'bank/norman2019/samples.jsonl.gz','rt') as f:
        first=json.loads(next(f))
    if not first.get('levels'):raise ValueError('locator schema differs')
    ip=params['ipsc'];root=mounted(ip['dataset'].split('/')[1])
    if sha(root/'complete.json')!=ip['receipt_sha256']:raise ValueError('iPSC receipt mismatch')
    checked=[]
    for name,expected in ip['files'].items():
        path=root/(name+'.bin' if name.endswith('.gz') else name)
        if not path.exists() and name.endswith('.gz'):path=root/name
        if path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:
            raise ValueError('iPSC mounted bytes differ: '+name)
        checked.append(name)
    result={'complete':True,'scope':'cross-account original bank/sample mounts and reader lineage only',
            'norman_dataset':n['dataset'],'norman_version':1,'norman_rows':len(population.rows),
            'norman_reader_lineage_verified':True,'ipsc_dataset':ip['dataset'],'ipsc_version':3,
            'ipsc_files_hash_checked':checked,'fit_admitted':False,'training_used':False,
            'producer_input_manifest_sha256':sha('params.json'),'seconds':round(time.monotonic()-started,2)}
    Path('runtime_receipt.json').write_text(json.dumps(result,indent=1))
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
