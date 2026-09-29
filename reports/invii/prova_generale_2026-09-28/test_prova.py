"""Tests of the rehearsal scripts of this folder, on tiny synthetic data only.

Not part of `tests/` (these scripts are a report's record, not live code). Run:

    scripts/py.cmd -m unittest reports/invii/prova_generale_2026-09-28/test_prova.py -v
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"prova_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_main(mod, argv: list[str]) -> str:
    old = sys.argv
    sys.argv = [mod.__file__, *map(str, argv)]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    finally:
        sys.argv = old
    return buf.getvalue()


# --- synthetic control files ------------------------------------------------------------------

def write_controls(path: Path, context: str, genes: list[str], n_cells: int = 40, seed: int = 0) -> Path:
    import anndata as ad

    rng = np.random.default_rng(seed)
    dense = rng.poisson(2.0, size=(n_cells, len(genes))).astype(np.float32)
    obs = pd.DataFrame({"target_gene": pd.Categorical(["non-targeting"] * n_cells),
                        "context": pd.Categorical([context] * n_cells),
                        "ntc_id": pd.Categorical([f"ntc{i % 3}" for i in range(n_cells)])},
                       index=[f"c{i}" for i in range(n_cells)])
    ad.AnnData(X=sp.csr_matrix(dense), obs=obs, var=pd.DataFrame(index=pd.Index(genes))).write_h5ad(path)
    return path


class TestBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from vcc2026.manifest import file_fingerprint

        cls.mod = load("bundle_finto")
        cls.tmp = Path(tempfile.mkdtemp(prefix="prova-bundle-"))
        cls.controls = cls.tmp / "controls"
        cls.controls.mkdir()
        cls.genes = [f"G{i}" for i in range(25)]
        for k, c in enumerate("ABC"):
            write_controls(cls.controls / f"context_{c}.h5ad", c, cls.genes, seed=k)
        (cls.controls / "gene_names.csv").write_text("gene_name\n" + "\n".join(cls.genes) + "\n")
        (cls.controls / "pert_counts.csv").write_text("target_gene\nG1\nG2\n")
        (cls.controls / "manifest.json").write_text(json.dumps({
            "season": "2026", "partition": "val", "contexts": ["A", "B", "C"], "pert_col": "target_gene",
            "context_col": "context", "control_label": "non-targeting", "n_genes": 25, "n_constructs": 2,
            "per_context": {c: {"n_perturbations": 2, "control_cells": 40, "ground_truth_cells": 99,
                                "n_ntc_ids": 3} for c in "ABC"}, "cells_per_pert": 400}))
        cls.t22 = cls.tmp / "t22.json"
        cls.t22.write_text(json.dumps({"inputs": {f"controls:{c}": file_fingerprint(cls.controls / f"context_{c}.h5ad")
                                                  for c in "ABC"}}))
        cls.estr = cls.tmp / "estrazione.json"
        cls.estr.write_text(json.dumps({"mapping_new_to_old": {"D": "B", "E": "A", "F": "C"}}))
        cls.panel = cls.tmp / "panel.csv"
        cls.panel.write_text("target_gene\nG3\nG4\n")
        cls.before = {c: (cls.controls / f"context_{c}.h5ad").read_bytes() for c in "ABC"}
        cls.out = cls.tmp / "controls_prova"
        cls.report = cls.tmp / "report"
        cls.log = run_main(cls.mod, ["--controls-dir", cls.controls, "--out", cls.out, "--estrazione", cls.estr,
                                     "--panel", cls.panel, "--t22-manifest", cls.t22, "--report", cls.report])
        cls.manifest = json.loads((cls.out / "manifest.json").read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_labels_follow_the_mapping_and_stage45_reads_them(self):
        from vcc2026.inference import read_basal_profile

        for new, old in {"D": "B", "E": "A", "F": "C"}.items():
            prof = read_basal_profile(self.out / f"context_{new}.h5ad")
            self.assertEqual(prof.context, new)
            ref = read_basal_profile(self.controls / f"context_{old}.h5ad")
            np.testing.assert_array_equal(prof.profile, ref.profile)
            np.testing.assert_array_equal(prof.library_sizes, ref.library_sizes)

    def test_originals_are_byte_identical(self):
        for c in "ABC":
            self.assertEqual((self.controls / f"context_{c}.h5ad").read_bytes(), self.before[c])

    def test_every_check_passes_and_is_recorded(self):
        checks = self.manifest["prova"]["checks"]
        self.assertTrue(all(checks.values()), checks)
        self.assertEqual(self.manifest["contexts"], ["D", "E", "F"])
        self.assertEqual(self.manifest["partition"], "prova")
        self.assertIsNone(self.manifest["per_context"]["D"]["ground_truth_cells"])
        self.assertEqual(self.manifest["per_context"]["D"]["copy_of"], "B")
        named = self.manifest["prova"]["copies"]["D"]["comparison"]["named"]
        for prefix in ("X/data", "X/indices", "X/indptr", "var/_index", "obs/target_gene", "obs/ntc_id"):
            self.assertTrue(any(k == prefix or k.startswith(prefix + "/") for k in named), prefix)
        self.assertEqual((self.out / "pert_counts.csv").read_text(), "target_gene\nG3\nG4\n")
        self.assertTrue((self.report / "bundle_manifest.json").exists())

    def test_copies_are_not_links(self):
        for new in "DEF":
            self.assertEqual(os.stat(self.out / f"context_{new}.h5ad").st_nlink, 1)

    def test_comparison_catches_a_changed_value(self):
        bad = self.tmp / "bad.h5ad"
        shutil.copyfile(self.controls / "context_A.h5ad", bad)
        with h5py.File(bad, "r+") as f:
            f["X/data"][0] = f["X/data"][0] + 1
        cmp = self.mod.compare_files(self.controls / "context_A.h5ad", bad)
        self.assertFalse(cmp["equal"])
        self.assertIn({"X/data": "values"}, cmp["differences"])

    def test_comparison_reports_only_the_label(self):
        cmp = self.mod.compare_files(self.controls / "context_B.h5ad", self.out / "context_D.h5ad")
        self.assertTrue(cmp["equal"])
        cmp = self.mod.compare_files(self.controls / "context_B.h5ad", self.out / "context_D.h5ad", allowed="")
        self.assertEqual(cmp["differences"], [{"obs/context/categories": "values"}])

    def test_a_second_run_refuses(self):
        with self.assertRaises(SystemExit):
            run_main(self.mod, ["--controls-dir", self.controls, "--out", self.out, "--estrazione", self.estr,
                                "--panel", self.panel, "--t22-manifest", self.t22, "--report", self.tmp / "r2"])


# --- synthetic universes -----------------------------------------------------------------------

G = 12


def table(targets: list[str], seed: int, nan_every: int = 5) -> dict:
    rng = np.random.default_rng(seed)
    T = len(targets)
    shr = rng.normal(size=(T, G)).astype(np.float32)
    raw = rng.normal(size=(T, G)).astype(np.float32)
    se = rng.uniform(0.1, 1, size=(T, G)).astype(np.float32)
    for a in (shr, raw, se):
        a[:, ::nan_every] = np.nan
    return {"targets": np.array(targets), "shrunk": shr, "raw": raw, "se": se,
            "n_cells": rng.integers(10, 500, size=T), "meta": json.dumps({"seed": seed})}


def save(path: Path, tab: dict) -> None:
    np.savez_compressed(path, **tab)


def rows_of(tab: dict, targets: list[str]) -> dict:
    pos = {t: i for i, t in enumerate(tab["targets"].astype(str))}
    sel = [pos[t] for t in targets]
    return {"targets": np.array(targets), **{k: tab[k][sel] for k in ("shrunk", "raw", "se", "n_cells")},
            "meta": tab["meta"]}


class TestAssemble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("assembla_cache")
        cls.tmp = Path(tempfile.mkdtemp(prefix="prova-cache-"))
        # file-named format (K562/Orion): two chunks, one target without effects (empty chunk)
        cls.u1 = cls.tmp / "universe_named"
        cls.u1.mkdir()
        cls.c0, cls.c1 = table(["T1", "T2", "T3"], 1), table(["T4", "T5"], 2)
        save(cls.u1 / "src_00.npz", cls.c0)
        save(cls.u1 / "src_01.npz", cls.c1)
        pd.DataFrame({"target": ["T1", "T2", "T3", "T4", "T5", "T6"],
                      "chunk": ["src_00.npz"] * 3 + ["src_01.npz"] * 2 + [""],
                      "n_cells": [1] * 6}).to_csv(cls.u1 / "index.csv", index=False)
        # integer-group format (CD4): groups 0 and 1, two tables; cd4_Rest lacks T5 in group 1
        cls.u2 = cls.tmp / "universe_group"
        cls.u2.mkdir()
        cls.m0, cls.m1 = table(["T2", "T4"], 3), table(["T5", "T7"], 4)
        cls.r0, cls.r1 = table(["T2", "T4"], 5), table(["T7"], 6)
        save(cls.u2 / "cd4_mix_000.npz", cls.m0)
        save(cls.u2 / "cd4_mix_001.npz", cls.m1)
        save(cls.u2 / "cd4_Rest_000.npz", cls.r0)
        save(cls.u2 / "cd4_Rest_001.npz", cls.r1)
        pd.DataFrame({"target": ["T2", "T4", "T5", "T7"], "chunk": [0, 0, 1, 1],
                      "n_cells": [1.0] * 4}).to_csv(cls.u2 / "index.csv", index=False)
        cls.targets = cls.tmp / "targets.csv"
        cls.targets.write_text("target_gene\nT5\nT1\nT6\nT4\nT2\nnon-targeting\nT5\n")
        # a reference cache as stage 98 would have written it (targets in panel order)
        cls.ref = cls.tmp / "ref"
        cls.ref.mkdir()
        save(cls.ref / "src.npz", rows_of({**cls.c0, **{k: np.concatenate([cls.c0[k], cls.c1[k]])
                                                         for k in ("targets", "shrunk", "raw", "se", "n_cells")}},
                                          ["T5", "T1", "T4", "T2"]))
        mix_all = {k: np.concatenate([cls.m0[k], cls.m1[k]]) for k in ("targets", "shrunk", "raw", "se", "n_cells")}
        near = rows_of({**cls.m0, **mix_all}, ["T5", "T4", "T2"])
        near["shrunk"] = near["shrunk"].copy()
        near["shrunk"][0, 1] += np.float32(1e-8)    # within cd4_mix's registered tolerance
        save(cls.ref / "cd4_mix.npz", near)
        cls.out = cls.tmp / "cache"
        cls.log = run_main(cls.mod, ["--targets-csv", cls.targets, "--out", cls.out,
                                     "--source", f"src={cls.u1}", "--source", f"cd4_mix={cls.u2}",
                                     "--source", f"cd4_Rest={cls.u2}", "--compare-to", cls.ref,
                                     "--report-json", cls.tmp / "parity.json"])
        cls.manifest = json.loads((cls.out / "manifest.json").read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_rows_are_selected_exactly_in_panel_order(self):
        z = np.load(self.out / "src.npz")
        self.assertEqual(z["targets"].tolist(), ["T5", "T1", "T4", "T2"])
        both = {k: np.concatenate([self.c0[k], self.c1[k]]) for k in ("targets", "shrunk", "raw", "se", "n_cells")}
        want = rows_of({**self.c0, **both}, ["T5", "T1", "T4", "T2"])
        for k in ("shrunk", "raw", "se", "n_cells"):
            np.testing.assert_array_equal(z[k], want[k])
        self.assertEqual(json.loads(str(z["meta"])), {"seed": 1})
        self.assertEqual(sorted(z.files), ["meta", "n_cells", "raw", "se", "shrunk", "targets"])

    def test_group_format_and_a_table_lacking_a_target(self):
        z = np.load(self.out / "cd4_mix.npz")
        self.assertEqual(z["targets"].tolist(), ["T5", "T4", "T2"])
        r = np.load(self.out / "cd4_Rest.npz")
        self.assertEqual(r["targets"].tolist(), ["T4", "T2"])
        info = self.manifest["sources"]["cd4_Rest"]
        self.assertEqual(info["listed_in_index_but_absent_from_chunk"], ["T5"])
        np.testing.assert_array_equal(r["raw"], rows_of(self.r0, ["T4", "T2"])["raw"])

    def test_missing_targets_and_targets_hash_are_recorded(self):
        self.assertEqual(self.manifest["sources"]["src"]["missing"], ["T6"])
        self.assertEqual(self.manifest["targets_requested"], 5)
        from comune import sha256_file

        self.assertEqual(self.manifest["targets_csv_sha256"], sha256_file(self.targets))

    def test_parity_rule(self):
        p = self.manifest["sources"]["src"]["parity"]
        self.assertTrue(p["rule_passed"])
        self.assertEqual(p["raw"]["max_abs_diff"], 0.0)
        self.assertTrue(p["same_order"])
        m = self.manifest["sources"]["cd4_mix"]["parity"]
        self.assertTrue(m["rule_passed"])
        self.assertGreater(m["shrunk"]["max_abs_diff"], 0.0)
        self.assertEqual(self.manifest["sources"]["cd4_Rest"]["parity"], {"reference": str(self.ref / "cd4_Rest.npz"),
                                                                           "missing": True})
        self.assertFalse(self.manifest["parity_rule_passed"])

    def test_parity_fails_above_tolerance_or_on_a_mask_change(self):
        bad = self.tmp / "bad.npz"
        z = dict(np.load(self.out / "src.npz"))
        z["raw"] = z["raw"].copy()
        z["raw"][0, 1] += np.float32(1e-6)
        np.savez_compressed(bad, **z)
        self.assertFalse(self.mod.compare(bad, self.ref / "src.npz")["rule_passed"])
        z["raw"][0, 1] = np.nan
        np.savez_compressed(bad, **z)
        p = self.mod.compare(bad, self.ref / "src.npz")
        self.assertEqual(p["raw"]["finite_mask_mismatches"], 1)
        self.assertFalse(p["rule_passed"])

    def test_refuses_an_existing_output(self):
        with self.assertRaises(SystemExit):
            run_main(self.mod, ["--targets-csv", self.targets, "--out", self.out, "--source", f"src={self.u1}"])

    def test_reuses_an_empty_folder_left_by_an_interrupted_run(self):
        empty = self.tmp / "left_empty"
        empty.mkdir()
        run_main(self.mod, ["--targets-csv", self.targets, "--out", empty, "--source", f"src={self.u1}"])
        m = json.loads((empty / "manifest.json").read_text())
        self.assertTrue(m["out_existed_empty"])
        self.assertFalse(self.manifest["out_existed_empty"])


# --- the D/E/F recipe ----------------------------------------------------------------------------

class TestRecipe(unittest.TestCase):
    def test_def_recipe_is_t22_with_the_keys_renamed_and_nothing_else(self):
        t22 = json.loads((REPO / "configs" / "recipes" / "t22.json").read_text(encoding="utf-8"))
        new = json.loads((HERE / "ricetta_t22_DEF.json").read_text(encoding="utf-8"))
        self.assertEqual(list(new["contexts"]), ["D", "E", "F"])
        mapping = json.loads((HERE / "estrazione.json").read_text(encoding="utf-8"))["mapping_new_to_old"]
        for n, o in mapping.items():
            self.assertEqual(new["contexts"][n], t22["contexts"][o])
        self.assertEqual({k: v for k, v in new.items() if k != "contexts"},
                         {k: v for k, v in t22.items() if k != "contexts"})


# --- control CPM ---------------------------------------------------------------------------------

def mean_cell_cpm_dense(path: Path) -> np.ndarray:
    import anndata as ad

    x = ad.read_h5ad(path).X.toarray().astype(np.float64)
    return (x / x.sum(axis=1, keepdims=True) * 1e6).mean(axis=0)


class TestCpm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("cpm_contesti")
        bundle = load("bundle_finto")
        cls.tmp = Path(tempfile.mkdtemp(prefix="prova-cpm-"))
        cls.genes = [f"G{i}" for i in range(25)]
        (cls.tmp / "genes.csv").write_text("gene_name\n" + "\n".join(cls.genes) + "\n")
        abc = cls.tmp / "abc"
        abc.mkdir()
        for k, c in enumerate("ABC"):
            write_controls(abc / f"context_{c}.h5ad", c, cls.genes, n_cells=30 + 7 * k, seed=10 + k)
        ref = pd.DataFrame({c: mean_cell_cpm_dense(abc / f"context_{c}.h5ad") for c in "ABC"},
                           index=pd.Index(cls.genes, name="gene_name"))
        ref.to_csv(cls.tmp / "reference.csv")
        cls.deff = cls.tmp / "def"
        cls.deff.mkdir()
        for new, old in {"D": "B", "E": "A", "F": "C"}.items():
            shutil.copyfile(abc / f"context_{old}.h5ad", cls.deff / f"context_{new}.h5ad")
            bundle.relabel(cls.deff / f"context_{new}.h5ad", old, new)
        cls.abc = abc

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_cpm(self, name, controls, contexts, *extra):
        out = self.tmp / name / "cpm.csv"
        run_main(self.mod, ["--controls-dir", controls, "--contexts", *contexts, "--out", out,
                            "--axis", self.tmp / "genes.csv", "--parity-with", self.tmp / "reference.csv", *extra])
        return out, json.loads(out.with_suffix(".json").read_text())

    def test_abc_reproduce_the_reference_definition(self):
        out, info = self.run_cpm("abc", self.abc, ["A", "B", "C"])
        self.assertTrue(info["parity"]["rule_passed"], info["parity"])
        frame = pd.read_csv(out).set_index("gene_name")
        np.testing.assert_allclose(frame["B"].to_numpy(), mean_cell_cpm_dense(self.abc / "context_B.h5ad"),
                                   rtol=1e-12)
        self.assertTrue(all(f["label_ok"] for f in info["per_context"].values()))
        self.assertGreater(info["per_context"]["A"]["pooled_cpm_max_rel_diff_from_written"], 0)

    def test_the_copies_match_their_sources_under_the_mapping(self):
        _, info = self.run_cpm("def", self.deff, ["D", "E", "F"], "--mapping", "D=B", "E=A", "F=C")
        self.assertTrue(info["parity"]["rule_passed"], info["parity"])
        self.assertEqual(info["per_context"]["D"]["label_in_file"], "D")
        _, bad = self.run_cpm("def_wrong", self.deff, ["D"], "--mapping", "D=A")
        self.assertFalse(bad["parity"]["rule_passed"])

    def test_library_median_is_recorded(self):
        _, info = self.run_cpm("lib", self.abc, ["C"])
        import anndata as ad

        lib = np.asarray(ad.read_h5ad(self.abc / "context_C.h5ad").X.sum(axis=1)).ravel()
        self.assertEqual(info["per_context"]["C"]["median_library_size"], float(np.median(lib)))


# --- effects parity ------------------------------------------------------------------------------

class TestEffectsParity(unittest.TestCase):
    def test_rule(self):
        mod = load("confronta_effetti")
        tmp = Path(tempfile.mkdtemp(prefix="prova-eff-"))
        try:
            rng = np.random.default_rng(1)
            lfc = rng.normal(size=(3, 5)).astype(np.float32)
            obs = lfc > 0
            kw = {"targets": np.array(["a", "b", "c"]), "genes": np.array(list("vwxyz"))}
            np.savez_compressed(tmp / "ref.npz", lfc=lfc, observed=obs, **kw)
            near = lfc.copy()
            near[0, 0] += np.float32(5e-7)
            np.savez_compressed(tmp / "near.npz", lfc=near, observed=obs, **kw)
            self.assertTrue(mod.compare(tmp / "near.npz", tmp / "ref.npz")["rule_passed"])
            far = lfc.copy()
            far[1, 1] += np.float32(1e-5)
            np.savez_compressed(tmp / "far.npz", lfc=far, observed=obs, **kw)
            self.assertFalse(mod.compare(tmp / "far.npz", tmp / "ref.npz")["rule_passed"])
            flip = obs.copy()
            flip[2, 2] = ~flip[2, 2]
            np.savez_compressed(tmp / "flip.npz", lfc=lfc, observed=flip, **kw)
            self.assertEqual(mod.compare(tmp / "flip.npz", tmp / "ref.npz")["observed_mismatches"], 1)
            np.savez_compressed(tmp / "order.npz", lfc=lfc, observed=obs, targets=np.array(["b", "a", "c"]),
                                genes=kw["genes"])
            self.assertFalse(mod.compare(tmp / "order.npz", tmp / "ref.npz")["rule_passed"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --- diagnostics ---------------------------------------------------------------------------------

def save_cache_table(path: Path, targets: list[str], shrunk: np.ndarray, n_cells) -> None:
    np.savez_compressed(path, targets=np.array(targets), shrunk=shrunk, raw=shrunk, se=np.abs(shrunk) + 0.1,
                        n_cells=np.asarray(n_cells), meta="{}")


class TestDiagnostica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from vcc2026.multisource import AxisTable, mix

        cls.mod = load("diagnostica")
        cls.tmp = Path(tempfile.mkdtemp(prefix="prova-diag-"))
        rng = np.random.default_rng(3)
        cls.axis = np.array([f"T{i}" for i in range(1, 41)])
        G = cls.axis.size
        cls.panel = ["T1", "T2", "T4", "T5", "T6"]           # T6: no source (P0)
        today = ["T1", "T8", "T9", "T10"]                     # today's panel (G-b)
        src_targets = {"src": ["T1", "T2", "T4", "T8", "T9"], "cd4_mix": ["T1", "T2", "T5", "T10"]}
        cls.univ = {}
        cls.new, cls.today = cls.tmp / "cache_new", cls.tmp / "cache_today"
        cls.new.mkdir()
        cls.today.mkdir()
        cls.tabs = {}
        for name, ts in src_targets.items():
            sh = rng.normal(0, 0.3, size=(len(ts), G)).astype(np.float32)
            sh[:, ::7] = np.nan
            nc = rng.integers(20, 300, size=len(ts))
            cls.tabs[name] = AxisTable(name, ts, sh, sh, sh, nc, {})
            keep = [i for i, t in enumerate(ts) if t in cls.panel]
            save_cache_table(cls.new / f"{name}.npz", [ts[i] for i in keep], sh[keep], nc[keep])
            keep = [i for i, t in enumerate(ts) if t in today]
            save_cache_table(cls.today / f"{name}.npz", [ts[i] for i in keep], sh[keep], nc[keep])
        # universes: src in the file-named format, cd4_mix in the group format
        u1 = cls.tmp / "universe_src"
        u1.mkdir()
        t = cls.tabs["src"]
        save_cache_table(u1 / "src_00.npz", t.targets[:3], t.shrunk[:3], t.n_cells[:3])
        save_cache_table(u1 / "src_01.npz", t.targets[3:], t.shrunk[3:], t.n_cells[3:])
        pd.DataFrame({"target": t.targets, "chunk": ["src_00.npz"] * 3 + ["src_01.npz"] * 2}).to_csv(
            u1 / "index.csv", index=False)
        u2 = cls.tmp / "universe_cd4"
        u2.mkdir()
        t = cls.tabs["cd4_mix"]
        save_cache_table(u2 / "cd4_mix_000.npz", t.targets, t.shrunk, t.n_cells)
        pd.DataFrame({"target": t.targets, "chunk": [0] * 4}).to_csv(u2 / "index.csv", index=False)
        cls.u1, cls.u2 = u1, u2
        # a stage-100-like run on the new cache: amplitude 1.5, no cis head
        cls.recipe = cls.tmp / "recipe.json"
        spec = {"amplitude": 1.5, "weights": {"src": 1.0, "cd4_mix": 1.0}}
        cls.recipe.write_text(json.dumps({"name": "tiny", "effect": "shrunk", "gamma": 1.0, "reliability_scale": 100,
                                          "allow_missing_targets": True, "contexts": {"D": spec, "E": spec}}))
        new_tabs = [cls.mod.light_table(cls.new, n) for n in ("cd4_mix", "src")]
        eff, den = mix(new_tabs, cls.panel, weights=spec["weights"], gamma=1.0, reliability_scale=100)
        cls.lfc = (eff * 1.5).astype(np.float32)
        covered = (den > 0).any(axis=1)
        cls.effects = cls.tmp / "effects"
        cls.effects.mkdir()
        for c in "DE":
            np.savez_compressed(cls.effects / f"effects_{c}.npz", targets=np.array(cls.panel), genes=cls.axis,
                                lfc=cls.lfc, observed=den > 0)
        missing = [p for p, c in zip(cls.panel, covered) if not c]
        (cls.effects / "manifest.json").write_text(json.dumps({"contexts": {c: {
            "targets_covered": int(covered.sum()), "targets_missing": missing} for c in "DE"}}))
        # the G-b re-mix, by hand
        today_tabs = [cls.mod.light_table(cls.today, n) for n in ("cd4_mix", "src")]
        eff_b, _ = mix(new_tabs, cls.panel, weights=spec["weights"], gamma=1.0, reliability_scale=100,
                       common={t.name: t.common() for t in today_tabs})
        cls.lfc_b = (eff_b * 1.5).astype(np.float32)
        cpm = pd.DataFrame({"D": rng.lognormal(3, 1.5, G), "E": rng.lognormal(3, 1.5, G)},
                           index=pd.Index(cls.axis, name="gene_name"))
        cpm.to_csv(cls.tmp / "cpm.csv")
        cls.cpm = cpm
        pd.DataFrame({"target_gene": cls.panel, "stratum": ["P3", "P1-2", "P1-1", "P1-1", "P0"],
                      "n_sources": [2, 2, 1, 1, 0]}).to_csv(cls.tmp / "bersagli.csv", index=False)
        cls.out = cls.tmp / "diag.json"
        run_main(cls.mod, ["--out", cls.out, "--recipe", cls.recipe, "--bersagli", cls.tmp / "bersagli.csv",
                           "--estrazione", cls.tmp / "none.json", "--effects", cls.effects,
                           "--cache-new", cls.new, "--cache-today", cls.today,
                           "--universe", f"src={u1}", "--universe", f"cd4_mix={u2}",
                           "--cpm-new", cls.tmp / "cpm.csv", "--cpm-ref", cls.tmp / "none.csv"])
        cls.report = json.loads(cls.out.read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_remix_reproduces_the_effects_exactly(self):
        for c in "DE":
            self.assertTrue(self.report["gamma"]["flips"][c]["reproduces_stage100_exactly"])

    def test_mixing_in_blocks_gives_the_same_rows(self):
        from vcc2026.multisource import mix

        tabs = [self.mod.light_table(self.new, n) for n in ("cd4_mix", "src")]
        kw = {"weights": {"src": 1.0, "cd4_mix": 1.0}, "gamma": 1.0, "reliability_scale": 100}
        whole, _ = mix(tabs, self.panel, **kw)
        self.assertTrue(np.array_equal(self.mod.mix_blocks(tabs, self.panel, block=2, **kw), whole))

    def test_flips_match_a_count_by_hand(self):
        from vcc2026.transfer_model import detectable_threshold

        cpm = self.cpm["D"].to_numpy()
        gate, thr = cpm >= 5, detectable_threshold(cpm)
        a = np.abs(self.lfc[:, gate]) > thr[gate]
        b = np.abs(self.lfc_b[:, gate]) > thr[gate]
        self.assertEqual(self.report["gamma"]["flips"]["D"]["flips_G-a_to_G-b"], int((a != b).sum()))
        self.assertIn("flips_G-a_to_G-c", self.report["gamma"]["flips"]["D"])

    def test_universe_common_is_the_table_common(self):
        vec, info = self.mod.universe_common(self.u1, "src")
        np.testing.assert_allclose(vec, self.tabs["src"].common(), rtol=1e-12)
        self.assertEqual(info["targets"], 5)
        vec, _ = self.mod.universe_common(self.u2, "cd4_mix")
        np.testing.assert_allclose(vec, self.tabs["cd4_mix"].common(), rtol=1e-12)
        g = self.report["gamma"]["per_source"]["src"]
        self.assertIn("G-a vs G-c", g)
        self.assertLessEqual(abs(g["G-b vs G-c"]["cosine"]), 1.0)

    def test_coverage_by_stratum(self):
        cov = self.report["coverage"]["per_context"]["D"]
        self.assertEqual(cov["covered"], 4)
        self.assertTrue(cov["covered_as_expected"])
        self.assertEqual(cov["by_stratum"]["P0"], {"targets": 1, "expected_covered": 0, "covered": 0,
                                                   "all_zero_rows": 1, "uncovered_with_cis_only": 0,
                                                   "own_gene_zero": 1, "own_gene_on_axis": 1})
        self.assertFalse(cov["prediction_4"]["covered_270"])
        self.assertTrue(cov["prediction_4"]["p0_own_gene_zero_all"])

    def test_solver_returns_the_reference_on_permuted_copies(self):
        rng = np.random.default_rng(5)
        E = rng.normal(0, 0.3, size=(41, 300)).astype(np.float32)
        K = np.zeros_like(E)
        K[3, 7] = -0.8
        cpms = {c: rng.lognormal(3, 1.5, 300) for c in "ABC"}
        from vcc2026.transfer_model import detectable_threshold

        def parts(cpm):
            gate = cpm >= 5
            return E[:, gate], K[:, gate], detectable_threshold(cpm)[gate]

        ref = {c: parts(cpms[c]) for c in "ABC"}
        target = float(np.mean([self.mod.n_det(e, k, 1.576, t) for e, k, t in ref.values()]))
        new = {n: parts(cpms[o]) for n, o in {"D": "B", "E": "A", "F": "C"}.items()}
        r = self.mod.solve(lambda s: float(np.mean([self.mod.n_det(e, k, s, t) for e, k, t in new.values()])),
                           target, 1.576)
        self.assertEqual(r["s"], 1.576)
        self.assertTrue(r["exact_level"])
        self.assertLessEqual(r["s_cross"], 1.576)
        self.assertGreaterEqual(r["s_upper"], 1.576)
        # a deeper context (lower thresholds) needs a smaller amplitude for the same count
        deep, shallow = parts(cpms["A"] * 4), parts(cpms["A"] / 4)
        s_deep = self.mod.solve(lambda s: self.mod.n_det(*deep[:2], s, deep[2]), target, 1.576)["s"]
        s_shallow = self.mod.solve(lambda s: self.mod.n_det(*shallow[:2], s, shallow[2]), target, 1.576)["s"]
        self.assertLess(s_deep, s_shallow)


if __name__ == "__main__":
    unittest.main()
