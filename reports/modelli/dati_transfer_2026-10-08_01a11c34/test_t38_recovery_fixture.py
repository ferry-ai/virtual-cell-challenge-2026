"""Exercise frozen stage48 on six sparse cells with scratch-only packaging."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import h5py
import numpy as np
from scipy import sparse
from percorso import HERE, ROOT, write_new, now
from prepare_extended_generation import unpack
sys.path.insert(0,str(ROOT/'src'))
from vcc2026.submission import SubmissionWriter

label=sys.argv[1]
members,_=unpack(ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package/run.py')
with tempfile.TemporaryDirectory() as td:
    root=Path(td);work=root/'work';scratch=root/'scratch';work.mkdir();scratch.mkdir()
    for name,data in members.items():
        if name.startswith(('repo/','vendor/')):
            path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    genes=['G'+str(i) for i in range(18533)];source=scratch/'recovery_prediction.h5ad'
    with SubmissionWriter(source,genes,compression='lzf',compression_opts=None) as writer:
        for context in ('A','B','C'):
            x=sparse.csr_matrix(([1.,2.],([0,1],[1,2])),shape=(2,18533),dtype=np.float32)
            writer.add(x,target_gene='G0',context=context)
    # Tiny fixture has fewer values than SubmissionWriter's extensible 1M
    # chunk. Use valid fixed-size small chunks for the frozen copy routine;
    # the full T3 input has 2B values, so it does not have this fixture issue.
    with h5py.File(source,'a') as h:
        for name in ('data','indices'):
            arr=h['X/'+name][:];del h['X/'+name]
            h['X'].create_dataset(name,data=arr,chunks=(len(arr),),compression='lzf')
    g=root/'genes.csv';g.write_text('gene_name\n'+'\n'.join(genes)+'\n')
    p=root/'perts.csv';p.write_text('target_gene,n_cells\nG0,2\n')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    cmd=[sys.executable,str(work/'repo/scripts/48_package_prediction.py'),'--run-id','t38-recovery-fixture',
        '--prediction',str(source),'--expect-sha256',digest,'--out',str(scratch/'pack'),
        '--workdir',str(scratch/'payload'),'--genes',str(g),'--perts',str(p),
        '--contexts','A,B,C','--reserve-gib','0.1','--zstd-threads','1']
    env=dict(os.environ,PYTHONUTF8='1',PYTHONPATH=str(work/'vendor')+os.pathsep+str(work/'repo/src'))
    result=subprocess.run(cmd,capture_output=True,text=True,env=env,encoding='utf-8')
    (HERE/('t38_recovery_fixture_'+label+'.txt')).open('x',encoding='utf-8').write(result.stdout+result.stderr)
    if result.returncode:
        print((result.stdout+result.stderr)[-3000:]);raise SystemExit(result.returncode)
    doc=json.loads((scratch/'pack/packaging.json').read_text())
    assert doc['verification']['payload_vs_input']['x_arrays_bit_identical']
    assert doc['verification']['official_container_validator']=='passed'
    write_new(HERE/('t38_recovery_fixture_'+label+'.json'),dict(utc=now(),status='PASS',fixture_shape=[6,18533],
        real_generated_cells=False,verification=doc['verification'],package=doc['package'],
        archive_kept_only_in_temporary_fixture=True))
    print('PASS: frozen stage48, scratch output/payload, full hash and official container/payload verification')
