"""Tests of the panel caches stage 100 reads: stage 98's manifest, and stage 106's assembly from the universes.

Each test pins a way a cache could reach stage 100 built for another panel, or hold something other
than what its manifest says (dress rehearsal of 22 October, reports/invii/prova_generale_2026-09-28/):

* a cache that does not record the panel it was built for, which stage 100 can only guess at from
  its coverage (defect D4);
* a panel file read by column position, so a file with a ``context`` column names the wrong
  targets (D2);
* a manifest written in a way that changes the tables it describes;
* a universe row copied from the wrong chunk or in the wrong order, or one index format misread (D10);
* an existing cache overwritten.

Stages 98 and 106 run end to end on tiny synthetic inputs; the official axis is replaced by a
short list of genes.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026.multisource import AxisTable, effects_from_pseudobulk  # noqa: E402
from vcc2026.panel import panel_record, panel_sha256  # noqa: E402


def load_stage(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(stage, argv: list, axis) -> str:
    """Run a stage's ``main`` with ``argv`` and ``axis`` as the official axis; returns what it printed."""
    out = io.StringIO()
    with mock.patch.object(sys, "argv", ["stage", *map(str, argv)]), \
            mock.patch.object(stage, "official_axis", lambda: SimpleNamespace(symbols=tuple(axis))), \
            contextlib.redirect_stdout(out):
        stage.main()
    return out.getvalue()


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def npz_arrays(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


# --- stage 98 --------------------------------------------------------------------------------------

GENES = [f"G{i:02d}" for i in range(80)]                  # what the sources measure
AXIS98 = tuple(GENES[:76] + ["Z1", "Z2", "Z3", "Z4"])      # four source genes off the axis, four axis genes unmeasured
PANEL98 = ["G03", "G01", "G05", "G02", "G04", "G06"]      # not sorted: the panel's order is the tables' order


def write_stage98_inputs(root: Path, seed: int = 11) -> dict:
    """Synthetic inputs of stage 98: a K562 per-cell-mean bulk, CD4 pseudobulk rows in three conditions
    and four donors, and one extra source. Every target knocks its own gene down and moves twelve others;
    G06 is missing from CD4 Rest and from the extra source, and G09 is measured but not in the panel.
    Returns the paths."""
    rng = np.random.default_rng(seed)
    frac = rng.gamma(2.0, 1.0, len(GENES))
    frac /= frac.sum()
    targets = PANEL98 + ["G09"]
    response = {}
    for t in targets:
        r = np.zeros(len(GENES))
        others = rng.choice([i for i in range(len(GENES)) if GENES[i] != t], 12, replace=False)
        r[others] = rng.choice([-0.8, 0.8], 12)
        r[GENES.index(t)] = -1.5
        response[t] = r

    labels, means, cells = [], [], []
    for i in range(3):
        labels.append(f"{i}_non-targeting_x_y")
        means.append(5000 * frac * np.exp(rng.normal(0, 0.02, len(GENES))))
        cells.append(900)
    for i, t in enumerate(targets):
        for copy in range(2 if t == "G02" else 1):
            labels.append(f"{10 + 2 * i + copy}_{t}_P1P2_ENSG{i:05d}")
            means.append(5000 * frac * np.exp(response[t] + rng.normal(0, 0.05, len(GENES))))
            cells.append(int(rng.integers(150, 300)))
    bulk = root / "k562_bulk.h5ad"
    with h5py.File(bulk, "w") as f:
        f.create_dataset("X", data=np.asarray(means, dtype=np.float32))
        obs = f.create_group("obs")
        obs.create_dataset("gene_transcript", data=np.array(labels, dtype="S"))
        obs.create_dataset("num_cells_filtered", data=np.asarray(cells, dtype=np.float64))
        var = f.create_group("var")
        var.create_dataset("_index", data=np.array([f"ENSG{i:05d}" for i in range(len(GENES))], dtype="S"))
        var.create_dataset("gene_name", data=np.array(GENES, dtype="S"))

    def pseudobulk(path: Path, donors, conditions, lacking: dict) -> Path:
        import anndata as ad

        rows, obs = [], []
        for c_i, cond in enumerate(conditions):
            cond_scale = np.exp(rng.normal(0, 0.3, len(GENES)))
            for donor in donors:
                donor_scale = np.exp(rng.normal(0, 0.2, len(GENES)))
                for t in ["non-targeting"] + targets:
                    if t in lacking.get(cond, ()):
                        continue
                    n = 800.0 if t == "non-targeting" else float(rng.integers(60, 150))
                    if (donor, t) == (donors[0], "G05"):
                        n = 5.0                                       # under min_cells: that donor is skipped
                    effect = 0.0 if t == "non-targeting" else response[t] * (0.7 + 0.1 * c_i)
                    rows.append(rng.poisson(n * 2000 * frac * donor_scale * cond_scale * np.exp(effect)))
                    obs.append({"target": t, "donor": donor, "condition": cond, "n_cells": n})
        frame = pd.DataFrame(obs, index=[f"r{i}" for i in range(len(obs))])
        ad.AnnData(X=sp.csr_matrix(np.asarray(rows, dtype=np.float32)), obs=frame,
                   var=pd.DataFrame(index=pd.Index(GENES))).write_h5ad(path)
        return path

    cd4 = pseudobulk(root / "cd4_rows.h5ad", ["d1", "d2", "d3", "d4"], ["Rest", "Stim8hr", "Stim48hr"],
                     {"Rest": ("G06",)})
    extra = pseudobulk(root / "extra_rows.h5ad", ["b1", "b2", "b3"], ["pool"], {"pool": ("G06",)})
    panel = root / "pert_counts.csv"
    panel.write_text("target_gene\n" + "\n".join(PANEL98) + "\n", encoding="utf-8")
    per_context = root / "pert_counts_per_context.csv"
    per_context.write_text("context,target_gene,n_cells\n"
                           + "".join(f"{c},{t},400\n" for c in ("D", "E") for t in PANEL98), encoding="utf-8")
    return {"bulk": bulk, "cd4": cd4, "extra": extra, "panel": panel, "per_context": per_context}


def stage98_argv(inputs: dict, cache: Path, report: Path, panel: Path) -> list:
    return ["--k562-bulk", inputs["bulk"], "--cd4-rows", inputs["cd4"], "--targets-csv", panel,
            "--cache", cache, "--report-dir", report, "--extra", f"orion_x={inputs['extra']}"]


TABLES98 = ["cd4_Rest", "cd4_Stim48hr", "cd4_Stim8hr", "cd4_halfA", "cd4_halfB", "cd4_mix", "k562", "orion_x"]


class Stage98CacheManifestTests(unittest.TestCase):
    """Stage 98 writes a manifest naming its panel; its npz tables are what they were."""

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("98_multisource_effects.py", "stage98")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.inputs = write_stage98_inputs(cls.root)
        cls.cache = cls.root / "cache"
        cls.argv = stage98_argv(cls.inputs, cls.cache, cls.root / "report", cls.inputs["panel"])
        run_main(cls.stage, cls.argv, AXIS98)
        cls.manifest = json.loads((cls.cache / "manifest.json").read_text(encoding="utf-8"))
        cls.cache_ctx = cls.root / "cache_ctx"
        run_main(cls.stage, stage98_argv(cls.inputs, cls.cache_ctx, cls.root / "report_ctx",
                                         cls.inputs["per_context"]), AXIS98)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_cache_holds_its_tables_and_a_manifest_naming_its_panel(self):
        self.assertEqual(sorted(p.name for p in self.cache.iterdir()),
                         sorted([f"{n}.npz" for n in TABLES98] + ["manifest.json"]))
        m = self.manifest
        self.assertEqual(m["stage"], "98_multisource_effects")
        self.assertEqual(m["targets_sha256"], panel_sha256(PANEL98))
        self.assertEqual(m["targets"], panel_record(self.inputs["panel"], PANEL98))
        self.assertEqual(m["argv"][1:], [str(a) for a in self.argv])
        self.assertLessEqual(m["started_utc"], m["written_utc"])
        self.assertEqual(m["inputs"]["k562_bulk"]["sha256"], sha256(self.inputs["bulk"]))
        self.assertEqual(m["inputs"]["extra"]["orion_x"]["sha256"], sha256(self.inputs["extra"]))
        self.assertEqual((m["pseudo_scale"], m["min_expected"]), ("constant", 0.0))
        self.assertEqual(sorted(m["sources"]), TABLES98)
        for name, info in m["sources"].items():
            with self.subTest(source=name):
                targets = npz_arrays(self.cache / f"{name}.npz")["targets"].astype(str).tolist()
                self.assertEqual(info["targets"], len(targets))
                self.assertEqual(info["panel_targets_missing"], [t for t in PANEL98 if t not in targets])
                self.assertEqual((info["file"], info["sha256"]), (f"{name}.npz", sha256(self.cache / f"{name}.npz")))
        self.assertEqual(m["sources"]["cd4_Rest"]["panel_targets_missing"], ["G06"])
        self.assertEqual(m["sources"]["orion_x"]["panel_targets_missing"], ["G06"])
        self.assertEqual(m["sources"]["k562"]["panel_targets_missing"], [])

    def test_stage_100_verifies_the_cache_against_its_panel_and_refuses_another(self):
        stage100 = load_stage("100_build_context_effects.py", "stage100_for_98")
        tables = [stage100.load_table(self.cache, n) for n in ("k562", "cd4_mix", "orion_x")]
        check = stage100.check_cache_targets(self.cache, PANEL98, tables, False)
        self.assertTrue(check["targets_verified"])
        self.assertEqual(check["targets_covered"], 6)
        with self.assertRaises(SystemExit) as caught:
            stage100.check_cache_targets(self.cache, PANEL98 + ["G07"], tables, False)
        self.assertIn("built for other targets", str(caught.exception))

    def test_a_per_context_panel_file_gives_the_same_tables_and_panel_hash(self):
        for name in TABLES98:
            with self.subTest(source=name):
                a, b = npz_arrays(self.cache / f"{name}.npz"), npz_arrays(self.cache_ctx / f"{name}.npz")
                self.assertEqual(sorted(a), ["meta", "n_cells", "raw", "se", "shrunk", "targets"])
                self.assertEqual(sorted(a), sorted(b))
                for key in a:
                    self.assertEqual(a[key].dtype, b[key].dtype)
                    self.assertEqual(a[key].tobytes(), b[key].tobytes())
        other = json.loads((self.cache_ctx / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(other["targets_sha256"], self.manifest["targets_sha256"])
        self.assertNotEqual(other["targets"]["file_sha256"], self.manifest["targets"]["file_sha256"])

    def test_the_tables_are_what_the_library_computes_for_the_panel(self):
        k562 = self.stage.k562_table(self.inputs["bulk"], PANEL98, np.asarray(AXIS98))
        import anndata as ad
        extra = ad.read_h5ad(self.inputs["extra"])
        src = effects_from_pseudobulk(extra.X, extra.obs[["target", "donor", "condition", "n_cells"]].copy(),
                                      extra.var_names, targets=PANEL98, condition=None)
        orion = AxisTable.from_source("orion_x", src, np.asarray(AXIS98))
        for tab in (k562, orion):
            saved = npz_arrays(self.cache / f"{tab.name}.npz")
            with self.subTest(source=tab.name):
                self.assertEqual(saved["targets"].tolist(), tab.targets)
                for key in ("shrunk", "raw", "se", "n_cells"):
                    self.assertEqual(saved[key].tobytes(), np.asarray(getattr(tab, key)).tobytes())
                self.assertEqual(json.loads(str(saved["meta"])), json.loads(json.dumps(tab.meta, default=str)))
                self.assertEqual(np.asarray(saved["shrunk"]).shape, (len(tab.targets), len(AXIS98)))

    def test_a_panel_with_the_control_label_is_refused_before_anything_is_written(self):
        bad = self.root / "pert_counts_ntc.csv"
        bad.write_text("target_gene\nG01\nnon-targeting\n", encoding="utf-8")
        cache = self.root / "cache_ntc"
        with self.assertRaises(ValueError):
            run_main(self.stage, stage98_argv(self.inputs, cache, self.root / "report_ntc", bad), AXIS98)
        self.assertFalse(cache.exists())

    def test_an_existing_cache_is_refused(self):
        with self.assertRaises(FileExistsError):
            run_main(self.stage, stage98_argv(self.inputs, self.cache, self.root / "report_again",
                                              self.inputs["panel"]), AXIS98)


# --- stage 106 -------------------------------------------------------------------------------------

G = 12
AXIS106 = tuple(f"A{i}" for i in range(G))


def universe_table(targets: list[str], seed: int, width: int = G) -> dict:
    rng = np.random.default_rng(seed)
    n = len(targets)
    shrunk = rng.normal(size=(n, width)).astype(np.float32)
    raw = rng.normal(size=(n, width)).astype(np.float32)
    se = rng.uniform(0.1, 1, size=(n, width)).astype(np.float32)
    for a in (shrunk, raw, se):
        a[:, ::5] = np.nan                          # unmeasured genes stay NaN
    return {"targets": np.array(targets), "shrunk": shrunk, "raw": raw, "se": se,
            "n_cells": rng.integers(10, 500, size=n), "meta": json.dumps({"seed": seed})}


def rows_of(tables: list[dict], targets: list[str]) -> dict:
    both = {k: np.concatenate([t[k] for t in tables]) for k in ("targets", "shrunk", "raw", "se", "n_cells")}
    pos = {t: i for i, t in enumerate(both["targets"].astype(str))}
    sel = [pos[t] for t in targets]
    return {"targets": np.array(targets), **{k: both[k][sel] for k in ("shrunk", "raw", "se", "n_cells")},
            "meta": tables[0]["meta"]}


class Stage106AssembleTests(unittest.TestCase):
    """Stage 106 on synthetic universes in both index formats."""

    PANEL = ["T5", "T1", "T6", "T4", "T2"]       # the file below, read by read_panel: the second T5 dropped

    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage("106_assemble_panel_cache.py", "stage106")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        # file-named format (K562, Orion): two chunks, and a target without effects (empty chunk)
        cls.u1 = cls.root / "universe_named"
        cls.u1.mkdir()
        cls.c0, cls.c1 = universe_table(["T1", "T2", "T3"], 1), universe_table(["T4", "T5"], 2)
        np.savez_compressed(cls.u1 / "src_00.npz", **cls.c0)
        np.savez_compressed(cls.u1 / "src_01.npz", **cls.c1)
        pd.DataFrame({"target": ["T1", "T2", "T3", "T4", "T5", "T6"],
                      "chunk": ["src_00.npz"] * 3 + ["src_01.npz"] * 2 + [""],
                      "n_cells": [1] * 6}).to_csv(cls.u1 / "index.csv", index=False)
        # integer-group format (CD4): groups 0 and 1, two tables; cd4_Rest lacks T5 in group 1
        cls.u2 = cls.root / "universe_group"
        cls.u2.mkdir()
        cls.m0, cls.m1 = universe_table(["T2", "T4"], 3), universe_table(["T5", "T7"], 4)
        cls.r0, cls.r1 = universe_table(["T2", "T4"], 5), universe_table(["T7"], 6)
        for name, tab in (("cd4_mix_000", cls.m0), ("cd4_mix_001", cls.m1), ("cd4_Rest_000", cls.r0),
                          ("cd4_Rest_001", cls.r1)):
            np.savez_compressed(cls.u2 / f"{name}.npz", **tab)
        pd.DataFrame({"target": ["T2", "T4", "T5", "T7"], "chunk": [0, 0, 1, 1],
                      "n_cells": [1.0] * 4}).to_csv(cls.u2 / "index.csv", index=False)
        cls.targets = cls.root / "targets.csv"
        cls.targets.write_text("target_gene\nT5\nT1\nT6\nT4\nT2\nT5\n", encoding="utf-8")
        # a reference cache as stage 98 would have written it
        cls.ref = cls.root / "ref"
        cls.ref.mkdir()
        np.savez_compressed(cls.ref / "src.npz", **rows_of([cls.c0, cls.c1], ["T5", "T1", "T4", "T2"]))
        near = rows_of([cls.m0, cls.m1], ["T5", "T4", "T2"])
        near["shrunk"] = near["shrunk"].copy()
        near["shrunk"][0, 1] += np.float32(1e-8)    # within cd4_mix's tolerance
        np.savez_compressed(cls.ref / "cd4_mix.npz", **near)
        cls.out = cls.root / "cache"
        cls.report = cls.root / "parity.json"
        cls._run106(["--targets-csv", cls.targets, "--out", cls.out, "--source", f"src={cls.u1}",
                 "--source", f"cd4_mix={cls.u2}", "--source", f"cd4_Rest={cls.u2}", "--compare-to", cls.ref,
                 "--report-json", cls.report])
        cls.manifest = json.loads((cls.out / "manifest.json").read_text(encoding="utf-8"))

    @classmethod
    def _run106(cls, argv: list) -> str:
        return run_main(cls.stage, [*argv, "--reserve-gib", "0"], AXIS106)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_rows_are_copied_exactly_in_the_panel_order(self):
        z = npz_arrays(self.out / "src.npz")
        self.assertEqual(sorted(z), ["meta", "n_cells", "raw", "se", "shrunk", "targets"])
        self.assertEqual(z["targets"].tolist(), ["T5", "T1", "T4", "T2"])
        want = rows_of([self.c0, self.c1], ["T5", "T1", "T4", "T2"])
        for key in ("shrunk", "raw", "se", "n_cells"):
            self.assertEqual(z[key].dtype, want[key].dtype)
            self.assertEqual(z[key].tobytes(), want[key].tobytes())
        self.assertEqual(json.loads(str(z["meta"])), {"seed": 1})

    def test_the_group_format_and_a_table_lacking_a_listed_target(self):
        mix_ = npz_arrays(self.out / "cd4_mix.npz")
        self.assertEqual(mix_["targets"].tolist(), ["T5", "T4", "T2"])
        self.assertEqual(mix_["raw"].tobytes(), rows_of([self.m0, self.m1], ["T5", "T4", "T2"])["raw"].tobytes())
        rest = npz_arrays(self.out / "cd4_Rest.npz")
        self.assertEqual(rest["targets"].tolist(), ["T4", "T2"])
        self.assertEqual(rest["raw"].tobytes(), rows_of([self.r0], ["T4", "T2"])["raw"].tobytes())
        info = self.manifest["sources"]["cd4_Rest"]
        self.assertEqual(info["listed_in_index_but_absent_from_chunk"], ["T5"])
        self.assertEqual([c["file"] for c in info["chunks_read"]], ["cd4_Rest_000.npz", "cd4_Rest_001.npz"])

    def test_the_manifest_names_the_panel_the_files_and_what_is_missing(self):
        m = self.manifest
        self.assertEqual(m["stage"], "106_assemble_panel_cache")
        self.assertEqual(m["targets_sha256"], panel_sha256(self.PANEL))
        self.assertEqual(m["targets"], panel_record(self.targets, self.PANEL))
        self.assertEqual(m["sources"]["src"]["missing"], ["T6"])
        self.assertEqual(m["sources"]["cd4_mix"]["missing"], ["T1", "T6"])
        self.assertEqual(m["sources"]["src"]["index_sha256"], sha256(self.u1 / "index.csv"))
        for name in ("src", "cd4_mix", "cd4_Rest"):
            self.assertEqual(m["sources"][name]["sha256"], sha256(self.out / f"{name}.npz"))
        self.assertFalse(m["out_existed_empty"])
        self.assertIsNone(m["preset"])
        self.assertEqual(json.loads(self.report.read_text(encoding="utf-8")), m)
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ["cd4_Rest.npz", "cd4_mix.npz", "manifest.json", "src.npz"])

    def test_stage_100_verifies_the_assembled_cache(self):
        stage100 = load_stage("100_build_context_effects.py", "stage100_for_106")
        tables = [stage100.load_table(self.out, n) for n in ("src", "cd4_mix")]
        check = stage100.check_cache_targets(self.out, self.PANEL, tables, False)
        self.assertTrue(check["targets_verified"])
        self.assertEqual(check["targets_covered"], 4)
        with self.assertRaises(SystemExit):
            stage100.check_cache_targets(self.out, ["T1", "T2"], tables, False)

    def test_the_parity_rule(self):
        p = self.manifest["sources"]["src"]["parity"]
        self.assertTrue(p["rule_passed"])
        self.assertEqual((p["raw"]["max_abs_diff"], p["same_order"]), (0.0, True))
        m = self.manifest["sources"]["cd4_mix"]["parity"]
        self.assertTrue(m["rule_passed"])
        self.assertGreater(m["shrunk"]["max_abs_diff"], 0.0)
        self.assertEqual(self.manifest["sources"]["cd4_Rest"]["parity"],
                         {"reference": str(self.ref / "cd4_Rest.npz"), "missing": True})
        self.assertFalse(self.manifest["parity_rule_passed"])

    def test_parity_fails_above_the_tolerance_or_on_a_mask_change(self):
        bad = self.root / "bad.npz"
        z = npz_arrays(self.out / "src.npz")
        z["raw"] = z["raw"].copy()
        z["raw"][0, 1] += np.float32(1e-6)
        np.savez_compressed(bad, **z)
        self.assertFalse(self.stage.compare(bad, self.ref / "src.npz")["rule_passed"])
        z["raw"][0, 1] = np.nan
        np.savez_compressed(bad, **z)
        p = self.stage.compare(bad, self.ref / "src.npz")
        self.assertEqual(p["raw"]["finite_mask_mismatches"], 1)
        self.assertFalse(p["rule_passed"])

    def test_an_existing_output_is_refused_and_an_empty_folder_reused(self):
        with self.assertRaises(SystemExit):
            self._run106(["--targets-csv", self.targets, "--out", self.out, "--source", f"src={self.u1}"])
        empty = self.root / "left_empty"
        empty.mkdir()
        self._run106(["--targets-csv", self.targets, "--out", empty, "--source", f"src={self.u1}"])
        self.assertTrue(json.loads((empty / "manifest.json").read_text(encoding="utf-8"))["out_existed_empty"])

    def test_a_table_off_the_official_axis_is_refused(self):
        wide = self.root / "universe_wide"
        wide.mkdir()
        np.savez_compressed(wide / "src_00.npz", **universe_table(["T1", "T2"], 7, width=G + 1))
        pd.DataFrame({"target": ["T1", "T2"], "chunk": ["src_00.npz"] * 2}).to_csv(wide / "index.csv", index=False)
        with self.assertRaises(SystemExit) as caught:
            self._run106(["--targets-csv", self.targets, "--out", self.root / "wide", "--source", f"src={wide}"])
        self.assertIn("official axis", str(caught.exception))

    def test_the_sources_are_named_explicitly_and_a_preset_lives_under_the_data_root(self):
        with self.assertRaises(SystemExit):              # neither --preset nor --source
            with contextlib.redirect_stderr(io.StringIO()):
                self._run106(["--targets-csv", self.targets, "--out", self.root / "none"])
        with self.assertRaises(SystemExit):
            self.stage.parse_sources(["src=a", "src=b"], None)
        with mock.patch.object(self.stage, "DATA_ROOT", self.root):
            me1 = self.stage.parse_sources(None, "me1")
        self.assertEqual(sorted(me1), ["cd4_mix", "k562", "orion_hct116", "orion_hek293t"])
        self.assertEqual(me1["cd4_mix"], self.root / "processed" / "universe_cd4_2026-09-27_me1")


if __name__ == "__main__":
    unittest.main()
