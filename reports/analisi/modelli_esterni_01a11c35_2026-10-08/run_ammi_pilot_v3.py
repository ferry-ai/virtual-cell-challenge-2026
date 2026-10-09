"""Run one predeclared AMMI arm/seed on CUDA with pinned mounted inputs.

No network, quota allocation, external scoring, tuning or submission. A complete
runtime manifest is produced only after DATI has published numeric artifacts and
VALIDAZIONE has reviewed the inner truth/control routing. Paths are runtime-local.
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

from ammi_context import ContextCorrection
from ammi_inputs_v3 import checked, read_json, load_ntc, load_anchors, training_data
from ammi_guard_v3 import inner_guard, predict
from ammi_contract_v2 import export_residual, swapped_contexts
from ammi_train_v2 import fit
from pie_adapter import sha256

ARMS = [('cells', 17), ('cells', 29), ('cells', 43),
        ('none', 17), ('none', 29), ('none', 43), ('mean', 17)]


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def features(spec, panel):
    meta = read_json(spec['meta'])
    array = np.load(checked(spec['array']), mmap_mode='r', allow_pickle=False)
    keys = meta['keys']
    if (len(set(keys)) != len(keys) or meta['name'] != 'esm2' or meta['index'] != 'pert'
            or meta['layout'] != 'dense' or array.shape != (len(keys), meta['dim'])
            or array.dtype != np.dtype(meta['dtype'])):
        raise ValueError('ESM2 identity/axes differ')
    positions = {t:i for i,t in enumerate(keys)}
    available = np.array([t in positions for t in panel], dtype=bool)
    result = np.zeros((len(panel), meta['dim']), dtype=np.float32)
    for i, t in enumerate(panel):
        if available[i]: result[i] = array[positions[t]]
    if not np.isfinite(result).all(): raise ValueError('nonfinite ESM2 features')
    return result, available


def save_checkpoint(model, path, identity):
    torch.save(dict(state={k: v.detach().cpu() for k,v in model.state_dict().items()},
                    control_genes=model.control_genes, response_genes=model.decoder.out_features,
                    context_mode=model.context_mode, identity=identity), path)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=sha256(path))


def reload_checkpoint(pin, device):
    payload = torch.load(checked(pin), map_location='cpu', weights_only=True)
    model = ContextCorrection(payload['control_genes'], payload['response_genes'],
        payload['state']['reference_mean'], context_mode=payload['context_mode'])
    model.load_state_dict(payload['state'], strict=True)
    return model.to(device).eval(), payload['identity']


def run(manifest_path, digest, mode, seed, out):
    path, out = Path(manifest_path), Path(out)
    if sha256(path) != digest: raise ValueError('runtime manifest changed')
    spec = json.loads(path.read_text(encoding='utf-8'))
    if (spec.get('schema') != 'AMMI-biological-runtime/3' or spec.get('status') != 'ready'
            or spec['fold'] not in ('C-K562', 'C-iPSC') or (mode, seed) not in ARMS):
        raise ValueError('ready frozen pilot manifest/arm required')
    if out.exists(): raise FileExistsError(out)
    if not torch.cuda.is_available(): raise RuntimeError('biological fit requires actual CUDA')
    # A manifest pins code as well as data. A bootstrap must validate this list
    # before executing the entrypoint; here we also attest the running module set.
    required = ('run_ammi_pilot_v3.py','ammi_inputs_v3.py','ammi_guard_v3.py',
                'ammi_context.py','ammi_train_v2.py','ammi_contract_v2.py','pie_adapter.py')
    for name in required:
        if sha256(Path(__file__).with_name(name)) != spec['code'][name]:
            raise ValueError('runtime code differs: '+name)
    checked(spec['protocol'])
    checked(spec['authorization'])
    contract = read_json(spec['anchor_contract'])
    if contract['protocol']['sha256'] != spec['protocol']['sha256']:
        raise ValueError('anchor/model protocol differs')
    fold = contract['folds'][spec['fold']]
    view = read_json(spec['view'])
    if spec['view']['sha256'] != fold['view']['sha256']:
        raise ValueError('training view differs from anchor contract')
    genes = view['genes']; panel = spec['panel']
    if len(set(genes)) != len(genes) or len(set(panel)) != len(panel):
        raise ValueError('duplicate axes')
    # The panel CSV is hashed independently; values/order must also be exact.
    import csv
    with checked(spec['panel_file']).open(newline='', encoding='utf-8') as stream:
        frozen_panel = [r['target_gene'] for r in csv.DictReader(stream)]
    if panel != frozen_panel or spec['panel_file']['sha256'] != contract['panel']['sha256']:
        raise ValueError('panel order changed')
    root = out.parent
    while not root.exists(): root = root.parent
    import psutil
    resources = dict(cpu_count=os.cpu_count(), available_RAM=psutil.virtual_memory().available,
        free_disk=shutil.disk_usage(root).free, cuda_free=torch.cuda.mem_get_info()[0],
        cuda_device=torch.cuda.get_device_name(0), utc=datetime.now(timezone.utc).isoformat())
    # Counts derive from signed completions, not an assumed machine capacity.
    ntc_cells = sum(sum(read_json(p['completion'])['contexts'].values()) for p in spec['ntc_parts'])
    estimate = ntc_cells*len(genes)*10 + len(fold['contexts'])*64*len(genes)*16 + (1<<30)
    if resources['available_RAM'] < estimate or resources['free_disk'] < 1<<30:
        raise RuntimeError('measured runtime resources below input-derived memory/disk estimate')
    resources['estimated_RAM_required'] = estimate
    started = time.monotonic()
    out.mkdir(parents=True, exist_ok=False)
    write(out/'preflight.json', dict(resources, manifest_sha256=digest, mode=mode, seed=seed))
    anchors = load_anchors(contract, spec['anchor_completion'], spec['anchors'], fold, genes, panel)
    controls, ntc_audit = load_ntc(spec['ntc_parts'], genes, spec['ntc_contexts'],
                                 spec['ntc_reader'], spec['ntc_expected_parts'])
    query = spec['outer_queries']
    expected_outer = {c for c,g in spec['ntc_context_lineages'].items() if g == fold['outer']}
    if (set(query) != expected_outer or not expected_outer or not set(query) <= set(controls)
            or set(spec['ntc_context_lineages']) != set(spec['ntc_contexts'])):
        raise ValueError('outer NTC context coverage/routing differs')
    x, available = features(spec['features'], panel)
    data, row_audit = training_data(view, fold, anchors, panel, x, available,
        spec['chunk_locations'], digest, spec['anchor_completion']['sha256'])
    if spec['guard']['axis']['sha256'] != contract['axis']['sha256']:
        raise ValueError('guard axis differs from frozen validation axis')
    guard, baseline = inner_guard(spec['guard'], fold, spec['metrics'], controls,
        anchors, x, available, panel, genes)
    write(out/'input_audit.json', dict(ntc=ntc_audit, training=row_audit,
        inner_baseline=baseline, missing_features=[t for t,a in zip(panel,available) if not a]))
    anchor_id = fold['outer_query_anchor']; anchor = anchors[anchor_id]
    anchor_pin = spec['anchors'][anchor_id]
    # Byte-for-byte null export, tested before consuming training quota.
    export_residual(anchor_pin['path'], anchor_pin['sha256'], np.zeros_like(anchor['lfc']),
        anchor['observed'], panel, genes, out/'zero_residual_parity.npz', 'outer-anchor-parity')
    model, receipt = fit(data, controls, [fold['outer'], fold['inner']], mode, seed, guard)
    receipt['input_audit_sha256'] = sha256(out/'input_audit.json')
    receipt['controls_used_by_training'] = {c: len(controls[c][0]) for c in sorted(set(data['contexts']))}
    checkpoint = save_checkpoint(model, out/'checkpoint.pt', dict(manifest_sha256=digest, mode=mode, seed=seed))
    restored, identity = reload_checkpoint(checkpoint, torch.device('cuda'))
    if identity != dict(manifest_sha256=digest, mode=mode, seed=seed):
        raise ValueError('checkpoint identity changed')
    for key, tensor in model.state_dict().items():
        if not torch.equal(tensor, restored.state_dict()[key]): raise ValueError('checkpoint state changed')
    exports = []
    train_contexts = {c:fold['contexts'][c]['lineage'] for c in set(data['contexts'])}
    swaps = swapped_contexts(query, [fold['outer']]*len(query), train_contexts) if mode == 'cells' else []
    for i, context in enumerate(query):
        for intervention, control_context in [('native',context)] + ([('swapped',swaps[i])] if swaps else []):
            prediction, residual, diagnostics = predict(restored,x,available,control_context,controls,
                                                       anchor['lfc'],anchor['observed'])
            if intervention == 'native':
                original, _, _ = predict(model,x,available,context,controls,anchor['lfc'],anchor['observed'])
                if not np.array_equal(original,prediction): raise ValueError('checkpoint prediction parity failed')
            name = 'query_%03d_%s.npz' % (i,intervention)
            exported = export_residual(anchor_pin['path'],anchor_pin['sha256'],residual,
                anchor['observed'],panel,genes,out/name,context)
            exports.append(dict(context_id=context,control_context_id=control_context,
                intervention=intervention,file=name,receipt=exported))
    write(out/'training_receipt.json',receipt)
    write(out/'complete.json',dict(status='COMPLETE',manifest_sha256=digest,
        fold=spec['fold'],mode=mode,seed=seed,checkpoint=checkpoint,exports=exports,
        seconds=time.monotonic()-started,device='cuda',complete_D053=False,
        training_receipt_sha256=sha256(out/'training_receipt.json'),
        scientific_benefit='requires independent validation',no_outer_truth_read=True))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(__doc__)
    for field in ('manifest','sha256','mode','out'): parser.add_argument('--'+field,required=True)
    parser.add_argument('--seed',type=int,required=True)
    args=parser.parse_args()
    run(args.manifest,args.sha256,args.mode,args.seed,args.out)
