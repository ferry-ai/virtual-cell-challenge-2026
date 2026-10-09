"""Pilot integration helpers: global loss mass, context swap and faithful export.

Only small fixtures run locally. The principal trainer and biological input
construction remain with DATI-TRANSFER; this module performs no network actions.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import torch

from ammi_context import export_guard
from pie_adapter import sha256


def lineage_weights(contexts, lineages):
    """Equal lineage, then equal context, then equal row mass; no batch renormalization."""
    if not contexts or len(contexts) != len(lineages):
        raise ValueError('nonempty paired row metadata required')
    mapping = {}
    for context, lineage in zip(contexts, lineages):
        if not context or not lineage or mapping.setdefault(context, lineage) != lineage:
            raise ValueError('ambiguous context lineage')
    rows = Counter(contexts)
    group_contexts = Counter(mapping.values())
    weights = np.asarray([1. / (len(group_contexts) * group_contexts[g] * rows[c])
                          for c, g in zip(contexts, lineages)], dtype=np.float64)
    return weights


def row_objective(prediction, response, observed, weights, population_size):
    """N/B-scaled global-weighted row means, unbiased under uniform row batching."""
    if prediction.ndim != 2 or prediction.shape != response.shape or observed.shape != response.shape:
        raise ValueError('response axes differ')
    if observed.dtype != torch.bool or weights.shape != response.shape[:1]:
        raise ValueError('mask or global row weights differ')
    if (len(prediction) == 0 or population_size < len(prediction)
            or not torch.isfinite(weights).all() or (weights <= 0).any()
            or not torch.isfinite(prediction[observed]).all()
            or not torch.isfinite(response[observed]).all()):
        raise ValueError('invalid supervised values or population size')
    counts = observed.sum(1)
    if (counts == 0).any():
        raise ValueError('every supervised row needs support')
    error = torch.where(observed, prediction, 0) - torch.where(observed, response, 0)
    contribution = weights * error.square().sum(1) / counts
    return contribution.sum() * population_size / len(prediction), contribution


def consumption(rows, contexts, lineages, weights, contributions):
    """Audit one complete epoch; duplicate or omitted row IDs fail closed."""
    n = len(weights)
    if (len(contexts) != n or len(lineages) != n or len(rows) != n
            or sorted(rows) != list(range(n)) or len(contributions) != n):
        raise ValueError('epoch row coverage differs')
    if not np.allclose(weights, lineage_weights(contexts, lineages), rtol=1e-12, atol=1e-15):
        raise ValueError('global masses differ from protocol')
    contributions = np.asarray(contributions, dtype=np.float64)
    if not np.isfinite(contributions).all() or (contributions < 0).any():
        raise ValueError('invalid loss contributions')
    result = {}
    for level, labels in [('lineage', lineages), ('context', contexts)]:
        result[level] = []
        for label in sorted(set(labels)):
            ids = [i for i, x in enumerate(labels) if x == label]
            id_set = set(ids)
            seen = [j for j, row in enumerate(rows) if row in id_set]
            result[level].append(dict(id=label, expected_rows=len(ids), seen_rows=len(seen),
                expected_mass=float(np.asarray(weights)[ids].sum()),
                consumed_mass=float(sum(weights[rows[j]] for j in seen)),
                loss_contribution=float(contributions[seen].sum())))
    return result


def swapped_contexts(query_contexts, query_lineages, training_context_lineages):
    """Choose another training lineage's controls using identifiers alone.

    This is an inference intervention on a trained cells checkpoint. It neither
    trains a new model nor permutes anchors, target features or query order.
    """
    if len(query_contexts) != len(query_lineages) or not training_context_lineages:
        raise ValueError('paired context metadata and eligible training controls required')
    output = []
    for context, lineage in zip(query_contexts, query_lineages):
        eligible = sorted(c for c, g in training_context_lineages.items() if g != lineage)
        if not eligible:
            raise ValueError('no controls from another allowed training lineage')
        key = json.dumps(['ammi-context-swap-r2', context, lineage], separators=(',', ':')).encode()
        output.append(eligible[int.from_bytes(hashlib.sha256(key).digest(), 'big') % len(eligible)])
    return output


def final_diagnostics(anchor, residual, observed, contexts):
    """Same residual guards plus descriptive whole-prediction/anchor common shares."""
    reports = export_guard(anchor, residual, observed, contexts)
    for report in reports:
        ix = torch.tensor([i for i, c in enumerate(contexts) if c == report['context']], device=anchor.device)
        mask = observed[ix]
        support = mask.sum(0)
        enough = support >= 2
        for name, values in [('anchor', anchor[ix]), ('prediction', anchor[ix] + residual[ix])]:
            values = torch.where(mask, values, 0)
            mean = values.sum(0)[enough] / support[enough]
            second = values.square().sum(0)[enough] / support[enough]
            common = mean.square().sum() / second.sum() if second.sum() > 0 else second.sum() * 0
            report[name + '_common_share'] = float(common.detach())
        report['whole_prediction_threshold'] = None
    return reports


def export_residual(anchor_path, anchor_sha256, residual, observed, targets, genes, out, context):
    """Apply one frozen correction with strict axes and exact byte parity at zero."""
    anchor_path, out = Path(anchor_path), Path(out)
    if out.exists() or out.with_suffix('.receipt.json').exists():
        raise FileExistsError('new export destination required')
    if sha256(anchor_path) != anchor_sha256:
        raise ValueError('frozen anchor changed')
    with np.load(anchor_path, allow_pickle=False) as source:
        arrays = {name: source[name] for name in source.files}
    if arrays['targets'].tolist() != list(targets) or arrays['genes'].tolist() != list(genes):
        raise ValueError('anchor query axes differ')
    a = arrays['lfc']; mask = arrays['observed']
    residual = np.asarray(residual)
    if (a.dtype != np.float32 or mask.dtype != bool or observed.dtype != bool
            or a.shape != residual.shape or mask.shape != a.shape
            or not np.array_equal(mask, observed) or not np.isfinite(a).all()
            or np.any(a[~mask] != 0) or not np.isfinite(residual).all()
            or np.any(residual[~mask] != 0)):
        raise ValueError('finite stage100 values, unchanged support and masked zeros required')
    diagnostics = final_diagnostics(torch.from_numpy(a.astype(np.float64)),
        torch.from_numpy(residual.astype(np.float64)), torch.from_numpy(mask), [context]*len(a))
    zero = bool(np.all(residual == 0))
    if zero:
        shutil.copyfile(anchor_path, out)
    else:
        combined = (a.astype(np.float64) + residual.astype(np.float64)).astype(np.float32)
        if not np.isfinite(combined).all(): raise ValueError('float32 overflow')
        # Report/guard the actual serialized correction, not merely float64 intent.
        diagnostics = final_diagnostics(torch.from_numpy(a.astype(np.float64)),
            torch.from_numpy(combined.astype(np.float64)-a.astype(np.float64)),
            torch.from_numpy(mask), [context]*len(a))
        arrays['lfc'] = combined
        with out.open('xb') as f: np.savez_compressed(f, **arrays)
    result = dict(anchor_sha256=anchor_sha256, output_sha256=sha256(out), bytes=out.stat().st_size,
                  zero_residual=zero, byte_parity=zero and sha256(out) == anchor_sha256,
                  diagnostics=diagnostics, quantity='ln_fold_change', emission_scale_applied=False,
                  source_code_sha256=sha256(__file__))
    with out.with_suffix('.receipt.json').open('x', encoding='utf-8') as f: json.dump(result, f, indent=2)
    return result
