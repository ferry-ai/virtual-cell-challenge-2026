import copy
import json
import math
import unittest
import read_t28_score as reader


class ScoreReaderTest(unittest.TestCase):
    def setUp(self):
        self.reg = json.loads(reader.REGISTRATION.read_text())
        self.base = json.loads(reader.BASELINE.read_text(encoding='utf-8-sig'))
        self.status = copy.deepcopy(self.base)
        self.status.update(entry_id='synthetic-t28', model_name=reader.MODEL)

    def candidate(self, value):
        obj = copy.deepcopy(self.status)
        obj['score_avg'] = value
        obj['score_pds'] += 6*(value-self.base['score_avg'])
        return obj

    def test_literal_inclusive_cutoffs_and_adjacent_floats(self):
        cases = [(reader.UPPER, reader.UPPER_RULE), (math.nextafter(reader.UPPER, -math.inf), 'otherwise'),
                 (reader.LOWER, reader.LOWER_RULE), (math.nextafter(reader.LOWER, math.inf), 'otherwise')]
        for score, expected in cases:
            out = reader.compare(self.candidate(score), self.base, self.reg, 'synthetic-t28')
            self.assertEqual(out['rule_branch'], expected)
            self.assertEqual(out['rule_text'], self.reg['reading_rule_fixed_before_the_result'][expected])

    def test_new_best_can_still_be_inconclusive(self):
        out = reader.compare(self.candidate(.144), self.base, self.reg, 'synthetic-t28')
        self.assertTrue(out['new_best_observed_among_registered_references'])
        self.assertEqual(out['rule_branch'], 'otherwise')

    def test_missing_raw_scaled_nonfinite_and_bad_mean_are_rejected(self):
        for key in ['score_avg', *reader.SCORES, *reader.SCORES.values()]:
            for invalid in (None, float('nan'), float('inf'), True):
                obj = copy.deepcopy(self.status); obj[key] = invalid
                with self.assertRaises(ValueError):
                    reader.compare(obj, self.base, self.reg, 'synthetic-t28')
        obj = copy.deepcopy(self.status); obj['score_avg'] += .001
        with self.assertRaisesRegex(ValueError, 'six-member mean'):
            reader.compare(obj, self.base, self.reg, 'synthetic-t28')

    def test_wrong_entry_panel_pending_result_are_rejected(self):
        for key, value in [('entry_id', 'wrong'), ('panel_id', 'new-panel'), ('anchor_version', 'new'),
                           ('partition', 'test'), ('status', 'scoring'), ('is_terminal', False),
                           ('model_name', 'other-model')]:
            obj = copy.deepcopy(self.status); obj[key] = value
            with self.assertRaises(ValueError):
                reader.compare(obj, self.base, self.reg, 'synthetic-t28')

    def test_positive_mse_and_negative_fidelity_are_never_clipped(self):
        obj = copy.deepcopy(self.status)
        obj['score_mse'] = .06; obj['score_avg'] += .01
        out = reader.compare(obj, self.base, self.reg, 'synthetic-t28')
        self.assertEqual(out['scaled_published']['t28']['score_mse'], .06)
        self.assertLess(out['scaled_published']['t28']['score_fid'], 0)
        self.assertAlmostEqual(out['scaled_published']['t28_minus_t25_contribution_to_mean']['score_mse'], .01)


if __name__ == '__main__':
    unittest.main()
