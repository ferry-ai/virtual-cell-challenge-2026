"""Tests of the K562 panel bench's reader and build helpers, on synthetic jobs (no data, no scorer).

Each test pins a way the reading of RISULTATI.md could go wrong in silence:
* a worse nMAE read as a gain (its anchors run downwards), a NaN target turning a mean into NaN, the
  official spans not the ones anchors.json holds;
* a per-target file missed because Drive shows ':' as a space, or two candidate files for one arm;
* V1 (pass, inconclusive, contradicting), V2, V3 and V4 each deciding the wrong way;
* the rule: interval, every seed, twice the seed SD, the admission of E by V1+V2 and of A2/RB by V3, the
  winner and the tie-break towards the simpler arm;
* the share CSV not reading back to the float32 of the npy, the 0/1 exclusion off by a gene, a file
  in the way silently replaced, and a recipe run from the wrong place.

    scripts/py.cmd reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/test_banco_k562.py
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_arms  # noqa: E402
import leggi_banco as lb  # noqa: E402

ROLES = ["C1", "C2", "C3", "T26", "E1", "E2", "A1", "A2", "G1", "D1"]
BASE_RANGES = {"pds_cosine": (0.6, 0.8), "de_wilcoxon_lfc_nmae": (0.8, 1.0),
               "de_wilcoxon_direction_fidelity_yield_raw": (0.3, 0.6), "de_wilcoxon_direction_reach_raw": (0.1, 0.3),
               "de_wilcoxon_sig_jaccard": (0.05, 0.2)}
FULL = {m: s for s, m in [("pds", "pds_cosine"), ("nmae", "de_wilcoxon_lfc_nmae"),
                          ("fid", "de_wilcoxon_direction_fidelity_yield_raw"), ("reach", "de_wilcoxon_direction_reach_raw"),
                          ("jac", "de_wilcoxon_sig_jaccard")]}
# A scenario where every check passes: t23 as officially (pds up, nmae worse, reach down), amplitude with
# the official direction, t26 flat, E1 and E2 (nearly equal) and A2 above C1.
GOOD = {"C2": {"pds": 0.02, "nmae": 0.02, "reach": -0.02}, "C3": {"pds": 0.005, "reach": 0.01},
        "A1": {"pds": -0.02, "fid": -0.03}, "E1": {"pds": 0.03}, "E2": {"pds": 0.0302}, "A2": {"pds": 0.012}}


def make_job(folder: Path, shifts: dict, *, seed_shifts: dict | None = None, rb: bool = False, noise: float = 0.004,
             n_targets: int = 80, twin: dict | None = None) -> None:
    """bench.json and Drive-named per_pert CSVs: every arm is C1's per-target values plus a shift per member,
    a shift per seed and independent noise; nMAE absent for 70% of targets, reach empty for a few. ``twin``
    maps an arm to (another arm, per-target pds offsets): its values are that arm's plus the offsets."""
    rng = np.random.default_rng(0)
    targets = [f"T{i:02d}" for i in range(n_targets)]
    base = {m: rng.uniform(lo, hi, n_targets) for m, (lo, hi) in BASE_RANGES.items()}
    base["de_wilcoxon_lfc_nmae"][rng.random(n_targets) < 0.7] = np.nan
    base["de_wilcoxon_direction_reach_raw"][:4] = np.nan
    results = {"replicate": {"raw": {"pds_cosine": 0.9, "expr_mse_unbiased_capped_norm": 0.0, "de_wilcoxon_lfc_nmae": 0.4,
                                     "de_wilcoxon_direction_fidelity_yield_raw": 0.8,
                                     "de_wilcoxon_direction_reach_raw": 0.9, "de_wilcoxon_sig_jaccard": 0.4}},
               "baseline": {"raw": {"pds_cosine": 0.5, "expr_mse_unbiased_capped_norm": 1.0, "de_wilcoxon_lfc_nmae": 1.0,
                                    "de_wilcoxon_direction_fidelity_yield_raw": 0.5,
                                    "de_wilcoxon_direction_reach_raw": 0.1, "de_wilcoxon_sig_jaccard": 0.03}}}
    drawn = {}
    for role in ROLES + (["RB"] if rb else []):
        arm = lb.ARMS[role]
        for s in (1, 2, 3):
            rows, raw = [], {}
            for m in lb.MEMBERS:
                if twin and role in twin:
                    other, offsets = twin[role]
                    v = drawn[(other, s, m)] + (offsets if m == "pds_cosine" else 0.0)
                else:
                    v = (base[m] + shifts.get(role, {}).get(FULL[m], 0.0)
                         + (seed_shifts or {}).get(role, {}).get(FULL[m], [0.0, 0.0, 0.0])[s - 1]
                         + rng.normal(0.0, noise, n_targets))
                drawn[(role, s, m)] = v
                raw[m] = float(np.nanmean(v))
                for t, x in zip(targets, v):
                    if m == "de_wilcoxon_lfc_nmae" and np.isnan(x):
                        continue                              # the scorer omits the target
                    rows.append({"perturbation": t, "metric": m, "value": x})
            raw["expr_mse_unbiased_capped_norm"] = 1.0 + 0.01 * s
            results[f"{arm}@s{s}"] = {"raw": raw}
            pd.DataFrame(rows).to_csv(folder / f"per_pert_{arm.replace(':', ' ')}@s{s}.csv", index=False)
    (folder / "bench.json").write_text(json.dumps({"results": results}), encoding="utf-8")


