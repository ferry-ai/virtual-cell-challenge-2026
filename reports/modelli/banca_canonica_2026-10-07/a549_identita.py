"""A549: are the eight 'pools' of the 27 September universe donors? Compare the two derivations.

    a549_identita.py <out.json>

Reads the old effect chunks (lane pools as pseudo-donors) and the new table (one pooled group)
for the 21 panel targets. Small local read of two existing tables; nothing is re-estimated.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

import percorso as P

OLD = P.DATA / 'processed/universe_a549_2026-09-27_me1'
OLD_REPORT = P.REPO / 'reports/sorgenti/universo_nuovi_2026-09-27'
NEW = P.DATA / 'processed/banca_canonica_2026-10-07/derivati_r1/a549_ko/a549_ko.npz'


def main():
    manifest = json.loads((OLD_REPORT / 'a549_me1/manifest.json').read_text(encoding='utf-8'))
    chunks = {c['file']: c for c in manifest['chunks']}
    with np.load(NEW, allow_pickle=False) as z:
        targets = [str(t) for t in z['targets']]
        genes = [str(g) for g in z['genes']]
        new = {k: np.asarray(z[k], np.float64) for k in ('shrunk', 'raw')}
        new_cells = dict(zip(targets, z['n_cells'].tolist()))
    index = list(csv.DictReader((OLD_REPORT / 'a549_me1/index.csv').open(encoding='utf-8')))
    where = {r['target']: r for r in index}
    rows, loaded = [], {}
    for i, target in enumerate(targets):
        r = where[target]
        if r['chunk'] not in loaded:
            path = OLD / r['chunk']
            assert P.sha(path) == chunks[r['chunk']]['sha256'], 'old chunk changed'
            with np.load(path, allow_pickle=False) as z:
                loaded[r['chunk']] = dict(targets=[str(t) for t in z['targets']],
                                          genes=[str(g) for g in z['genes']] if 'genes' in z.files else None,
                                          shrunk=np.asarray(z['shrunk'], np.float64), raw=np.asarray(z['raw'], np.float64))
        old = loaded[r['chunk']]
        assert old['genes'] is None or old['genes'] == genes, 'old table on another axis'
        j = old['targets'].index(target)
        record = dict(target=target, old_cells=int(float(r['n_cells'])), new_cells=int(new_cells[target]),
                      old_pools_with_cells=int(r['pools_with_cells']))
        for key in ('shrunk', 'raw'):
            a, b = new[key][i], old[key][j]
            both = np.isfinite(a) & np.isfinite(b)
            norm = np.linalg.norm(a[both]) * np.linalg.norm(b[both])
            record[key + '_cosine'] = float(a[both] @ b[both] / norm) if norm > 0 else None
            record[key + '_genes_both'] = int(both.sum())
        rows.append(record)
    cos = [r['raw_cosine'] for r in rows if r['raw_cosine'] is not None]
    shr = [r['shrunk_cosine'] for r in rows if r['shrunk_cosine'] is not None]
    P.write_new(sys.argv[1], dict(
        utc=P.now(), question='are the eight A549 pools biological donors?',
        answer='no: the old sums assign each cell to pool = category code of a batch-like column modulo 8',
        evidence=dict(code='reports/sorgenti/universo_nuovi_2026-09-27/h5ad_sums.py (docstring and --pool-col help)',
                      manifest_donors=manifest['estimator'] if isinstance(manifest['estimator'], str) else manifest['estimator'].get('donors'),
                      old_manifest=P.pin(OLD_REPORT / 'a549_me1/manifest.json'), new_table=P.pin(NEW),
                      same_cells=dict(old=manifest['summary']['cells'], new_bank=606075,
                                      old_controls=manifest['summary']['ntc_cells'], new_bank_controls=45320)),
        difference='old: one contrast per pool against that pool\'s controls, pooled by cells; new: one contrast on the '
                   'summed counts. Same cells, different batch matching. The bank does not keep the pool column.',
        targets=len(rows), cells_equal=all(r['old_cells'] == r['new_cells'] for r in rows),
        raw_cosine_median=float(np.median(cos)), raw_cosine_min=float(min(cos)),
        shrunk_cosine_median=float(np.median(shr)), shrunk_cosine_min=float(min(shr)), per_target=rows,
        reading='descriptive; A549 is a KO arm and is not in the vote of this release'))
    print(json.dumps(dict(targets=len(rows), cells_equal=all(r['old_cells'] == r['new_cells'] for r in rows),
                          raw_cosine_median=float(np.median(cos)), raw_cosine_min=float(min(cos)),
                          shrunk_cosine_median=float(np.median(shr)), shrunk_cosine_min=float(min(shr)))))


if __name__ == '__main__':
    main()
