"""How the common response left in T2 relates to the one the panel centring removes: comune_t2.py <out.json>

For a fold, with the effects of T1 (panel centring), T1 at gamma 0 (no centring) and T2 (frozen all-target
vectors): P = mean row of (gamma 0 - T1) is the common response the panel centring removes from the mixture, and
D = mean row of (T2 - T1) is what T2 puts back. The slope <D,P>/<P,P> says how much of P stays in T2 (1 = all of
it, 0 = none, negative = T2 removes more than the panel centring). Measured on the fold effects, no truth read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepara_banco as B  # noqa: E402

DATA = Path('C:/Users/ferra/vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08')
FOLDS = {'C-K562': 'effetti_k562_t2', 'C-iPSC': 'effetti_ipsc_t2'}
SLUG = 'davideferrante11/vcc-validazione-logo-8a8ca58a-r5'


def rows(path):
    with np.load(path, allow_pickle=False) as z:
        return z['lfc'].astype(np.float64), z['observed'].astype(bool)


def main():
    out = Path(sys.argv[1])
    stage = DATA / 'livello_a_r5_gamma0'
    stage.mkdir(parents=True, exist_ok=True)
    pattern = '|'.join('effects/T1g0__%s.npz' % f for f in FOLDS)
    rc, answer = B.call(B.OWNER, ['kernels', 'output', SLUG, '-p', str(stage), '--file-pattern', pattern])
    report = {'kernel': SLUG, 'retrieval_returncode': rc, 'folds': {}, 'not_vcc_scores': True}
    for fid, folder in FOLDS.items():
        g0_path = next(stage.rglob('T1g0__%s.npz' % fid))
        t1, obs = rows(DATA / folder / 'T1.npz')
        t2, obs2 = rows(DATA / folder / 'T2.npz')
        g0, obs0 = rows(g0_path)
        assert np.array_equal(obs, obs2) and np.array_equal(obs, obs0)
        keep = obs.any(axis=1)
        mask = obs[keep]
        count = np.maximum(mask.sum(axis=0), 1)
        p = (np.where(mask, g0[keep] - t1[keep], 0.0)).sum(axis=0) / count
        d = (np.where(mask, t2[keep] - t1[keep], 0.0)).sum(axis=0) / count
        slope = float(d @ p / (p @ p))
        cosine = float(d @ p / np.sqrt((d @ d) * (p @ p)))
        top = np.argsort(-np.abs(p))[:500]
        report['folds'][fid] = {
            'targets': int(keep.sum()), 'gamma0_file': dict(B.pin(g0_path), path=g0_path.as_posix()),
            'norm_P_removed_by_panel_centring': float(np.sqrt(p @ p)), 'norm_D_put_back_by_T2': float(np.sqrt(d @ d)),
            'slope_D_on_P': slope, 'cosine_D_P': cosine,
            'slope_on_the_500_genes_with_largest_P': float(d[top] @ p[top] / (p[top] @ p[top])),
            'share_of_genes_where_D_and_P_agree_in_sign_top500': float((np.sign(d[top]) == np.sign(p[top])).mean())}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(report, fh, indent=1)
        fh.write('\n')
    print(json.dumps(report['folds'], indent=1))


if __name__ == '__main__':
    main()
