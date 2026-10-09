"""Isolated AMMI pilot training engine; real runs require CUDA and pinned inputs.

Input packaging and numeric anchors are separate prerequisites. This engine does
not resolve remote data, infer lineages, choose epochs, or launch cloud resources.
The caller supplies already normalized individual NTCs and fold-safe anchors.
"""
import hashlib
import time
import numpy as np
import torch

from ammi_context import ContextCorrection
from ammi_encoder_v4 import forward_grouped, control_shape, batch
from ammi_contract_v2 import lineage_weights, row_objective, consumption


def validate(data, controls, excluded_lineages):
    n = len(data['contexts'])
    if not n or len(data['lineages']) != n or len(data['row_ids']) != n or len(set(data['row_ids'])) != n:
        raise ValueError('unique training row identities required')
    if set(data['lineages']) & set(excluded_lineages):
        raise ValueError('excluded response lineage in training')
    features, response, anchor, observed = (data[k] for k in ('features','response','anchor','observed'))
    if (features.ndim != 2 or features.shape[0] != n or not np.isfinite(features).all()
            or response.ndim != 2 or response.shape[0] != n or anchor.shape != response.shape
            or observed.shape != response.shape or observed.dtype != bool
            or not observed.any(1).all() or not np.isfinite(response[observed]).all()
            or not np.isfinite(anchor).all()):
        raise ValueError('finite available ESM2 and supported response rows required')
    if not data.get('input_receipt_sha256') or not data.get('anchor_receipt_sha256'):
        raise ValueError('verified input/anchor receipts must be identified')
    dimensions = set()
    for context in set(data['contexts']):
        shape = control_shape(controls[context])
        if not shape[0]: raise ValueError("empty controls")
        cells, mask = batch(controls[context], 0, min(shape[0], 256))
        if (cells.ndim != 2 or mask.shape != cells.shape or mask.dtype != bool
                or not len(cells) or not mask.any(1).all() or not np.isfinite(cells[mask]).all()):
            raise ValueError('observed individual controls required')
        dimensions.add(cells.shape[1])
    if len(dimensions) != 1: raise ValueError('control gene axes differ')
    return n, dimensions.pop()


def fit(data, controls, excluded_lineages, context_mode, seed, guard, *, fixture=False, checkpoint_callback=None):
    """Fit exactly two epochs; guard failures abort without selecting a checkpoint.

    `guard(model, epoch)` must inspect the fixed inner fold and return a serializable
    passed receipt. The biological wrapper must verify input hashes and anchor
    provenance before calling this engine. `fixture=True` is only for tiny CPU tests.
    """
    n, control_genes = validate(data, controls, excluded_lineages)
    if guard is None: raise ValueError('fixed inner-fold guard callback required')
    if fixture and (n > 32 or data['response'].shape[1] > 32 or control_genes > 32):
        raise ValueError('CPU fixture limit exceeded')
    device = torch.device('cpu' if fixture else 'cuda')
    if not fixture and not torch.cuda.is_available(): raise RuntimeError('real training requires CUDA')
    torch.manual_seed(seed)
    if device.type == 'cuda': torch.cuda.manual_seed_all(seed)
    weights = lineage_weights(data['contexts'], data['lineages'])
    mean = weights @ data['features'].astype(np.float64)
    model = ContextCorrection(control_genes, data['response'].shape[1],
                              mean.astype(np.float32), context_mode=context_mode).to(device)
    if next(model.parameters()).device.type != device.type: raise RuntimeError('model device mismatch')
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0003, weight_decay=.0001)
    rng = np.random.default_rng(seed)
    receipts = []
    for epoch in range(2):
        epoch_started = time.perf_counter()
        order = rng.permutation(n).tolist()
        observed_rows, loss_pieces, penalty_pieces = [], [], []
        model.train()
        for start in range(0,n,32):
            ids = order[start:start+32]
            kwargs = dict(dtype=torch.float32, device=device)
            features = torch.as_tensor(data['features'][ids], **kwargs)
            anchor = torch.as_tensor(data['anchor'][ids], **kwargs)
            truth = torch.as_tensor(data['response'][ids], **kwargs)
            observed = torch.as_tensor(data['observed'][ids], dtype=torch.bool, device=device)
            global_weights = torch.as_tensor(weights[ids], **kwargs)
            optimizer.zero_grad(set_to_none=True)
            prediction, residual = forward_grouped(model,features,[data['contexts'][i] for i in ids],controls,anchor,device)
            if epoch == 0 and start == 0 and not torch.equal(prediction,anchor):
                raise ValueError('initial anchor parity failed')
            objective, pieces = row_objective(prediction,truth,observed,global_weights,n)
            penalty, pp = row_objective(residual,torch.zeros_like(residual),observed,global_weights,n)
            total = objective + .01*penalty
            if not torch.isfinite(total): raise ValueError('nonfinite training loss')
            total.backward()
            gradients = [p.grad for p in model.parameters() if p.grad is not None]
            if not gradients or not all(torch.isfinite(g).all() for g in gradients):
                raise ValueError('nonfinite or absent gradients')
            if epoch == 0 and start == 0 and not model.decoder.weight.grad.abs().sum() > 0:
                raise ValueError('initial decoder gradient is zero')
            optimizer.step()
            observed_rows.extend(ids)
            loss_pieces.extend(pieces.detach().cpu().double().tolist())
            penalty_pieces.extend(pp.detach().cpu().double().tolist())
        audit = consumption(observed_rows,data['contexts'],data['lineages'],weights,loss_pieces)
        optimization_seconds = time.perf_counter() - epoch_started
        model.eval()
        if checkpoint_callback is not None:
            checkpoint_callback(model, epoch+1, audit)
        with torch.no_grad(): checked = guard(model,epoch+1)
        if not isinstance(checked,dict) or checked.get('pass') is not True:
            raise ValueError('fixed inner-fold guard failed; no checkpoint selection')
        receipts.append(dict(epoch=epoch+1,coverage=audit,loss=float(sum(loss_pieces)),
                             residual_penalty=float(sum(penalty_pieces)),guard=checked,
                             optimization_seconds=optimization_seconds,
                             epoch_seconds=time.perf_counter()-epoch_started))
    receipt = dict(seed=seed,context_mode=context_mode,device=str(device),fixture=fixture,
        input_receipt_sha256=data['input_receipt_sha256'],anchor_receipt_sha256=data['anchor_receipt_sha256'],
        excluded_lineages=sorted(excluded_lineages),epochs=receipts,
        reference_sha256=hashlib.sha256(mean.astype(np.float32).tobytes()).hexdigest(),
        row_ids=list(data['row_ids']),weights=weights.tolist(),complete_D053=False,
        cuda_device=torch.cuda.get_device_name(device) if device.type=='cuda' else None)
    return model, receipt