def read(folder: Path, *extra: str) -> dict:
    with mock.patch.object(sys, "argv", ["leggi_banco.py", "--job-dir", str(folder), "--n-boot", "600", *extra]), \
            contextlib.redirect_stdout(io.StringIO()):
        lb.main()
    return json.loads((folder / "esito.json").read_text(encoding="utf-8"))


def scenario(shifts: dict, **kw) -> dict:
    with tempfile.TemporaryDirectory() as d:
        make_job(Path(d), shifts, **kw)
        return read(Path(d))


class TestMembers(unittest.TestCase):
    OFF = {"pds_cosine": 0.4, "de_wilcoxon_lfc_nmae": -0.6, "de_wilcoxon_direction_fidelity_yield_raw": 0.3,
           "de_wilcoxon_direction_reach_raw": 0.9, "de_wilcoxon_sig_jaccard": 0.36}

    def test_official_weights_and_the_nmae_sign(self):
        raw = np.array([0.01, 0.03, -0.006, 0.009, 0.0036])            # pds, nmae (worse), fid, reach, jac
        d = np.broadcast_to(raw[None, :, None], (3, 5, 40)).copy()
        c = lb.contrast(d, self.OFF, self.OFF, np.random.default_rng(1).integers(0, 40, size=(50, 40)))
        want = (0.01 / 0.4 + 0.03 / -0.6 - 0.006 / 0.3 + 0.009 / 0.9 + 0.0036 / 0.36) / 6
        self.assertAlmostEqual(c["mean_official"], want, places=12)
        self.assertLess(c["members"]["nmae"]["official"], 0)             # worse nMAE lowers the mean
        only_nmae = np.zeros((3, 5, 40))
        only_nmae[:, 1, :] = 0.05
        self.assertLess(lb.contrast(only_nmae, self.OFF, self.OFF, np.zeros((5, 40), dtype=int))["mean_official"], 0)
        self.assertEqual(c["mean_official_seed_sd"], 0.0)

    def test_nan_targets_are_skipped_not_propagated(self):
        d = np.full((3, 5, 40), 0.01)
        d[:, 1, 5:] = np.nan                                            # nMAE on 5 targets only
        c = lb.contrast(d, self.OFF, self.OFF, np.random.default_rng(2).integers(0, 40, size=(200, 40)))
        self.assertEqual(c["members"]["nmae"]["targets_with_value"], 5)
        self.assertAlmostEqual(c["members"]["nmae"]["raw"], 0.01)
        self.assertTrue(np.isfinite(c["mean_official"]))
        self.assertTrue(all(v is not None and np.isfinite(v) for v in c["mean_official_ci95"]))

    def test_the_spans_are_the_official_anchors(self):
        spans = lb.official_scales(lb.ANCHORS)
        self.assertAlmostEqual(spans["pds_cosine"], 0.9494896274559461 - 0.5021055713992504)
        self.assertAlmostEqual(spans["de_wilcoxon_lfc_nmae"], 0.393243176368133 - 1.0011992318260274)
        self.assertEqual(set(spans), set(lb.MEMBERS))


