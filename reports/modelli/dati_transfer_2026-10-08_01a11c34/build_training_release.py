"""Assemble one explicit production/T view, retaining donors and clone contexts."""
import argparse
from training_view import build
from percorso import DATA,HERE,now,pin,read,write_new


def main(regime,revision):
    byunit={}
    revisions=('01a11c34-r3','01a11c34-r4private') if regime=='production' else ('01a11c34-tj1','01a11c34-tj2private')
    for rev in revisions:
        for verification in (HERE/'alltargets'/rev).glob('*/completion_*/verification.json'):
            unit=verification.parent.parent.name
            if unit in byunit:raise ValueError('duplicate accepted unit')
            byunit[unit]=verification.parent
    expected={u for u,r in read(HERE/'alltargets/01a11c34-r3/inventory.json')['units'].items() if r['state']=='package_ready'}
    if set(byunit)!=expected:raise ValueError('campaign receipt gap: '+str(sorted(expected-set(byunit))))
    for unit in ('h1_train','h1_val','k562_gwps_a','k562_gwps_b'):byunit.pop(unit)
    jointrev='01a11c34-j2'+('p' if regime=='production' else 't')
    for unit in ('h1','k562_gwps'):
        verified=list((HERE/'joint'/jointrev/unit).glob('completion_*/verification.json'))
        if len(verified)!=1:raise ValueError('joint unit missing: '+unit)
        byunit[unit]=verified[0].parent
    out=DATA/'processed/dati_transfer_2026-10-08_01a11c34/training_views'/revision
    out.mkdir(parents=True,exist_ok=False);path=out/'view.json'
    build([byunit[u] for u in sorted(byunit)],path)
    view=read(path)
    write_new(HERE/('training_release_'+revision+'.json'),dict(utc=now(),regime=regime,
        view=pin(path),inputs=pin(out/'view_inputs.json'),split=pin(out/'view_split.json'),
        response_shape=view['response_shape'],contexts=len(view['expected_rows_by_context']),
        chunks=len(view['chunks']),mmap_bytes=view['mmap_bytes'],
        pipeline_role='CRISPRi training contract; KO and activation are separate mechanism arms',
        excluded=view['excluded'],claims_complete_corpus=False,model_fit=False,arrays_independently_rehashed=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('regime',choices=['production','T']);parser.add_argument('revision')
    a=parser.parse_args();main(a.regime,a.revision)
