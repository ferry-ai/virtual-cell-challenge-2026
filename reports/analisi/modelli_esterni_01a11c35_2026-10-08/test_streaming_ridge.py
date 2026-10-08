"""Synthetic numerical parity, bounded response reads and staging guards."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from chunk_store import build_store, load_store
from embedding_ridge import MaskedRidge
from embedding_ridge_streaming import StreamingMaskedRidge
from pie_adapter import sha256
from run_embedding_probe import run as run_dense
from run_streaming_probe import run as run_streaming


class BoundedColumns:
    """Fail if a fit tries to coerce the full responses or reads too many genes."""
    def __init__(self, array, maximum):
        self.array, self.maximum = array, maximum
        self.shape, self.dtype = array.shape, array.dtype
        self.reads = []

    def __array__(self, *args, **kwargs):
        raise AssertionError("full response materialization forbidden")

    def __getitem__(self, key):
        rows, columns = key
        if rows != slice(None) or not isinstance(columns, slice):
            raise AssertionError("expected a bounded column slice")
        start, stop, step = columns.indices(self.shape[1])
        if step != 1 or stop-start > self.maximum:
            raise AssertionError("oversized response read")
        self.reads.append((start, stop))
        return self.array[key]


class StreamingTests(unittest.TestCase):
    def arrays(self, n=12, d=4, g=9):
        rng = np.random.default_rng(991)
        x = rng.normal(size=(n,d))
        x[:, -1] = 2.0  # Constant feature exercises scaling protection.
        y = rng.normal(size=(n,g)).astype(np.float32)
        m = np.ones((n,g), bool)
        m[:2, 1::3] = False
        m[:, -1] = False
        y[~m] = np.nan
        weights = np.linspace(0.4, 2.3, n)
        policy = dict(row_contexts=["train"]*n, row_targets=[f"T{i}" for i in range(n)],
                      excluded_contexts=["held"], excluded_targets=["query"], sample_weight=weights)
        return x, y, m, policy

    def test_dense_equivalence_primal_dual_weighted_masks_and_bounded_reads(self):
        for n,d in ((12,4), (4,8)):
            with self.subTest(n=n, d=d):
                x,y,m,policy = self.arrays(n,d)
                reference = MaskedRidge(alpha=0.7).fit(x,y,m,**policy)
                source, masks = BoundedColumns(y,2), BoundedColumns(m,2)
                actual = StreamingMaskedRidge(alpha=0.7).fit(x,source,masks,**policy,gene_block=2)
                for name in ("coef", "intercept", "generic", "feature_mean", "feature_scale"):
                    np.testing.assert_allclose(getattr(actual,name),getattr(reference,name),rtol=1e-11,atol=1e-12)
                p, support = actual.predict(x)
                q, mask = reference.predict(x)
                np.testing.assert_allclose(p,q,rtol=1e-11,atol=1e-12,equal_nan=True)
                np.testing.assert_array_equal(support, mask)
                self.assertEqual(source.reads, [(0,2),(2,4),(4,6),(6,8),(8,9)])
                self.assertGreater(actual.receipt["cache_hits"], 0)
                self.assertEqual(actual.receipt["observed_per_gene"], reference.receipt["observed_per_gene"])

    def test_masked_values_exclusions_and_invalid_observed_values(self):
        x,y,m,policy = self.arrays()
        first = StreamingMaskedRidge().fit(x,y,m,**policy,gene_block=2)
        y[~m] = 1e30
        second = StreamingMaskedRidge().fit(x,y,m,**policy,gene_block=3,factor_cache=0)
        np.testing.assert_allclose(first.coef,second.coef,atol=1e-12)
        with self.assertRaisesRegex(ValueError,"excluded"):
            StreamingMaskedRidge().fit(x,y,m,**{**policy,"excluded_targets":["T0"]})
        y[0,0] = np.nan
        with self.assertRaisesRegex(ValueError,"nonfinite observed"):
            StreamingMaskedRidge().fit(x,y,m,**policy)

    def write_chunks(self, root):
        x,y,m,policy = self.arrays()
        genes = [f"g{i}" for i in range(y.shape[1])]
        identity = dict(study="synthetic", line_group="train", context="state1",
                        condition="toy", modality="CRISPRi", chemistry="toy")
        chunks = []
        for i,(start,stop) in enumerate(((0,5),(5,12))):
            path = root/f"chunk{i}.npz"
            ts = policy["row_targets"][start:stop]
            np.savez_compressed(path, genes=genes, targets=ts, shrunk=y[start:stop],
                                raw=y[start:stop], mask=m[start:stop],
                                n_cells=np.ones(stop-start), meta=json.dumps(identity))
            chunks.append(dict(path=path.name,sha256=sha256(path),context_id="study1",context_group="train",
                               targets=ts,weights=policy["sample_weight"][start:stop].tolist(),identity=identity))
        spec = dict(schema="external-ridge-chunks/1",modality="CRISPRi",validation_review="synthetic-test",
                    regime="J",release_sha256="a"*64,split_manifest_sha256="b"*64,
                    quantity="toy",normalization="toy",effect_field="shrunk",genes=genes,chunks=chunks,
                    excluded_contexts=["held"],excluded_targets=["query"],expected_rows_by_context={"study1":12})
        path=root/"chunks.json"; path.write_text(json.dumps(spec))
        return path,spec,x,y,m,policy

    def test_mmap_store_and_runner_match_dense_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path,spec,x,y,m,policy=self.write_chunks(root)
            store=root/"store"; build_store(path,store)
            yy,mm,axes,receipt=load_store(store,sha256(store/"manifest.json"))
            self.assertIsInstance(yy,np.memmap)
            self.assertTrue(yy.flags.f_contiguous)
            np.testing.assert_array_equal(yy,y)
            np.testing.assert_array_equal(mm,m)
            del yy,mm,axes,receipt
            features=root/"esm2";features.mkdir()
            meta=dict(name="esm2",layout="dense",index="pert",keys=policy["row_targets"]+["query"],
                      dim=x.shape[1],dtype="float32",provenance={"synthetic":True})
            (features/"meta.json").write_text(json.dumps(meta))
            np.save(features/"embeddings.npy",np.vstack((x,x[:1])).astype(np.float32))
            dense=root/"train.npz"
            np.savez(dense,targets=policy["row_targets"],context_ids=["study1"]*len(x),
                     context_groups=policy["row_contexts"],genes=spec["genes"],effects=y,observed=m,
                     weights=policy["sample_weight"])
            config=dict(schema_version=1,protocol_status="agreed",validation_review="synthetic-test",
                        mode="development",regime="J",modality="CRISPRi",quantity="toy",normalization="toy",
                        train=dict(path=str(dense),sha256=sha256(dense)),expected_rows_by_context={"study1":len(x)},
                        esm2=dict(path=str(features),sha256={n:sha256(features/n) for n in ("meta.json","embeddings.npy")}),
                        queries=[dict(context_id="held-study",context_group="held",target="query")],alpha=1.0,
                        excluded_contexts=["held"],excluded_targets=["query"],gene_block=2)
            conf=root/"fit.json";conf.write_text(json.dumps(config))
            run_dense(conf,root/"dense-output")
            config["train"]=dict(path=str(store),sha256=sha256(store/"manifest.json"))
            config.update(release_sha256="a"*64,split_manifest_sha256="b"*64,
                          validation_review=dict(status="reviewed",review_id="synthetic-test"))
            conf.write_text(json.dumps(config))
            result=run_streaming(conf,root/"stream-output")
            self.assertFalse(result["exposure"]["full_response_float64_materialized"])
            with np.load(root/"dense-output"/"native_predictions.npz") as a, np.load(root/"stream-output"/"native_predictions.npz") as b:
                np.testing.assert_allclose(a["effects"],b["effects"],rtol=1e-11,atol=1e-12,equal_nan=True)
                np.testing.assert_array_equal(a["observed"],b["observed"])
            config["regime"]="production"
            conf.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,"release/split"):
                run_streaming(conf,root/"wrong-regime")
            config["regime"]="J"
            config["validation_review"]["status"]="pending"
            conf.write_text(json.dumps(config))
            pending = run_streaming(conf,root/"pending-review")
            self.assertEqual(pending["scientific_benefit"],"not_scored")
            self.assertEqual(pending["manifest"]["validation_review"]["status"],"pending")
            with (store/"effects.npy").open("ab") as stream: stream.write(b"tamper")
            with self.assertRaisesRegex(ValueError,"checksum"):
                load_store(store,sha256(store/"manifest.json"))

    def test_chunk_hash_axis_identity_and_coverage_guards(self):
        for case in ("hash","axis","identity","coverage","duplicate","modality","chunk_bound"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);path,spec,*_=self.write_chunks(root)
                if case=="hash": spec["chunks"][0]["sha256"]="0"*64
                if case=="axis": spec["genes"]=list(reversed(spec["genes"]))
                if case=="identity":
                    for chunk in spec["chunks"]: chunk["identity"]["chemistry"]="different"
                if case=="coverage": spec["expected_rows_by_context"]["study1"]+=1
                if case=="duplicate": spec["chunks"][1]["targets"][0]=spec["chunks"][0]["targets"][0]
                if case=="modality": spec["modality"]="CRISPRko"
                if case=="chunk_bound": spec["max_chunk_rows"]=4
                path.write_text(json.dumps(spec))
                with self.assertRaises(ValueError): build_store(path,root/"store")
                self.assertFalse((root/"store"/"manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