class TestFileNames(unittest.TestCase):
    def test_colon_and_its_drive_spelling(self):
        key = "g0:t22_a1.0@s1"
        self.assertEqual(lb.per_pert_file({"per_pert_g0:t22_a1.0@s1.csv"}, key), "per_pert_g0:t22_a1.0@s1.csv")
        self.assertEqual(lb.per_pert_file({"per_pert_g0 t22_a1.0@s1.csv", "per_pert_g0d t22_a1.0@s1.csv"}, key),
                         "per_pert_g0 t22_a1.0@s1.csv")
        with self.assertRaises(SystemExit):
            lb.per_pert_file({"per_pert_g0:t22_a1.0@s1.csv", "per_pert_g0 t22_a1.0@s1.csv"}, key)
        with self.assertRaises(SystemExit):
            lb.per_pert_file({"per_pert_g0 t22_a1.0@s2.csv"}, key)


class TestReading(unittest.TestCase):
    def test_everything_passes_and_the_simpler_of_two_close_arms_wins(self):
        offsets = 0.0005 + np.tile([0.01, -0.01], 40)                   # E2 above E1 on average, by less than noise
        e = scenario(GOOD, twin={"E2": ("E1", offsets)})
        self.assertLess(e["aggregate_check_max_abs"], 1e-12)
        for v in ("V1", "V2", "V3", "V4"):
            self.assertTrue(e["checks"][v]["passed"], (v, e["checks"][v]))
        self.assertEqual(e["checks"]["V1"]["outcome"], "passa")
        self.assertEqual(set(e["choice"]["passing"]), {"E1", "E2", "A2"})
        self.assertEqual(e["choice"]["passing"][0], "E2")               # the largest estimate ...
        self.assertEqual(e["choice"]["winner"], "E1")                   # ... but E2 - E1 straddles 0
        self.assertIn("E2 - E1", e["contrasts"])
        self.assertFalse(e["candidates"]["RB"]["built"])
        self.assertEqual(e["predictions"]["P1"], "confermata")
        self.assertEqual(e["predictions"]["P4"], "confermata")
        self.assertEqual(set(e["contrasts"]), {"C2 - C1", "C3 - C1", "T26 - C1", "E1 - C1", "E2 - C1", "A1 - C1",
                                               "A2 - C1", "G1 - C1", "D1 - C1", "C2 - C3", "C1 - A1", "E2 - E1"})

    def test_a_clearly_larger_arm_wins_and_rb_counts_after_a2(self):
        e = scenario(GOOD | {"E2": {"pds": 0.06}, "RB": {"pds": 0.012}}, rb=True)
        self.assertEqual(e["choice"]["winner"], "E2")
        self.assertIn("esclude lo zero", e["choice"]["why"])
        self.assertTrue(e["candidates"]["RB"]["built"])
        self.assertTrue(e["candidates"]["RB"]["passes_rule"])

    def test_v1_inconclusive_keeps_the_e_arms_out(self):
        e = scenario(GOOD | {"C2": {"pds": 0.0, "nmae": -0.02, "reach": 0.0}}, noise=0.004)
        self.assertFalse(e["checks"]["V1"]["passed"])
        self.assertEqual(e["checks"]["V1"]["outcome"], "il banco contraddice l'ufficiale")   # nMAE clearly the other way
        e = scenario(GOOD | {"C2": {"pds": 0.0}}, seed_shifts={"C2": {"nmae": [0.01, -0.01, -0.01]}}, noise=0.03)
        self.assertEqual(e["checks"]["V1"]["outcome"], "non conclusivo per risoluzione")
        self.assertFalse(e["candidates"]["E1"]["admitted"])
        self.assertFalse(e["candidates"]["E1"]["passes_rule"])
        self.assertTrue(e["candidates"]["A2"]["admitted"])
        self.assertIn("exclusion_note", e["choice"])

    def test_v1_contradicted_by_pds(self):
        e = scenario(GOOD | {"C2": {"pds": -0.03, "nmae": 0.02, "reach": -0.02}})
        self.assertEqual(e["checks"]["V1"]["outcome"], "il banco contraddice l'ufficiale")
        self.assertTrue(e["checks"]["V1"]["wrong_side"]["pds_interval_below_0"])
        self.assertEqual(e["predictions"]["P1"], "contraddetta")

    def test_v2_fails_when_c2_is_its_amplitude_control(self):
        e = scenario(GOOD | {"C3": {"pds": 0.02, "nmae": 0.02, "reach": -0.02}})
        self.assertFalse(e["checks"]["V2"]["passed"])
        self.assertFalse(e["candidates"]["E1"]["admitted"])

    def test_v3_fails_and_no_amplitude_is_chosen(self):
        e = scenario(GOOD | {"A1": {"pds": 0.02}})
        self.assertFalse(e["checks"]["V3"]["passed"])
        self.assertFalse(e["candidates"]["A2"]["admitted"])
        self.assertIn("amplitude_note", e["choice"])
        self.assertNotIn("A2", e["choice"]["passing"])

    def test_v4_fails_beyond_the_band_and_is_written_beside_the_choice(self):
        e = scenario(GOOD | {"T26": {"reach": 0.02}})
        self.assertFalse(e["checks"]["V4"]["passed"])
        self.assertTrue(e["checks"]["V4"]["members_beyond_0.005"]["reach"])
        self.assertIn("v4_note", e["choice"])
        self.assertEqual(e["predictions"]["P4"], "contraddetta")
        e = scenario(GOOD | {"T26": {"reach": 0.004}}, noise=0.001)   # outside 0 but inside the band
        self.assertTrue(e["checks"]["V4"]["passed"])

    def test_v4_says_when_t26_scored_exactly_as_c1(self):
        e = scenario(GOOD, twin={"T26": ("C1", np.zeros(80))})
        self.assertTrue(e["checks"]["V4"]["passed"])
        self.assertTrue(e["checks"]["V4"]["identical_to_C1"])
        self.assertIn("per costruzione", e["predictions"]["P4_note"])
        e = scenario(GOOD)
        self.assertFalse(e["checks"]["V4"]["identical_to_C1"])
        self.assertNotIn("P4_note", e["predictions"])

    def test_the_rule_needs_every_seed_and_twice_the_seed_sd(self):
        e = scenario(GOOD | {"E2": {"pds": 0.0}, "A2": {"pds": 0.0}},
                     seed_shifts={"E1": {"pds": [0.02, 0.02, -0.08]}})
        self.assertFalse(e["candidates"]["E1"]["positive_in_every_seed"])
        self.assertFalse(e["candidates"]["E1"]["passes_rule"])
        e = scenario(GOOD | {"E1": {"pds": 0.0}, "E2": {"pds": 0.0}, "A2": {"pds": 0.0}},
                     seed_shifts={"E1": {"pds": [0.004, 0.03, 0.06]}})
        c = e["candidates"]["E1"]
        self.assertTrue(c["positive_in_every_seed"])
        self.assertFalse(c["above_twice_seed_sd"])
        self.assertFalse(c["passes_rule"])
        self.assertIsNone(e["choice"]["winner"])
        self.assertIn("nessun braccio passa", e["choice"]["why"])

    def test_outputs_are_new_files_and_stage_84_can_read_the_seed_mean(self):
        with tempfile.TemporaryDirectory() as d:
            make_job(Path(d), GOOD)
            read(Path(d))
            media = json.loads((Path(d) / "bench_media_semi.json").read_text(encoding="utf-8"))["results"]
            bench = json.loads((Path(d) / "bench.json").read_text(encoding="utf-8"))["results"]
            for m in [*lb.MEMBERS, lb.MSE]:
                want = np.mean([bench[f"g0:t22_a1.0@s{s}"]["raw"][m] for s in (1, 2, 3)])
                self.assertAlmostEqual(media["g0:t22_a1.0"]["raw"][m], want)
            table = pd.read_csv(Path(d) / "contrasti.csv")
            self.assertIn("pds_raw_ci95", table.columns)
            with self.assertRaises(SystemExit):
                read(Path(d))


