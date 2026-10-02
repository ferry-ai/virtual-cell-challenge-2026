"""Share the R-LAB corpus datasets of the owner account with other Kaggle accounts (readers), or make them public.

`kaggle datasets metadata <ref> --update` rewrites a dataset's settings from its metadata file, and a file without
``isPrivate: true`` makes the dataset PUBLIC (kaggle 2.2.4, `dataset_metadata_update`). This script downloads the
current metadata of each dataset, adds the reader accounts to its collaborators, sets ``isPrivate`` explicitly
(true unless ``--public``) and uploads it. ``--dry-run`` only downloads and prints what would change.
The owner token is read from KAGGLE_CONFIG_DIR (default ~/.kaggle); no key is printed.

    python share_datasets.py --readers davideferante davideferrante11 --dry-run
    python share_datasets.py --readers davideferante davideferrante11
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

DATASETS = ['rlab-cellnet-code', 'rlab-hepg2-nadig', 'rlab-jurkat-nadig', 'rlab-k562-gwps-r3', 'rlab-k562-essential-r2',
            'rlab-rpe1-r2', 'rlab-hipsci-targeted19', 'rlab-kolf-small', 'rlab-kolf-strong', 'rlab-tian-norman',
            'rlab-a549', 'rlab-h1-vcc2025-trainval']
OWNER = 'davidmaisterx'


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--readers', nargs='+', required=True)
    p.add_argument('--public', action='store_true', help='make the datasets public instead of sharing privately')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--datasets', nargs='*', default=DATASETS)
    a = p.parse_args()
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    for slug in a.datasets:
        ref = f'{OWNER}/{slug}'
        with tempfile.TemporaryDirectory() as d:
            meta_file = Path(api.dataset_metadata(ref, path=d))
            meta = json.loads(meta_file.read_text(encoding='utf-8'))
            info = meta.get('info', meta)
            before = dict(isPrivate=info.get('isPrivate'), collaborators=info.get('collaborators'))
            collab = {c['username']: c for c in (info.get('collaborators') or [])}
            for r in a.readers:
                collab.setdefault(r, {'username': r, 'role': 'reader'})
            info['collaborators'] = list(collab.values())
            info['isPrivate'] = not a.public
            if 'info' in meta:
                meta['info'] = info
            else:
                meta = info
            print(json.dumps({'dataset': ref, 'before': before,
                              'after': {'isPrivate': info['isPrivate'], 'collaborators': info['collaborators']}}))
            if a.dry_run:
                continue
            meta_file.write_text(json.dumps(meta), encoding='utf-8')
            api.dataset_metadata_update(ref, d)
            check = json.loads(Path(api.dataset_metadata(ref, path=d)).read_text(encoding='utf-8'))
            check = check.get('info', check)
            print(json.dumps({'dataset': ref, 'now': {'isPrivate': check.get('isPrivate'),
                                                      'collaborators': check.get('collaborators')}}))


if __name__ == '__main__':
    main()
