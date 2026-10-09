"""Local refusal tests for the dedicated production packager and launcher."""
from pathlib import Path
import json
import tempfile
import unittest
from package_ammi_production_v1 import package
from launch_ammi_production_v1 import launch

HERE = Path(__file__).resolve().parent


class ProductionToolTests(unittest.TestCase):
    def test_packager_rejects_pending_gate_before_private_access(self):
        draft = json.loads((HERE/'ammi_production_draft_prepared_r1.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'actual comparative readout'):
                package(draft['runtime_package'], root/'absent_locators', root/'absent_mounts',
                        root/'out', root/'receipt')
            self.assertFalse((root/'out').exists())

    def test_launcher_cannot_dispatch_a_pilot_or_another_account(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for fold, owner in [('C-K562','davideferrante11'), ('production','davidmaisterx')]:
                prepared = root/'prepared.json'
                prepared.write_text(json.dumps(dict(slug=owner+'/ammi-'+fold.lower()+'-cells-17-01a11c35-r1',
                                                    fold=fold, mode='cells', private=True)))
                (root/'access.json').write_text('{}')
                (root/'quota.json').write_text('{}')
                with self.assertRaisesRegex(ValueError, 'authorized private account'):
                    launch(prepared, root/'access.json', root/'quota.json', root/'launch.json')
                self.assertFalse((root/'launch.json').exists())
                self.assertFalse((root/'launch.json.lock').exists())


if __name__ == '__main__':
    unittest.main()
