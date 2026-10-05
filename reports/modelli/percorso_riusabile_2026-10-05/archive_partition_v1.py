"""Partition complete BIO/target populations; never split their sampling strata.

Frozen original bank code is copied, not edited. All raw axes are reconciled
before selecting rows. Every part preserves full-population moments and the
same bottom-hash sample as the unpartitioned bank. Cross-part control lookup
is a consumer requirement, not a reason to duplicate controls.
"""
import base64, hashlib, json, math, zlib
from pathlib import Path
from prepare_archive_derivatives import replace


def partition_bank(source):
    source = replace(source, '    N = len(keys); shape = (N, G)', '''    all_keys = keys
    all_keys_sha256 = hashlib.sha256(json.dumps(all_keys, separators=(',', ':')).encode()).hexdigest()
    partition = spec['partition']; part, parts = partition['part'], partition['parts']
    if not 0 <= part < parts: raise ValueError('invalid row partition')
    keys = all_keys[part::parts]
    if not keys: raise ValueError('empty row partition')
    lookup = {k: i for i, k in enumerate(keys)}
    source_cells = actual
    actual = sum(counts[k] for k in keys)
    units = {k[:-1] for k in keys}
    N = len(keys); shape = (N, G)''')
    source = replace(source, '            rid = np.array([lookup[k] for k in rkeys])',
                     '            rid = np.array([lookup.get(k, -1) for k in rkeys])')
    source = replace(source, '                depth = np.asarray(x.sum(1)).ravel(); good = depth > 0',
                     '                depth = np.asarray(x.sum(1)).ravel(); selected = rid[lo:hi] >= 0; good = (depth > 0) & selected')
    source = replace(source, '                for j in np.flatnonzero(~good): zero_depth[int(rid[lo+j])] += 1',
                     '                for j in np.flatnonzero((depth <= 0) & selected): zero_depth[int(rid[lo+j])] += 1')
    source = replace(source, "               'source_verification': spec['receipt_sha256'], 'sample_levels': [32,64,128],",
                     "               'source_verification': spec['receipt_sha256'], 'sample_levels': [32,64,128],\n               'partition': {**partition, 'all_keys_sha256': all_keys_sha256, 'global_rows': len(all_keys), 'global_cells': source_cells, 'selected_cells': actual},")
    return source


def zero_population_sample(source):
    # Empty measured-depth populations retain a bank row; there is no cell to sample.
    return replace(source, "    if set(row_of) != seen_targets or totals['128'] != receipt['samples128']:",
        "    active_keys = {k for k, i in row_of.items() if int(rows.iloc[i]['n']) > 0}\n    if active_keys != seen_targets or totals['128'] != receipt['samples128']:")


def pack(files):
    payload = {n: {'data': base64.b64encode(zlib.compress(b)).decode(),
                  'sha256': hashlib.sha256(b).hexdigest()} for n, b in files.items()}
    code = 'import base64,hashlib,runpy,sys,os,zlib\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
    code += 'for n,v in P.items():\n b=zlib.decompress(base64.b64decode(v["data"]));assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
    code += 'runpy.run_path("archive_runtime.py",run_name="__main__")\n'
    compile(code, 'run.py', 'exec')
    if len(code.encode()) >= 1 << 20: raise ValueError('oversized payload')
    return code


def prepare(stage, out, parts=8):
    stage, out = Path(stage), Path(out)
    params = json.loads((stage/'params.json').read_text())
    if len(params['units']) != 1: raise ValueError('one archived unit per partition campaign')
    spec = params['units'][0]
    # Even if every cell is its own bank row, each part fits the observed 20.94GB
    # runtime disk/RAM guard. Actual source groups can only reduce this bound.
    if math.ceil(spec['cells']/parts)*18533*21+(2 << 30) >= 20940029952:
        raise ValueError('partition worst-case disk bound too large')
    out.mkdir(parents=True, exist_ok=False)
    files = {n: (stage/n).read_bytes() for n in
             ('bank.py','preparation.py','materialize_samples.py','archive_runtime.py','raw_files.json','raw_complete.json')}
    files['bank.py'] = partition_bank(files['bank.py'].decode()).encode()
    files['materialize_samples.py'] = zero_population_sample(files['materialize_samples.py'].decode()).encode()
    plan = []
    for part in range(parts):
        target = out/f'p{part}'; target.mkdir()
        p = {**params, 'units': [{**spec, 'partition': {'part': part, 'parts': parts,
              'method': 'sorted_complete_BIO_target_round_robin_v1'}}]}
        frozen = {**files, 'params.json': json.dumps(p).encode()}
        for name, raw in frozen.items(): (target/name).write_bytes(raw)
        code = pack(frozen); (target/'run.py').write_text(code, encoding='utf-8', newline='\n')
        slug = 'vcc-derivatives-'+params['slug'].removeprefix('rlab-')+f'-p{part}of{parts}-r2'
        meta = {'id': 'davidmaisterx/'+slug, 'title': slug, 'code_file': 'run.py',
                'language': 'python', 'kernel_type': 'script', 'is_private': True,
                'enable_gpu': False, 'enable_tpu': False, 'enable_internet': False,
                'dataset_sources': [params['dataset']], 'kernel_sources': [], 'competition_sources': []}
        (target/'kernel-metadata.json').write_text(json.dumps(meta, indent=1))
        proof = {'code_sha256': hashlib.sha256(code.encode()).hexdigest(), 'partition': p['units'][0]['partition'],
                 'raw_files_sha256': params['source_files_sha256'], 'raw_complete_sha256': params['raw_complete_sha256'],
                 'unit': spec['name'], 'global_cells': spec['cells']}
        (target/'prepared.json').write_text(json.dumps(proof, indent=1))
        plan.append({'slug': meta['id'], 'stage': str(target.resolve()), **proof})
    (out/'plan.json').write_text(json.dumps(plan, indent=1))
    return plan


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--stage', required=True); p.add_argument('--out', required=True)
    p.add_argument('--parts', type=int, default=8); a=p.parse_args()
    print(json.dumps({'prepared': len(prepare(a.stage, a.out, a.parts))}))
