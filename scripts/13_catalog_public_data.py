"""Fetch public Figshare metadata only; never download expression matrices."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import httpx


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'reports/data_audit/public_catalog.json')
    args = p.parse_args()
    result = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'articles': []}
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        for article in [27261219, 26819743, 27989294]:
            url = f'https://api.figshare.com/v2/articles/{article}'
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            result['articles'].append({
                'id': article, 'metadata_url': url,
                'title': data['title'], 'doi': data.get('doi'),
                'version': data.get('version'), 'license': data.get('license'),
                'files': [{k: f.get(k) for k in ['id', 'name', 'size', 'download_url', 'computed_md5', 'supplied_md5']} for f in data['files']],
            })
            print(article, [(f['name'], round(f['size'] / 1e9, 3)) for f in data['files']])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
