"""Small exactness fixtures with repeated targets, distinct contexts and masks."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from chunk_store import build_store
from embedding_ridge import MaskedRidge
from pie_adapter import sha256
from target_sufficient_ridge import TargetSufficientRidge
from run_sufficient_probe import run as run_sufficient
from run_embedding_probe import run as run_dense


class BoundedMatrix:
    def __init__(self,array,row_bound,gene_bound):
        self.array,self.shape,self.dtype=array,array.shape,array.dtype
        self.row_bound,self.gene_bound=row_bound,gene_bound
        self.reads=0

    def __array__(self,*args,**kwargs):
        raise AssertionError("whole response conversion forbidden")

    def __getitem__(self,key):
        r,c=key
        if not isinstance(r,slice) or not isinstance(c,slice):
            raise AssertionError("bounded row/column slices required")
        rs,re,rr=r.indices(self.shape[0]); cs,ce,cr=c.indices(self.shape[1])
        if rr!=1 or cr!=1 or re-rs>self.row_bound or ce-cs>self.gene_bound:
            raise AssertionError("response block exceeds bounds")
        self.reads+=1
        return self.array[key]


class SufficientTests(unittest.TestCase):
    errors=[]

    def fixture(self,d=3):
        rng=np.random.default_rng(816)
        feature_targets=["A","B","C","D"]
        x=rng.normal(size=(4,d)); x[:,-1]=2.0
        index=np.array([0,1,2,3,0,1,2,3,0,1,2,3],dtype=np.int64)
        targets=[feature_targets[i] for i in index]
        contexts=[f"study{i//4}" for i in range(12)]
        y=rng.normal(size=(12,7)).astype(np.float32)
        m=np.ones(y.shape,dtype=bool)
        m[[0,5,9],1]=False; m[:4,2]=False; m[[2,6,10],3]=False
        m[:,5]=False; m[:,6]=False; m[7,6]=True
        y[~m]=np.nan
        policy=dict(row_contexts=contexts,row_targets=targets,excluded_contexts=["held"],
                    excluded_targets=["query"],sample_weight=np.array([1.,3.,2.,4.,0.2,5.,2.,1.,7.,0.1,8.,6.]))
        return x,index,feature_targets,y,m,policy

    def fit_reduced(self,x,index,feature_targets,y,m,policy,**kwargs):
        return TargetSufficientRidge(alpha=0.7).fit(x,y,m,feature_targets=feature_targets,
            row_feature_indices=index,**policy,**kwargs)

    def test_dense_and_independent_least_squares_parity_with_repeated_targets(self):
        for d in (3,8):
            x,index,names,y,m,policy=self.fixture(d)
            dense=MaskedRidge(alpha=0.7).fit(x[index],y,m,**policy)
            by,bm=BoundedMatrix(y,3,2),BoundedMatrix(m,3,2)
            reduced=self.fit_reduced(x,index,names,by,bm,policy,row_block=3,gene_block=2)
            for field in ("coef","intercept","generic","feature_mean","feature_scale"):
                np.testing.assert_allclose(getattr(reduced,field),getattr(dense,field),rtol=1e-10,atol=1e-11)
            prediction,support=reduced.predict(x)
            reference,expected=dense.predict(x)
            self.errors.append(float(np.max(np.abs(prediction[support]-reference[support]))))
            np.testing.assert_allclose(prediction,reference,rtol=1e-10,atol=1e-11,equal_nan=True)
            np.testing.assert_array_equal(support,expected)
            self.assertEqual(reduced.receipt["rows_read"],12)
            self.assertEqual(reduced.receipt["rows_by_context_group"],{"study0":4,"study1":4,"study2":4})
            self.assertEqual(reduced.receipt["unique_feature_targets"],4)
            self.assertEqual(reduced.receipt["observed_per_gene"],dense.receipt["observed_per_gene"])
            np.testing.assert_allclose(reduced.receipt["weighted_observations_per_gene"],dense.receipt["weighted_observations_per_gene"])
            self.assertEqual(by.reads,16)
            # Independent augmented least squares on the original uncollapsed rows.
            z=(x[index]-dense.feature_mean)/dense.feature_scale
            for gene in np.flatnonzero(m.any(axis=0)):
                valid=m[:,gene]; w=policy["sample_weight"][valid]
                root=np.sqrt(w/w.sum())
                design=np.column_stack((z[valid],np.ones(valid.sum())))*root[:,None]
                penalty=np.column_stack((np.sqrt(0.7)*np.eye(d),np.zeros(d)))
                coef=np.linalg.lstsq(np.vstack((design,penalty)),
                    np.r_[y[valid,gene]*root,np.zeros(d)],rcond=None)[0]
                np.testing.assert_allclose(reduced.coef[:,gene],coef[:d],rtol=1e-10,atol=1e-11)
                self.assertAlmostEqual(reduced.intercept[gene],coef[-1],places=10)

    def test_masked_values_row_order_and_block_sizes_do_not_change_fit(self):
        x,index,names,y,m,policy=self.fixture()
        reference=self.fit_reduced(x,index,names,y,m,policy,row_block=2,gene_block=2)
        y[~m]=1e30
        permutation=np.random.default_rng(911).permutation(len(y))
        moved={**policy,"row_contexts":[policy["row_contexts"][i] for i in permutation],
               "row_targets":[policy["row_targets"][i] for i in permutation],
               "sample_weight":policy["sample_weight"][permutation]}
        actual=self.fit_reduced(x,index[permutation],names,y[permutation],m[permutation],moved,
                                row_block=5,gene_block=3,factor_cache=0)
        np.testing.assert_allclose(actual.coef,reference.coef,rtol=1e-10,atol=1e-11)
        changed=y.copy(); changed[0,0]+=2.0
        different=self.fit_reduced(x,index,names,changed,m,policy)
        self.assertGreater(np.max(np.abs(reference.coef-different.coef)),1e-4)
        # Equal-weight means would lose the original observation weights.
        unweighted=self.fit_reduced(x,index,names,y,m,{**policy,"sample_weight":np.ones(len(y))})
        self.assertGreater(np.max(np.abs(reference.coef-unweighted.coef)),1e-4)

    def test_wrong_target_mapping_exclusions_and_unused_features_rejected(self):
        x,index,names,y,m,policy=self.fixture()
        with self.assertRaisesRegex(ValueError,"target identifiers"):
            self.fit_reduced(x,index[::-1],names,y,m,policy)
        with self.assertRaisesRegex(ValueError,"excluded"):
            self.fit_reduced(x,index,names,y,m,{**policy,"excluded_contexts":["study1"]})
        with self.assertRaisesRegex(ValueError,"exactly the consumed"):
            self.fit_reduced(np.vstack((x,x[:1])),index,names+["unused"],y,m,policy)

    def test_chunk_store_to_frozen_predictions_matches_dense(self):
        x,index,names,y,m,policy=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); genes=[f"g{i}" for i in range(y.shape[1])]; chunks=[]
            for study in range(3):
                rows=slice(study*4,study*4+4)
                identity=dict(study=f"study{study}",line_group="train",modality="CRISPRi")
                path=root/f"chunk{study}.npz"
                np.savez(path,targets=names,genes=genes,shrunk=y[rows],mask=m[rows],meta=json.dumps(identity))
                chunks.append(dict(path=path.name,sha256=sha256(path),context_id=f"study{study}",
                                   context_group="train",targets=names,weights=policy["sample_weight"][rows].tolist(),identity=identity))
            counts={f"study{i}":4 for i in range(3)}
            source=dict(schema="external-ridge-chunks/1",modality="CRISPRi",quantity="toy",normalization="toy",
                        regime="J",release_sha256="a"*64,split_manifest_sha256="b"*64,
                        validation_review="synthetic-pending",effect_field="shrunk",genes=genes,chunks=chunks,
                        excluded_contexts=["held"],excluded_targets=["query"],expected_rows_by_context=counts)
            source_path=root/"source.json";source_path.write_text(json.dumps(source))
            store=root/"store";build_store(source_path,store)
            features=root/"esm2";features.mkdir()
            np.save(features/"embeddings.npy",np.vstack((x,x[:1])).astype(np.float32))
            meta=dict(name="esm2",layout="dense",index="pert",keys=names+["query"],dim=x.shape[1],
                      dtype="float32",provenance={"synthetic":True})
            (features/"meta.json").write_text(json.dumps(meta))
            dense=root/"dense.npz"
            np.savez(dense,targets=policy["row_targets"],context_ids=policy["row_contexts"],context_groups=["train"]*12,
                     effects=y,observed=m,weights=policy["sample_weight"],genes=genes)
            config=dict(schema_version=1,protocol_status="agreed",validation_review="synthetic-pending",
                        quantity="toy",normalization="toy",modality="CRISPRi",regime="J",mode="development",alpha=1.0,
                        train=dict(path=str(dense),sha256=sha256(dense)),expected_rows_by_context=counts,
                        esm2=dict(path=str(features),sha256={name:sha256(features/name) for name in ("meta.json","embeddings.npy")}),
                        queries=[dict(context_id="held-study",context_group="held",target="query")],
                        excluded_contexts=["held"],excluded_targets=["query"],row_block=3,gene_block=2,
                        release_sha256="a"*64,split_manifest_sha256="b"*64)
            manifest=root/"fit.json";manifest.write_text(json.dumps(config));run_dense(manifest,root/"dense-output")
            config["train"]=dict(path=str(store),sha256=sha256(store/"manifest.json"))
            manifest.write_text(json.dumps(config));receipt=run_sufficient(manifest,root/"sufficient-output")
            self.assertEqual(receipt["exposure"]["unique_feature_targets"],4)
            self.assertEqual(receipt["consumed_rows_by_context"],counts)
            self.assertFalse(receipt["exposure"]["expanded_row_features_materialized"])
            with np.load(root/"dense-output"/"native_predictions.npz") as a,np.load(root/"sufficient-output"/"native_predictions.npz") as b:
                np.testing.assert_allclose(a["effects"],b["effects"],rtol=1e-10,atol=1e-11,equal_nan=True)
                np.testing.assert_array_equal(a["observed"],b["observed"])

    @classmethod
    def tearDownClass(cls):
        print(json.dumps(dict(fixture_prediction_max_abs_error=max(cls.errors,default=None),
                              biological_arrays_read=False, scientific_benefit="not_evaluated")))


if __name__ == "__main__":
    unittest.main()
