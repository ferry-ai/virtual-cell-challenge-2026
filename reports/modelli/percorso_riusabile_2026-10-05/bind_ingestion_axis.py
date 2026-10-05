"""Recover the nominal gene axis from frozen accepted ingestion launches, not legacy guesses."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from pipeline_state import REPO, sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True)
    p.add_argument('--axis',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();state=json.loads(a.state.read_text());axis_sha=sha(a.axis)
    with a.axis.open(newline='',encoding='utf-8') as f:
        names=[r['gene_name'] for r in csv.DictReader(f)]
    if len(names)!=18533 or len(set(names))!=len(names) or not all(names):
        raise ValueError('nominal axis invalid')
    ledger=REPO/'reports/sorgenti/ingestione_completa_2026-10-03/kaggle_cpu/lancio_cd4_r1.jsonl'
    launches=[r for r in map(json.loads,ledger.read_text().splitlines()) if r.get('accepted')]
    jobs=sorted({j for info in state['units'].values() for j in info['raw']['kernel_sources']})
    proof=[]
    for job in jobs:
        candidates=[r for r in launches if r['slug']==job]
        if len(candidates)!=1:
            raise ValueError('missing/ambiguous ingestion launch: '+job)
        launch=candidates[0];source=Path(launch['stage'])/'run.py';text=source.read_text(encoding='utf-8')
        if launch['run_sha256'] not in {sha(source),hashlib.sha256(text.encode()).hexdigest()}:
            raise ValueError('frozen ingestion code changed')
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.Assign)
                  and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        params=json.loads(ast.literal_eval(node.value.args[0]))
        if params['axis_sha256']!=axis_sha:
            raise ValueError('ingestion axes differ')
        proof.append({'kernel':job,'run_sha256':launch['run_sha256'],'axis_sha256':axis_sha,
                      'code_dataset':job.split('/')[0]+'/'+params['code_slug']})
    result={'axis_file':str(a.axis.resolve()),'axis_sha256':axis_sha,'genes':len(names),
            'ordering':'gene_name CSV row order, zero based official_index',
            'ingestion_launches':proof,'consumer_axis_verified':False,
            'required_consumer_check':'Hash mounted gene_names.csv before constructing any gene/descriptor mapping.'}
    a.out.open('x',encoding='utf-8').write(json.dumps(result,indent=1))
    print(json.dumps({'genes':len(names),'ingestion_launches_bound':len(proof),'axis_sha256':axis_sha}))


if __name__=='__main__':
    main()
