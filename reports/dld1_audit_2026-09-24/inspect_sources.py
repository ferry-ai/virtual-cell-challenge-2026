"""Inspect complete DLD1 labels and the small Mixscale DE archive, without extracting it.

Run: scripts\\py.cmd reports\\dld1_audit_2026-09-24\\inspect_sources.py
     --download-dir <data-root>/external/mixscale_zenodo14518762 --out <new-directory>
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from vcc2026.config import paths


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--download-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    root = paths().data_root
    panel = set(pd.read_csv(root/'raw/controls/pert_counts.csv').iloc[:, 0])
    with gzip.open(root/'external/dld1_gse337988/GSE337988_sublib2_de_matrices_lfc_matrix_Low1.csv.gz', 'rt') as f:
        labels = next(csv.reader(f))[1:]
    # Exact panel-symbol prefix, followed by delimiter. No speculative alias mapping.
    coverage = {t: [label for label in labels if label.startswith(t+'_')] for t in sorted(panel)}
    coverage = {t: cols for t, cols in coverage.items() if cols}
    (args.out/'dld1_complete_labels.json').write_text(json.dumps(coverage, indent=2), encoding='utf-8')
    print('DLD1 exact-prefix targets:', len(coverage), flush=True)
    args.download_dir.mkdir(parents=True, exist_ok=True)
    archive = args.download_dir/'DE_results_all_pathway.zip'
    url = 'https://zenodo.org/records/14518762/files/DE_results_all_pathway.zip?download=1'
    expected_md5 = 'f077cba680a1affc599f5153d99b0e45'
    if not archive.exists():
        with urllib.request.urlopen(url, timeout=90) as response, archive.open('xb') as dest:
            while block := response.read(1024*1024):
                dest.write(block)
        print('Download completed', flush=True)
    with archive.open('rb') as f:
        md5 = hashlib.file_digest(f, 'md5').hexdigest()
    if md5 != expected_md5:
        raise ValueError('Archive checksum differs from Zenodo')
    with archive.open('rb') as f:
        sha256 = hashlib.file_digest(f, 'sha256').hexdigest()
    records = []
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            match = re.fullmatch(r'(.+)_(IFNB|IFNG|INS|TGFB1|TNFA)_pathway_DE_results.txt', Path(item.filename).name)
            if match and not item.filename.startswith('__MACOSX/'):
                records.append(dict(path=item.filename, target=match[1], pathway=match[2],
                                    bytes=item.file_size, compressed=item.compress_size))
        examples = []
        for pathway in sorted({r['pathway'] for r in records}):
            item = next(r for r in records if r['pathway'] == pathway)
            with z.open(item['path']) as f:
                df = pd.read_csv(f, sep='\t')
            examples.append(dict(path=item['path'], shape=list(df.shape), columns=df.columns.tolist(),
                                 first_rows=df.head(2).to_dict(orient='records')))
        overlaps = sorted({r['target'] for r in records} & panel)
    result = dict(url=url, md5=md5, sha256=sha256, bytes=archive.stat().st_size,
                  files=records, targets=len({r['target'] for r in records}),
                  panel_overlap=overlaps, examples=examples)
    with (args.out/'mixscale_inventory.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    manifest = args.download_dir/'manifest.json'
    if not manifest.exists():
        manifest.write_text(json.dumps({k: result[k] for k in ['url','md5','sha256','bytes']}, indent=2))
    print(json.dumps({k:result[k] for k in ['bytes','targets','panel_overlap','examples']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
