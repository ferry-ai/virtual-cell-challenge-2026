"""Dispatch exactly the one private access diagnostic explicitly approved by the owner."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
STAGE = Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/cloud/J-iPSC-access-diag-r1')
JOB = 'esm2-j-ipsc-access-01a11c35-r1'
SLUG = 'davideferante/' + JOB


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE/name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=1)


def main():
    snapshot = HERE/'slots_preflight_r7_refresh.json'
    slots = json.loads(snapshot.read_text())
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(slots['utc'])).total_seconds()
    if not 0 <= age <= 900 or slots['active']['davideferante'] >= 4:
        raise ValueError('fresh available slot required')
    meta = json.loads((STAGE/'kernel-metadata.json').read_text())
    if (meta['id'] != SLUG or meta['is_private'] is not True or meta['enable_gpu'] or
        meta['kernel_sources'] or meta['dataset_sources'] != ['davideferante/esm2-j-ipsc-01a11c35-r4-private-bundle']):
        raise ValueError('diagnostic scope differs')
    if sha(STAGE/'run.py') != sha(HERE/'diagnose_private_input.py'):
        raise ValueError('diagnostic source differs')
    env = {k:v for k,v in os.environ.items() if k not in ('KAGGLE_CONFIG_DIR','KAGGLE_USERNAME','KAGGLE_KEY','KAGGLE_API_TOKEN')}
    env.update(KAGGLE_CONFIG_DIR='C:/Users/ferra/.kaggle-codex', PYTHONUTF8='1')
    lookup = subprocess.run([sys.executable,'-m','kaggle','kernels','list','--mine','--search',JOB,'--csv'],
        env=env,capture_output=True,text=True,timeout=120)
    if lookup.returncode or SLUG in lookup.stdout:
        raise ValueError('duplicate lookup failed or diagnostic already exists')
    save(JOB+'.launch.lock',dict(utc=datetime.now(timezone.utc).isoformat(),slug=SLUG,
        source_sha256=sha(STAGE/'run.py'),metadata_sha256=sha(STAGE/'kernel-metadata.json'),
        slots_sha256=sha(snapshot),approval='call_617ab433f8a74ae79fbdf3ada3933036 item 0: Sì, autorizzo il singolo job diagnostico',
        scope='one private remote first-chunk hash diagnostic; no training; no local RNA'))
    pushed = subprocess.run([sys.executable,str(HERE/'push_private_v2.py'),str(STAGE)],
        env=env,capture_output=True,text=True,timeout=300)
    accepted = pushed.returncode == 0 and 'successfully pushed' in pushed.stdout
    save(JOB+'.launch.json',dict(utc=datetime.now(timezone.utc).isoformat(),slug=SLUG,
        accepted=accepted,returncode=pushed.returncode,sanitized_answer=pushed.stdout))
    print(pushed.stdout)
    if not accepted:
        raise RuntimeError('diagnostic push not confirmed; do not retry this identity')


if __name__ == '__main__':
    main()
