"""Snapshot public candidate metadata, never expression matrices (4 MiB/URL cap)."""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import httpx

ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS = {
    'geo_keratinocyte_ko': 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE281860&targ=self&form=text&view=full',
    'keratinocyte_ko_files': 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE281nnn/GSE281860/suppl/filelist.txt',
    'geo_cd4': 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE314342&targ=self&form=text&view=full',
    'geo_nadig': 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE264667&targ=self&form=text&view=full',
    'geo_cd4_files': 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE314nnn/GSE314342/suppl/',
    'geo_nadig_files': 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE264nnn/GSE264667/suppl/',
    'pisces_info': 'https://huggingface.co/api/datasets/Xaira-Therapeutics/X-Atlas-Pisces',
    'pisces_tree': 'https://huggingface.co/api/datasets/Xaira-Therapeutics/X-Atlas-Pisces/tree/main?recursive=true&limit=1000',
    'orion_info': 'https://huggingface.co/api/datasets/Xaira-Therapeutics/X-Atlas-Orion',
    'orion_tree': 'https://huggingface.co/api/datasets/Xaira-Therapeutics/X-Atlas-Orion/tree/main?recursive=true&limit=1000',
    'figshare_claimed': 'https://api.figshare.com/v2/articles/20022944',
    'figshare_local': 'https://api.figshare.com/v2/articles/20029387',
    'cd4_repo_tree': 'https://api.github.com/repos/emdann/GWT_perturbseq_analysis_2025/git/trees/master?recursive=1',
    'cd4_readme': 'https://raw.githubusercontent.com/emdann/GWT_perturbseq_analysis_2025/master/README.md',
    'cd4_s3': 'https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/?list-type=2&prefix=marson2025_data/&max-keys=1000',
    'cd4_filelist': 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE314nnn/GSE314342/suppl/filelist.txt',
    'nadig_filelist': 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE264nnn/GSE264667/suppl/filelist.txt',
    'orion_readme': 'https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/raw/main/README.md',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=ROOT / 'reports/candidate_verification')
    p.add_argument('--only', nargs='*', choices=list(ENDPOINTS))
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'requests': {}}
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        for key in args.only or ENDPOINTS:
            url = ENDPOINTS[key]
            try:
                with client.stream('GET', url) as r:
                    body = bytearray()
                    for chunk in r.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 4 * 1024**2:
                            raise ValueError('Metadata response exceeds 4 MiB budget')
                    content = bytes(body)
                    (args.out / (key + '.txt')).write_bytes(content)
                    record = {'url': url, 'status': r.status_code, 'bytes': len(content),
                              'sha256': hashlib.sha256(content).hexdigest(), 'content_type': r.headers.get('content-type'),
                              'next_link': r.headers.get('link')}
                    if r.status_code == 200:
                        try:
                            data = json.loads(content)
                            if key.startswith('figshare'):
                                record.update(title=data.get('title'), doi=data.get('doi'), license=data.get('license'),
                                              files=[{k: f.get(k) for k in ['id','name','size','download_url','computed_md5']} for f in data.get('files',[])])
                            elif key.endswith('_info'):
                                record.update(sha=data.get('sha'), gated=data.get('gated'), files=data.get('siblings'), card=data.get('cardData'))
                            elif key.endswith('_tree') and isinstance(data, list):
                                record['files'] = [{k: f.get(k) for k in ['path', 'type', 'size', 'lfs']} for f in data]
                        except (ValueError, TypeError):
                            pass
                    manifest['requests'][key] = record
                    print(key, r.status_code, len(content), record.get('title', ''), flush=True)
            except Exception as e:
                manifest['requests'][key] = {'url': url, 'error': str(e)}
                print(key, type(e).__name__, str(e), flush=True)
    (args.out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(s, ctypes.c_ulonglong) for s in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','extended']]
    mem = MemoryStatus()
    mem.length = ctypes.sizeof(mem)
    ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    disk = shutil.disk_usage(ROOT)
    hardware = {'ram_total': mem.total_phys if ok else None, 'ram_available': mem.avail_phys if ok else None,
                'disk_total': disk.total, 'disk_free': disk.free, 'dense_float32_22m_x18533_bytes': 22000000*18533*4,
                'dense_float32_25_6m_x18533_bytes': 25600000*18533*4}
    (args.out / 'hardware.json').write_text(json.dumps(hardware, indent=2))
    print('hardware', hardware)


if __name__ == '__main__':
    main()
