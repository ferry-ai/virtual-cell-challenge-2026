"""Freeze per-bank-part NTC extraction plans; metadata only, no launch."""
from collections import defaultdict
import argparse
import csv
import json
from pathlib import Path
from percorso import HERE, ROOT, read, pin, sha, now, write_new


def receipts(node):
    if isinstance(node, dict):
        if isinstance(node.get('receipt'), str) and node.get('receipt_sha256'):
            yield node
        else:
            for value in node.values():
                yield from receipts(value)
    elif isinstance(node, list):
        for value in node:
            yield from receipts(value)


def raw_inventory(node):
    files, evidence, mounts = [], [], []
    if isinstance(node, list):
        for value in node:
            f,e,m = raw_inventory(value); files += f; evidence += e; mounts += m
    elif isinstance(node, dict):
        if node.get('files_receipt'):
            path = ROOT/node['files_receipt']
            if sha(path) != node['files_sha256']:
                raise ValueError('raw file inventory changed')
            files.extend(read(path)); evidence.append(pin(path))
            mounts.append(dict(kind='dataset', ref=node['dataset'], version=node['version']))
        elif node.get('receipt') and node.get('sha256'):
            path = ROOT/node['receipt']
            if sha(path) != node['sha256']:
                raise ValueError('raw verification receipt changed')
            evidence.append(pin(path))
            table = path.parent/'shards.csv'
            if table.exists():
                with table.open(encoding='utf-8', newline='') as src:
                    for row in csv.DictReader(src):
                        if row.get('sha256_here') != row['sha256'] or row.get('same','').lower() != 'true':
                            raise ValueError('raw shard was not previously verified')
                        files.append(dict(file=row['path'], bytes=int(row['bytes']),
                                          sha256=row['sha256'], cells=int(row['cells'])))
                evidence.append(pin(table))
            mounts += [dict(kind='kernel', ref=r) for r in node.get('kernel_sources',[])]
        else:
            for value in node.values():
                if isinstance(value, (dict,list)):
                    f,e,m = raw_inventory(value); files += f; evidence += e; mounts += m
    return files,evidence,mounts


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--revision', required=True)
    args=parser.parse_args()
    manifest = read(HERE/'neural_input_contract_manifest_r2.json')
    if sha(manifest['contract']['path']) != manifest['contract']['sha256']:
        raise ValueError('input contract changed')
    contract = read(manifest['contract']['path'])
    expected = read(contract['canonical_storage']['path'])['expected_storage_units']
    production_ids = contract['folds']['production']['training_context_ids']
    view = read(contract['frozen_view']['path'])
    groups, aliases, skipped = {}, {}, []
    lookup = {}
    for cid in production_ids:
        ctx = contract['contexts'][cid]
        key = tuple((s['unit'], s['rows']['sha256'], tuple(s['bank_row_indices'])) for s in ctx['NTC_rows'])
        lookup[key] = cid
    for cid, ctx in contract['contexts'].items():
        key = tuple((s['unit'], s['rows']['sha256'], tuple(s['bank_row_indices'])) for s in ctx['NTC_rows'])
        aliases[cid] = lookup[key]
    for cid in production_ids:
        ctx = contract['contexts'][cid]
        for ntc in ctx['NTC_rows']:
            unit = ntc['unit']
            if unit == 'h1_val':
                skipped.append(dict(context_id=cid, unit=unit,
                    reason='shared H1 controls: canonical train source only; joint effects already verified equal',
                    evidence=ctx['verified_derivation']))
                continue
            key = (unit, ntc['rows']['sha256'])
            if key not in groups:
                groups[key] = dict(unit=unit, rows=ntc['rows'], controls=[])
            with Path(ntc['rows']['path']).open(encoding='utf-8', newline='') as src:
                rows = list(csv.DictReader(src))
            for index in ntc['bank_row_indices']:
                row = rows[index]
                if row['target'] != 'NTC':
                    raise ValueError('noncontrol included')
                groups[key]['controls'].append(dict(context_id=cid, bank_row=index,
                    expected_cells=int(float(row['n'])), identity={k:row[k] for k in
                    ('study','line_group','context','donor_or_clone','condition','modality','chemistry')}))
    outputs, gaps = [], []
    destination = HERE/'neural_inputs'/args.revision/'plans'
    if destination.exists():
        raise FileExistsError(destination)
    for (unit, digest), entry in groups.items():
        candidates = []
        for spec in receipts(contract['bank_units'][unit]['bank_metadata']):
            path = ROOT/spec['receipt']
            if sha(path) != spec['receipt_sha256']:
                raise ValueError('bank receipt changed')
            receipt = read(path)
            if receipt['files']['rows.csv']['sha256'] == digest:
                candidates.append((path, receipt))
        if len(candidates) != 1:
            gaps.append(dict(unit=unit, rows_sha256=digest, bank_receipts_matching=len(candidates)))
            continue
        path, receipt = candidates[0]
        controls = entry['controls']
        if len({r['bank_row'] for r in controls}) != len(controls):
            raise ValueError('duplicate control row')
        inventory,evidence,mounts = raw_inventory(expected[unit]['raw'])
        sample_hashes = {}
        for sample in contract['bank_units'][unit]['sample_receipts']:
            if sha(sample['receipt']['path']) != sample['receipt']['sha256']:
                raise ValueError('sample receipt changed')
            evidence.append(sample['receipt'])
            for name,item in sample['files'].items():
                if name.startswith('shard_'):
                    key=item['source_file'].replace('\\','/')
                    if sample_hashes.setdefault(key,item['source_sha256']) != item['source_sha256']:
                        raise ValueError('contradictory source hash')
        sources = []
        for source in receipt['sources']:
            relative = source['file'].replace('\\','/')
            matches = [s for s in inventory if s['file'].replace('\\','/').endswith('/'+relative)
                       or s['file'].replace('\\','/') == relative]
            if not matches and relative in sample_hashes:
                # Materialization verified the raw hash before emitting these
                # samples. The source size remains explicitly unknown locally.
                matches=[dict(file=relative,bytes=None,sha256=sample_hashes[relative],cells=source['cells'])]
            if len(matches) != 1 or matches[0]['cells'] != source['cells']:
                gaps.append(dict(unit=unit, raw_file=relative, inventory_matches=len(matches)))
                continue
            sources.append({**matches[0], 'file':relative})
        if len(sources) != len(receipt['sources']):
            continue
        if len({s['sha256'] for s in sources}) != len(sources):
            raise ValueError('duplicate raw source; resolve before extraction')
        part_id = unit + '_' + digest[:12]
        plan = dict(schema='native-NTC-extraction/1', part_id=part_id,
            **entry, genes=view['genes'], bank_receipt=pin(path),
            sources=sources, raw_inventory_evidence=evidence, mount_hints=mounts,
            cells_per_stratum=64, seed='esm2-ammi-ntc-r1',
            stratum_columns=['library','batch','guides'],
            preserve_columns=['study','line_group','context','donor_or_clone','condition','modality','chemistry'],
            policy='resample NTC only from pinned raw metadata; 64 per stratum; merge storage parts by common bottom-hash priority',
            denominator='obs/depth_native retained by ingestion; no aligned-axis substitute',
            H1_test_admitted=False, new_runtime_access_authorized=False)
        out = destination/(part_id+'.json')
        write_new(out, plan)
        outputs.append(dict(plan=pin(out), unit=unit, part_id=part_id,
            contexts=sorted({r['context_id'] for r in controls}),
            raw_files=len(sources), raw_bytes_known=sum(s['bytes'] or 0 for s in sources),
            raw_file_sizes_unknown=sum(s['bytes'] is None for s in sources),
            control_population=sum(r['expected_cells'] for r in controls)))
    report = dict(schema='NTC-extraction-plans/1', utc=now(),
        source=pin(HERE/'neural_input_contract_manifest_r2.json'),
        code=pin(HERE/'ntc_cells.py'), plans=outputs, context_aliases=aliases,
        skipped_duplicate_controls=skipped, gaps=gaps,
        summary=dict(plans=len(outputs), contexts=len({c for p in outputs for c in p['contexts']}),
            raw_files=sum(p['raw_files'] for p in outputs), raw_bytes_known=sum(p['raw_bytes_known'] for p in outputs),
            raw_file_sizes_unknown=sum(p['raw_file_sizes_unknown'] for p in outputs),
            numeric_outputs_ready=False, runtime_access_verified=False, cloud_jobs_started=0),
        limitations=['raw hashes still need verification on consuming runtime',
            'old level64 samples cap the biological unit across strata, not 64 cells per stratum',
            'raw metadata scan/extraction required for proposed per-stratum64 protocol',
            'cellular perturbed supervision not implemented by this NTC input path',
            'anchors require model-owner protocol choice and double/inner exclusions'])
    write_new(HERE/('ntc_extraction_plans_'+args.revision+'.json'), report)
    print(json.dumps(dict(summary=report['summary'], gap_count=len(gaps),gap_units=sorted({g['unit'] for g in gaps}))))


if __name__ == '__main__':
    main()
