import json
from pathlib import Path
import tempfile
import unittest
import stack_pack_runtime as runtime


class RuntimeTest(unittest.TestCase):
    def test_nullable_roundtrip_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'probe'
            runtime.preflight(out)
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'nullable_string_and_counts_roundtrip_passed')
            self.assertEqual(manifest['frozen_pack_sha256'], runtime.PACK_SHA)
            with self.assertRaises(FileExistsError):
                runtime.preflight(out)


if __name__ == '__main__':
    unittest.main()
