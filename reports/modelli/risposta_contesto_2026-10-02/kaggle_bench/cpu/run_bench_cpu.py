"""Kaggle kernels of the R-LEAD bench on ten line groups: CPU mode (P4 data: simple arms, C and J) or GPU mode (P4 network).

The private dataset `davideferrante11/rlead-bench-cube-r2` carries the bench cube (flat files), the research code of
reports/modelli/risposta_contesto_2026-10-02 and the two frozen protocols. This script rebuilds the cube folder
layout under /kaggle/working (hard links when possible), points the protocols at the gene table of the dataset and runs,
in order, each step writing its own folder so that a timeout keeps the finished steps:

1. p3_run.py      regime C, every arm of PROTOCOLLO.json, ten groups held out whole (CPU);
2. nn_residual.py the network of PROTOCOLLO_NN.json on the same rows (GPU when available);
3. decide.py      the frozen rules on 1 and on 1+2;
4. p3_run_j.py    regime J (CPU), last because it is the longest.

Nothing here changes a rule, a threshold or a parameter of the protocols except the path of the gene table.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

t0 = time.time()
INPUT = os.environ.get('BENCH_INPUT', '/kaggle/input')
src = Path(sorted(glob.glob(f'{INPUT}/**/rlead-bench-cube-r2', recursive=True))[0])
work = Path(os.environ.get('BENCH_WORKING', '/kaggle/working'))
code = work / 'code'
cube = work / 'cube_r2'
# the dataset is flat (Kaggle skips sub-folders): cube__<table>__<file>, cube__<file>, code__<file>, protocol__<file>
code.mkdir()
cube.mkdir()
for f in sorted(src.iterdir()):
    if f.name.startswith('code__'):
        shutil.copy2(f, code / f.name[len('code__'):])
        continue
    if not f.name.startswith('cube__'):
        continue
    rest = f.name[len('cube__'):]
    if '__' in rest:
        table, name = rest.split('__', 1)
        (cube / table).mkdir(exist_ok=True)
        dest = cube / table / name
    else:
        dest = cube / rest
    try:
        os.symlink(f, dest)          # /kaggle/input is read-only and on another file system
    except OSError:
        shutil.copy2(f, dest)
coords = src / 'gene_coordinates_gencode_v50.tsv'
protos = {}
for name in ('PROTOCOLLO.json', 'PROTOCOLLO_NN.json'):
    proto = json.loads((src / f'protocol__{name}').read_text(encoding='utf-8'))
    proto['parameters']['gene_coordinates'] = str(coords)
    protos[name] = work / name
    protos[name].write_text(json.dumps(proto, indent=1), encoding='utf-8')
print(json.dumps({'t': round(time.time() - t0, 1), 'msg': 'layout ready', 'tables': len(list(cube.iterdir()))}), flush=True)
if os.environ.get('BENCH_LAYOUT_ONLY'):
    sys.exit(0)


def run(args, label):
    t = time.time()
    done = subprocess.run([sys.executable] + args, cwd=code, capture_output=True, text=True)
    (work / f'{label}.log').write_text(done.stdout + '\n--- stderr ---\n' + done.stderr[-20000:], encoding='utf-8')
    print(json.dumps({'t': round(time.time() - t0, 1), 'step': label, 'seconds': round(time.time() - t, 1),
                      'returncode': done.returncode}), flush=True)
    return done.returncode == 0


MODE = os.environ.get('BENCH_MODE', 'cpu')
if MODE == 'gpu':
    run(['nn_residual.py', '--cube', str(cube), '--gm-cache', str(work / 'gm_cache'), '--gm-cache-writable',
         '--protocol', str(protos['PROTOCOLLO_NN.json']), '--out', str(work / 'p4_nn_r2')], 'p4_nn_r2')
    shutil.rmtree(cube, ignore_errors=True)
    shutil.rmtree(work / 'gm_cache', ignore_errors=True)
    print(json.dumps({'t': round(time.time() - t0, 1), 'msg': 'done'}), flush=True)
    sys.exit(0)
ok = run(['p3_run.py', '--cube', str(cube), '--protocol', str(protos['PROTOCOLLO.json']),
          '--out', str(work / 'p3_c_r3')], 'p3_c_r3')
if ok:
    run(['decide.py', '--run', str(work / 'p3_c_r3'), '--protocol', str(protos['PROTOCOLLO.json']),
         '--out', str(work / 'decision_c_r3')], 'decision_c_r3')
    run(['p3_run_j.py', '--cube', str(cube), '--protocol', str(protos['PROTOCOLLO.json']),
         '--out', str(work / 'p3_j_r3')], 'p3_j_r3')
    run(['decide.py', '--run', str(work / 'p3_c_r3'), str(work / 'p3_j_r3'), '--protocol',
         str(protos['PROTOCOLLO.json']), '--out', str(work / 'decision_cj_r3')], 'decision_cj_r3')
shutil.rmtree(cube, ignore_errors=True)            # the cube is input, not output
for d in work.glob('p3_*_r3/gm_cache'):
    shutil.rmtree(d, ignore_errors=True)
print(json.dumps({'t': round(time.time() - t0, 1), 'msg': 'done'}), flush=True)
