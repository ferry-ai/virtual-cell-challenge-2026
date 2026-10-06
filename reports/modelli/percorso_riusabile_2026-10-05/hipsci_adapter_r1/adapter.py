"""Count-sum adapter; no fit admission, target inference or source-weight policy.

Input arrays/axis must already be hash-verified in the consuming runtime. Resolution
is an explicit biological crosswalk, never a delimiter heuristic or gene overlap.
"""
import numpy as np
import pandas as pd

BIO = ('study', 'context', 'donor_or_clone', 'condition', 'modality', 'chemistry')
CONTEXT = tuple(c for c in BIO if c != 'donor_or_clone')
CALL = dict(phi=.2, min_control_frac=1e-6, min_cells=10., pseudo=.5,
            pseudo_scale='constant', min_expected=1.)


def prepare(rows, counts, masks, genes, panel, resolutions, *, held_groups=(),
            hidden_targets=(), protected_units=(), unit):
    if unit in protected_units:
        raise ValueError('protected unit: ' + unit)
    required = {*BIO, 'line_group', 'target', 'n'}
    if not required.issubset(rows.columns):
        raise ValueError('missing biological identity')
    if rows.duplicated([*BIO, 'target']).any():
        raise ValueError('duplicate BIO/target')
    if len(genes) != len(set(genes)) or len(panel) != len(set(panel)):
        raise ValueError('duplicate axis or panel identifier')
    if counts.shape != masks.shape or counts.shape != (len(rows), len(genes)):
        raise ValueError('count/mask/axis shape mismatch')
    if masks.dtype != bool:
        raise ValueError('mask must be boolean')
    panel_set, hidden, held = set(panel), set(hidden_targets), set(held_groups)
    kept, labels, inventory = [], {}, []
    # Filter metadata before reading any counts or forming control statistics.
    for pos, row in enumerate(rows.to_dict('records')):
        token = str(row['target'])
        if row['line_group'] in held:
            inventory.append((pos, 'held_group')); continue
        if token == 'NTC':
            label, components = 'non-targeting', ()
        else:
            if token not in resolutions:
                raise ValueError('unresolved biological target: ' + token)
            label, components = resolutions[token]
            if (not isinstance(label, str) or not label or
                    not isinstance(components, (list, tuple)) or not components or
                    any(not isinstance(c, str) or not c for c in components)):
                raise ValueError('empty target resolution: ' + token)
            if label in hidden or hidden.intersection(components):
                inventory.append((pos, 'hidden_component')); continue
            if len(components) != 1:
                inventory.append((pos, 'compound_validation_exclusion')); continue
            if label not in panel_set:
                inventory.append((pos, 'outside_frozen_panel')); continue
        if any(not str(row[c]) or str(row[c]).upper() in ('MISSING', 'UNASSIGNED') for c in BIO):
            raise ValueError('unresolved BIO identity at row ' + str(pos))
        kept.append(pos); labels[pos] = label
    groups = {}
    for pos in kept:
        key = tuple(str(rows.iloc[pos][c]) for c in CONTEXT)
        groups.setdefault(key, []).append(pos)
    blocks = []
    for key, positions in groups.items():
        wanted = [t for t in panel if any(labels[p] == t for p in positions)]
        if not wanted:
            continue
        control_donors = {str(rows.iloc[p].donor_or_clone) for p in positions
                          if labels[p] == 'non-targeting'}
        for p in positions:
            if labels[p] != 'non-targeting' and str(rows.iloc[p].donor_or_clone) not in control_donors:
                raise ValueError('missing matched donor controls: ' + str(key))
        ix = np.array(positions, dtype=int)
        measured = masks[ix].all(axis=0)
        if not measured.any():
            raise ValueError('empty measured axis: ' + str(key))
        x = np.asarray(counts[ix], dtype=np.float64)
        n = rows.iloc[ix].n.to_numpy(dtype=float)
        if not np.isfinite(x).all() or (x < 0).any() or (x[~masks[ix]] != 0).any():
            raise ValueError('invalid observed counts')
        x = x[:, measured]
        if not np.isfinite(n).all() or (n <= 0).any() or (x.sum(axis=1) <= 0).any():
            raise ValueError('population/QC unresolved')
        obs = pd.DataFrame(dict(target=[labels[p] for p in positions],
                                donor=rows.iloc[ix].donor_or_clone.astype(str).to_list(),
                                condition=[key[2]] * len(ix), n_cells=n))
        blocks.append(dict(context=key, bank_rows=positions, counts=x, obs=obs,
                           genes=np.asarray(genes)[measured], mask=measured, targets=wanted))
    return blocks, inventory


def estimate(block, effects_fn):
    """Call the original estimator once per biological context, before shrinkage."""
    return effects_fn(block['counts'], block['obs'], block['genes'],
                      targets=block['targets'], condition=None, **CALL)
