"""Four initial pilot fits and a distinct production fit, all using real CUDA.

One architecture: cells/none, seed 17, on two frozen folds. Swapped is diagnostic
inference, never another fit. Production has a separately pinned anchor contract
and no claim that readmitted training rows remain independent validation.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time

import numpy as np
import torch

from ammi_inputs_v3 import checked, read_json
from ammi_inputs_v4 import load_anchors, training_data
from ammi_controls_v4 import stage_controls, resources_required, available_memory
from ammi_encoder_v4 import control_shape, ControlsNotConsumed
from ammi_guard_v4 import inner_guard, predict
from ammi_train_v4 import fit
from ammi_contract_v2 import export_residual, swapped_contexts
from ammi_io_v4 import features, write, save_checkpoint, reload_checkpoint
from pie_adapter import sha256
from ammi_timing_v1 import measured

PILOT_FITS=[(f,m,17) for f in ('C-K562','C-iPSC') for m in ('cells','none')]


def query_export(model,x,available,query,controls,anchor,anchor_pin,panel,genes,out,training_contexts,mode):
    """Native export failure is fatal; swapped failure is retained as diagnostics."""
    exports=[];failures=[]
    swaps=swapped_contexts(list(query),list(query.values()),training_contexts) if mode=='cells' else []
    for i,context in enumerate(query):
        prediction,residual,diagnostics=predict(model,x,available,context,controls,anchor['lfc'],anchor['observed'])
        name='query_%03d_native.npz'%i
        exported=export_residual(anchor_pin['path'],anchor_pin['sha256'],residual,
            anchor['observed'],panel,genes,out/name,context)
        exports.append(dict(context_id=context,control_context_id=context,intervention='native',file=name,receipt=exported))
        # Each valid native output gets an immediate receipt before a diagnostic.
        write(out/('query_%03d_native.json'%i),exports[-1])
        if not swaps:continue
        control=swaps[i]
        try:
            prediction,residual,diagnostics=predict(model,x,available,control,controls,anchor['lfc'],anchor['observed'])
            name='query_%03d_swapped.npz'%i
            exported=export_residual(anchor_pin['path'],anchor_pin['sha256'],residual,
                anchor['observed'],panel,genes,out/name,context)
            exports.append(dict(context_id=context,control_context_id=control,intervention='swapped',file=name,receipt=exported))
        except ValueError as error:
            item=dict(context_id=context,control_context_id=control,intervention='swapped',
                status='GUARD_FAILED_DIAGNOSTIC_ONLY',error=str(error),native_export_preserved=True,
                new_fit_required=False)
            write(out/('query_%03d_swapped_failed.json'%i),item);failures.append(item)
    return exports,failures


def run(manifest_path,digest,mode,seed,out,*,runtime_resolver=None):
    path,out=Path(manifest_path),Path(out)
    if sha256(path)!=digest:raise ValueError('runtime manifest changed')
    spec=json.loads(path.read_text(encoding='utf-8'))
    production=spec.get('mode')=='production'
    valid_choice=(spec.get('fold'),mode,seed) in PILOT_FITS if not production else (spec.get('fold')=='production' and mode=='cells' and seed==17)
    if spec.get('schema')!='AMMI-biological-runtime/4' or spec.get('status')!='ready' or not valid_choice:
        raise ValueError('ready initial-pilot or distinct production contract required')
    if out.exists():raise FileExistsError(out)
    if not torch.cuda.is_available():raise RuntimeError('biological training requires actual CUDA')
    required=('run_ammi_v4.py','ammi_inputs_v4.py','ammi_inputs_v3.py','ammi_controls_v4.py',
        'ammi_encoder_v4.py','ammi_guard_v4.py','ammi_train_v4.py','ammi_context.py',
        'ammi_contract_v2.py','ammi_io_v4.py','ammi_resolve_v4.py','ammi_bootstrap_v4.py','pie_adapter.py','ammi_timing_v1.py')
    for name in required:
        if sha256(Path(__file__).with_name(name))!=spec['code'][name]:raise ValueError('runtime code differs: '+name)
    checked(spec['protocol']);checked(spec['authorization']);checked(spec['phase_mandate'])
    contract=read_json(spec['anchor_contract']);fold=contract['folds'][spec['fold']]
    if (fold.get('mode')=='production')!=production:raise ValueError('production/pilot anchor contract mismatch')
    view=read_json(spec['view'])
    if spec['view']['sha256']!=fold['view']['sha256']:raise ValueError('view differs from anchor contract')
    if not production and contract['protocol']['sha256']!=spec['protocol']['sha256']:
        raise ValueError('nested anchor protocol differs')
    if production:
        checked(spec['production_readout'])
        readout=read_json(spec['production_readout'])
        if (set(readout['folds'])!={'C-K562','C-iPSC'}
                or any(not readout['folds'][f].get('cells_minus_T0_read') or not readout['folds'][f].get('cells_minus_none_read') for f in readout['folds'])
                or readout.get('production_technical_fit_decision')!='proceed'):
            raise ValueError('both frozen pilot comparisons must be read before production decision')
    genes=view['genes'];panel=spec['panel']
    import csv
    with checked(spec['panel_file']).open(newline='',encoding='utf-8') as stream:
        expected_panel=[r['target_gene'] for r in csv.DictReader(stream)]
    if (panel!=expected_panel or spec['panel_file']['sha256']!=contract['panel']['sha256']
            or len(set(genes))!=len(genes) or len(set(panel))!=len(panel)):
        raise ValueError('frozen panel/axes differ')
    staging=Path(spec['staging_root'])
    if not str(staging).startswith('/kaggle/temp/') or staging.exists():
        raise ValueError('fresh temporary sparse staging path outside output required')
    started=time.monotonic();out.mkdir(parents=True)
    control_free=spec.get('controls_not_consumed') is True
    if control_free:
        if mode!='none' or production or spec['ntc_parts']:raise ValueError('invalid control-free pilot')
        checked(spec['control_free_amendment']);checked(spec['control_free_equivalence'])
    resource=dict(controls_not_consumed=True) if control_free else resources_required(spec['ntc_parts'])
    write(out/'preflight.json',dict(utc=datetime.now(timezone.utc).isoformat(),
        manifest_sha256=digest,mode=mode,seed=seed,cuda_free=torch.cuda.mem_get_info()[0],
        available_RAM=available_memory(),free_disk=shutil.disk_usage(out).free,cpu_count=os.cpu_count(),
        cuda_device=torch.cuda.get_device_name(0),resources_required=resource,
        versions=dict(torch=torch.__version__,numpy=np.__version__,cuda=torch.version.cuda)))
    anchors=measured(out,'anchors',load_anchors,contract,spec['anchor_completion'],spec['anchors'],fold,genes,panel)
    if control_free:
        controls=ControlsNotConsumed(spec['ntc_contexts'],len(genes))
        ntc_audit=dict(status='NOT_CONSUMED_BY_DESIGN',controls_not_consumed=True,
            declared_contexts=sorted(controls.contexts),control_genes=len(genes),
            no_synthetic_controls=True,NTC_completeness_not_asserted=True)
    else:
        controls,ntc_audit=measured(out,'controls',stage_controls,spec['ntc_parts'],genes,spec['ntc_contexts'],
            spec['ntc_reader'],spec['ntc_expected_parts'],staging)
    x,available=measured(out,'features',features,spec['features'],panel)
    locations=spec.get('chunk_locations',{})
    if runtime_resolver is not None:
        from ammi_resolve_v4 import ResponseLocations
        locations=ResponseLocations(runtime_resolver,spec['chunk_pins'])
    data,row_audit=measured(out,'responses',training_data,view,fold,anchors,panel,x,available,locations,
                               digest,spec['anchor_completion']['sha256'])
    query=spec['queries']
    if not query or not set(query)<=set(controls):raise ValueError('query controls missing')
    if production:
        if set(query)!=set(spec['destination_contexts']):raise ValueError('production destination coverage differs')
    else:
        expected={c for c,g in spec['ntc_context_lineages'].items() if g==fold['outer']}
        if set(query)!=expected or any(g!=fold['outer'] for g in query.values()):
            raise ValueError('outer query context routing differs')
    anchor_id=fold['outer_query_anchor'];anchor=anchors[anchor_id];anchor_pin=spec['anchors'][anchor_id]
    if production:
        baseline={}
        def guard(model,epoch):
            reports={}
            for context in query:
                _,_,reports[context]=predict(model,x,available,context,controls,anchor['lfc'],anchor['observed'])
            return dict(epoch=epoch,query_structural=reports,truth_read=False,independent_validation=False,**{'pass':True})
    else:
        if spec['guard']['axis']['sha256']!=contract['axis']['sha256']:raise ValueError('guard gene axis differs')
        guard,baseline=measured(out,'inner_baseline',inner_guard,spec['guard'],fold,spec['metrics'],controls,anchors,x,available,panel,genes)
    write(out/'input_audit.json',dict(ntc=ntc_audit,training=row_audit,inner_baseline=baseline,
        mode=spec['mode'],missing_features=[t for t,a in zip(panel,available) if not a]))
    export_residual(anchor_pin['path'],anchor_pin['sha256'],np.zeros_like(anchor['lfc']),
        anchor['observed'],panel,genes,out/'zero_residual_parity.npz','anchor-parity')
    checkpoint_history=[]
    def checkpoint_epoch(model,epoch,audit):
        saved=save_checkpoint(model,out/('checkpoint_epoch%d.pt'%epoch),dict(manifest_sha256=digest,
            mode=mode,seed=seed,epoch=epoch,guard_not_yet_checked=True))
        checkpoint_history.append(saved)
        write(out/('epoch%d_before_guard.json'%epoch),dict(checkpoint=saved,coverage=audit))
    try:
        excluded=[] if production else [fold['outer'],fold['inner']]
        model,receipt=measured(out,'fit',fit,data,controls,excluded,mode,seed,guard,checkpoint_callback=checkpoint_epoch)
        receipt['controls_not_consumed']=control_free
        receipt['controls_used_by_training']={} if control_free else {c:control_shape(controls[c])[0] for c in sorted(set(data['contexts']))}
        write(out/'training_receipt.json',receipt)
        checkpoint=save_checkpoint(model,out/'checkpoint.pt',dict(manifest_sha256=digest,mode=mode,seed=seed))
        restored,identity=reload_checkpoint(checkpoint,torch.device('cuda'))
        if identity!=dict(manifest_sha256=digest,mode=mode,seed=seed):raise ValueError('checkpoint identity differs')
        for key,tensor in model.state_dict().items():
            if not torch.equal(tensor,restored.state_dict()[key]):raise ValueError('checkpoint state differs')
        context=next(iter(query))
        a,_,_=predict(model,x,available,context,controls,anchor['lfc'],anchor['observed'])
        b,_,_=predict(restored,x,available,context,controls,anchor['lfc'],anchor['observed'])
        if not np.array_equal(a,b):raise ValueError('checkpoint prediction parity failed')
        training_contexts={c:fold['contexts'][c]['lineage'] for c in set(data['contexts'])}
        exports,diagnostics=measured(out,'exports',query_export,restored,x,available,query,controls,anchor,anchor_pin,
            panel,genes,out,training_contexts,mode if not production else 'production')
        write(out/'complete.json',dict(status='COMPLETE',manifest_sha256=digest,fold=spec['fold'],
            mode=mode,seed=seed,checkpoint=checkpoint,exports=exports,diagnostic_failures=diagnostics,
            seconds=time.monotonic()-started,device='cuda',complete_D053=False,
            training_receipt_sha256=sha256(out/'training_receipt.json'),
            scientific_benefit='requires frozen comparative readout',no_outer_truth_read=True))
    except Exception as error:
        write(out/'failure.json',dict(status='FAILED',error_type=type(error).__name__,error=str(error),
            manifest_sha256=digest,checkpoints=checkpoint_history,seconds=time.monotonic()-started,
            no_automatic_refit=True))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    for field in ('manifest','sha256','mode','out'):parser.add_argument('--'+field,required=True)
    parser.add_argument('--seed',type=int,default=17)
    args=parser.parse_args();run(args.manifest,args.sha256,args.mode,args.seed,args.out)
