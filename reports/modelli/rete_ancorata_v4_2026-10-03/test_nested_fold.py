"""The samples and the caps of a fold depend only on that fold's training data (CAMPIONI_ANNIDATI.md §10).

A synthetic corpus with a training line K (24 trained targets and one hidden target, GH) and a held-out line (context
La, group LINE: five of the targets and GH). Three variants, each through prepass -> twins -> nested_samples.py
(--classes train, the default) -> nested_rule.decide:
- base;
- excluded responses changed: two genes' counts swapped in every perturbed cell of the held-out line and in the cells
  of the hidden target of the training line (library size, genes detected and mitochondrial share stay the same, so
  quality control admits the same cells);
- allowed responses changed (the positive control): the trained targets of the training line lose their effect.

Asserted: base and "excluded changed" give the same groups table (the summaries the choice reads, generic response
included), the same statuses and recommended levels, and the same level and inclusion probability for every cell;
neither the held-out line nor the hidden target has a row in the table or a sampled cell. The positive control changes
the table and the recommended level: the procedure does react to the data it is allowed to read. With --classes all
(the exploratory mode) the excluded cells are in the table and changing them changes it: the leak the default closes.

    python -m unittest test_nested_fold -v      (from this folder, with the project venv; a few minutes)
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
import nested_rule as NR  # noqa: E402
from fixtures import GENES, counts, key_in_fold, make_twins  # noqa: E402
from test_nested_samples import write_shard  # noqa: E402

CAPS = [4, 8, 16]
TARGETS = [f"T{t}" for t in range(24)]
SWAP = (5, 20)


def build(root: Path, variant: str):
    """Shards of one variant in root/shards; the same random draws for every variant, changed afterwards."""
    rng = np.random.default_rng(7)
    p = rng.dirichlet(np.ones(len(GENES)) * 2)
    p[-4:] = 0.0075
    p /= p.sum()
    effect = {}
    for s in TARGETS + ["GH"]:
        q = p.copy()
        q[:-4] *= np.exp(rng.normal(0, 0.8, len(GENES) - 4))
        effect[s] = q / q.sum()
    sh = root / "shards"
    sh.mkdir(parents=True)
    other = np.random.default_rng(99)

    def swap(x, rows):
        a, b = SWAP
        x[np.ix_(rows, [a, b])] = x[np.ix_(rows, [b, a])]

    for i in range(2):                                   # the training line: 60 controls, 20 cells per target
        t = ["NTC"] * 60
        g = ["NTC"] * 60
        blocks = [counts(rng, p, 60)]
        for s in TARGETS + ["GH"]:
            t += [s] * 20
            g += [f"{s}_g{j % 2}" for j in range(20)]
            blocks.append(counts(rng, effect[s], 20))
        x = np.vstack(blocks)
        t = np.array(t, dtype=object)
        if variant == "excluded":
            swap(x, np.flatnonzero(t == "GH"))
        if variant == "allowed":
            rows = np.flatnonzero(np.isin(t, TARGETS))
            x[rows] = counts(other, p, rows.size)
        write_shard(sh / f"sk_{i}.h5ad", x, "sk", "K", f"K{i}", t, g, [f"K{i}_{j}-1" for j in range(len(t))],
                    "file://sk")
    t = ["NTC"] * 80                                     # the held-out line
    g = ["NTC"] * 80
    blocks = [counts(rng, p, 80)]
    for s in TARGETS[:5] + ["GH"]:
        t += [s] * 30
        g += [f"{s}_g0"] * 30
        blocks.append(counts(rng, effect[s], 30))
    x = np.vstack(blocks)
    t = np.array(t, dtype=object)
    if variant == "excluded":
        swap(x, np.flatnonzero(t != "NTC"))
    write_shard(sh / "sa.h5ad", x, "sa", "La", "A1", t, g, [f"A{j}-1" for j in range(len(t))], "file://sa")
    (root / "axis.csv").write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
    keys = {s: key_in_fold(s, 0, want=(s == "GH")) for s in TARGETS + ["GH"]}
    (root / "keys.json").write_text(json.dumps(keys), encoding="utf-8")
    (root / "groups.json").write_text(json.dumps({"contexts": {"La": "LINE"}}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(HERE / "train_cellnet.py"), "prepass", "--shards", str(sh), "--axis",
                        str(root / "axis.csv"), "--line-groups", str(root / "groups.json"), "--holdout-group", "LINE",
                        "--hidden-fold", "0", "--target-keys", str(root / "keys.json"), "--pool-size", "48",
                        "--ctrl-k", "16", "--input-genes", "16", "--eval-min-cells", "10",
                        "--min-controls-per-key", "20", "--out", str(root / "pre")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    make_twins(sh, root / "twins")


def study(root: Path, classes: str):
    out = root / f"out_{classes}"
    r = subprocess.run([sys.executable, str(HERE / "nested_samples.py"), "--prepass", str(root / "pre"),
                        "--shard-roots", str(root / "shards"), "--fast-roots", str(root / "twins"), "--caps",
                        *map(str, CAPS), "--classes", classes, "--dispersion", "--out", str(out), "--workers", "1"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    df = pd.read_csv(out / "groups.csv.gz")
    sel = {}
    for f in sorted((out / "selection").glob("*.npz")):
        with np.load(f) as z:
            sel[f.name] = (z["level"].copy(), z["prob"].copy())
    return df, sel, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


class FoldOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.out = {}
        for variant in ("base", "excluded", "allowed"):
            build(d / variant, variant)
            cls.out[variant] = study(d / variant, "train")
        cls.all_base = study(d / "base", "all")
        cls.all_excluded = study(d / "excluded", "all")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_excluded_responses_change_nothing(self):
        (a, sel_a, man_a), (b, sel_b, _) = self.out["base"], self.out["excluded"]
        pd.testing.assert_frame_equal(a, b)                            # the summaries the choice reads
        self.assertEqual(NR.decide(a, CAPS), NR.decide(b, CAPS))       # statuses and recommended levels
        self.assertEqual(sorted(sel_a), sorted(sel_b))
        for name in sel_a:                                             # the training samples
            np.testing.assert_array_equal(sel_a[name][0], sel_b[name][0])
            np.testing.assert_array_equal(sel_a[name][1], sel_b[name][1])
        self.assertEqual(man_a["classes"], "train")

    def test_excluded_cells_are_not_read(self):
        df, sel, _ = self.out["base"]
        self.assertEqual(set(df["key"]), {"sk|K"})
        self.assertNotIn("GH", set(df["target"]))
        self.assertEqual(len(df), len(TARGETS))
        self.assertEqual(int(sel["sa.h5ad.npz"][0].sum()), 0)          # no cell of the held-out line is sampled
        self.assertEqual(int((sel["sk_0.h5ad.npz"][0] > 0).sum()), 20 * len(TARGETS))   # nor of the hidden target

    def test_allowed_responses_change_the_choice(self):
        a, c = self.out["base"][0], self.out["allowed"][0]
        self.assertFalse(a["r_spec_halves"].round(6).equals(c["r_spec_halves"].round(6)))
        da, dc = NR.decide(a, CAPS)["units"], NR.decide(c, CAPS)["units"]
        self.assertEqual(list(da), list(dc))
        unit = list(da)[0]
        self.assertEqual(da[unit]["recommended"]["why"], "sufficient")
        self.assertNotEqual(da[unit]["recommended"], dc[unit]["recommended"])

    def test_exploratory_mode_reads_them(self):
        a, b = self.all_base[0], self.all_excluded[0]
        self.assertIn("sa|La", set(a["key"]))
        self.assertIn("GH", set(a["target"]))
        self.assertFalse(a.round(6).equals(b.round(6)))                # the leak the default closes
        self.assertEqual(self.all_base[2]["classes"], "all")

    def test_dispersion_columns(self):
        df = self.out["base"][0]
        for c in CAPS:
            self.assertIn(f"var_r_{c}", df.columns)
            self.assertTrue((df[f"zero_mad_{c}"].dropna() >= 0).all())


if __name__ == "__main__":
    unittest.main()
