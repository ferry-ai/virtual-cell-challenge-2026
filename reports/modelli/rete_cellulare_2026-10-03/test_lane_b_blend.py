"""The blend of MISCELE.md on a made-up row with known answers: the mixture where both effects are observed, the
transfer where the network is missing, nothing where the transfer is missing; the mask is the transfer's.

    python -m unittest test_lane_b_blend -v       (from this folder, with the project venv)
"""
from __future__ import annotations

import unittest

import numpy as np

from lane_b_blend import WEIGHTS, blend


class Blend(unittest.TestCase):
    def test_known_row(self):
        t = np.array([[1.0, 2.0, 0.0, 4.0]], np.float32)
        t_obs = np.array([[True, True, False, True]])
        n = np.array([[3.0, 0.0, 5.0, -4.0]], np.float32)
        n_obs = np.array([[True, False, True, True]])
        lfc, obs = blend(t, t_obs, n, n_obs, 0.25)
        np.testing.assert_allclose(lfc, [[2.5, 2.0, 0.0, -2.0]])
        np.testing.assert_array_equal(obs, t_obs)
        self.assertEqual(lfc.dtype, np.float32)

    def test_ends(self):
        rng = np.random.default_rng(0)
        t, n = rng.normal(size=(5, 9)).astype(np.float32), rng.normal(size=(5, 9)).astype(np.float32)
        t_obs, n_obs = rng.random((5, 9)) > 0.3, rng.random((5, 9)) > 0.3
        t = np.where(t_obs, t, 0.0)
        np.testing.assert_allclose(blend(t, t_obs, n, n_obs, 1.0)[0], t)
        only = blend(t, t_obs, n, n_obs, 0.0)[0]
        np.testing.assert_allclose(only[t_obs & n_obs], n[t_obs & n_obs])
        np.testing.assert_allclose(only[t_obs & ~n_obs], t[t_obs & ~n_obs])

    def test_primary_first(self):
        self.assertEqual(WEIGHTS[0], 0.5)


if __name__ == "__main__":
    unittest.main()
