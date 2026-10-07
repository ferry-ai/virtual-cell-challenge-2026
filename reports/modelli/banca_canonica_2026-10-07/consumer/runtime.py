"""General count_sum bank consumer: pinned bank units -> panel effects of one source.

Same adapter and estimator as the verified HIPSCI consumer (hipsci_adapter_r3). The bank is
never re-ingested: only count_sum, mask, rows and the bank receipt are read, after their
hashes match. Nothing is admitted here: admission is a recorded decision made on the receipt.
"""
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import adapter
import estimator

SPECIAL = {'NTC': 'control', 'UNASSIGNED': 'aux_unassigned', 'NO_METADATA': 'metadata_unresolved'}
BANK_FILES = ('count_sum.npz', 'mask.npz', 'rows.csv', 'complete.json')
UNSET = ('', 'MISSING', 'UNASSIGNED')
INPUT = Path(os.environ.get('VCC_INPUT_ROOT', '/kaggle/input'))
WORK = Path(os.environ.get('VCC_WORK_ROOT', '/kaggle/working'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ram_available():
    """Measured on the runtime. An unreadable value is 0, so a real job refuses to start blind."""
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def locate(unit, root=None):
    """Every pinned bank file, found by content: pinned size and sha256, never by name alone.

    A bank whose producer cannot be mounted is read from its declared mountable copy; the pin
    is the same, so a different copy cannot pass.
    """
    found = {}
    root = root or INPUT
    for name in BANK_FILES:
        pin = unit['files'][name]
        # A mountable copy may rename files: any file of the pinned size is a candidate.
        sized = [f for f in root.rglob('*') if f.is_file() and f.stat().st_size == pin['bytes']]
        matches = [f for f in sized if sha(f) == pin['sha256']]
        if not matches:
            raise ValueError('missing or changed bank file: %s %s (%d same-size candidates)'
                             % (unit['unit'], name, len(sized)))
        preferred = [f for f in matches if f.as_posix().endswith('/' + unit['relative_path'] + '/' + name)]
        found[name] = str((preferred or matches)[0])
    return found


def classify(rows, panel):
    """Role of every bank row, from metadata only, before any count is read."""
    panel = set(panel)
    roles = []
    for target in rows.target:
        roles.append(SPECIAL.get(target) or ('panel_target' if target in panel else 'outside_frozen_panel'))
    return roles


def namespace(frame, study):
    """An unreported identity stays unreported, scoped to its study. Nothing is imputed."""
    frame = frame.copy()
    for column in ('donor_or_clone', 'condition', 'chemistry'):
        unset = frame[column].astype(str).str.upper().isin(UNSET)
        frame.loc[unset, column] = 'UNREPORTED@' + study
    return frame


def merge_blocks(frames, counts, masks):
    """Sum count rows that share BIO identity and target (storage blocks of one experiment)."""
    frame = pd.concat(frames, ignore_index=True)
    x = np.concatenate(counts, axis=0)
    m = np.concatenate(masks, axis=0)
    keys = [*adapter.BIO, 'target', 'line_group']
    groups = frame.groupby(keys, sort=False).indices
    out_rows, out_x, out_m, origin = [], [], [], []
    for key, ix in groups.items():
        ix = np.asarray(ix)
        first = frame.iloc[ix[0]].to_dict()
        first['n'] = float(frame.iloc[ix].n.sum())
        out_rows.append(first)
        out_x.append(x[ix].sum(axis=0, dtype=np.float64))
        out_m.append(m[ix].all(axis=0))
        origin.append(frame.iloc[ix].origin.to_list())
    merged = pd.DataFrame(out_rows)
    merged['origin'] = origin
    x = np.vstack(out_x)
    m = np.vstack(out_m)
    x[~m] = 0.0  # a gene not measured in every block is not measured in the merged row
    return merged, x, m


def own_gene(result, genes_measured, panel_targets):
    index = {g: i for i, g in enumerate(genes_measured)}
    records = []
    for i, target in enumerate(result['targets']):
        record = dict(target=target, cells=int(result['n_cells'][i]))
        j = index.get(target)
        if j is None:
            record['state'] = 'own_transcript_not_measured'
        elif result['control_mean'][j] < 1e-6:
            record['state'] = 'own_transcript_control_fraction_below_original_mask'
        elif not np.isfinite(result['raw'][i, j]):
            record['state'] = 'own_transcript_expected_count_below_original_guard'
        else:
            record.update(state='measured', raw=float(result['raw'][i, j]),
                          shrunk=float(result['shrunk'][i, j]), se=float(result['se'][i, j]))
        records.append(record)
    measured = [r['raw'] for r in records if r['state'] == 'measured']
    summary = dict(derived_targets=len(records), measured_own_gene=len(measured),
                   median_own_raw=float(np.median(measured)) if measured else None,
                   fraction_negative=float(np.mean(np.asarray(measured) < 0)) if measured else None)
    return records, summary


def on_axis(result, measured, width):
    usable = np.asarray(result['control_mean']) >= 1e-6
    columns = np.flatnonzero(measured)[usable]
    arrays = {k: np.full((len(result['targets']), width), np.nan, np.float32) for k in ('raw', 'shrunk', 'se')}
    for k in arrays:
        arrays[k][:, columns] = result[k][:, usable]
    return arrays


def collapse(tables, panel):
    """Equal weight per context, after each context was pooled before its own shrink."""
    targets = [t for t in panel if any(t in tb['targets'] for tb in tables)]
    width = tables[0]['arrays']['raw'].shape[1]
    out = {k: np.full((len(targets), width), np.nan, np.float32) for k in ('raw', 'shrunk', 'se')}
    cells = np.zeros(len(targets))
    for row, target in enumerate(targets):
        parts = [(tb, tb['targets'].index(target)) for tb in tables if target in tb['targets']]
        for k in ('raw', 'shrunk'):
            stack = np.stack([tb['arrays'][k][i] for tb, i in parts])
            present = np.isfinite(stack)
            total = np.where(present, stack, 0).sum(axis=0)
            n = present.sum(axis=0)
            out[k][row] = np.where(n > 0, total / np.maximum(n, 1), np.nan)
        stack = np.stack([tb['arrays']['se'][i] for tb, i in parts])
        present = np.isfinite(stack)
        n = present.sum(axis=0)
        out['se'][row] = np.where(n > 0, np.sqrt(np.where(present, stack ** 2, 0).sum(axis=0)) / np.maximum(n, 1), np.nan)
        cells[row] = sum(float(tb['n_cells'][i]) for tb, i in parts)
    return targets, out, cells


def compare(reference, targets, arrays, genes):
    with np.load(reference, allow_pickle=False) as z:
        ref_targets = [str(t) for t in z['targets']]
        ref = np.asarray(z['shrunk'], dtype=np.float64)
        ref_raw = np.asarray(z['raw'], dtype=np.float64)
        ref_genes = [str(g) for g in z['genes']] if 'genes' in z.files else None
    if ref.shape[1] != len(genes) or (ref_genes is not None and ref_genes != list(genes)):
        raise ValueError('reference axis differs')
    index = {t: i for i, t in enumerate(ref_targets)}
    rows = []
    for i, target in enumerate(targets):
        if target not in index:
            continue
        record = dict(target=target)
        for key, new, old in (('shrunk', arrays['shrunk'][i], ref[index[target]]),
                              ('raw', arrays['raw'][i], ref_raw[index[target]])):
            both = np.isfinite(new) & np.isfinite(old)
            a, b = np.asarray(new[both], np.float64), old[both]
            norm = np.linalg.norm(a) * np.linalg.norm(b)
            record[key + '_cosine'] = float(a @ b / norm) if norm > 0 else None
            record[key + '_genes_both'] = int(both.sum())
            record[key + '_max_abs_diff'] = float(np.abs(a - b).max()) if both.any() else None
        rows.append(record)
    cos = [r['shrunk_cosine'] for r in rows if r['shrunk_cosine'] is not None]
    raw = [r['raw_cosine'] for r in rows if r['raw_cosine'] is not None]
    return dict(reference_targets=len(ref_targets), new_targets=len(targets), shared=len(rows),
                only_reference=sorted(set(ref_targets) - set(targets)),
                only_new=sorted(set(targets) - set(ref_targets)),
                shrunk_cosine_median=float(np.median(cos)) if cos else None,
                shrunk_cosine_q10=float(np.quantile(cos, .1)) if cos else None,
                raw_cosine_median=float(np.median(raw)) if raw else None,
                raw_cosine_q10=float(np.quantile(raw, .1)) if raw else None, per_target=rows,
                reading='descriptive equivalence check; it changes no weight and admits nothing')


def main():
    p = json.loads(Path('params.json').read_text())
    if p['recipe'] != adapter.CALL or p['recipe'] != estimator.CALL:
        raise ValueError('recipe differs from frozen original')
    resources = dict(ram_available=ram_available(), disk_free=shutil.disk_usage(WORK).free)
    Path('resources.json').write_text(json.dumps(resources))
    if resources['ram_available'] < p['min_ram_bytes'] or resources['disk_free'] < 2 << 30:
        raise RuntimeError('insufficient runtime resources')
    for name, pin in p['embedded_inputs'].items():
        if Path(name).stat().st_size != pin['bytes'] or sha(name) != pin['sha256']:
            raise ValueError('changed embedded input: ' + name)
    genes = pd.read_csv('gene_names.csv').iloc[:, 0].astype(str).to_list()
    if len(genes) != p['axis']['genes'] or sha('gene_names.csv') != p['axis']['sha256']:
        raise ValueError('axis differs')
    panel = p['panel']['targets']
    if hashlib.sha256('\n'.join(panel).encode()).hexdigest() != p['panel']['panel_sha256']:
        raise ValueError('panel changed')
    hidden, held = p['hidden_targets'], p['held_groups']
    verified, frames, counts, masks, inventory = {}, [], [], [], []
    for unit in p['units']:
        files = locate(unit)
        verified[unit['unit']] = files
        rows = pd.read_csv(files['rows.csv'], keep_default_na=False)
        receipt = json.loads(Path(files['complete.json']).read_text())
        if len(rows) != receipt['rows'] or int(rows.n.sum()) != receipt['cells_used']:
            raise ValueError('population coverage changed: ' + unit['unit'])
        if set(rows.study) != {p['study']} or set(rows.modality) != {p['modality']}:
            raise ValueError('unexpected study or modality: ' + unit['unit'])
        roles = classify(rows, panel)
        cells = Counter()
        for role, n in zip(roles, rows.n):
            cells[role] += int(n)
        selected = [i for i, r in enumerate(roles) if r in ('control', 'panel_target')]
        inventory.append(dict(unit=unit['unit'], bank_rows=len(rows), cells_by_role=dict(cells),
                              rows_by_role=dict(Counter(roles)), selected_rows=len(selected)))
        if not any(roles[i] == 'panel_target' for i in selected):
            continue
        frame = namespace(rows.iloc[selected].reset_index(drop=True), p['study'])
        frame['context'] = frame.context.map(lambda c: p['context_rename'].get(c, c))
        frame['origin'] = [unit['unit'] + ':' + str(i) for i in selected]
        # Counts are read only now, after the metadata plan, and only for the selected rows.
        with np.load(files['count_sum.npz'], allow_pickle=False) as z:
            x = z['value']
            if x.shape != (len(rows), len(genes)):
                raise ValueError('count shape differs from rows x official axis: ' + unit['unit'])
            x = np.asarray(x[selected], dtype=np.float64)
        with np.load(files['mask.npz'], allow_pickle=False) as z:
            m = z['value']
            if m.shape != (len(rows), len(genes)) or m.dtype != bool:
                raise ValueError('mask shape or type differs: ' + unit['unit'])
            m = np.asarray(m[selected])
        frames.append(frame); counts.append(x); masks.append(m)
    if not frames:
        raise ValueError('no unit has a panel target with controls')
    if p['merge_blocks']:
        frame, x, m = merge_blocks(frames, counts, masks)
    else:
        frame, x, m = pd.concat(frames, ignore_index=True), np.concatenate(counts), np.concatenate(masks)
    del counts, masks
    crosswalk = {t: (t, (t,)) for t in set(frame.target) - {'NTC'}}
    blocks, excluded = adapter.prepare(frame, x, m, genes, panel, crosswalk, unit=p['name'],
                                       hidden_targets=hidden, held_groups=held,
                                       protected_units=p['protected_units'])
    by_context = {}
    for block in blocks:
        # Clones of one study that differ only by context are donors of one pooled source.
        key = block['context'] if not p['context_is_donor'] else tuple(
            c for i, c in enumerate(block['context']) if i != 1)
        by_context.setdefault(key, []).append(block)
    tables = []
    for key, group in sorted(by_context.items()):
        result = adapter.estimate_joint(group, panel, estimator.effects_from_pseudobulk)
        if not result['targets']:
            continue
        records, summary = own_gene(result, group[0]['genes'], panel)
        tables.append(dict(context=list(key), targets=list(result['targets']),
                           n_cells=np.asarray(result['n_cells'], dtype=np.float64),
                           arrays=on_axis(result, group[0]['mask'], len(genes)),
                           own_gene=records, own_gene_summary=summary,
                           control_cells=float(sum(b['obs'].loc[b['obs'].target == 'non-targeting', 'n_cells'].sum() for b in group)),
                           donors=sorted({d for b in group for d in b['obs'].donor}),
                           bank_rows=[frame.iloc[i].origin for b in group for i in b['bank_rows']]))
    if not tables:
        raise ValueError('no usable panel targets')
    if len(tables) == 1:
        targets, arrays, cells = tables[0]['targets'], tables[0]['arrays'], tables[0]['n_cells']
        aggregation = 'one context; donors pooled before shrink'
    else:
        targets, arrays, cells = collapse(tables, panel)
        aggregation = 'donors pooled before shrink inside each context; contexts equal-weighted'
    meta = dict(source=p['name'], study=p['study'], modality=p['modality'], recipe=adapter.CALL,
                aggregation=aggregation, contexts=[t['context'] for t in tables])
    out = Path(p['name'] + '.npz')
    np.savez_compressed(out, genes=np.asarray(genes), targets=np.asarray(targets), n_cells=cells,
                        meta=np.asarray(json.dumps(meta)), **arrays)
    outputs = {out.name: dict(bytes=out.stat().st_size, sha256=sha(out))}
    if len(tables) > 1:
        for number, table in enumerate(tables):
            part = Path('%s__context%d.npz' % (p['name'], number))
            np.savez_compressed(part, genes=np.asarray(genes), targets=np.asarray(table['targets']),
                                n_cells=table['n_cells'], meta=np.asarray(json.dumps(dict(meta, context=table['context']))),
                                **table['arrays'])
            outputs[part.name] = dict(bytes=part.stat().st_size, sha256=sha(part))
    comparison = None
    if p.get('compare_to'):
        ref = p['compare_to']
        hits = [f for f in INPUT.rglob(ref['file'])
                if f.stat().st_size == ref['bytes'] and sha(f) == ref['sha256']]
        if len(hits) != 1:
            raise ValueError('reference table identity not mounted')
        comparison = compare(hits[0], targets, arrays, genes)
        comparison['reference'] = ref
    proof = dict(state='derived_production_fragment', name=p['name'], study=p['study'], modality=p['modality'],
                 arm=p['arm'], full_training=False, not_heldout_validation=not (hidden or held),
                 hidden_targets=hidden, held_groups=held, input_files=verified,
                 input_hashes={u['unit']: u['files'] for u in p['units']},
                 producers={u['unit']: u['producer'] for u in p['units']},
                 axis_sha256=p['axis']['sha256'], panel_sha256=p['panel']['panel_sha256'],
                 params_sha256=sha('params.json'), recipe=adapter.CALL, inventory=inventory,
                 validation_excluded=len(excluded), merge_blocks=p['merge_blocks'], aggregation=aggregation,
                 identity_policy='unreported donor/condition/chemistry namespaced to the study; no imputation',
                 crosswalk='exact native label equal to a frozen panel symbol; every other label is inventoried, not resolved',
                 contexts=[dict(context=t['context'], targets=t['targets'], n_cells=t['n_cells'].tolist(),
                                control_cells=t['control_cells'], donors=t['donors'], bank_rows=t['bank_rows'],
                                own_gene=t['own_gene'], own_gene_summary=t['own_gene_summary']) for t in tables],
                 targets=list(targets), n_cells=np.asarray(cells).tolist(), outputs=outputs,
                 comparison=comparison, matrix_hash_verified_in_consumer=True, mixer_consumed=False,
                 automatic_admission=False)
    Path('fit_receipt.json').write_text(json.dumps(proof, indent=1, allow_nan=False) + '\n')
    print(json.dumps(dict(state=proof['state'], name=p['name'], contexts=len(tables), targets=len(targets))), flush=True)


if __name__ == '__main__':
    main()
