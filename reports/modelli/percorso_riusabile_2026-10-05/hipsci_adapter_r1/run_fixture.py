import hashlib
import json
from pathlib import Path
import unittest
import test_adapter

root = Path(__file__).resolve().parent
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromModule(test_adapter))
paths = [root/'adapter.py', root/'test_adapter.py',
         root.parents[3]/'src/vcc2026/multisource.py']
receipt = dict(fixture_only=True, tests=result.testsRun,
               passed=result.wasSuccessful(), real_bank_consumed=False,
               files={str(p.relative_to(root.parents[3])):
                      hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
out = root/'fixture_result_r1.json'
if out.exists():
    raise FileExistsError('preserve fixture evidence; use a new output')
out.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
raise SystemExit(0 if result.wasSuccessful() else 1)
