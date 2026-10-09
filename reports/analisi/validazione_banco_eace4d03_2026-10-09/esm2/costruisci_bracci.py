"""Write, for one fold, the three fill arms of the fallback as stage-100 effect files with ONE mask and ONE scale.

    E2f      the fallback delivered by MODELLI-ESTERNI, copied byte for byte
    E2gen    the same pairs filled with amplitude x the target-independent part of the ridge
    E2swap   the same pairs filled with amplitude x the ridge prediction of another target

The arrays are the ones `supporto_fallback.audit` measured (same derangement, same amplitude, same mask): this
file only saves them, so that the six-member bench scores exactly what level A read. No truth is opened.

    py costruisci_bracci.py <spec.json of the support audit> <out dir> <manifest out.json>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import supporto_fallback as S  # noqa: E402


def build(spec: dict, M):
    amplitude = float(spec['amplitude'])
    panel, axis, lfc_t0, obs_t0 = S.load_effects(S.checked(spec['arms']['T0']))
    arrays = {}
    for name in ('fallback', 'E2', 'E2g'):
        targets, genes, lfc, obs = S.load_effects(S.checked(spec[name]))
        if targets != panel or genes != axis:
            raise SystemExit('axes differ in ' + name)
        arrays[name] = (lfc, obs)
    (lfc_f, obs_f), (lfc_e2, obs_e2), (lfc_g, obs_g) = arrays['fallback'], arrays['E2'], arrays['E2g']
    fill = obs_f & ~obs_t0
    if (fill & ~obs_e2).any() or (fill & ~obs_g).any() or (obs_t0 & ~obs_f).any():
        raise SystemExit('the fill mask is not covered by E2 and E2g')
    expected = (lfc_e2.astype(np.float64) * amplitude).astype(np.float32)
    rows = np.flatnonzero(obs_e2.any(axis=1))
    donor = np.arange(len(panel))
    donor[rows] = rows[M.shuffled_rows(rows.size)]                 # the derangement of the audit
    if (fill & ~obs_e2[donor]).any():
        raise SystemExit('a donor lacks a filled gene')
    gen = np.where(fill, (lfc_g.astype(np.float64) * amplitude).astype(np.float32), lfc_t0).astype(np.float32)
    swap = np.where(fill, expected[donor], lfc_t0).astype(np.float32)
    for name, lfc in (('E2gen', gen), ('E2swap', swap)):
        if not np.array_equal(lfc[obs_t0], lfc_t0[obs_t0]) or (lfc[~obs_f] != 0).any():
            raise SystemExit(name + ' changes a transfer value or predicts outside the mask')
    return panel, axis, obs_f, {'E2gen': gen, 'E2swap': swap}, {
        'filled_pairs': int(fill.sum()), 'targets_with_a_donor': int(rows.size), 'amplitude': amplitude,
        'swap_seed': M.BOOT_SEED, 'pairs_where_swap_equals_esm2': int((fill & (swap == lfc_f)).sum())}


def main() -> None:
    spec_path, out_dir, manifest_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    M = S.load_metrics()
    panel, axis, observed, arms, facts = build(spec, M)
    out_dir.mkdir(parents=True, exist_ok=False)
    files = {}
    delivered = out_dir / 'E2f.npz'
    shutil.copyfile(S.checked(spec['fallback']), delivered)
    for name, lfc in arms.items():
        np.savez_compressed(out_dir / (name + '.npz'), targets=np.array(panel), genes=np.array(axis), lfc=lfc,
                            observed=observed)
    for name in ('E2f', 'E2gen', 'E2swap'):
        path = out_dir / (name + '.npz')
        targets, genes, lfc, obs = S.load_effects(path)           # read back what the bench will read
        if targets != panel or genes != axis or not np.array_equal(obs, observed):
            raise SystemExit('written file differs: ' + name)
        if name in arms and not np.array_equal(lfc, arms[name]):
            raise SystemExit('written values differ: ' + name)
        files[name] = {'path': str(path).replace('\\', '/'), 'bytes': path.stat().st_size, 'sha256': S.sha(path)}
    if files['E2f']['sha256'] != spec['fallback']['sha256']:
        raise SystemExit('the copy of the delivered fallback is not byte-identical')
    doc = {'fold': spec['fold'], 'spec_sha256': S.sha(spec_path), 'code_sha256': S.sha(__file__),
           'reference_T0': {'sha256': spec['arms']['T0']['sha256']}, 'one_mask_for_the_three_arms': True, **facts,
           'files': files, 'reads_no_truth': True}
    with manifest_path.open('x', encoding='utf-8') as fh:
        json.dump(doc, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'fold': doc['fold'], **{k: (v['bytes'], v['sha256'][:12]) for k, v in files.items()}}))


if __name__ == '__main__':
    main()
