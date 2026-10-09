"""Tests of the forecast ledger on a tiny synthetic repository: nothing is reconstructed, errors are read right."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registro as R  # noqa: E402


def status(entry, name, score, date, pds=0.6, fid=-0.05):
    members = {'score_pds': pds, 'score_mse': 0.0, 'score_nmae': 0.1, 'score_fid': fid, 'score_reach': 0.1, 'score_jac': 0.0}
    rest = score * 6 - sum(members.values())
    members['score_jac'] = rest                                  # the six scaled members average to the score
    return {'entry_id': entry, 'status': 'published', 'model_name': name, 'submission_date': date, 'score_avg': score,
            'panel_id': 'val-1', 'anchor_version': 'r4', **members, 'pds_cosine': 0.78}


def write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def make_repo(root: Path) -> Path:
    inv = root / 'reports/invii'
    # t40: the reference, scored, with no prediction at all
    write(inv / 'trial_a/status_E40.json', status('E40', 't40 - reference', 0.1400, '2026-10-01T10:00:00Z'))
    # t41: a bench promised +0.03, the site gave +0.008: right direction, a quarter of the size, outside the seeds
    write(inv / 'prediction_t41_2026-10-02/prediction.json', {
        'written_utc': '2026-10-02T08:00:00+00:00', 'label': 't41 candidate',
        'expected': {'score_avg_band': [0.13, 0.18], 'working_centre': 0.155, 't41_minus_t40_band': [-0.005, 0.04]},
        'bench': {'delta': 0.03, 'sd': 0.004, 'members': {'pds_cosine': 0.001, 'de_wilcoxon_direction_fidelity_yield_raw': 0.02}}})
    write(inv / 'trial_a/status_E41.json', status('E41', 't41 - candidate', 0.1480, '2026-10-02T12:00:00Z', pds=0.59, fid=0.01))
    # t42: registered with no numeric forecast: it must stay absent
    write(inv / 'prediction_t42_2026-10-03/prediction.json', {'numeric_forecast_not_registered': True, 'expected_band': None})
    write(inv / 'trial_a/status_E42.json', status('E42', 't42 - no forecast', 0.1300, '2026-10-03T12:00:00Z'))
    # t43: expected delta zero against t40, the site moved by -0.02: the null expectation is refuted
    write(inv / 'prediction_t43_2026-10-04/prediction.json', {
        'written_utc': '2026-10-04T08:00:00+00:00', 'candidate': 'T-X', 'reference': {'name': 't40'},
        'expected_score_band': [0.13, 0.15], 'expected_delta': 0, 'decision_threshold_absolute': 0.005})
    write(inv / 'trial_a/status_E43.json', status('E43', 't43 - null expected', 0.1200, '2026-10-04T12:00:00Z'))
    # t44: prediction written AFTER the entry existed: not preregistered
    write(inv / 'prediction_t44_2026-10-05/prediction.json', {
        'written_utc': '2026-10-05T13:00:00+00:00', 'label': 't44 late', 'expected': {'score_avg_band': [0.1, 0.2]}})
    write(inv / 'trial_a/status_E44.json', status('E44', 't44 - late', 0.1500, '2026-10-05T12:00:00Z'))
    # t45: sent, not scored yet
    write(inv / 'prediction_t45_2026-10-06/prediction.json', {
        'written_utc': '2026-10-06T08:00:00+00:00', 'candidate': 'T-Y', 'reference': {'name': 't41'},
        'expected_score_band': [0.13, 0.16], 'expected_delta': 0, 'decision_threshold_absolute': 0.005})
    write(inv / 'trial_b/status_E45.json', {'entry_id': 'E45', 'status': 'scoring', 'model_name': 't45 - waiting',
                                           'submission_date': '2026-10-06T12:00:00Z', 'score_avg': None})
    curated = root / 'curated'
    write(curated / 'banchi.json', {'BX': {'name': 'toy bench', 'period': 'x', 'source': 'reports/invii/prediction_t41_2026-10-02/prediction.json'}})
    write(curated / 'previsioni_di_banco.json', [{
        'label': 't41', 'bench': 'BX', 'kind': 'delta', 'reference': 't40',
        'path': 'reports/invii/prediction_t41_2026-10-02/prediction.json', 'pointer': 'bench.delta', 'sd_pointer': 'bench.sd',
        'registered_before_submission': True, 'candidate_is_a_bench_arm': True,
        'members': {'pointer': 'bench.members', 'unit': 'contribution_to_mean'}}])
    write(curated / 'spiegazioni.json', {'t41': [{'testo': 'x', 'stato': 'ipotizzata',
                                                 'fonte': 'reports/invii/prediction_t41_2026-10-02/prediction.json'}]})
    return curated


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.curated = make_repo(self.root)
        self.ledger = R.build(self.root, curated_dir=self.curated)
        self.subs = self.ledger['submissions']

    def tearDown(self):
        self.tmp.cleanup()

    def test_official_members_and_their_mean(self):
        off = self.subs['t41']['official']
        self.assertAlmostEqual(off['score_avg'], 0.148)
        self.assertTrue(off['mean_matches_score_avg'])
        self.assertEqual(off['panel_id'], 'val-1')

    def test_direction_amplitude_and_uncertainty_of_a_bench_forecast(self):
        f = self.subs['t41']['bench_forecasts'][0]
        self.assertAlmostEqual(f['predicted_delta'], 0.03)
        self.assertAlmostEqual(f['official']['delta'], 0.008)
        self.assertEqual(f['direction'], 'giusta')
        self.assertAlmostEqual(f['amplitude']['official_over_predicted'], 0.008 / 0.03)
        self.assertFalse(f['uncertainty']['within_two_seed_sd'])        # 0.022 away, two sd are 0.008
        members = f['member_errors']['members']
        self.assertEqual(members['fid']['direction'], 'giusta')         # +0.02 promised, +0.06/6 published
        self.assertAlmostEqual(members['fid']['official'], (0.01 - (-0.05)) / 6)
        self.assertEqual(members['pds']['direction'], 'sbagliata')      # +0.001 promised, PDS fell
        self.assertIsNone(members['nmae']['predicted'])                 # the bench had no such member: stays absent

    def test_bands_and_signed_forecast_from_the_registration(self):
        err = self.subs['t41']['errors']
        self.assertTrue(err['score_band']['inside'])
        self.assertTrue(err['delta']['band']['inside'])
        self.assertEqual(err['delta']['signed_forecast_from'], 'working centre minus reference')
        self.assertEqual(err['delta']['direction'], 'giusta')

    def test_a_missing_forecast_stays_missing(self):
        s = self.subs['t42']
        self.assertFalse(s['prediction']['numeric_forecast_registered'])
        self.assertIsNone(s['errors'])
        self.assertEqual(s['bench_forecasts'], [])
        self.assertIsNone(self.subs['t40']['prediction'])
        self.assertIn('t40', self.ledger['summary']['scored_without_any_registered_prediction'])
        self.assertIn('t42', self.ledger['summary']['registered_without_numeric_forecast'])

    def test_a_refuted_null_expectation(self):
        d = self.subs['t43']['errors']['delta']
        self.assertEqual(d['direction'], 'attesa nulla smentita')
        self.assertFalse(self.subs['t43']['errors']['score_band']['inside'])

    def test_a_late_prediction_is_not_preregistered_and_leaves_the_counts(self):
        self.assertEqual(self.subs['t44']['prediction']['registration'], 'non preregistrata')
        self.assertNotIn('t44', self.ledger['summary']['score_bands']['outside'])
        self.assertEqual(self.ledger['summary']['score_bands']['read'], 2)       # t41 and t43 only

    def test_pending_submission_and_calibration_statement(self):
        self.assertEqual(self.ledger['summary']['pending'], ['t45'])
        self.assertIn('nessun punteggio', R.after_submission(self.ledger, 't45'))
        row = self.ledger['summary']['by_bench']['BX']
        self.assertEqual(row['signed_delta_forecasts'], 1)
        self.assertTrue(row['calibration'].startswith('non sostenuta'))

    def test_the_report_and_the_diagnosis_render(self):
        text = R.report(self.ledger)
        self.assertIn('| t41 |', text)
        self.assertIn('t45', text.split('## 6. In attesa')[1])
        self.assertIn('membri con verso sbagliato: PDS', R.after_submission(self.ledger, 't41'))

    def test_an_explanation_must_carry_an_evidence_label_and_a_real_source(self):
        (self.curated / 'spiegazioni.json').write_text(json.dumps({'t41': [{'testo': 'x', 'stato': 'certa'}]}), encoding='utf-8')
        with self.assertRaises(SystemExit):
            R.build(self.root, curated_dir=self.curated)
        (self.curated / 'spiegazioni.json').write_text(json.dumps(
            {'t41': [{'testo': 'x', 'stato': 'verificata', 'fonte': 'reports/missing.md'}]}), encoding='utf-8')
        with self.assertRaises(SystemExit):
            R.build(self.root, curated_dir=self.curated)


if __name__ == '__main__':
    unittest.main()
