"""Audit a completed external fit against the immutable bank view, without refitting.

Reads metadata only. Prediction arrays, scientific benefit and emitter admission
remain separate checks. No bearer locator file or biological chunk is opened.
"""
import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify(view_path, view_sha256, fit_path, complete_path, resolution_path, prepared_path):
    require(sha(view_path) == view_sha256, 'frozen view hash differs')
    view, fit, done = read(view_path), read(fit_path), read(complete_path)
    resolution, prepared = read(resolution_path), read(prepared_path)
    require(done['status'] == 'COMPLETE', 'fit is not complete')
    require(done['receipt_sha256'] == sha(fit_path), 'completion receipt hash differs')
    for key in ('model_sha256', 'predictions_sha256'):
        fit_key = 'native_predictions_sha256' if key == 'predictions_sha256' else key
        require(done[key] == fit[fit_key], 'completion artifact identity differs')
    require(prepared['view_sha256'] == view_sha256 and prepared['private'] is True,
            'prepared private view identity differs')
    require(prepared['slug'].startswith('davideferrante11/esm2-'), 'destination differs')
    store = fit['store_receipt']
    consumed = copy.deepcopy(store['source_manifest'])
    runtime = consumed.pop('runtime_resolution')
    require(runtime['source_view_sha256'] == view_sha256 and runtime['chunk_hashes_verified'] is True,
            'runtime source verification differs')
    require(runtime['source_visibility_changed'] is False, 'source visibility changed')
    require(consumed.pop('mask_storage') == 'finite_verified', 'unexpected mask policy')
    require(len(consumed['chunks']) == len(view['chunks']), 'chunk count differs')
    for actual, frozen in zip(consumed['chunks'], view['chunks']):
        require(actual['path'].startswith('/kaggle/'), 'chunk was resolved outside Kaggle')
        actual['path'] = frozen['path']
    require(consumed == view, 'consumed view changed identities, weights, axes or exclusions')
    chunks = view['chunks']
    rows_by_context = Counter()
    rows_by_lineage = Counter()
    targets, all_weights, context_lineages = set(), [], {}
    for chunk in chunks:
        n = len(chunk['targets'])
        rows_by_context[chunk['context_id']] += n
        rows_by_lineage[chunk['context_group']] += n
        require(context_lineages.setdefault(chunk['context_id'], chunk['context_group']) == chunk['context_group'],
                'ambiguous lineage')
        targets.update(chunk['targets'])
        all_weights.extend(chunk['weights'])
    require(dict(rows_by_context) == view['expected_rows_by_context'], 'frozen row inventory differs')
    n_rows, n_genes = sum(rows_by_context.values()), len(view['genes'])
    require(store['shape'] == [n_rows, n_genes], 'stored shape differs')
    require(store['original_mask_equivalence_verified_chunks'] == len(chunks), 'original masks not verified')
    require(store['builder_sha256'] == prepared['modules']['chunk_store_v2.py'], 'builder identity differs')
    require(fit['consumed_rows_by_context'] == dict(rows_by_context), 'consumed context inventory differs')
    require(fit['consumed_rows_by_lineage'] == dict(rows_by_lineage), 'consumed lineage inventory differs')
    require(fit['context_lineages'] == context_lineages, 'consumed context lineage mapping differs')
    exposure = fit['exposure']
    require(exposure['rows_read'] == n_rows and exposure['unique_feature_targets'] == len(targets),
            'fit row/target consumption differs')
    require(exposure['targets_read'] == sorted(targets), 'fit target identities differ')
    require(exposure['rows_by_context_group'] == dict(rows_by_lineage), 'fit lineage counts differ')
    require(math.isclose(exposure['total_row_weight'], math.fsum(all_weights), rel_tol=1e-12, abs_tol=1e-12),
            'fit total row weight differs')
    require(exposure['alpha'] == 1.0 and exposure['uses_context'] is False,
            'registered model contract differs')
    require(exposure['changes_to_bank_or_shrinkage'] is False, 'fit changed the bank')
    for key in ('observed_per_gene', 'weighted_observations_per_gene'):
        require(len(exposure[key]) == n_genes, 'gene consumption axis differs')
    for count, weight in zip(exposure['observed_per_gene'], exposure['weighted_observations_per_gene']):
        require(isinstance(count, int) and 0 <= count <= n_rows and math.isfinite(weight) and weight >= 0,
                'invalid gene consumption')
        require((count > 0) == (weight > 0), 'weighted gene support differs')
    for name, digest in fit['code'].items():
        require(prepared['modules'].get(name) == digest, 'fit code identity differs: ' + name)
    require(set(fit['code']) == {'run_sufficient_probe_v2.py', 'target_sufficient_ridge_v2.py',
            'embedding_ridge.py', 'chunk_store_v2.py', 'pie_adapter.py', 'feature_policy.py'},
            'fit code inventory differs')
    for key in ('quantity', 'normalization', 'modality', 'regime', 'release_sha256',
                'split_manifest_sha256', 'expected_rows_by_context', 'excluded_targets', 'excluded_contexts'):
        require(fit['manifest'][key] == view[key], 'fit protocol differs: ' + key)
    expected_inputs = Counter((c['producer'], c['producer_file'], c['bytes'], c['sha256']) for c in chunks)
    actual_inputs = Counter((c['producer'], c['file'], c['bytes'], c['sha256']) for c in resolution['inputs'])
    require(actual_inputs == expected_inputs, 'resolved source inventory differs')
    require(resolution['source_view_sha256'] == view_sha256, 'resolution view hash differs')
    require(resolution['chunks'] == len(chunks) and resolution['rows'] == n_rows
            and resolution['contexts'] == len(rows_by_context), 'resolution counts differ')
    require(resolution['bytes_verified'] == sum(c['bytes'] for c in chunks), 'resolved byte count differs')
    require(0 <= resolution['downloaded_bytes'] <= prepared['private_bytes'], 'private download bytes exceed scope')
    require(all(c['route'] in ('native_mount', 'authenticated_output_download') for c in resolution['inputs']),
            'unknown source access route')
    return dict(status='PASS', evidence='completed fit receipts checked against frozen metadata',
        regime=view['regime'], source_view_sha256=view_sha256, fit_receipt_sha256=sha(fit_path),
        prepared_sha256=sha(prepared_path), rows=n_rows, contexts=len(rows_by_context),
        targets=len(targets), chunks=len(chunks), genes=n_genes,
        total_row_weight=exposure['total_row_weight'], resolved_bytes=resolution['bytes_verified'],
        private_downloaded_bytes=resolution['downloaded_bytes'],
        prediction_arrays_independently_verified=False, remote_saved_source_independently_verified=False,
        scientific_benefit='not_evaluated', emitter_admission=False, complete_D053=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    for name in ('view', 'view-sha256', 'fit', 'complete', 'resolution', 'prepared', 'out'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    result = verify(a.view, a.view_sha256, a.fit, a.complete, a.resolution, a.prepared)
    with Path(a.out).open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(result))
