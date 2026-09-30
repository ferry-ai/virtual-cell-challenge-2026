"""Reproduce the original exact-baseline guard failure without rescoring."""
import json
from pathlib import Path
import unittest
import select_stack_ab as selector

HERE = Path(__file__).resolve().parent


class NumericalIncidentTests(unittest.TestCase):
    def test_completed_original_reports_reproduce_exact_guard_failure(self):
        comparisons, tables = {}, {}
        for variant, name in [('A', 'stack_a_scoring_r2'), ('B', 'stack_b_scoring_r1')]:
            directory = HERE / name
            comparisons[variant] = selector.read_json(directory / 'pilot_comparison.json')
            targets = selector.read_json(directory / 'evaluation_manifest.json')['targets']
            tables[variant] = {arm: selector.table(directory / f'per_pert_{arm}.csv', targets)
                               for arm in ['transfer', 'stack']}
        self.assertEqual(comparisons['A']['raw']['transfer'], comparisons['B']['raw']['transfer'])
        with self.assertRaisesRegex(ValueError, 'Transfer per-target scores are not exactly identical'):
            selector.verify_tables(tables, comparisons, {})


if __name__ == '__main__':
    unittest.main()
