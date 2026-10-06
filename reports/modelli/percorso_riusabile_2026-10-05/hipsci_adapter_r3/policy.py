"""Published Guide_Call identities; chemistry unreported, scoped to this study."""
from collections import Counter
import adapter


def metadata_plan(rows, panel):
    if set(rows.study) != {'hipsci_targeted_19'}:
        raise ValueError('unexpected study')
    roles, cells = [], Counter()
    for pos, row in enumerate(rows.to_dict('records')):
        t = row['target']
        role = ('control' if t == 'NTC' else 'aux_unassigned' if t == 'UNASSIGNED'
                else 'metadata_unresolved' if t == 'NO_METADATA'
                else 'panel_target' if t in panel else 'outside_frozen_panel')
        roles.append(dict(bank_row=pos, role=role, cells=int(row['n']), target=t))
        cells[role] += int(row['n'])
    selected = [r['bank_row'] for r in roles if r['role'] in ('control','panel_target')]
    frame = rows.iloc[selected].copy().reset_index(drop=True)
    if set(frame.condition) != {'day3'} or set(frame.modality) != {'CRISPRi'}:
        raise ValueError('unexpected assay identity')
    if set(frame.chemistry) != {'MISSING'}:
        raise ValueError('chemistry policy requires revision')
    # This is an uncertainty namespace, not a claim about the assay chemistry.
    frame['chemistry'] = 'UNREPORTED@hipsci_targeted_19'
    crosswalk = {t:(t,(t,)) for t in set(frame.target)-{'NTC'}}
    return selected, frame, crosswalk, roles, dict(cells)


def prepare(rows, counts, masks, genes, panel, *, hidden_targets=(), held_groups=()):
    selected, frame, crosswalk, roles, cells = metadata_plan(rows, panel)
    blocks, excluded = adapter.prepare(frame, counts[selected], masks[selected], genes,
        panel, crosswalk, unit='hipsci_targeted_19', hidden_targets=hidden_targets,
        held_groups=held_groups)
    for block in blocks:
        block['bank_rows'] = [selected[p] for p in block['bank_rows']]
    return blocks, dict(roles=roles, cells_by_role=cells, validation_excluded=excluded,
        chemistry='unreported; isolated to one study', crosswalk='exact native Guide_Call gene label to frozen panel; no inferred aliases',
        outside_panel_aliases_resolved=False, claims_complete_catalogue=False)
