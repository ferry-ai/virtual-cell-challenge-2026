"""Resume after an H5AD nullable-string serialization failure, no science change."""
import ast
import hashlib
import json
from pathlib import Path

from build_stack_resume_r2 import replace_once

HERE = Path(__file__).resolve().parent
ROUNDTRIP = r'''import json, sys
from pathlib import Path
import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp
ad.settings.allow_write_nullable_strings = True
out = Path(sys.argv[1])
out.mkdir()
results = []
for arm, values in [('transfer', [[0, 3, 4], [5, 0, 6]]), ('stack', [[7, 1, 0], [0, 2, 8]])]:
    x = sp.csr_matrix(values, dtype=np.float32)
    obs = pd.DataFrame({'gene': pd.array(['TEST_A', 'TEST_B'], dtype='string')}, index=['c0', 'c1'])
    var = pd.DataFrame(index=pd.Index(pd.array(['G_B', 'G_A', 'G_C'], dtype='string'), name=None))
    obj = ad.AnnData(x, obs=obs, var=var)
    path = out / f'prediction_{arm}.h5ad'
    obj.write_h5ad(path, compression='gzip')
    restored = ad.read_h5ad(path)
    np.testing.assert_array_equal(restored.X.toarray(), x.toarray())
    assert list(restored.var_names) == ['G_B', 'G_A', 'G_C']
    assert restored.obs.gene.astype(str).tolist() == ['TEST_A', 'TEST_B']
    assert str(obj.var.index.dtype) == 'string'
    results.append({'arm': arm, 'counts_exact': True, 'axis_exact': True, 'labels_exact': True})
print(json.dumps({'setting': 'anndata.settings.allow_write_nullable_strings=True', 'anndata': ad.__version__, 'roundtrips': results}))
'''


def main():
    old = HERE / "stack_resume_r2/colab_stack_infer_r2.py"
    if hashlib.sha256(old.read_bytes()).hexdigest() != "ccbf39e6339389a6aae53aa005b0a62f2fc4605abde504cfdfb1ab5a5c983ce3":
        raise ValueError("Previous reviewed launcher differs")
    text = old.read_text(encoding="utf-8")
    text = replace_once(text, 'previous = work.parent / "lead_stack_infer_2026-09-29_r1"',
                         'previous = work.parent / "lead_stack_infer_2026-09-29_r2"')
    start = text.index('        # The real traceback is a missing eager import.')
    end = text.index('        run([python, "-m", "pip", "check"]', start)
    text = text[:start] + '''        save(work / "managed_python.json", managed | {"reused_from": str(previous),
            "runtime_format_fix": "anndata.settings.allow_write_nullable_strings=True; no package changes"})
''' + text[end:]
    text = replace_once(text,
        '''        if after - before != {"pooch==1.8.2"} or before - after:
            raise ValueError("Runtime repair changed packages beyond the approved pooch addition")''',
        '''        if after != before:
            raise ValueError("Serialization-only resume changed the environment")''')
    text = replace_once(text, '        model_dir.mkdir()\n',
                         '        if not model_dir.is_dir():\n            raise FileNotFoundError("Verified r2 model cache is missing")\n')
    start = text.index('        if available["disk_free_bytes"] < sum(')
    end = text.index('        save(work / "verified_model_files.json"', start)
    text = text[:start] + '''        if available["disk_free_bytes"] < 2 * 1024**3:
            raise RuntimeError("Need 2 GiB working disk reserve")
        for model_file in review["model_files"]:
            path = model_dir / model_file["path"]
            if path.stat().st_size != model_file["bytes"] or sha(path) != model_file["sha256"]:
                raise ValueError("Cached public model file differs: " + model_file["path"])
''' + text[end:]
    text = replace_once(text, '        prediction = work / "prediction"',
        '        roundtrip_script = work / "serialization_roundtrip.py"\n'
        '        roundtrip_script.write_text(' + repr(ROUNDTRIP) + ', encoding="utf-8")\n'
        '        run([python, roundtrip_script, work / "serialization_roundtrip"],\n'
        '            work / "serialization_roundtrip.log", cwd=code, env=env)\n'
        '        prediction = work / "prediction"')
    text = replace_once(text, 'from pathlib import Path\nimport stack.model_loading as loading',
                         'from pathlib import Path\nimport anndata as ad\nad.settings.allow_write_nullable_strings = True\nimport stack.model_loading as loading')
    text = replace_once(text,
        '''        if not (prediction / "finished.json").exists():
            raise RuntimeError("Inference returned without a completion manifest")''',
        '''        if not (prediction / "finished.json").exists():
            raise RuntimeError("Inference returned without a completion manifest")
        comparisons = []
        for i, target in enumerate(review["targets"]):
            old_path = previous / "prediction" / f"diagnostic_{i:02d}.json"
            new_path = prediction / f"diagnostic_{i:02d}.json"
            old_value = json.loads(old_path.read_text(encoding="utf-8"))
            new_value = json.loads(new_path.read_text(encoding="utf-8"))
            comparisons.append({"target": target, "identical": old_value == new_value,
                "old_sha256": sha(old_path), "new_sha256": sha(new_path),
                "differences": {k: {"old": old_value.get(k), "new": new_value.get(k)}
                    for k in set(old_value) | set(new_value) if old_value.get(k) != new_value.get(k)}})
        save(work / "diagnostic_repeat_comparison.json", {"targets": comparisons,
             "all_identical": all(x["identical"] for x in comparisons),
             "claim": "Numerical diagnostics only; does not reconstruct or compare the previous missing final cells"})''')
    text = replace_once(text,
        "work='/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_2026-09-29_r2'",
        "work='/content/drive/MyDrive/vcc2026/runs/lead_stack_infer_2026-09-29_r3'")
    ast.parse(text)
    out = HERE / "stack_resume_r3"
    out.mkdir()
    (out / "colab_stack_infer_r3.py").write_bytes(text.encode())
    (out / "serialization_roundtrip.py").write_bytes(ROUNDTRIP.encode())
    digest = hashlib.sha256(text.encode()).hexdigest()
    shell = f'''#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_infer_setup_2026-09-29_r3"
test ! -e "$DRIVE/runs/lead_stack_infer_2026-09-29_r3"
test -x /content/lead_stack_scratch_r1/venv/bin/python
echo "{digest}  $SETUP/colab_stack_infer_r3.py" | sha256sum -c -
python -u "$SETUP/colab_stack_infer_r3.py"
'''
    (out / "076_lead_stack_infer_r3.sh").write_bytes(shell.encode())
    review = {"status": "prepared_not_run", "runtime_only_fix": "anndata.settings.allow_write_nullable_strings=True",
        "checkpoint_download": False, "dependency_install": False,
        "scientific_adapter_plan_bundle_weights_unchanged": True,
        "preflight": "Two H5AD roundtrips with nullable gene index, sparse counts and nullable obs labels before checkpoint loading",
        "verification": "Same frozen payload; full cached hashes; identical before/after env; 12 diagnostics compared after inference",
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())}}
    (out / "review_manifest.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(review, indent=2))


if __name__ == "__main__":
    main()
