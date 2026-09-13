"""Parity between our streaming packager and the official `vcc prep`.

The claim under test is narrow and has to stay narrow: *for the inputs this
packager accepts, it accepts and rejects exactly what `vcc prep` does, and the
archive it writes decodes to the same prediction.* Anything weaker would make the
memory saving worthless, because a packager that is merely close is a packager
that ships a submission the server rejects.

So the fixtures are full-shape — 300 perturbations x 400 cells x 3 contexts,
18,533 genes, the real `gene_names.csv` and `pert_counts.csv` — with every
official limit left on. Only the density is synthetic: one stored value per cell
instead of ~6,000, which is what makes a 360,000-cell fixture cost seconds rather
than minutes. Density is the one property these tests do not exercise, and it is
exercised instead by the cap check and by the real run.

Each invalid fixture is derived from the valid one by changing the smallest thing
that breaks a single rule, and is asserted to be rejected by BOTH implementations.
A rejection that only we produce is as much a parity failure as one only prep
produces: the first would block a valid submission, the second would ship an
invalid one.

These are slow by the standards of this repo (tens of seconds). They are in their
own module for that reason.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vcc2026 import packaging as pk  # noqa: E402
from vcc2026.config import paths  # noqa: E402

CONTROLS = paths().raw / "controls"
GENES_CSV = CONTROLS / "gene_names.csv"
PERTS_CSV = CONTROLS / "pert_counts.csv"

HAVE_CONTROLS = GENES_CSV.exists() and PERTS_CSV.exists()
try:
    from vcc import prep as official_prep

    HAVE_CLI = True
except Exception:  # pragma: no cover - environment without the CLI
    HAVE_CLI = False

requires_env = unittest.skipUnless(
    HAVE_CONTROLS and HAVE_CLI,
    "needs the official controls bundle and an installed vcc-cli",
)

# Cells per perturbation is the official 400; the panel and gene axis come from
# the real files. Only `values per cell` is reduced.
CELLS_PER_PERT = 400
CONTEXTS = ("A", "B", "C")


def _genes() -> list[str]:
    return official_prep.read_gene_list(str(GENES_CSV))


def _panel() -> list[str]:
    frame = pd.read_csv(PERTS_CSV)
    return [str(g) for g in frame["target_gene"]]


def build_fixture(
    path: Path,
    *,
    genes: list[str],
    panel: list[str],
    contexts: tuple[str, ...] = CONTEXTS,
    cells_per_pert: int = CELLS_PER_PERT,
    values_per_cell: int = 1,
    seed: int = 7,
) -> Path:
    """A full-shape, low-density prediction that every official check passes.

    Values are >= 1 so no perturbation is all-zero, and each cell's total stays
    far under the per-cell cap.
    """
    rng = np.random.default_rng(seed)
    n_obs = len(panel) * cells_per_pert * len(contexts)
    n_vars = len(genes)

    labels = np.empty(n_obs, dtype=object)
    ctx_labels = np.empty(n_obs, dtype=object)
    i = 0
    for context in contexts:
        for target in panel:
            labels[i : i + cells_per_pert] = target
            ctx_labels[i : i + cells_per_pert] = context
            i += cells_per_pert

    nnz = n_obs * values_per_cell
    data = rng.integers(1, 50, size=nnz).astype(np.float32)
    indices = rng.integers(0, n_vars, size=nnz).astype(np.int32)
    indptr = (np.arange(n_obs + 1, dtype=np.int64) * values_per_cell)
    # Column indices must be sorted within a row for a canonical CSR.
    for start in range(0, n_obs, 20000):
        stop = min(start + 20000, n_obs)
        lo, hi = int(indptr[start]), int(indptr[stop])
        block = indices[lo:hi].reshape(stop - start, values_per_cell)
        block.sort(axis=1)
        indices[lo:hi] = block.reshape(-1)

    matrix = sp.csr_matrix((data, indices, indptr), shape=(n_obs, n_vars))
    obs = pd.DataFrame(
        {
            "target_gene": pd.Categorical(labels),
            "context": pd.Categorical(ctx_labels),
        },
        index=[f"{c}_{g}_{k:06d}" for k, (g, c) in enumerate(zip(labels, ctx_labels))],
    )

    import anndata as ad

    adata = ad.AnnData(X=matrix, obs=obs, var=pd.DataFrame(index=pd.Index(genes)))
    adata.write_h5ad(path)
    return path


def mutate(src: Path, dst: Path, *, obs_fn=None, x_fn=None, var_fn=None) -> Path:
    """Copy a fixture and apply one targeted change.

    Reads through AnnData: a fixture is a few tens of megabytes, so the cost of
    correctness here is irrelevant and the mutation reads like the rule it breaks.
    """
    import anndata as ad

    adata = ad.read_h5ad(src)
    if obs_fn is not None:
        adata.obs = obs_fn(adata.obs)
    if var_fn is not None:
        adata.var = var_fn(adata.var)
    if x_fn is not None:
        adata.X = x_fn(adata.X)
    adata.write_h5ad(dst)
    return dst


def run_official(input_path: Path, out: Path, **kwargs):
    return official_prep.run_prep(
        input_path=str(input_path),
        genes_path=str(GENES_CSV),
        perts_path=str(PERTS_CSV),
        output_path=str(out),
        cells_per_pert=CELLS_PER_PERT,
        **kwargs,
    )


def run_ours(input_path: Path, out: Path, **kwargs):
    return pk.package_prediction(
        input_path,
        out,
        genes_path=GENES_CSV,
        perts_path=PERTS_CSV,
        cells_per_pert=CELLS_PER_PERT,
        **kwargs,
    )


@requires_env
class TestValidFixtureParity(unittest.TestCase):
    """The accept path: same verdict, same prediction in the archive."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="vcc-parity-valid-"))
        cls.genes, cls.panel = _genes(), _panel()
        cls.fixture = build_fixture(
            cls.tmp / "valid.h5ad", genes=cls.genes, panel=cls.panel
        )
        cls.official_vcc = cls.tmp / "official.vcc"
        cls.official_result = run_official(cls.fixture, cls.official_vcc)
        cls.our_vcc = cls.tmp / "ours.vcc"
        cls.our_result = run_ours(cls.fixture, cls.our_vcc, workdir=cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_both_accept_the_same_shape(self):
        self.assertEqual(self.official_result.n_cells, self.our_result.n_obs)
        self.assertEqual(self.official_result.n_genes, self.our_result.n_vars)

    def test_both_report_the_same_stored_entry_count(self):
        self.assertEqual(self.official_result.nnz, self.our_result.nnz)

    def test_our_archive_passes_the_official_container_validator(self):
        from vcc import vccfile

        vccfile.validate_vcc(str(self.our_vcc))  # raises on failure

    def test_meta_sidecar_matches_the_official_one(self):
        from vcc import vccfile

        theirs = vccfile.read_vcc_meta(str(self.official_vcc))
        ours = vccfile.read_vcc_meta(str(self.our_vcc))
        self.assertEqual(theirs, ours)

    def test_nnz_recoverable_from_our_archive(self):
        from vcc import vccfile

        self.assertEqual(
            vccfile.nnz_from_vcc(str(self.our_vcc)), self.our_result.nnz
        )

    def test_payloads_are_equivalent(self):
        with pk.extracted_payload(self.official_vcc, self.tmp / "a") as a, \
                pk.extracted_payload(self.our_vcc, self.tmp / "b") as b:
            summary = pk.assert_payloads_equivalent(a, b)
        self.assertTrue(summary["equivalent"])
        self.assertEqual(summary["nnz"], self.our_result.nnz)

    def test_our_payload_preserves_the_input_matrix_exactly(self):
        import anndata as ad

        source = ad.read_h5ad(self.fixture)
        with pk.extracted_payload(self.our_vcc, self.tmp / "c") as payload:
            packed = ad.read_h5ad(payload)
            self.assertEqual(source.shape, packed.shape)
            np.testing.assert_array_equal(source.X.data, packed.X.data)
            np.testing.assert_array_equal(source.X.indices, packed.X.indices)
            np.testing.assert_array_equal(source.X.indptr, packed.X.indptr)
            self.assertEqual(
                list(source.var_names), list(packed.var_names)
            )
            np.testing.assert_array_equal(
                source.obs["target_gene"].astype(str).to_numpy(),
                packed.obs["target_gene"].astype(str).to_numpy(),
            )
            np.testing.assert_array_equal(
                source.obs["context"].astype(str).to_numpy(),
                packed.obs["context"].astype(str).to_numpy(),
            )

    def test_payload_hdf5_encodings_match_the_official_ones(self):
        # Comparing decoded values is not enough: obs columns first came out as
        # `nullable-string-array` here while prep wrote `categorical`, because
        # prep's frames pass through AnnData's constructor and ours did not. The
        # labels read back identical either way, so only an encoding-level check
        # catches it.
        def encodings(path):
            found = {}
            with h5py.File(path, "r") as f:
                def visit(name, obj):
                    enc = obj.attrs.get("encoding-type")
                    if enc is not None:
                        found[name] = (
                            enc.decode() if isinstance(enc, bytes) else str(enc)
                        )
                f.visititems(visit)
                found["/"] = str(f.attrs.get("encoding-type"))
            return found

        with pk.extracted_payload(self.official_vcc, self.tmp / "enc_a") as a,                 pk.extracted_payload(self.our_vcc, self.tmp / "enc_b") as b:
            theirs, ours = encodings(a), encodings(b)
        self.assertEqual(
            theirs, ours,
            "payload element encodings differ from the official ones",
        )

    def test_payload_dataset_dtypes_match_the_official_ones(self):
        def dtypes(path):
            found = {}
            with h5py.File(path, "r") as f:
                def visit(name, obj):
                    if isinstance(obj, h5py.Dataset):
                        found[name] = str(obj.dtype)
                f.visititems(visit)
            return found

        with pk.extracted_payload(self.official_vcc, self.tmp / "dt_a") as a,                 pk.extracted_payload(self.our_vcc, self.tmp / "dt_b") as b:
            theirs, ours = dtypes(a), dtypes(b)
        self.assertEqual(theirs, ours, "payload dataset dtypes differ")

    def test_archive_payload_matches_the_input_bit_for_bit(self):
        # The function the real run's verification phase depends on. It compares
        # the archive against the INPUT rather than against a re-derived payload,
        # so this is the test that it actually detects a difference rather than
        # comparing the writer with itself.
        with pk.extracted_payload(self.our_vcc, self.tmp / "e") as payload:
            summary = pk.assert_payload_matches_input(self.fixture, payload)
        self.assertTrue(summary["matches_input"])
        self.assertTrue(summary["x_arrays_bit_identical"])
        self.assertTrue(summary["obs_index_rewritten"])
        self.assertEqual(summary["nnz"], self.our_result.nnz)

    def test_the_input_comparison_fails_on_a_changed_value(self):
        # A verification that cannot fail verifies nothing.
        tampered = self.tmp / "tampered.payload.h5ad"
        pk.write_payload(self.fixture, tampered)
        with h5py.File(tampered, "r+") as f:
            f["X/data"][0] = float(f["X/data"][0]) + 1.0
        with self.assertRaises(AssertionError) as ctx:
            pk.assert_payload_matches_input(self.fixture, tampered)
        self.assertIn("stored values differ", str(ctx.exception))
        tampered.unlink()

    def test_the_input_comparison_fails_on_a_changed_label(self):
        tampered = self.tmp / "relabelled.payload.h5ad"
        pk.write_payload(self.fixture, tampered)
        with h5py.File(tampered, "r+") as f:
            codes = f["obs/target_gene/codes"]
            codes[0] = (int(codes[0]) + 1) % f["obs/target_gene/categories"].shape[0]
        with self.assertRaises(AssertionError) as ctx:
            pk.assert_payload_matches_input(self.fixture, tampered)
        self.assertIn("target_gene", str(ctx.exception))
        tampered.unlink()

    def test_documented_transformations_are_the_ones_observed(self):
        import anndata as ad

        source = ad.read_h5ad(self.fixture)
        with pk.extracted_payload(self.our_vcc, self.tmp / "d") as payload:
            packed = ad.read_h5ad(payload)
        # The obs index IS rewritten, and that is transformation #1.
        self.assertNotEqual(list(source.obs.index[:3]), list(packed.obs.index[:3]))
        self.assertEqual(list(packed.obs.index[:3]), ["0", "1", "2"])
        self.assertEqual(list(packed.obs.columns), ["target_gene", "context"])
        self.assertEqual(list(packed.var.columns), [])
        self.assertTrue(
            any("obs index replaced" in t for t in pk.payload_transformations())
        )

    def test_validation_report_is_clean_and_specific(self):
        report = self.our_result.validation
        self.assertTrue(report.ok, report.failures)
        self.assertEqual(report.cells_per_context, {"A": 120000, "B": 120000,
                                                    "C": 120000})
        self.assertEqual(
            report.n_targets_per_context,
            {c: len(self.panel) for c in CONTEXTS},
        )
        self.assertTrue(all(report.csr_checks.values()), report.csr_checks)
        self.assertTrue(all(report.checks.values()), report.checks)

    def test_peak_memory_is_bounded_far_below_the_matrix(self):
        # The fixture is small, so this only proves the packager does not read
        # the matrix whole; the real bound is measured on the real prediction.
        peak = self.our_result.peak_rss_bytes
        if peak is None:
            self.skipTest("peak RSS unavailable on this platform")
        self.assertLess(peak, 3 * 1024**3)


@requires_env
class TestRejectionParity(unittest.TestCase):
    """The reject path: every rule, refused by both, for the same reason."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="vcc-parity-bad-"))
        cls.genes, cls.panel = _genes(), _panel()
        cls.valid = build_fixture(
            cls.tmp / "valid.h5ad", genes=cls.genes, panel=cls.panel
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def assert_both_reject(self, bad: Path, *, needle: str | None = None, **kwargs):
        """Both implementations must refuse `bad`, and nothing may be written."""
        out_official = self.tmp / f"{bad.stem}.official.vcc"
        with self.assertRaises(official_prep.PrepError, msg="official accepted it") as o:
            run_official(bad, out_official, **kwargs)
        out_ours = self.tmp / f"{bad.stem}.ours.vcc"
        with self.assertRaises(pk.PackagingError, msg="we accepted it") as m:
            run_ours(bad, out_ours, workdir=self.tmp, **kwargs)
        self.assertFalse(out_ours.exists(), "we wrote an archive for invalid input")
        if needle:
            self.assertIn(needle.lower(), str(m.exception).lower())
        return str(o.exception), str(m.exception)

    def test_fractional_counts(self):
        bad = mutate(
            self.valid, self.tmp / "fractional.h5ad",
            x_fn=lambda X: X.multiply(1.5).tocsr().astype(np.float32),
        )
        self.assert_both_reject(bad, needle="fractional")

    def test_negative_counts(self):
        def flip(X):
            X = X.tocsr().copy()
            X.data[0] = -5.0
            return X

        bad = mutate(self.valid, self.tmp / "negative.h5ad", x_fn=flip)
        self.assert_both_reject(bad, needle="negative")

    def test_non_finite_counts(self):
        def poison(X):
            X = X.tocsr().copy()
            X.data[5] = np.nan
            return X

        bad = mutate(self.valid, self.tmp / "nonfinite.h5ad", x_fn=poison)
        self.assert_both_reject(bad, needle="non-finite")

    def test_missing_context(self):
        def drop_c(obs):
            obs = obs.copy()
            ctx = obs["context"].astype(str)
            obs["context"] = pd.Categorical(np.where(ctx == "C", "B", ctx))
            return obs

        bad = mutate(self.valid, self.tmp / "missing_ctx.h5ad", obs_fn=drop_c)
        self.assert_both_reject(bad, needle="context")

    def test_unknown_context_label(self):
        def relabel(obs):
            obs = obs.copy()
            ctx = obs["context"].astype(str).to_numpy()
            ctx[:10] = "Z"
            obs["context"] = pd.Categorical(ctx)
            return obs

        bad = mutate(self.valid, self.tmp / "unknown_ctx.h5ad", obs_fn=relabel)
        self.assert_both_reject(bad, needle="context")

    def test_missing_target(self):
        def drop_target(obs):
            obs = obs.copy()
            labels = obs["target_gene"].astype(str).to_numpy()
            labels[labels == labels[0]] = labels[-1]
            obs["target_gene"] = pd.Categorical(labels)
            return obs

        bad = mutate(self.valid, self.tmp / "missing_target.h5ad", obs_fn=drop_target)
        self.assert_both_reject(bad, needle="perturbation")

    def test_unexpected_target_label(self):
        def add_bogus(obs):
            obs = obs.copy()
            labels = obs["target_gene"].astype(str).to_numpy()
            labels[:CELLS_PER_PERT] = "NOT_A_PANEL_GENE"
            obs["target_gene"] = pd.Categorical(labels)
            return obs

        bad = mutate(self.valid, self.tmp / "bogus_target.h5ad", obs_fn=add_bogus)
        self.assert_both_reject(bad, needle="perturbation")

    def test_wrong_cells_per_perturbation(self):
        # Move one cell from the first target to the second, in context A only.
        def shift(obs):
            obs = obs.copy()
            labels = obs["target_gene"].astype(str).to_numpy()
            labels[0] = labels[CELLS_PER_PERT]
            obs["target_gene"] = pd.Categorical(labels)
            return obs

        bad = mutate(self.valid, self.tmp / "wrong_counts.h5ad", obs_fn=shift)
        self.assert_both_reject(bad, needle="cells")

    def test_control_rows_present(self):
        def add_controls(obs):
            obs = obs.copy()
            labels = obs["target_gene"].astype(str).to_numpy()
            labels[:5] = "non-targeting"
            obs["target_gene"] = pd.Categorical(labels)
            return obs

        bad = mutate(self.valid, self.tmp / "controls.h5ad", obs_fn=add_controls)
        self.assert_both_reject(bad, needle="control")

    def test_all_zero_perturbation(self):
        # The official check is over the WHOLE matrix, not per context: a target
        # zeroed in one context only still has nonzero cells elsewhere and is not
        # "all-zero". Verified against prep, which accepts that case — so the
        # fixture has to zero the target in all three contexts to break the rule
        # the check actually states.
        target = self.panel[0]

        def zero_target(X):
            X = X.tocsr().copy()
            import anndata as ad

            labels = ad.read_h5ad(self.valid).obs["target_gene"].astype(str).to_numpy()
            rows = np.flatnonzero(labels == target)
            for r in rows:
                X.data[X.indptr[r] : X.indptr[r + 1]] = 0.0
            X.eliminate_zeros()
            return X

        bad = mutate(self.valid, self.tmp / "empty_pert.h5ad", x_fn=zero_target)
        _official_msg, ours = self.assert_both_reject(bad, needle="all-zero")
        self.assertIn(target.lower(), ours.lower())

    def test_a_target_zeroed_in_one_context_only_is_accepted_by_both(self):
        # The boundary of the rule above, and the reason it is worth a test: this
        # is a real prediction shape (a model that produced nothing for one
        # context) and BOTH implementations must let it through, or we would
        # block a submission prep accepts.
        def zero_first_block(X):
            X = X.tocsr().copy()
            X.data[: CELLS_PER_PERT] = 0.0
            X.eliminate_zeros()
            return X

        edge = mutate(self.valid, self.tmp / "one_ctx_zero.h5ad", x_fn=zero_first_block)
        run_official(edge, self.tmp / "one_ctx_zero.official.vcc")
        out = self.tmp / "one_ctx_zero.ours.vcc"
        result = run_ours(edge, out, workdir=self.tmp)
        self.assertTrue(result.validation.ok, result.validation.failures)
        self.assertTrue(out.exists())

    def test_wrong_gene_set(self):
        def rename(var):
            var = var.copy()
            names = list(var.index)
            names[0] = "NOT_A_REAL_GENE"
            var.index = pd.Index(names)
            return var

        bad = mutate(self.valid, self.tmp / "wrong_genes.h5ad", var_fn=rename)
        self.assert_both_reject(bad, needle="gene")

    def test_missing_perturbation_column(self):
        def drop_col(obs):
            return obs.drop(columns=["target_gene"])

        bad = mutate(self.valid, self.tmp / "no_pert_col.h5ad", obs_fn=drop_col)
        self.assert_both_reject(bad, needle="target_gene")

    def test_missing_context_column(self):
        def drop_col(obs):
            return obs.drop(columns=["context"])

        bad = mutate(self.valid, self.tmp / "no_ctx_col.h5ad", obs_fn=drop_col)
        self.assert_both_reject(bad, needle="context")

    def test_per_cell_count_cap(self):
        # One cell just over the cap; the bound is strict, so exactly-at-cap passes.
        def blow_up(X):
            X = X.tocsr().copy()
            X.data[0] = 1_000_001.0
            return X

        bad = mutate(self.valid, self.tmp / "too_many_counts.h5ad", x_fn=blow_up)
        self.assert_both_reject(bad, needle="above the maximum")

    def test_a_cell_exactly_at_the_cap_is_accepted_by_both(self):
        # Boundary: prep's check is `> cap`, so the cap itself is legal. Both
        # implementations must agree, or a legitimate submission gets blocked.
        def at_cap(X):
            X = X.tocsr().copy()
            X.data[0] = 1_000_000.0
            return X

        edge = mutate(self.valid, self.tmp / "at_cap.h5ad", x_fn=at_cap)
        official_out = self.tmp / "at_cap.official.vcc"
        run_official(edge, official_out)
        ours_out = self.tmp / "at_cap.ours.vcc"
        result = run_ours(edge, ours_out, workdir=self.tmp)
        self.assertTrue(result.validation.ok, result.validation.failures)
        self.assertTrue(ours_out.exists())


@requires_env
class TestCsrIntegrity(unittest.TestCase):
    """Structural damage official prep never sees, because scipy rebuilds for it.

    These matter precisely because this packager copies the arrays instead of
    rebuilding them: a corrupt offset array would otherwise be carried into the
    archive intact.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="vcc-parity-csr-"))
        cls.genes, cls.panel = _genes(), _panel()
        cls.valid = build_fixture(
            cls.tmp / "valid.h5ad", genes=cls.genes, panel=cls.panel
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _damaged(self, name: str, fn) -> Path:
        dst = self.tmp / name
        shutil.copy2(self.valid, dst)
        with h5py.File(dst, "r+") as f:
            fn(f)
        return dst

    def _report(self, path: Path):
        return pk.validate_prediction(
            path, genes_path=GENES_CSV, perts_path=PERTS_CSV,
            cells_per_pert=CELLS_PER_PERT,
        )

    def test_non_monotonic_indptr_is_caught(self):
        def damage(f):
            ptr = f["X/indptr"]
            ptr[5] = int(ptr[9])

        report = self._report(self._damaged("nonmono.h5ad", damage))
        self.assertFalse(report.ok)
        self.assertFalse(report.csr_checks["indptr_monotonic"])

    def test_indptr_length_mismatch_is_caught(self):
        def damage(f):
            data = f["X/indptr"][:-1]
            del f["X/indptr"]
            f["X"].create_dataset("indptr", data=data)

        report = self._report(self._damaged("shortptr.h5ad", damage))
        self.assertFalse(report.ok)
        self.assertFalse(report.csr_checks["indptr_length_is_n_obs_plus_1"])

    def test_indptr_not_matching_data_length_is_caught(self):
        def damage(f):
            ptr = f["X/indptr"]
            ptr[-1] = int(ptr[-1]) + 7

        report = self._report(self._damaged("ptrend.h5ad", damage))
        self.assertFalse(report.ok)
        self.assertFalse(report.csr_checks["indptr_end_matches_data_length"])

    def test_out_of_range_column_index_is_caught(self):
        def damage(f):
            idx = f["X/indices"]
            idx[0] = 10**6

        report = self._report(self._damaged("badcol.h5ad", damage))
        self.assertFalse(report.ok)
        self.assertFalse(report.checks["column_indices_in_range"])

    def test_negative_offset_from_a_wrapped_indptr_is_caught(self):
        def damage(f):
            ptr = f["X/indptr"]
            ptr[3] = -1

        report = self._report(self._damaged("wrapped.h5ad", damage))
        self.assertFalse(report.ok)
        self.assertFalse(report.csr_checks["indptr_non_negative"])

    def test_a_clean_fixture_passes_every_csr_check(self):
        report = self._report(self.valid)
        self.assertTrue(report.ok, report.failures)
        self.assertTrue(all(report.csr_checks.values()))


@requires_env
class TestUnsupportedLayoutsAreRefused(unittest.TestCase):
    """Refused explicitly, never approximated."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="vcc-parity-layout-"))
        cls.genes, cls.panel = _genes(), _panel()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _tiny(self, name: str, **kw) -> Path:
        """A small, structurally complete file; these tests never reach the
        panel checks, so the shape does not have to be official."""
        import anndata as ad

        n_obs, n_vars = 6, len(self.genes)
        matrix = sp.csr_matrix(
            (np.ones(n_obs, dtype=kw.get("dtype", np.float32)),
             np.arange(n_obs, dtype=np.int32),
             np.arange(n_obs + 1, dtype=np.int64)),
            shape=(n_obs, n_vars),
        )
        if kw.get("csc"):
            matrix = matrix.tocsc()
        if kw.get("dense"):
            matrix = np.asarray(matrix.todense())
        obs = pd.DataFrame(
            {"target_gene": pd.Categorical(["AAA"] * n_obs),
             "context": pd.Categorical(["A"] * n_obs)}
        )
        genes = list(self.genes)
        if kw.get("shuffle_genes"):
            genes = genes[1:] + genes[:1]
        adata = ad.AnnData(X=matrix, obs=obs, var=pd.DataFrame(index=pd.Index(genes)))
        path = self.tmp / name
        adata.write_h5ad(path)
        return path

    def test_dense_matrix_is_refused_with_a_reason(self):
        path = self._tiny("dense.h5ad", dense=True)
        with self.assertRaises(pk.PackagingError) as ctx:
            pk.inspect_layout(path)
        self.assertIn("dense", str(ctx.exception).lower())
        self.assertIn("vcc prep", str(ctx.exception))

    def test_csc_matrix_is_refused_with_a_reason(self):
        path = self._tiny("csc.h5ad", csc=True)
        with self.assertRaises(pk.PackagingError) as ctx:
            pk.inspect_layout(path)
        self.assertIn("csr", str(ctx.exception).lower())

    def test_float64_matrix_is_refused_rather_than_cast(self):
        path = self._tiny("f64.h5ad", dtype=np.float64)
        with self.assertRaises(pk.PackagingError) as ctx:
            pk.inspect_layout(path)
        self.assertIn("float32", str(ctx.exception))

    def test_genes_out_of_order_are_refused_not_reordered(self):
        path = self._tiny("shuffled.h5ad", shuffle_genes=True)
        report = pk.validate_prediction(
            path, genes_path=GENES_CSV, perts_path=PERTS_CSV,
            cells_per_pert=CELLS_PER_PERT,
        )
        self.assertFalse(report.ok)
        self.assertTrue(
            any("OUT OF ORDER" in f for f in report.failures), report.failures
        )

    def test_missing_file_is_refused(self):
        with self.assertRaises(pk.PackagingError):
            pk.inspect_layout(self.tmp / "nope.h5ad")


class TestRowBlocking(unittest.TestCase):
    """The block walker, which every streamed pass depends on."""

    def test_blocks_cover_every_row_exactly_once(self):
        indptr = np.cumsum(np.concatenate([[0], np.full(50, 7)])).astype(np.int64)
        blocks = list(pk._row_blocks(indptr, values_per_block=20))
        self.assertEqual(blocks[0][0], 0)
        self.assertEqual(blocks[-1][1], 50)
        for (a, b), (c, _d) in zip(blocks, blocks[1:]):
            self.assertLess(a, b)
            self.assertEqual(b, c)

    def test_a_row_wider_than_the_budget_still_gets_a_block(self):
        indptr = np.array([0, 100, 101], dtype=np.int64)
        blocks = list(pk._row_blocks(indptr, values_per_block=10))
        self.assertEqual(blocks, [(0, 1), (1, 2)])

    def test_empty_matrix_yields_no_blocks(self):
        self.assertEqual(list(pk._row_blocks(np.array([0], dtype=np.int64), 10)), [])

    def test_transformations_are_documented(self):
        transformations = pk.payload_transformations()
        self.assertGreaterEqual(len(transformations), 4)
        self.assertTrue(all(isinstance(t, str) and t for t in transformations))


if __name__ == "__main__":
    unittest.main()
