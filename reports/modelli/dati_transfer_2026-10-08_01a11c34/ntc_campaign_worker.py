"""Cloud CPU worker for assigned native NTC parts, with immutable outputs."""
import json
from pathlib import Path
import traceback
from collections import Counter
import h5py
from ntc_cells import sha, gene_mapping
from run_ntc_extraction import run


def main(work=Path('/kaggle/working'), inputs=Path('/kaggle/input')):
    config=json.loads((work/'job.json').read_text())
    raw=list(inputs.rglob('*.h5ad'))
    results=[]; resolved=[]; schemas=Counter()
    for item in config['parts']:
        plan_path=work/item['plan']; plan=json.loads(plan_path.read_text())
        locations={}
        for source in plan['sources']:
            basename=Path(source['file']).name
            hits=[p for p in raw if p.name==basename and
                  (source.get('bytes') is None or p.stat().st_size==source['bytes'])]
            if len(hits)!=1:
                hits=[p for p in hits if sha(p)==source['sha256']]
            if len(hits)!=1:
                raise ValueError('raw source missing/ambiguous: '+basename)
            locations[source['sha256']]=str(hits[0])
        path=work/(plan['part_id']+'_locations.json')
        path.write_text(json.dumps(locations))
        genes=json.loads((plan_path.parent/plan['genes_file']).read_text())
        for source in plan['sources']:
            # Schema-only preflight, not admission of data. The extractor still
            # verifies every full source hash before selecting or reading RNA.
            with h5py.File(locations[source['sha256']],'r') as h5:
                gene_mapping(h5,genes)
                node=h5['var/symbol']
                schemas[json.dumps(dict(encoding=str(node.attrs.get('encoding-type','')),
                    children=sorted(node.keys()) if isinstance(node,h5py.Group) else []),sort_keys=True)]+=1
        resolved.append((item,plan_path,plan,path))
    (work/'schema_preflight.json').write_text(json.dumps(dict(status='PASS',
        files=sum(schemas.values()),symbol_schemas=dict(schemas),RNA_rows_read=0,
        source_hash_admission='performed later by extractor before selection'),indent=2))
    for item,plan_path,plan,path in resolved:
        result=run(plan_path,item['plan_sha256'],path,work/item['rows'],work/'ntc'/plan['part_id'])
        results.append(dict(part_id=plan['part_id'],contexts=result['contexts'],
                            cells=result['NTC_cells_read']))
        (work/'progress.json').write_text(json.dumps(results))
    (work/'campaign_complete.json').write_text(json.dumps(dict(status='COMPLETE',parts=results,
        control_inputs_only=True,trainer_cells_consumed=0,complete_D053=False),indent=2))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        Path('/kaggle/working/failure.json').write_text(json.dumps(dict(
            status='ERROR',error_type=type(exc).__name__,message=str(exc))))
        raise
