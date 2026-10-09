"""Build pinned private runtime templates; never launch or manufacture input PASS."""
import argparse
import csv
import json
from pathlib import Path
import shutil
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATI=ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
VALID=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08'
DATA=Path('C:/Users/ferra/vcc2026-data')
CODE=['run_ammi_v4.py','ammi_inputs_v4.py','ammi_inputs_v3.py','ammi_controls_v4.py',
      'ammi_encoder_v4.py','ammi_guard_v4.py','ammi_train_v4.py','ammi_context.py',
      'ammi_contract_v2.py','ammi_io_v4.py','ammi_resolve_v4.py','ammi_bootstrap_v4.py','pie_adapter.py','ammi_timing_v1.py']

def pin(path):
    path=Path(path);return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def build(fold_name,mode,out,ntc_contract,verifications,authorization,production_readout=None):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    if out.resolve().is_relative_to(ROOT):raise ValueError('numeric metadata package belongs outside public Git')
    production=fold_name=='production'
    if mode not in ('cells','none') or (production and mode!='cells'):raise ValueError('undeclared fit')
    cp=DATI/('panel_anchor_requests_production_r1.json' if production else 'panel_anchor_requests_r1.json')
    contract=read(cp);fold=contract['folds'][fold_name];view=read(checked(fold['view']))
    anchor=read(DATI/('production_anchors_verified_r1.json' if production else 'ammi_anchors_verified_r1.json'))
    if anchor['status']!='PASS':raise ValueError('verified numeric anchors required')
    ntc=read(ntc_contract)
    known={};origins={};relocations={}
    for path in verifications:
        report=read(path)
        if not report.get('status','').startswith('PASS'):raise ValueError('NTC verification not PASS')
        verified_parts=report.get('parts',{})
        # Restoration reports list part IDs; their file pins are checked below.
        if isinstance(verified_parts,list):verified_parts={}
        for key,value in verified_parts.items():
            if key in known and known[key]['completion']['sha256']!=value['completion']['sha256']:
                raise ValueError('conflicting NTC completion')
            known[key]=value;origins[key]=str(path)
        if report.get('receipt') and report.get('files'):
            restored=read(checked(report['receipt']))
            if restored.get('status')!='COMPLETE':raise ValueError('relocation incomplete')
            for entry in restored['files']:
                if entry['file'].endswith('/complete.json'):
                    relocations[entry['sha256']]=report['receipt']
    expected=ntc['folds'][fold_name]['ntc_expected_parts'] if not production else {k:v['plan_sha256'] for k,v in ntc['parts'].items()}
    if production:
        expected=dict(expected,**{k:v['plan_sha256'] for k,v in known.items() if v.get('part_role')=='destination'})
    missing=sorted(set(expected)-set(known))
    if missing:raise ValueError('verified NTC completions missing: '+','.join(missing))
    parts=[]
    for key in sorted(expected):
        verified=known[key];req=ntc['parts'].get(key,verified)
        completion=read(checked(verified['completion']))
        if completion['plan_sha256']!=expected[key] or completion['code']!=req['producer_code']:
            raise ValueError('NTC producer/plan differs')
        part=dict(req,completion=verified['completion'],verification=pin(origins[key]))
        if req.get('relocation_requires_receipt'):
            relocation=verified.get('relocation_receipt',relocations.get(verified['completion']['sha256']))
            if not relocation:raise ValueError('relocation pin absent: '+key)
            part['relocation_receipt']=relocation
        parts.append(part)
    with checked(contract['panel']).open(newline='',encoding='utf-8') as stream:
        panel=[r['target_gene'] for r in csv.DictReader(stream)]
    chunks={c['sha256']:c for c in view['chunks'] if fold['contexts'][c['context_id']]['role']=='training'
            and any(t in panel and t!='TMEM104' for t in c['targets'])}
    assets={Path(i['path']).name:i for i in read(HERE/'public_audit_r1.json')['acquisition_plan'] if i['path'].startswith('esm2/')}
    feature_hash=read(HERE/'feature_coverage_r1.json')['esm2_sha256']
    assets={k:dict(bytes=v['bytes'],sha256=feature_hash[k],url=v['url']) for k,v in assets.items()}
    esm=DATA/'external_models/01a11c35/PIE_sources/cb1aaa4e7655605bdc70a9bd77bbd62016b8c7d7/esm2'
    feature_pins={k:dict(path=str(esm/name),**{a:assets[name][a] for a in ('bytes','sha256')})
                  for k,name in [('array','embeddings.npy'),('meta','meta.json')]}
    contexts=ntc['folds'][fold_name]['required_contexts'] if not production else sorted({c for p in parts for c in read(checked(p['completion']))['contexts']})
    # A fold view deliberately omits its outer lineage; routing comes from the
    # union of the original frozen fold contracts, never inferred from names.
    lineages={c:i['lineage'] for f in contract['folds'].values() for c,i in f['contexts'].items()}
    queries={c:g for c,g in lineages.items() if g==fold.get('outer')} if not production else {c:'destination' for c in ('A','B','C')}
    if not queries or not set(queries)<=set(contexts):raise ValueError('query controls/lineage routing incomplete')
    needed={r['anchor_id'] for r in fold['contexts'].values()}|{fold['outer_query_anchor']}
    if fold.get('inner_query_anchor'):needed.add(fold['inner_query_anchor'])
    spec=dict(schema='AMMI-biological-runtime/4',status='ready',mode='production' if production else 'pilot',
        fold=fold_name,protocol=pin(HERE/'PROTOCOLLO_AMMI_r2.md'),authorization=pin(authorization),
        phase_mandate=pin(HERE/'CONTRATTO_CHIUSURA_AMMI_r4.md'),anchor_contract=pin(cp),
        view=fold['view'],panel=panel,panel_file=contract['panel'],anchor_completion=anchor['completion'],
        anchors={k:anchor['anchors'][k]['effects'] for k in needed},ntc_parts=parts,
        ntc_expected_parts=expected,ntc_contexts=contexts,ntc_context_lineages=lineages,
        ntc_reader=ntc['reader'],queries=queries,features=feature_pins,public_assets=assets,
        chunk_pins=chunks,chunk_locations={},metrics=pin(VALID/'banco/metrics.py'),
        code={n:sha256(HERE/n) for n in CODE},
        staging_root='/kaggle/temp/ammi-'+fold_name.lower()+'-'+mode+'-17-r4/controls')
    if production:
        if production_readout is None:raise ValueError('frozen pilot readout decision required')
        spec['production_readout']=pin(production_readout);spec['destination_contexts']=['A','B','C']
        if not set(spec['destination_contexts'])<=set(contexts):raise ValueError('official destination parts missing')
    else:
        routing=read(DATI/('ammi_inner_truth_'+fold_name+'_r1.json'))
        routes=[]
        for route in routing['routes']:
            table=routing['tables'][route['table']]
            truth=dict(path=table.get('file',table.get('suffix',route['table']+'.npz')),bytes=table['bytes'],sha256=table['sha256'])
            role=route['role'] if fold_name=='C-K562' else ('primary' if route['context_id'].startswith('k562_gwps:') else 'descriptive')
            routes.append(dict(route,role=role,truth=truth))
        spec['guard']=dict(review_status='existing-contract-applied',review_pin=pin(VALID/'PROTOCOLLO_v1.md'),
            routing_basis=spec['phase_mandate'],truth_replication_policy='one table is one reference; context results never pooled as independent truths',
            rule='anchor-shuffle-disc95-lo-positive; structural-residual-r2; no-benefit-threshold',
            axis=routing['axis'],routes=routes)
    out.mkdir(parents=True);embedded=out/'assets';embedded.mkdir()
    def capture(value):
        if isinstance(value,dict):
            if set(('path','bytes','sha256'))<=set(value):
                p=Path(value['path'])
                if p.exists() and p.suffix in ('.json','.md','.csv','.py'):
                    checked(value);dest=embedded/value['sha256']
                    if not dest.exists():shutil.copyfile(p,dest)
            for v in value.values():capture(v)
        elif isinstance(value,list):
            for v in value:capture(v)
    capture(spec)
    for name in CODE:shutil.copyfile(HERE/name,out/name)
    write(out/'runtime_template.json',spec)
    receipt=dict(status='TEMPLATE_READY_ACCESS_AND_PREFLIGHT_REQUIRED',fold=fold_name,mode=mode,
        template=pin(out/'runtime_template.json'),code=spec['code'],
        embedded={p.name:pin(p) for p in embedded.iterdir()},no_cloud_job_launched=True)
    write(out/'prepared.json',receipt);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for key in ('fold','mode','out','ntc-contract','authorization'):p.add_argument('--'+key,required=True)
    p.add_argument('--ntc-verifications',nargs='+',required=True);p.add_argument('--production-readout');a=p.parse_args()
    result=build(a.fold,a.mode,a.out,a.ntc_contract,a.ntc_verifications,a.authorization,a.production_readout)
    print(json.dumps(dict(status=result['status'],template=result['template'])))
