"""Additive CPU diagnostic on the completed seed-0 outputs; no training or promotion."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import traceback


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(payload64, review):
    os.environ.update({'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2',
                       'PYTHONUNBUFFERED':'1','CUDA_VISIBLE_DEVICES':''})
    work=Path('/kaggle/working/neural_cluster0_r1')
    work.mkdir()
    status={'started_utc':datetime.now(timezone.utc).isoformat(),'training':False,
            'changes_primary_gate':False,'seed0_eligible_for_cell_scorer':False}
    (work/'runtime_review.json').write_text(json.dumps(review,indent=2))
    try:
        payload=base64.b64decode(payload64,validate=True)
        if hashlib.sha256(payload).hexdigest()!=review['payload_sha256']:
            raise ValueError('Code archive hash differs')
        code=work/'code'
        expected={e['path']:e for e in review['code_allowlist']}
        with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
            entries=archive.getmembers()
            if len(entries)!=len(expected) or {e.name for e in entries}!=set(expected):
                raise ValueError('Code allowlist differs')
            for entry in entries:
                path=(code/entry.name).resolve()
                if not entry.isfile() or not path.is_relative_to(code.resolve()):
                    raise ValueError('Unsafe source entry')
                data=archive.extractfile(entry).read()
                if hashlib.sha256(data).hexdigest()!=expected[entry.name]['sha256']:
                    raise ValueError('Source hash differs')
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as f:
                    f.write(data)
        all_manifests=list(Path('/kaggle/input').rglob('manifest.json'))
        datasets=[p.parent for p in all_manifests if 'vcc-rete-contesti-r2' in p.parts
                  and sha(p)==review['dataset_manifest_sha256']]
        if len(datasets)!=1:
            raise ValueError('Cannot locate exact r2 dataset')
        folds=[]
        for family in review['fold_order']:
            evidence=review['fold_evidence'][family]
            candidates=[p.parent for p in all_manifests if p.parent.name==f'C_{family}_s0'
                        and sha(p)==evidence['manifest.json']['sha256']]
            if len(candidates)!=1:
                raise ValueError(f'Completed seed0 kernel output is not uniquely mounted: {family}')
            folder=candidates[0]
            for name,record in evidence.items():
                if (folder/name).stat().st_size!=record['bytes'] or sha(folder/name)!=record['sha256']:
                    raise ValueError(f'Frozen seed0 report differs: {family}/{name}')
            folds.append(folder)
        import numpy as np
        import pandas as pd
        (work/'environment.json').write_text(json.dumps({'python':sys.version,'numpy':np.__version__,
                                                        'pandas':pd.__version__},indent=2))
        script=code/'reports/analisi/lead_scientist_2026-09-29/neural_external_validation/cluster_pds.py'
        command=[sys.executable,str(script),'--runs',*[str(p) for p in folds],
                 '--data',str(datasets[0]),'--out',str(work/'diagnostic')]
        (work/'command.json').write_text(json.dumps(command,indent=2))
        with (work/'diagnostic.log').open('x',encoding='utf-8') as log:
            child=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,text=True)
        status['returncode']=child.returncode
        if child.returncode:
            raise RuntimeError('Additive diagnostic failed; original gate remains negative')
        status['complete']=True
    except Exception:
        status.update({'complete':False,'exception':traceback.format_exc()})
        raise
    finally:
        status['finished_utc']=datetime.now(timezone.utc).isoformat()
        (work/'completion.json').write_text(json.dumps(status,indent=2))
        print(json.dumps(status))