class TestShareAndRecipes(unittest.TestCase):
    def test_the_share_reads_back_and_its_exclusion_is_share_above_zero(self):
        axis = np.array([f"G{i}" for i in range(7)])
        share = np.array([0.0, 1.0, 0.123456789, 1e-7, 0.5, 0.0, 0.999999], dtype=np.float32)
        frac, excl = build_arms.share_texts(share, axis)
        back = pd.read_csv(io.StringIO(frac))
        self.assertEqual(back["gene"].tolist(), axis.tolist())
        np.testing.assert_array_equal(back["share"].to_numpy().astype(np.float32), share)
        zero_one = pd.read_csv(io.StringIO(excl))["share"].to_numpy()
        np.testing.assert_array_equal(zero_one, [0, 1, 1, 1, 1, 0, 1])
        for bad in (share[:-1], np.where(share > 0.9, 1.5, share), np.where(share == 0, np.nan, share)):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                build_arms.share_texts(bad, axis)

    def test_conversion_reuses_identical_files_and_refuses_others(self):
        axis = np.array([f"G{i}" for i in range(5)])
        with tempfile.TemporaryDirectory() as d:
            npy = Path(d) / "share.npy"
            np.save(npy, np.array([0.0, 0.25, 1.0, 0.0, 0.75], dtype=np.float32))
            first = build_arms.convert_share(npy, axis, Path(d) / "quota")
            self.assertTrue(first["csv_reads_back_to_the_float32"])
            self.assertEqual(first["genes_zero"], 2)
            self.assertFalse(any(f["reused"] for f in first["files"].values()))
            again = build_arms.convert_share(npy, axis, Path(d) / "quota")
            self.assertTrue(all(f["reused"] for f in again["files"].values()))
            self.assertEqual({k: v["sha256"] for k, v in first["files"].items()},
                             {k: v["sha256"] for k, v in again["files"].items()})
            (Path(d) / "quota" / build_arms.EXCL_CSV).write_text("gene,share\nG0,1\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                build_arms.convert_share(npy, axis, Path(d) / "quota")

    def test_recipes_point_at_this_build_and_say_so(self):
        template = json.loads((HERE / "ricette" / "t23.json").read_text(encoding="utf-8"))
        same, changes = build_arms.materialise(template, share_dir=build_arms.DEFAULT_SHARE_DIR,
                                               data_out=build_arms.DEFAULT_DATA_OUT)
        self.assertEqual((same, changes), (template, []))
        with tempfile.TemporaryDirectory() as d:
            moved, changes = build_arms.materialise(template, share_dir=Path(d) / "q", data_out=Path(d) / "out")
        self.assertEqual(moved["gene_share"]["path"], str(Path(d) / "q" / build_arms.SHARE_CSV))
        self.assertEqual(moved["gene_share"]["match_detectable"], str(Path(d) / "out" / "t22"))
        self.assertEqual({c["key"] for c in changes}, {"gene_share.path", "gene_share.match_detectable"})
        self.assertEqual({k: v for k, v in moved.items() if k != "gene_share"},
                         {k: v for k, v in template.items() if k != "gene_share"})

    def test_templates_are_t22_without_k562_and_differ_by_one_factor(self):
        c1 = json.loads((HERE / "ricette" / "t22.json").read_text(encoding="utf-8"))
        t22 = json.loads((build_arms.REPO / "configs/recipes/t22.json").read_text(encoding="utf-8"))
        self.assertEqual(list(c1["contexts"]), ["k562"])
        weights = c1["contexts"]["k562"]["weights"]
        self.assertEqual(weights, {k: v for k, v in t22["contexts"]["A"]["weights"].items() if k != "k562"})
        for key in ("effect", "gamma", "reliability_scale", "allow_missing_targets"):
            self.assertEqual(c1[key], t22[key])
        self.assertEqual(c1["cis"]["max_distance_bp"], t22["cis"]["max_distance_bp"])
        self.assertEqual(c1["cis"]["scale"], t22["cis"]["scale"])
        ignore = {"name", "why"}
        for name, extra in (("t23", {"gene_share"}), ("gate", {"expression_gate"}), ("excl", {"gene_share"}),
                            ("t22r9", set())):
            r = json.loads((HERE / "ricette" / f"{name}.json").read_text(encoding="utf-8"))
            with self.subTest(recipe=name):
                self.assertEqual({k: v for k, v in r.items() if k not in ignore | extra},
                                 {k: v for k, v in c1.items() if k not in ignore})
        for name, amp in (("t22h", 0.788), ("t22d", 3.152)):
            r = json.loads((HERE / "ricette" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(r["contexts"]["k562"]["amplitude"], amp)
        s = 1.4
        self.assertAlmostEqual(build_arms.derived_t22s(c1, s)["contexts"]["k562"]["amplitude"], 1.576 * s)
        e2 = build_arms.derived_exclrs(json.loads((HERE / "ricette" / "excl.json").read_text(encoding="utf-8")))
        self.assertEqual(e2["gene_share"]["match_detectable"], "processed/banco_k562_pannello_2026-09-29/t22")


if __name__ == "__main__":
    unittest.main()
