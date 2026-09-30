"""Synthetic-only tests: leakage, source identities, initialization and executable fit."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from neural_sources import P, SourceAttention, SourceView, directional_loss, cis_hidden
import train_neural_sources as runner
import train as legacy

torch.set_num_threads(2)


class NeuralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name) / "data"
        legacy.synthetic(cls.folder, planted=True, seed=19)
        cls.pool = P.Pool.from_dir(cls.folder)
        cls.visible = np.flatnonzero(cls.pool.ctx_family[cls.pool.row_context] < 5)
        cls.view = SourceView(cls.pool, cls.visible)
        cls.targets = np.arange(30, 38)
        cls.genes = np.arange(50, 114)

    @classmethod
    def tearDownClass(cls):
        # All fixture files are confined to TemporaryDirectory, never project data.
        cls.view = cls.pool = None
        import gc
        gc.collect()
        cls.temp.cleanup()

    def batch(self, view=None):
        view = view or self.view
        return view.batch(self.targets, np.full(8, 6), np.full(8, 6), self.genes)

    def test_exact_initial_baseline_and_masked_values(self):
        b = self.batch()
        model = SourceAttention(self.view.n_priors)
        result = model(b)
        self.assertTrue(torch.equal(result["prediction"], result["baseline"]))
        self.assertTrue(torch.isfinite(result["prediction"]).all())
        self.assertTrue(torch.equal(result["weights"][~b["mask"]], torch.zeros_like(result["weights"][~b["mask"]])))

    def test_tokens_keep_context_and_source_permutation_equivariance(self):
        b = self.batch()
        model = SourceAttention(self.view.n_priors)
        torch.nn.init.normal_(model.token[-1].weight, std=.05)
        order = np.arange(len(self.view.contexts))[::-1].copy()
        shuffled = {k: v[:, order] if k != "priors" else v for k, v in b.items()}
        torch.testing.assert_close(model(b)["prediction"], model(shuffled)["prediction"])
        self.assertEqual(b["value"].shape[1], len(self.view.contexts))

    def test_no_invisible_outcome_changes_features_or_centres(self):
        hidden = np.flatnonzero(~self.view.visible)
        poisoned = legacy.poisoned(self.pool, hidden, seed=101)
        view = SourceView(poisoned, self.visible)
        a, b = self.batch(), self.batch(view)
        for key in a:
            self.assertTrue(torch.equal(a[key], b[key]), key)
        for c in self.view.contexts:
            np.testing.assert_array_equal(self.view.mu["shrunk"][int(c)], view.mu["shrunk"][int(c)])
        with self.assertRaises(P.LeakageError):
            view.read("shrunk", hidden[:2], self.genes)

    def test_j_removes_targets_everywhere_and_uses_only_visible_partners(self):
        hidden_targets = cis_hidden(self.pool, self.targets[:2])
        visible = self.visible[~np.isin(self.pool.row_target[self.visible], hidden_targets)]
        view = SourceView(self.pool, visible)
        self.assertTrue((view.lookup[:, hidden_targets] < 0).all())
        changed = legacy.poisoned(self.pool, np.flatnonzero(~view.visible), seed=202)
        other = SourceView(changed, visible)
        for key, value in self.batch(view).items():
            self.assertTrue(torch.equal(value, self.batch(other)[key]), key)

    def test_own_family_and_cis_are_never_sources(self):
        t = self.targets[:1]
        family = self.pool.ctx_family[self.view.contexts[0]]
        genes = np.arange(self.pool.G)
        b = self.view.batch(t, np.array([6]), np.array([family]), genes)
        blocked = self.pool.ctx_family[self.view.contexts] == family
        self.assertFalse(b["mask"][:, blocked].any())
        ex = self.view._exclusion(t[0], genes)
        self.assertFalse(b["mask"][:, :, ex].any())

    def test_loss_ignores_noncommon_genes(self):
        torch.manual_seed(9)
        y = torch.randn(4, 30)
        pred = torch.randn(4, 30, requires_grad=True)
        out = {"prediction": pred, "baseline": pred.detach().clone(), "support": torch.ones(4, 30, dtype=torch.bool)}
        keep = torch.ones(4, 30, dtype=torch.bool)
        keep[0, 0] = False
        loss, count = directional_loss(out, y, keep)
        y[:, 0] = 1e6
        loss2, count2 = directional_loss(out, y, keep)
        self.assertEqual(count, count2)
        torch.testing.assert_close(loss, loss2)
        loss.backward()
        self.assertTrue(torch.equal(pred.grad[:, 0], torch.zeros(4)))

    def test_empty_support_and_zero_baseline_are_explicit(self):
        model = SourceAttention(self.view.n_priors)
        b = self.batch()
        b["mask"][:] = False
        b["reliability"][:] = 0
        out = model(b)
        self.assertFalse(out["support"].any())
        self.assertTrue(torch.equal(out["prediction"], torch.zeros_like(out["prediction"])))
        loss, count = directional_loss(out, torch.ones_like(out["prediction"]), torch.ones_like(out["support"]))
        self.assertIsNone(loss)
        self.assertEqual(count, 0)

    def test_attention_learns_a_planted_source_choice(self):
        torch.manual_seed(12)
        B, S, G = 12, 2, 40
        value = torch.randn(B, S, G)
        features = torch.zeros(B, S, G, 20)
        # A control-derived source-match channel identifies source 0 as the matching state.
        features[:, 1, :, 4] = 1
        batch = {"value": value, "features": features, "mask": torch.ones(B, S, G, dtype=torch.bool),
                 "reliability": torch.ones(B, S, G), "priors": torch.zeros(B, self.view.n_priors)}
        y, keep = value[:, 0].clone(), torch.ones(B, G, dtype=torch.bool)
        model = SourceAttention(self.view.n_priors)
        initial = float(directional_loss(model(batch), y, keep)[0].detach())
        opt = torch.optim.Adam(model.parameters(), lr=.01)
        for _ in range(60):
            loss, _ = directional_loss(model(batch), y, keep)
            opt.zero_grad()
            loss.backward()
            opt.step()
        final = float(directional_loss(model(batch), y, keep)[0].detach())
        self.assertLess(final, initial * .6)
        self.assertGreater(float(model(batch)["weights"][:, 0].mean().detach()), .8)

    def test_missing_prediction_does_not_remove_truth_gene_support(self):
        rng = np.random.default_rng(15)
        truth = rng.normal(size=(5, 30))
        prediction = truth.copy()
        prediction[0] = 0
        keep = np.ones(truth.shape, bool)
        measured = runner.metrics(prediction, truth, keep, prediction)
        self.assertEqual(measured["common_genes"], 30)
        self.assertEqual(measured["rank"][0], .5)
        self.assertTrue(measured["zero_prediction"][0])
        out = {"prediction": torch.tensor(prediction, requires_grad=True), "baseline": torch.tensor(prediction),
               "support": torch.tensor(np.tile(np.arange(5)[:, None] > 0, (1, 30)))}
        loss, count = directional_loss(out, torch.tensor(truth), torch.tensor(keep))
        self.assertEqual(count, 4)
        self.assertTrue(torch.isfinite(loss))

    def test_design_nested_family_and_j_disjoint(self):
        args = runner.parser().parse_args(["--data", str(self.folder), "--out", "unused", "--holdout", "f7", "--regime", "J",
                                           "--test-targets", "12", "--validation-targets", "8"])
        plan = runner.design(self.pool, args)
        self.assertFalse(np.isin(self.pool.row_target[plan["refit"]], plan["hidden_targets"]).any())
        self.assertFalse(np.isin(self.pool.row_target[plan["train"]], plan["inner_hidden_targets"]).any())
        self.assertFalse(np.isin(self.pool.row_context[plan["refit"]], plan["hidden_contexts"]).any())
        val_rows = np.concatenate(list(plan["validation"].values()))
        self.assertFalse(np.isin(plan["train"], val_rows).any())

    def test_zero_step_is_selectable_and_runner_roundtrip(self):
        out = Path(self.temp.name) / "run"
        target_file = Path(self.temp.name) / "predict_targets.txt"
        target_file.write_text("\n".join(self.pool.target_names[t] for t in self.targets), encoding="utf-8")
        args = runner.parser().parse_args(["--data", str(self.folder), "--out", str(out), "--holdout", "f7",
                                           "--steps", "2", "--eval-every", "1", "--batch", "4", "--gene-batch", "64",
                                           "--test-targets", "12", "--validation-targets", "8", "--validation-genes", "64", "--device", "cpu",
                                           "--predict-contexts", "A", "--predict-targets", str(target_file)])
        summary = runner.run(args)
        self.assertIn(summary["best_steps"]["true"], [0, 1, 2])
        self.assertTrue((out / "manifest.json").is_file())
        self.assertTrue((out / "model_true.pt").is_file())
        with np.load(out / "pred_c8.npz", allow_pickle=False) as z:
            self.assertEqual(z["net"].shape, (12, len(self.pool.axis)))
            self.assertEqual(z["targets"].dtype.kind, "U")
        with np.load(out / "pred_A.npz", allow_pickle=False) as z:
            self.assertEqual(z["net"].shape, (8, len(self.pool.axis)))
            self.assertEqual(z["genes"].dtype.kind, "U")
        manifest = json.loads((out / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "registered_before_training")


if __name__ == "__main__":
    unittest.main()
