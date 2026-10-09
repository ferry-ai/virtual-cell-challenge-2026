"""Recover native depth for existing selected NTC identities from obs only.

This is an adapter primitive, not an amendment to the active AMMI selection.
The caller must authenticate the source version against its frozen receipt.
It does not restore counts discarded by an earlier common-axis mask.
"""
import numpy as np
from ntc_cells import column, BIO, STRATA


def recover_depth(h5, selected, bank_rows, *, expected_source_sha256, verified_source_sha256):
    if not expected_source_sha256 or verified_source_sha256 != expected_source_sha256:
        raise ValueError('source identity has not been verified by caller')
    obs = h5['obs']
    columns = {key: column(obs, key) for key in (*BIO, *STRATA, 'cell_key', 'control_kind', 'depth_native')}
    n = len(columns['cell_key'])
    if any(len(value) != n for value in columns.values()):
        raise ValueError('inconsistent metadata lengths')
    output = []; seen = set()
    for record in selected:
        row = record['source_row']; bank = bank_rows[record['bank_row']]
        if not isinstance(row, int) or not 0 <= row < n:
            raise ValueError('source row outside metadata')
        if bank['target'] != 'NTC' or str(columns['control_kind'][row]) != 'NTC':
            raise ValueError('only NTC records are admissible')
        if str(columns['cell_key'][row]) != record['cell_key']:
            raise ValueError('sample locator identifies a different cell')
        if tuple(str(columns[k][row]) for k in BIO) != tuple(str(bank[k]) for k in BIO):
            raise ValueError('biological identity differs')
        if [str(columns[k][row]) for k in STRATA] != record['stratum']:
            raise ValueError('sample stratum differs')
        key = (expected_source_sha256, row, record['cell_key'])
        if key in seen:
            raise ValueError('duplicate sampled cell')
        seen.add(key)
        depth = float(columns['depth_native'][row])
        if not np.isfinite(depth) or depth <= 0:
            raise ValueError('invalid native depth')
        output.append(dict(source_sha256=expected_source_sha256, source_row=row,
            cell_key=record['cell_key'], depth_native=depth))
    return dict(cells=output, RNA_matrix_opened=False, selection_changed=False,
        source_identity_verified_by_caller=True,
        original_sample_counts_and_masks_preserved=True,
        equivalent_to_active_AMMI_selection=False)
