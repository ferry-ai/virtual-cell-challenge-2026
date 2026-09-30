import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np
import stack_confirmation_effects as extend


class ExtensionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parent.parent / 'generator_bench.py'
        spec = importlib.util.spec_from_file_location('extension_test_generator', path)
        cls.generator = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.generator
        spec.loader.exec_module(cls.generator)

    def test_extension_preserves_values_zeros_mask_and_roundtrip(self):
        # Deliberately permuted axes and a genuinely unmeasured destination gene.
        target = np.array(['reserve', 'old'])
        axis = np.array(['B', 'A'])
        values = np.array([[.7, 0], [.1, -.2]], dtype=np.float32)
        mask = np.array([[True, False], [False, True]])  # selected old,reserve order
        new, observed = extend.derive(self.generator, target, axis, values, mask,
                                     ['old', 'reserve'], np.array(['A', 'MISSING', 'B']))
        np.testing.assert_array_equal(new, np.array([[-.2, 0, .1], [0, 0, .7]], dtype=np.float32))
        np.testing.assert_array_equal(observed, [[False, False, True], [True, False, False]])
        self.assertTrue(observed[1, 0])  # observed zero must remain observed
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'old.npz'
            np.savez_compressed(path, targets=np.array(['old'], dtype=str),
                genes=np.array(['A', 'MISSING', 'B'], dtype=str), lfc=new[:1], observed=observed[:1])
            self.assertEqual(extend.exact_existing(['A', 'MISSING', 'B'], new, observed,
                                                 ['old', 'reserve'], path), 1)
            changed = observed.copy(); changed[0, 0] = True
            with self.assertRaisesRegex(ValueError, 'changed'):
                extend.exact_existing(['A', 'MISSING', 'B'], new, changed, ['old', 'reserve'], path)

    def test_missing_and_duplicate_axes_rejected(self):
        for target, wanted in ((['A'], ['B']), (['A', 'A'], ['A']), (['A'], ['A', 'A'])):
            with self.assertRaises(ValueError):
                extend.checked_rows(target, wanted)
        with self.assertRaisesRegex(ValueError, 'shape/dtype'):
            extend.derive(self.generator, ['A'], ['G'], np.zeros((1, 1)),
                          np.ones((1, 1)), ['A'], ['G'])


if __name__ == '__main__':
    unittest.main()
