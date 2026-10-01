"""Portable, offline inventory for the R-LEAD handoff; standard library only.

Exit zero means the inventory was written, not that training/scoring is ready.
No datasets, model weights, credentials or holdout outcomes are opened.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata as md
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = '53d17fe'
CODE = 'reports/modelli/risposta_biologica_2026-09-30'
PACKAGES = {'numpy':'numpy', 'scipy':'scipy', 'pandas':'pandas', 'h5py':'h5py',
            'anndata':'anndata', 'PyYAML':'yaml', 'torch':'torch', 'scanpy':'scanpy',
            'cell-eval2':'cell_eval2.config', 'vcc-cli':'vcc'}


def git(*args):
    try:
        r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, timeout=30)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return -1, b''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def package(name, module):
    try:
        version = md.version(name)
    except md.PackageNotFoundError:
        version = None
    try:
        spec = importlib.util.find_spec(module)
        found = spec is not None
    except (ImportError, ValueError, AttributeError, OSError):
        found = False
    return {'version':version, 'required_module':module, 'module_found':found,
            'actual_import_and_api_check_required':True}


def disk(path):
    nearest = path
    while not nearest.exists() and nearest != nearest.parent:
        nearest = nearest.parent
    try:
        use = shutil.disk_usage(nearest)
        return {'checked_path':str(nearest), 'free_bytes':use.free, 'total_bytes':use.total}
    except OSError as exc:
        return {'error_type':type(exc).__name__}


def inspect(data_root):
    head_code, head = git('rev-parse', 'HEAD')
    ancestry_code, _ = git('merge-base', '--is-ancestor', BASE, 'HEAD')
    _, status = git('status', '--porcelain')
    runtime = {name:package(name, module) for name,module in PACKAGES.items()}
    config = ROOT/'reports/modelli/cellnet_esteso_2026-10-01/esito/training_r2/train/config.json'
    historical = json.loads(config.read_text(encoding='utf-8'))['code'] if config.exists() else {}
    code = {}
    for name in ('cellnet.py', 'cell_data.py', 'train_cellnet.py'):
        path = ROOT/CODE/name
        if not path.is_file():
            code[name] = {'exists':False}
            continue
        raw = path.read_bytes()
        rc, frozen = git('show', f'{BASE}:{CODE}/{name}')
        lf = raw.replace(b'\r\n', b'\n')
        code[name] = {'exists':True, 'sha256_bytes':sha(raw), 'sha256_lf':sha(lf),
                      'recorded_r2_sha256':historical.get(name),
                      'matches_r2_bytes':sha(raw) == historical.get(name),
                      'matches_audit_base_ignoring_line_endings':
                          sha(lf) == sha(frozen.replace(b'\r\n', b'\n')) if rc == 0 else None}
    required = ['CLAUDE.md', 'docs/CONSEGNA_TEAMMATE.md', 'docs/PROMPT_CLAUDE_TEAMMATE.md',
                'docs/piani/strategia-scientifica.md',
                'reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md',
                'reports/modelli/cellnet_completo_2026-10-01/esito/training_r3/train/desc/eval.json']
    repository = {'root':str(ROOT), 'head':head.decode().strip() if head_code == 0 else None,
                  'audit_base':BASE, 'audit_is_ancestor':ancestry_code == 0,
                  'working_tree_changes':status.decode(errors='replace').splitlines(),
                  'required_files':{p:(ROOT/p).is_file() for p in required}}
    data = {'configured':data_root is not None, 'root':str(data_root) if data_root else None,
            'exists':bool(data_root and data_root.is_dir()), 'files':{}}
    if data_root:
        relative = ['raw/controls/gene_names.csv', 'raw/controls/pert_counts.csv',
                    'raw/controls/context_A.h5ad', 'raw/controls/context_B.h5ad',
                    'raw/controls/context_C.h5ad',
                    'raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad']
        for name in relative:
            path = data_root/name
            try:
                data['files'][name] = {'exists':path.is_file(), 'bytes':path.stat().st_size if path.is_file() else None}
            except OSError as exc:
                data['files'][name] = {'exists':False, 'error_type':type(exc).__name__}
        data['disk'] = disk(data_root)
        data['inside_repository'] = data_root.is_relative_to(ROOT)
        expected_python = data_root/'.venv'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        data['expected_venv_python'] = str(expected_python)
        data['expected_venv_python_exists'] = expected_python.is_file()
        data['executing_expected_venv'] = Path(sys.executable).resolve() == expected_python.resolve()
    readiness = {
        'repo_evidence_present':all(repository['required_files'].values()) and repository['audit_is_ancestor'],
        'python_3_12':sys.version_info[:2] == (3,12),
        'cellnet_dependencies_located':all(runtime[n]['module_found'] for n in ('numpy','scipy','pandas','h5py','anndata','torch')),
        'scorer_config_module_located':runtime['cell-eval2']['module_found'],
        'data_root_configured_and_external':bool(data['exists'] and not data.get('inside_repository', True)),
        'heavy_training_ready':'not assessed: shard/weight access, imports, GPU/RAM, runtime smoke and permissions required',
        'limitations':'module discovery is not an import/API test; file size is not content/axis/checksum validation'}
    return {'written_utc':dt.datetime.now(dt.timezone.utc).isoformat(), 'platform':platform.platform(),
            'preflight_sha256_lf':sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
            'python':sys.version, 'executable':sys.executable, 'cpu_count':os.cpu_count(),
            'repository':repository, 'packages':runtime, 'code_against_audit':code,
            'data':data, 'repository_disk':disk(ROOT), 'readiness':readiness}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--data-root', default=os.environ.get('VCC2026_DATA_ROOT'), type=Path)
    a = p.parse_args()
    data_root = a.data_root.expanduser().resolve() if a.data_root else None
    result = inspect(data_root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({'out':str(a.out), 'readiness':result['readiness']}, indent=2))


if __name__ == '__main__':
    main()
