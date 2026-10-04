"""selector.py and the hybrid of hybrid_lanes.py on cases with known answers (PROTOCOLLO.md §4, §6, §7).

- hybrid with w = 0 is T bit for bit (float32 after the generator's cast), NaN where T is, an undefined R counts as 0;
- selector_stats: a and b of a row whose truth is T + R give the optimum w* = b / a = 1;
- a selector fitted on rows where R helps only when an input is high learns weights that follow that input, beats the
  fixed mixture out of fold, and the fixed mixture lands near the pooled optimum;
- rows where R never helps give weights near 0 and w_fix = 0;
- the frozen system written for a confirmation line never reads a or b.

    python -m unittest test_selector -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "risposta_contesto_2026-10-02"))
import selector as SEL  # noqa: E402
from hybrid_lanes import hybrid, selector_stats  # noqa: E402


def rows(rng, n, helps):
    """Synthetic rows: R helps (b = a) when helps(z) else hurts (b = -a)."""
    df = pd.DataFrame({"target_key": [f"K{i}" for i in range(n)], "f_support": rng.normal(size=n),
                       "f_concordance": rng.normal(size=n), "f_expression": rng.normal(size=n)})
    for arm in SEL.ARMS:
        df[f"{arm}__f_log_ratio"] = rng.normal(size=n)
        df[f"{arm}__f_cos_rt"] = rng.normal(size=n)
        a = rng.uniform(0.5, 1.5, n)
        good = helps(df)
        df[f"{arm}__a"] = a
        df[f"{arm}__b"] = np.where(good, a, -a)
        df[f"{arm}__base"] = 2.0
    return df


class Hybrid(unittest.TestCase):
    def test_w0_is_the_transfer(self):
        rng = np.random.default_rng(0)
        T = rng.normal(size=(5, 50)).astype(np.float32)
        T[0, :3] = np.nan
        R = rng.normal(size=(5, 50)).astype(np.float32)
        R[1, 4:9] = np.nan
        h0 = hybrid(T, R, 0.0)
        obs = np.isfinite(T)
        np.testing.assert_array_equal(np.isfinite(h0), obs)
        a = np.where(obs, np.nan_to_num(T), 0.0).astype(np.float32)
        b = np.where(obs, np.nan_to_num(h0), 0.0).astype(np.float32)
        self.assertEqual(a.tobytes(), b.tobytes())
        h1 = hybrid(T, R, np.ones(5))
        np.testing.assert_allclose(h1[1, 4:9], T[1, 4:9])          # undefined R counts as 0
        self.assertTrue(np.isnan(h1[0, :3]).all())

    def test_selector_stats(self):
        rng = np.random.default_rng(1)
        T = rng.normal(size=(3, 40))
        R = rng.normal(size=(3, 40))
        y = T + R
        st = selector_stats(T, R, y, np.ones(40), np.zeros((3, 40), bool))
        np.testing.assert_allclose(st["b"] / st["a"], 1.0)
        np.testing.assert_allclose(st["base"], (R ** 2).mean(1))


class Selector(unittest.TestCase):
    def test_learns_where_the_correction_helps(self):
        rng = np.random.default_rng(2)
        helps = lambda d: d["f_concordance"].to_numpy() > 0.3                   # noqa: E731
        fit_df, test_df = rows(rng, 3000, helps), rows(rng, 1000, helps)
        m = SEL.fit(fit_df, "ibrido")
        w = SEL.apply(m, test_df)
        good = helps(test_df)
        self.assertGreater(w[good].mean(), 0.5)          # a logistic on standardised inputs, not a step
        self.assertLess(w[~good].mean(), 0.15)
        self.assertGreater(abs(m["theta"][2]), 5 * max(abs(t) for i, t in enumerate(m["theta"][1:]) if i != 1))
        sel, fix = SEL.benefit(test_df, "ibrido", w), SEL.benefit(test_df, "ibrido", m["w_fix"])
        self.assertGreater(sel["mean_gain"], fix["mean_gain"])
        self.assertGreater(sel["mean_gain"], 0)

    def test_missing_input_is_zero(self):
        rng = np.random.default_rng(5)
        df = rows(rng, 800, lambda d: d["f_concordance"].to_numpy() > 0)
        df.loc[df.index[:100], "f_expression"] = np.nan                 # genes the line's table does not measure
        m = SEL.fit(df, "ibrido")
        self.assertTrue(np.all(np.isfinite(m["theta"])) and np.all(np.isfinite(m["mu"])))
        self.assertTrue(np.all(np.isfinite(SEL.apply(m, df))))

    def test_never_helps_gives_zero(self):
        rng = np.random.default_rng(3)
        df = rows(rng, 2000, lambda d: np.zeros(len(d), bool))
        m = SEL.fit(df, "ibrido")
        self.assertEqual(m["w_fix"], 0.0)
        self.assertLess(SEL.apply(m, df).mean(), 0.05)

    def test_frozen_system_reads_no_outcome(self):
        rng = np.random.default_rng(4)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            dev = rows(rng, 500, lambda x: x["f_support"].to_numpy() > 0)
            dev.to_csv(d / "dev.csv.gz", index=False)
            conf = rows(rng, 100, lambda x: x["f_support"].to_numpy() > 0)
            for arm in SEL.ARMS:                                   # the outcome of the confirmation line is unknown
                conf[f"{arm}__a"] = np.nan
                conf[f"{arm}__b"] = np.nan
            conf.to_csv(d / "conf.csv.gz", index=False)
            py = sys.executable
            r1 = subprocess.run([py, str(HERE / "selector.py"), "final", "--rows", f"DEV={d / 'dev.csv.gz'}",
                                 "--out", str(d / "sel")], capture_output=True, text=True)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = subprocess.run([py, str(HERE / "selector.py"), "apply", "--selector", str(d / "sel" / "selector_final.json"),
                                 "--rows", f"CONF={d / 'conf.csv.gz'}", "--out", str(d / "w")], capture_output=True,
                                text=True)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            doc = json.loads((d / "w" / "weights_CONF.json").read_text(encoding="utf-8"))
            self.assertNotIn("oof_benefit", doc)
            self.assertEqual(len(doc["selective"]["ibrido"]), 100)
            self.assertTrue(all(0 <= v <= 1 for v in doc["selective"]["ibrido"].values()))


if __name__ == "__main__":
    unittest.main()
