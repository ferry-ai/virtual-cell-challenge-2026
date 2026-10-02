"""Stage the bench cube, the research code and the protocols as one flat folder for a private Kaggle dataset.

Hard links (same volume) so nothing is copied; the folder lives in the data root. Writes dataset-metadata.json for
`kaggle datasets create` under the account given (private by default) and a manifest with every file's sha256.

    py.cmd stage_dataset.py --cube <data>/.../cube_r2 --owner davideferrante11 --out <data>/.../kaggle_stage_cube_r2
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import REPO, coords_path, now_utc, sha256  # noqa: E402

CODE = ['arms.py', 'common.py', 'metrics.py', 'splits.py', 'fitting.py', 'p3_run.py', 'p3_run_j.py', 'nn_residual.py',
        'decide.py', 'registry.py']


def link(src: Path, dest: Path) -> None:
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--slug', default='rlead-bench-cube-r2')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    a.out.mkdir(parents=True)
    for f in sorted(a.cube.rglob('*')):
        if f.is_file():
            rel = f.relative_to(a.cube)
            name = 'cube__' + '__'.join(rel.parts)
            link(f, a.out / name)
    for name in CODE:
        shutil.copy2(HERE.parent / name, a.out / f'code__{name}')
    report = REPO / 'reports' / 'analisi' / 'generalizzazione_contesti_2026-10-02'
    shutil.copy2(report / 'PROTOCOLLO.json', a.out / 'protocol__PROTOCOLLO.json')
    shutil.copy2(report / 'p4' / 'PROTOCOLLO_NN.json', a.out / 'protocol__PROTOCOLLO_NN.json')
    shutil.copy2(coords_path('external/annotation/gene_coordinates_gencode_v50.tsv'), a.out / 'gene_coordinates_gencode_v50.tsv')
    files = {f.name: dict(bytes=f.stat().st_size, sha256=sha256(f)) for f in sorted(a.out.iterdir())}
    (a.out / 'stage_manifest.json').write_text(json.dumps(dict(written_utc=now_utc(), cube=str(a.cube), files=files),
                                                          indent=1), encoding='utf-8')
    (a.out / 'dataset-metadata.json').write_text(json.dumps(dict(
        title='rlead bench cube r2', id=f'{a.owner}/{a.slug}', licenses=[dict(name='other')])), encoding='utf-8')
    print(json.dumps(dict(files=len(files), gigabytes=round(sum(v['bytes'] for v in files.values()) / 1e9, 2))))


if __name__ == '__main__':
    main()
