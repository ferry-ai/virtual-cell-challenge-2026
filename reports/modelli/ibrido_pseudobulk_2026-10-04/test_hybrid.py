"""Small CPU checks of biological strata, sufficient statistics, leakage and residual parity."""
import unittest

import numpy as np
import torch

from preparation import Moments, NestedSampler, admit_to_fit, hierarchical_weights, require_coverage
from hybrid import Hybrid, mean_supervision, predict_effect


def row(i, **kwargs):
    return {'cell_key': str(i), 'study': 's', 'context': 'CD4', 'line_group': 'CD4T',
            'donor_or_clone': 'D1', 'condition': 'Rest', 'modality': 'CRISPRi',
            'chemistry': 'Flex', 'target': 'T', 'library': 'L', 'batch': 'B',
            'guides': 'g1', **kwargs}


class PreparationTests(unittest.TestCase):
    def test_nested_order_independent_and_all_strata(self):
        rows = [row(i, guides=f'g{i % 5}') for i in range(45)]
        a, b = NestedSampler((2, 8, 16)), NestedSampler((2, 8, 16))
        for r in rows:
            a.add(r, r['cell_key'])
        for r in reversed(rows):
            b.add(r, r['cell_key'])
        self.assertEqual(a.finish(), b.finish())
        p = a.finish()[0]
        self.assertEqual(p['levels']['2']['effective_cap'], 5)
        ids = [set(x['cell_key'] for x in p['levels'][str(k)]['cells']) for k in (2, 8, 16)]
        self.assertTrue(ids[0] < ids[1] < ids[2])
        self.assertEqual(len(p['levels']['8']['cells']), 8)
        for c in p['levels']['2']['cells']:
            self.assertAlmostEqual(c['inclusion_probability'], 1 / 9)

    def test_donors_states_and_modalities_not_collapsed(self):
        s = NestedSampler((2,))
        for i, fields in enumerate(({}, {'donor_or_clone': 'D2'}, {'condition': 'Stim8hr'},
                                   {'modality': 'CRISPRa'})):
            s.add(row(i, **fields), str(i))
        self.assertEqual(len(s.finish()), 4)

    def test_fold_and_hidden_components(self):
        self.assertFalse(admit_to_fit(row(1), ['CD4T'], []))
        self.assertFalse(admit_to_fit(row(1), [], ['T']))
        self.assertFalse(admit_to_fit(row(1, target='A+T', target_components=['A', 'T']), [], ['T']))
        self.assertFalse(admit_to_fit(row(1), [], [], ['s']))
        self.assertTrue(admit_to_fit(row(1), ['H1'], ['Z']))

    def test_full_moments_are_not_ratio_of_sums(self):
        m = Moments([True, True, False])
        m.update([[9, 1, 999], [1, 1, np.nan]])
        result = m.summary()
        np.testing.assert_allclose(result['mean_proportion'][:2], [.7, .3])
        self.assertNotAlmostEqual(result['mean_proportion'][0], 10 / 12)
        self.assertTrue(np.isnan(result['mean_proportion'][2]))
        a, b = Moments(m.mask), Moments(m.mask)
        a.update([[9, 1, 2]])
        b.update([[1, 1, 300]])
        np.testing.assert_allclose(a.merge(b).summary()['variance_proportion'], result['variance_proportion'])
        with self.assertRaises(ValueError):
            m.merge(Moments([True, False, False]))

    def test_missing_context_blocks_complete(self):
        with self.assertRaises(ValueError):
            require_coverage(['H1', 'CD4D1', 'CD4D2'], ['H1', 'CD4D1'], {})
        with self.assertRaises(ValueError):
            require_coverage(['H1'], [], {'H1': {'kind': 'too_large', 'evidence': 'large'}})
        self.assertTrue(require_coverage(['H1'], [], {
            'H1': {'kind': 'validation', 'evidence': 'frozen split'}})['complete'])

    def test_weights_preserve_small_contexts(self):
        rows = [row(i) for i in range(100)] + [row(100, donor_or_clone='D2'),
                                             row(101, line_group='H1', study='other')]
        w = hierarchical_weights(rows) / len(rows)
        np.testing.assert_allclose([sum(w[:100]), w[100], w[101]], [.25, .25, .5])
        self.assertAlmostEqual(sum(w), 1)


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(7)
        self.model = Hybrid(3, 2, 2, width=8, rank=3)
        self.anchor = torch.tensor([[.1, -.2, float('nan')]])
        self.target, self.context = torch.ones(1, 2), torch.ones(1, 2)
        self.mask = torch.tensor([[True, True, False]])

    def test_zero_initialization_and_export_fallback(self):
        p = predict_effect(self.model, self.anchor, self.target, self.context, self.mask)
        torch.testing.assert_close(p, self.anchor, equal_nan=True)
        with torch.no_grad():
            self.model.decoder.weight.fill_(1)
        p = predict_effect(self.model, self.anchor, self.target, self.context, self.mask, 0)
        torch.testing.assert_close(p, self.anchor, equal_nan=True)
        r = self.model(self.anchor, self.target, self.context, self.mask)
        self.assertLessEqual(float(r.detach().abs().max()), .5)

    def test_without_context_ignores_context(self):
        m = Hybrid(3, 2, 2, with_context=False)
        with torch.no_grad():
            m.decoder.weight.fill_(.1)
        a = m(self.anchor, self.target, self.context, self.mask)
        b = m(self.anchor, self.target, self.context * 15, self.mask)
        torch.testing.assert_close(a, b)

    def test_mean_loss_trains_with_masked_nan(self):
        b = torch.tensor([[.5, .5, float('nan')]])
        y = torch.tensor([[.65, .35, float('nan')]])
        a = torch.zeros(1, 3)
        opt = torch.optim.Adam(self.model.parameters(), lr=.02)
        losses = []
        for _ in range(60):
            r = self.model(a, self.target, self.context, self.mask)
            loss = mean_supervision(a + r, b, y, self.mask, torch.ones(1), r)
            opt.zero_grad()
            loss.backward()
            self.assertTrue(all(torch.isfinite(p.grad).all() for p in self.model.parameters() if p.grad is not None))
            opt.step()
            losses.append(loss.item())
        self.assertLess(losses[-1], losses[0] * .15)

    def test_weights_do_not_cancel_and_impossible_support_fails(self):
        a = torch.zeros(1, 3)
        b, y = torch.tensor([[.5, .5, 0]]), torch.tensor([[.8, .2, 0]])
        args = (a, b, y, self.mask)
        x = mean_supervision(*args, torch.ones(1), a)
        z = mean_supervision(*args, torch.ones(1) * .25, a)
        torch.testing.assert_close(z, x * .25)
        b[0, 0] = 0
        with self.assertRaises(ValueError):
            mean_supervision(*args, torch.ones(1), a)


if __name__ == '__main__':
    unittest.main()
