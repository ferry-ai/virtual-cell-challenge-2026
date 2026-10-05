"""Recover partial saved Tian metadata before any retry; never transfer matrices."""
import json, os, subprocess, sys
from pathlib import Path
from pipeline_state import HERE,CONFIG,sha
from pipeline_state_r2 import isolated_receipts
from sample_state import validate


def main():
    job='davideferante/vcc-derivatives-tian-norman-r1'; owner='davideferante'
    out=HERE/'tian_partial_r1'; out.mkdir(exist_ok=False)
    banks,files,version=isolated_receipts(owner,job,out/'bank_receipts')
    stage=HERE/'fallback_tian_r2'; prepared=json.loads((stage/'prepared.json').read_text())
    if version['saved_source_sha256']!=prepared['code_sha256']:raise ValueError('unexpected saved producer')
    p=subprocess.run([sys.executable,str(HERE/'sample_state.py'),'--fetch',job,str(out)],
        env={**os.environ,'KAGGLE_CONFIG_DIR':str(Path.home()/CONFIG[owner])},capture_output=True,text=True,timeout=180)
    if p.returncode:raise RuntimeError('partial sample metadata recovery failed')
    samples=json.loads(p.stdout); units={}
    if samples['saved_version']!=version:raise ValueError('producer changed during inspection')
    specs={s['name']:s for s in json.loads((stage/'params.json').read_text())['units']}
    for unit,(r,path,digest) in banks.items():
        s=specs[unit]
        if not r['complete'] or r['cells_in']!=s['cells'] or r['cells_used']+r['zero_depth_excluded']!=s['cells']:
            raise ValueError('partial bank coverage differs')
        if r['source_verification']!=s['receipt_sha256'] or not all('bank/'+unit+'/'+n in files for n in r['files']):
            raise ValueError('partial bank lineage/output differs')
        b={'state':'remote_complete_manifest_checked','kernel':job,'receipt':path,'receipt_sha256':digest,
           'saved_version':version,'files':r['files'],'cells_used':r['cells_used'],'contexts':r['contexts'],'relative_path':'bank/'+unit}
        item={'bank':b,'samples':{'state':'not_complete'},'trainer':{'state':'not_integrated','training_used':False}}
        if unit in samples['receipts']:
            item['samples']=validate({'parameters':{'unit':unit,'bank_receipt_sha256':digest},
                'slug':job,'code_sha256':prepared['code_sha256']},samples,{'bank':b})
            item['samples']['relative_path']='samples/'+unit
        units[unit]=item
    (out/'state.json').write_text(json.dumps({'kernel':job,'units':units,'saved_version':version},indent=1))
    print(json.dumps({u:{'bank':i['bank']['state'],'samples':i['samples']['state']} for u,i in units.items()}))


if __name__=='__main__':main()
