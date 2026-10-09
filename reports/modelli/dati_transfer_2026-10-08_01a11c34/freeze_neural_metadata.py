"""Preserve the oversized metadata report outside Git and bind sample receipts."""
import json
from pathlib import Path
from percorso import HERE, DATA, ROOT, pin, read, sha, now, write_new


def main():
    original = HERE / 'neural_input_contract_r1.json'
    destination = DATA / 'processed/dati_transfer_2026-10-08_01a11c34/neural_inputs/r1/neural_input_contract_r1.json'
    if original.exists():
        if destination.exists():
            raise FileExistsError(destination)
        identity = pin(original)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # This is our newly generated JSON metadata, never raw data or an older report.
        original.rename(destination)
        if sha(destination) != identity['sha256']:
            raise ValueError('metadata relocation changed bytes')
    contract = read(destination)
    context_sources, missing, links = {}, [], []
    for cid, ctx in contract['contexts'].items():
        selected = []
        for bank, ntc in zip(ctx['source_banks'], ctx['NTC_rows']):
            unit = bank['unit']
            receipts = contract['bank_units'][unit]['sample_receipts']
            matching = []
            for sample in receipts:
                r = read(sample['receipt']['path'])
                if sha(sample['receipt']['path']) != sample['receipt']['sha256']:
                    raise ValueError('sample receipt changed')
                if r['files']['bank_rows.csv']['sha256'] != ntc['rows']['sha256']:
                    continue
                if r['genes'] != contract['genes'] or not r['complete']:
                    raise ValueError('sample incomplete or wrong axis length')
                matching.append(dict(receipt=sample['receipt'], kernel=sample['kernel'],
                    relative_path=sample['relative_path'], bank_receipt_sha256=r['bank_receipt_sha256'],
                    raw_shards=len([n for n in r['files'] if n.endswith('.npz') and n.startswith('shard_')]),
                    metadata_bytes=sum(v['bytes'] for n,v in r['files'].items() if n.endswith('.jsonl.gz')),
                    sample_matrix_bytes=sum(v['bytes'] for n,v in r['files'].items() if n.endswith('.npz') and n.startswith('shard_')),
                    raw_source_hashes=sorted({v['source_sha256'] for n,v in r['files'].items() if n.startswith('shard_')})))
            if not matching:
                missing.append(dict(context_id=cid, unit=unit, reason='no sample receipt with identical bank_rows.csv hash'))
            selected.append(dict(unit=unit, bank_rows=ntc['rows'], NTC_bank_rows=ntc['bank_row_indices'],
                                 cells=ntc['cells_before_joint_dedup'], samples=matching))
        context_sources[cid] = dict(identity=ctx['identity'], sources=selected,
            joint_adapter_required=ctx['joint_adapter_required'], pooling=ctx['pooling'])
    manifest = dict(schema='neural-context-input-manifest/2', utc=now(),
        evidence='metadata-only, receipt and bank-row hashes checked; no cell arrays read',
        contract=pin(destination), summary=contract['summary'],
        frozen_views={k:v['release'] for k,v in contract['folds'].items()},
        context_sources=context_sources, missing_sample_links=missing,
        controls_numeric_ready=False, current_remote_access_verified=False,
        native_depth=dict(materialized_sample_has_depth=False,
            required='pinned source H5AD obs/depth_native, or separately qualified native-axis sum',
            forbidden='using the sum of the aligned 18533-gene matrix as native depth'),
        sample_selection=dict(level=64, rule='existing nested sample; NTC rows only; retain each available stratum',
                              perturbed_cell_supervision=False),
        code=pin(Path(__file__)))
    write_new(HERE / 'neural_input_contract_manifest_r2.json', manifest)
    print(json.dumps(dict(contexts=len(context_sources), missing_sample_links=missing,
                          contract=manifest['contract'], manifest=pin(HERE/'neural_input_contract_manifest_r2.json'))))


if __name__ == '__main__':
    main()
