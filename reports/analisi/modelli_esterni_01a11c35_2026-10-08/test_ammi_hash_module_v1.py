"""Cloud metadata assets are named by SHA and need an explicit Python loader."""
from pathlib import Path
import tempfile
import unittest
from ammi_inputs_v3 import module
from pie_adapter import sha256


class HashModuleTests(unittest.TestCase):
    def test_pinned_independent_metrics_load_without_extension(self):
        original=Path(__file__).parent.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco/metrics.py'
        with tempfile.TemporaryDirectory() as folder:
            asset=Path(folder)/sha256(original);asset.write_bytes(original.read_bytes())
            loaded=module(dict(path=str(asset),bytes=asset.stat().st_size,sha256=sha256(asset)),
                          'ammi_hash_named_metrics_fixture')
            self.assertEqual(loaded.BOOT,10000)
            self.assertEqual(loaded.BOOT_SEED,20261008)
            self.assertTrue(callable(loaded.paired_bootstrap))
            self.assertEqual(sha256(asset),sha256(original))


if __name__=='__main__':unittest.main()
