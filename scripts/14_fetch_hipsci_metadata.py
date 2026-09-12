"""Download only the three HIPSCI cell-metadata tables (about 21 MB)."""
import hashlib
import json
from pathlib import Path
import httpx
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1] / 'reports/data_audit'
    catalog = json.loads((root / 'public_catalog.json').read_text())
    out = root / 'hipsci_metadata'
    out.mkdir(exist_ok=True)
    article = next(a for a in catalog['articles'] if a['id'] == 27989294)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for f in article['files']:
            if 'Cell-Metadata' not in f['name']:
                continue
            path = out / f['name']
            if not path.exists():
                r = client.get(f['download_url'])
                r.raise_for_status()
                content = r.content
                if len(content) != f['size'] or hashlib.md5(content).hexdigest() != f['computed_md5']:
                    raise ValueError(f"Invalid download: {f['name']}")
                path.write_bytes(content)
            content = path.read_bytes()
            if len(content) != f['size'] or hashlib.md5(content).hexdigest() != f['computed_md5']:
                raise ValueError(f"Invalid cached file: {f['name']}")
            frame = pd.read_csv(path, sep='\t', nrows=3)
            print(f['name'], len(content), frame.to_string(index=False))


if __name__ == '__main__':
    main()
