"""Exercise the adapted runner's closed gate and unchanged scientific manifest."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ammi_inputs_v3 import checked, module
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE=Path(__file__).resolve().parent


class CachedProductionTests(unittest.TestCase):
    def test_manifest_and_code_pins(self):
        receipt=json.loads((HERE/'ammi_cached_production_draft_prepared_r1.json').read_text())
        manifest=checked(receipt['runtime_template'])
        spec=json.loads(manifest.read_text())
        original=json.loads(checked(receipt['source_template']).read_text())
        self.assertEqual({k:v for k,v in spec.items() if k!='code'},
                         {k:v for k,v in original.items() if k!='code'})
        for name,digest in spec['code'].items(): self.assertEqual(pin(manifest.parent/name)['sha256'],digest)
        self.assertEqual(set(spec['code'])-set(original['code']),{'ammi_normalized_cache_v1.py'})
        for name,digest in original['code'].items():
            if name!='run_ammi_v4.py': self.assertEqual(spec['code'][name],digest)

    def test_actual_cached_runner_rejects_pending_readout(self):
        receipt=json.loads((HERE/'ammi_cached_production_draft_prepared_r1.json').read_text())
        manifest=checked(receipt['runtime_template'])
        runner=module(pin(manifest.parent/'run_ammi_v4.py'),'cached_production_test_runner')
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'production'
            with patch.object(runner.torch.cuda,'is_available',return_value=True):
                with self.assertRaisesRegex(ValueError,'both frozen pilot comparisons must be read'):
                    runner.run(manifest,receipt['runtime_template']['sha256'],'cells',17,out)
            self.assertFalse(out.exists())


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CachedProductionTests))
    if not result.wasSuccessful(): raise SystemExit(1)
    write_new(HERE/'ammi_cached_production_tests_r1.json',dict(status='PASS',tests=result.testsRun,
        test=pin(Path(__file__)),draft=pin(HERE/'ammi_cached_production_draft_prepared_r1.json'),
        no_cloud_launch=True,no_pilot_changes=True))
