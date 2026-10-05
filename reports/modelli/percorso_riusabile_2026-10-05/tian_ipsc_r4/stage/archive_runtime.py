"""Resume from the saved successful bank; raw data and sampled cells are not recreated."""
import gc,json,os,shutil,time
from pathlib import Path
import psutil
from bank import run_unit,sha
from materialize_samples import run as materialize


def main():
    p=json.loads(Path('params.json').read_text()); spec=p['units'][0]
    print(json.dumps({'cpus':os.cpu_count(),'ram_available':psutil.virtual_memory().available,
                      'disk_free':shutil.disk_usage('.').free,'provider':'kaggle'}),flush=True)
    roots=[x.parent for x in Path('/kaggle/input').rglob('files.json') if x.parent.name==p['slug']]
    if len(roots)!=1:raise ValueError('raw mount ambiguous')
    root=roots[0]
    if sha(root/'files.json')!=p['source_files_sha256'] or sha(root/'complete.json')!=p['raw_complete_sha256']:
        raise ValueError('raw archive identity differs')
    if p.get('resume_bank'):
        expected=p['resume_bank']
        banks=[x.parent for x in Path('/kaggle/input').rglob('complete.json')
               if sha(x)==expected['receipt_sha256']]
        if len(banks)!=1:raise ValueError('pinned successful bank not mounted uniquely')
        mounted=banks[0];bank=Path('/kaggle/working/reused_bank')
        bank.mkdir(exist_ok=False)
        for name in ('complete.json','rows.csv','mask.npz','samples.jsonl.gz'):
            source=mounted/(name+'.bin') if name=='samples.jsonl.gz' else mounted/name
            shutil.copyfile(source,bank/name)
        r=json.loads((bank/'complete.json').read_text())
        if not r['complete'] or r['cells_in']!=spec['cells'] or r['source_verification']!=spec['receipt_sha256']:
            raise ValueError('saved bank lineage differs')
        bank_ref={**expected,'reused_without_copy':True}
    else:
        bank=Path('bank')/spec['name'];run_unit(spec,root,bank);gc.collect()
        bank_ref={'relative_path':str(bank),'receipt_sha256':sha(bank/'complete.json')}
    samples=Path('samples')/spec['name']
    materialize({'unit':spec['name'],'bank_receipt_sha256':sha(bank/'complete.json'),
                 'bank_input_path':str(bank),'spec':spec},root,samples)
    Path('tian_resume_complete.json').write_text(json.dumps({'complete':True,'unit':spec['name'],
         'bank':bank_ref,'samples':{'relative_path':str(samples),'receipt_sha256':sha(samples/'complete.json')},
         'raw_files_sha256':p['source_files_sha256'],'axis_sha256':spec['axis_sha256'],'training_used':False},indent=1))


if __name__=='__main__':main()
