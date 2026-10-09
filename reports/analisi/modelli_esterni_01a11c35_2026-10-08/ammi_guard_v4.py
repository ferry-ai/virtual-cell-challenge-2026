"""Inner-fold guard calling the independently pinned discrimination implementation.

No tuning, outer truth, checkpoint selection, or promotion. The routing contract
must be reviewed before a biological run; every primary context is mandatory.
"""
import numpy as np
import torch
import csv

from ammi_inputs_v3 import checked, module
from ammi_contract_v2 import final_diagnostics
from ammi_encoder_v4 import forward_grouped


def predict(model, features, available, context, controls, anchor, observed, *, diagnostic=False):
    device = next(model.parameters()).device
    available = np.asarray(available, dtype=bool)
    safe = np.asarray(features, dtype=np.float32).copy()
    safe[~available] = model.reference_mean.detach().cpu().numpy()
    with torch.no_grad():
        base = torch.as_tensor(anchor, dtype=torch.float32, device=device)
        prediction, residual = forward_grouped(model,
            torch.as_tensor(safe, dtype=torch.float32, device=device),
            [context]*len(safe), controls, base, device)
    correction = residual.cpu().numpy()
    correction[~available] = 0
    correction[~observed] = 0
    output = (anchor.astype(np.float64) + correction.astype(np.float64)).astype(np.float32)
    if not np.isfinite(output).all(): raise ValueError('nonfinite query prediction')
    actual = output.astype(np.float64)-anchor.astype(np.float64)
    try:
        diagnostics = final_diagnostics(torch.from_numpy(anchor.astype(np.float64)),
            torch.from_numpy(actual), torch.from_numpy(observed), [context]*len(anchor))
    except ValueError as error:
        if not diagnostic: raise
        diagnostics = [dict(context=context, pass_=False, failure=str(error))]
    return output, actual, diagnostics


def discrimination(metrics, anchor, prediction, observed, truth, panel, genes):
    """Same T0-defined support, full-panel permutation and disc95 masking as bench_core."""
    positions = {t: i for i, t in enumerate(truth['targets'].tolist())}
    if len(positions) != len(truth['targets']): raise ValueError('duplicate truth targets')
    keep = [i for i, t in enumerate(panel) if t in positions and observed[i].any()]
    if len(keep) < 3: raise ValueError('insufficient inner truth target support')
    rows = [positions[panel[i]] for i in keep]
    shrunk, raw, se = (truth[k][rows] for k in ('shrunk', 'raw', 'se'))
    excluded = [i for i, gene in enumerate(genes) if gene in set(panel)]
    valid = metrics.valid_pairs(observed[keep], shrunk, raw, se, excluded)
    cols95 = valid.mean(0) >= .95
    if cols95.sum() < 2: raise ValueError('insufficient inner disc95 gene support')
    perm = metrics.shuffled_rows(len(panel))
    shuffled_valid = metrics.valid_pairs(observed[perm][keep], shrunk, raw, se, excluded)
    def score(values, mask):
        return metrics.per_target(np.where(mask, values[keep], 0), mask,
            np.where(mask, shrunk, 0), raw, se, cols95)['disc']
    base = score(anchor, valid)
    corrected = score(prediction, valid)
    shuffled = score(anchor[perm], shuffled_valid)
    if not all(np.isfinite(v).all() for v in (base, corrected, shuffled)):
        raise ValueError('nonfinite inner metric')
    positive = metrics.strip(metrics.paired_bootstrap(base, shuffled))
    delta = metrics.strip(metrics.paired_bootstrap(corrected, base))
    return dict(targets=len(keep), genes_disc95=int(cols95.sum()),
                anchor=float(base.mean()), prediction=float(corrected.mean()),
                shuffled=float(shuffled.mean()), positive_control=positive,
                prediction_minus_anchor=delta,
                support_sha256=__import__('hashlib').sha256(valid.tobytes()+cols95.tobytes()).hexdigest(),
                **{'pass': positive['lo'] is not None and positive['lo'] > 0})


def inner_guard(spec, fold, metrics_pin, controls, anchors, features, available, panel, genes):
    """Construct the fixed callback; this is the sole truth-reading boundary."""
    if spec.get('review_status') not in ('agreed', 'existing-contract-applied') or not spec.get('review_pin'):
        raise ValueError('independent routing/guard review required before biological fit')
    checked(spec['review_pin'])
    if spec['review_status'] == 'existing-contract-applied':
        checked(spec['routing_basis'])
        if spec.get('truth_replication_policy') != 'one table is one reference; context results never pooled as independent truths':
            raise ValueError('reused truth cannot be counted as independent replication')
    if spec.get('rule') != 'anchor-shuffle-disc95-lo-positive; structural-residual-r2; no-benefit-threshold':
        raise ValueError('unknown inner guard rule')
    metrics = module(metrics_pin, 'ammi_independent_metrics')
    if metrics.BOOT != 10000 or metrics.BOOT_SEED != 20261008:
        raise ValueError('independent bootstrap settings changed')
    with checked(spec['axis']).open(newline='', encoding='utf-8') as stream:
        axis = [r['gene_name'] for r in csv.DictReader(stream)]
    if axis != list(genes): raise ValueError('independent truth axis pin differs')
    tables, routes = {}, spec['routes']
    if not routes or len({r['context_id'] for r in routes}) != len(routes):
        raise ValueError('unique nonempty inner context routing required')
    expected = {c for c, x in fold['contexts'].items() if x['role'] == 'inner_guard'}
    if {r['context_id'] for r in routes} != expected:
        raise ValueError('inner context coverage differs')
    for route in routes:
        if route['lineage'] != fold['inner'] or route['context_id'] not in controls:
            raise ValueError('outer/non-inner truth routing forbidden')
        truth_spec = route['truth']
        digest = truth_spec['sha256']
        if digest not in tables:
            with np.load(checked(truth_spec), allow_pickle=False) as source:
                table = {k: source[k] for k in ('targets', 'shrunk', 'raw', 'se')}
                if 'genes' in source.files and source['genes'].tolist() != list(genes):
                    raise ValueError('inner truth gene axis differs')
            if any(table[k].shape != (len(table['targets']), len(genes)) for k in ('shrunk', 'raw', 'se')):
                raise ValueError('inner truth axes differ')
            tables[digest] = table
    anchor = anchors[fold['inner_query_anchor']]
    # Test identifiability before spending an epoch; no AMMI result is used here.
    baseline = {}
    for route in routes:
        baseline[route['context_id']] = discrimination(metrics, anchor['lfc'], anchor['lfc'],
            anchor['observed'], tables[route['truth']['sha256']], panel, genes)
        if route['role'] == 'primary' and not baseline[route['context_id']]['pass']:
            raise ValueError('inner anchor positive control failed before training')
    if not any(r['role'] == 'primary' for r in routes): raise ValueError('inner primary control absent')
    def guard(model, epoch):
        reports = []
        for route in routes:
            prediction, residual, diagnostics = predict(model, features, available, route['context_id'],
                controls, anchor['lfc'], anchor['observed'])
            scored = discrimination(metrics, anchor['lfc'], prediction, anchor['observed'],
                tables[route['truth']['sha256']], panel, genes)
            reports.append(dict(context=route['context_id'], role=route['role'],
                truth_sha256=route['truth']['sha256'], structural=diagnostics, disc95=scored))
        return dict(epoch=epoch, contexts=reports, metrics_sha256=metrics_pin['sha256'],
                    checkpoint_selection=False, benefit_threshold=None,
                    **{'pass': all(r['disc95']['pass'] for r in reports if r['role'] == 'primary')})
    return guard, baseline
