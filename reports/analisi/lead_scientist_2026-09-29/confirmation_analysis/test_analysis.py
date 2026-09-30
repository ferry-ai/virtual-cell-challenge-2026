"""Small synthetic contracts only; never read real confirmation results."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

import analyze_confirmation as review


def write_json(path, value):
    path.write_text(json.dumps(value, allow_nan=False), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root):
    """Nine tiny 96-row score tables, not cells and not a scorer execution."""
    folder = root / 'confirmation'
    folder.mkdir()
    targets = [f'T{i:03d}' for i in range(96)]
    finalists = [(1.5, 1., 'pooled'), (1.5, .5, 'pooled')]
    arms = [review.REFERENCE, *finalists]
    anchors_path = root / 'anchors.json'
    anchors = {m: {'baseline': 0., 'replicate': 1.} for m in review.FIVE}
    anchors[review.FIVE[1]] = {'baseline': 1., 'replicate': 0.}
    write_json(anchors_path, {'anchors': anchors})
    target_manifest = root / 'target_manifest.json'
    write_json(target_manifest, {'confirmation': targets, 'development': [f'D{i}' for i in range(48)],
        'cells_per_prediction': 400, 'control_rows': list(range(2000)),
        'target_rows': {t: list(range(50)) for t in targets},
        'fingerprints': {'anchors.json': {'sha256': sha(anchors_path)}, 'generator_bench.py': {'sha256': 'synthetic'}}})
    dev = root / 'development_selection.json'
    write_json(dev, {'shortlist': finalists, 'n_targets': 48, 'truth': 'full', 'finished_utc': 'synthetic fixture'})
    manifest = {'split': 'confirmation', 'truth': 'full', 'seeds': review.SEEDS, 'targets': targets,
                'arms': arms, 'target_manifest_sha256': sha(target_manifest), 'generator_script_sha256': 'synthetic'}
    write_json(folder / 'run_manifest.json', manifest)
    arrays, results = {}, {}
    for ai, arm in enumerate(arms):
        arrays[arm] = []
        for seed in review.SEEDS:
            key = review.name(arm, seed)
            k = 50 + ai + (seed - 1 if ai else 0)
            base = [.5 + ai * .02, 1. - ai * .02, k / 100., .1, .1]
            array = np.tile(base, (96, 1))
            arrays[arm].append(array)
            table = pd.DataFrame(array, index=targets, columns=review.FIVE)
            table.index.name = 'perturbation'
            table[review.DENOMINATOR] = np.arange(1, 97, dtype=float)
            table[review.NUMERATOR] = table[review.DENOMINATOR] * (.5 + ai * .1)
            table.reset_index().melt(id_vars='perturbation', var_name='metric', value_name='value').to_csv(folder / f'per_pert_{key}.csv', index=False)
            pd.DataFrame({'target': targets, 'n_conf': 20, 'n_pred': 100, 'k': k}).to_csv(folder / f'components_{key}.csv', index=False)
            write_json(folder / f'diagnostics_{key}.json', [{'target': t} for t in targets])
            raw = {m: float(table[m].mean()) for m in review.FIVE}
            raw[review.MSE] = float(table[review.NUMERATOR].sum() / table[review.DENOMINATOR].sum())
            result = {'raw': raw, 'amplitude_relative': arm[0], 'phi_scale': arm[1], 'generator': arm[2], 'generator_seed': seed}
            results[key] = result
            write_json(folder / f'result_{key}.json', result)
    write_json(folder / 'bench.json', {'run_manifest': manifest, 'results': results})
    slopes = [1 / (anchors[m]['replicate'] - anchors[m]['baseline']) for m in review.FIVE]
    comparisons = []
    for arm in finalists:
        result, _, _, _ = review.reconstruct(arrays[arm], arrays[review.REFERENCE], slopes)
        comparisons.append(result | {'amplitude': arm[0], 'phi_scale': arm[1], 'generator': arm[2]})
    write_json(folder / 'selection.json', {'finished_utc': 'synthetic fixture', 'n_targets': 96, 'truth': 'full',
                                         'comparisons': comparisons, 'shortlist': []})
    return folder, target_manifest, dev, anchors_path


class ConfirmationReviewTest(unittest.TestCase):
    def test_member_denominators_and_independent_weighted_bootstrap(self):
        reference = np.zeros((3, 3, 5))
        reference[:, 0, 1] = np.nan
        candidate = reference.copy()
        candidate[:, :, 0] = [.06, .12, .18]
        candidate[:, 1:, 1] = [[.06, .18]]
        draws = np.array([[0, 1, 2], [2, 1, 1], [1, 1, 2]])
        result, _, average, values = review.reconstruct(candidate, reference, np.ones(5), indices=draws)
        self.assertAlmostEqual(result['delta_projection'], .04)
        self.assertEqual(result['eligible_targets_per_member'][review.FIVE[1]], 2)
        self.assertAlmostEqual(values[0], .04)
        self.assertAlmostEqual(values[1], (.12 + .12 + .18) / 3 / 6 + (.06 + .06 + .18) / 3 / 6)
        pieces, diagnostic, strata = review.describe_targets(average, ['A', 'B', 'C'], np.array([0, 8, 100]))
        self.assertAlmostEqual(pieces.sum(), .04)
        self.assertAlmostEqual(sum(s['additive_contribution_to_full_panel'] for s in strata), .04)
        self.assertFalse(diagnostic['used_for_promotion'])

    def test_seed_pairing_sd_and_bonferroni_level(self):
        reference = np.zeros((3, 4, 5))
        candidate = reference.copy()
        candidate[:, :, 0] = np.array([.03, .06, .09])[:, None]
        result, _, _, _ = review.reconstruct(candidate, reference, np.ones(5))
        np.testing.assert_allclose(result['per_seed_delta'], [.005, .01, .015])
        self.assertAlmostEqual(result['seed_sd'], .005)
        self.assertEqual(result['confidence_level'], .975)
        single, _, _, _ = review.reconstruct(candidate, reference, np.ones(5), n_finalists=1)
        self.assertEqual(single['confidence_level'], .95)

    def test_registered_rule_boundaries_are_not_changed(self):
        self.assertTrue(review.promotion_rule(.005, [.001, .005, .009], [.0001, .01])[1])
        self.assertFalse(review.promotion_rule(.004999, [.01] * 3, [.001, .02])[1])
        self.assertFalse(review.promotion_rule(.01, [.02, .01, 0.], [.001, .02])[1])
        self.assertFalse(review.promotion_rule(.01, [.01] * 3, [0., .02])[1])

    def test_eligibility_drift_and_empty_bootstrap_fail(self):
        ref = np.zeros((3, 2, 5))
        candidate = ref.copy()
        candidate[0, 0, 1] = np.nan
        with self.assertRaisesRegex(ValueError, 'eligibility'):
            review.reconstruct(candidate, ref, np.ones(5))
        ref[:, 0, 1] = np.nan
        with self.assertRaisesRegex(ValueError, 'no eligible'):
            review.reconstruct(ref, ref, np.ones(5), indices=np.array([[0, 0]]))

    def test_incomplete_run_opens_no_partial_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'result_partial.json').write_text('secret partial values')
            with patch.object(review.Snapshot, 'read', side_effect=AssertionError('Must not read anything')):
                with self.assertRaisesRegex(ValueError, 'Incomplete confirmation'):
                    review.run(folder, folder / 'manifest.json', folder / 'dev.json', folder / 'anchors.json', folder / 'out')

    def test_end_to_end_complete_synthetic_reports_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = fixture(root)
            result = review.run(*inputs, root / 'out')
            self.assertEqual(len(result['comparisons']), 2)
            self.assertEqual(len(pd.read_csv(root / 'out/target_by_seed.csv')), 2 * 3 * 96)
            self.assertAlmostEqual(result['comparisons'][0]['MSE_raw_delta_mean_seeds_separate'], .1)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                review.run(*inputs, root / 'out')

    def test_changed_registered_decision_or_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = fixture(root)
            path = inputs[0] / 'selection.json'
            selection = json.loads(path.read_text())
            selection['comparisons'][0]['passes_confirmation'] = not selection['comparisons'][0]['passes_confirmation']
            write_json(path, selection)
            with self.assertRaisesRegex(ValueError, 'decision mismatch'):
                review.run(*inputs, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_same_missing_target_on_both_sides_cannot_disappear(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = fixture(root)
            path = inputs[0] / 'per_pert_a1_p0_s1.csv'
            data = pd.read_csv(path)
            data[data.perturbation != 'T000'].to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'Target set mismatch'):
                review.run(*inputs, root / 'out')
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
