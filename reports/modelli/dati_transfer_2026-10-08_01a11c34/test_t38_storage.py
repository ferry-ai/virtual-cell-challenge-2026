"""Verify that removing an intermediate lossless filter does not change cells."""
import ast
import json
from pathlib import Path
import tempfile
import time
import sys
import numpy as np
from scipy import sparse
from vcc2026.submission import SubmissionWriter
from vcc2026.packaging import assert_payloads_equivalent
from percorso import HERE, ROOT, write_new, now

variant=sys.argv[1] if len(sys.argv)>1 else 'none'
assert variant in ('none','lzf')
rng=np.random.default_rng(20260912)
blocks=[sparse.csr_matrix(rng.poisson(0.4,size=(400,1000)).astype(np.float32)) for _ in range(3)]
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);timing={}
    for label,compression in [('gzip','gzip'),(variant,None if variant=='none' else 'lzf')]:
        started=time.monotonic()
        with SubmissionWriter(root/(label+'.h5ad'),[f'G{i}' for i in range(1000)],compression=compression,compression_opts=4 if compression=='gzip' else None) as writer:
            for context,block in zip(('A','B','C'),blocks):writer.add(block.copy(),target_gene='G0',context=context)
        timing[label]=dict(seconds=time.monotonic()-started,bytes=(root/(label+'.h5ad')).stat().st_size)
    equivalence=assert_payloads_equivalent(root/'gzip.h5ad',root/(variant+'.h5ad'))
tree=ast.parse((ROOT/'scripts/45_generate_prediction.py').read_text())
filenames=[node.args[0].right.value for node in ast.walk(tree)
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='write'
    and node.args and isinstance(node.args[0],ast.BinOp) and isinstance(node.args[0].right,ast.Constant)]
assert 'manifest_45_generate_prediction.json' in filenames
driver=(HERE/'generate_t3_existing_v3.py').read_text()
assert "generated/'manifest_45_generate_prediction.json'" in driver
report=dict(utc=now(),status='PASS',equivalence=equivalence,fixture_timing=timing,
    full_runtime_speed_not_measured=True,stage45_manifest_filename_verified=True,
    scientific_parameters_changed=False)
write_new(HERE/('t38_storage_tests_r1.json' if variant=='none' else 't38_storage_tests_lzf_r1.json'),report)
print(json.dumps(report))
