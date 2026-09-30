"""Local diagnostic-reader checks; no remote inference or quality score."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('reader', HERE / 'compare_stack_diagnostics_r1.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReaderChecks(unittest.TestCase):
    def test_frozen_reference_complete(self):
        rows = reader.compare(reader.REFERENCE, reader.REFERENCE)
        self.assertEqual([row['target'] for row in rows], reader.EXPECTED)
        self.assertEqual(len(rows), 12)
        self.assertTrue(all(row['semantic_exact'] for row in rows))
        for row in rows:
            for value in row['fields'].values():
                self.assertTrue(value['exact'])
                if 'delta' in value:
                    self.assertEqual(value['delta'], 0)


if __name__ == '__main__':
    unittest.main()
