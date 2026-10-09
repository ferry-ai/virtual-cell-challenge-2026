"""Materialize pinned input requirements and shared helpers, without transfer."""
import json
from pathlib import Path
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATI=ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'

def pin(path):
    path=Path(path)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))

def prepare():
    contract=json.loads((DATI/'panel_anchor_requests_r1.json').read_text())
    audit=json.loads((HERE/'public_audit_r1.json').read_text())
    hashes=json.loads((HERE/'feature_coverage_r1.json').read_text())['esm2_sha256']
    assets={Path(x['path']).name:dict(x,sha256=hashes[Path(x['path']).name])
            for x in audit['acquisition_plan'] if x['path'].startswith('esm2/')}
    result=dict(schema='AMMI-input-dependencies/4',account='davidmaisterx',
                anchor_contract=pin(DATI/'panel_anchor_requests_r1.json'),features=assets,folds={})
    import csv
    with Path(contract['panel']['path']).open(encoding='utf-8',newline='') as f:
        panel={r['target_gene'] for r in csv.DictReader(f)}
    for name,fold in contract['folds'].items():
        view=json.loads(Path(fold['view']['path']).read_text())
        chunks=[x for x in view['chunks'] if fold['contexts'][x['context_id']]['role']=='training'
                and any(t in panel and t!='TMEM104' for t in x['targets'])]
        result['folds'][name]=dict(view=fold['view'],excluded_lineages=[fold['outer'],fold['inner']],
            chunks=chunks,unique_bytes=sum(x['bytes'] for x in {c['sha256']:c for c in chunks}.values()),
            contexts=sorted({c['context_id'] for c in chunks}),
            view_unchanged=True,outer_inner_response_files_not_required=True)
    out=Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_input_dependencies_r4.json')
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(manifest=pin(out),folds={k:dict(chunks=len(v['chunks']),bytes=v['unique_bytes']) for k,v in result['folds'].items()})))

if __name__=='__main__':prepare()
