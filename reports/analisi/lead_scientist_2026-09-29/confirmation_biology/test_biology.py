"""Small independent fixtures for ontology propagation and exact decomposition."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import analyze_biology as biology
from supplement_biology import fidelity_decomposition


class BiologyTests(unittest.TestCase):
    def test_ontology_does_not_infer_regulator_or_obsolete_membership(self):
        obo = '''format-version: 1.2
data-version: test
[Term]
id: GO:1
name: root
[Term]
id: GO:2
name: child
alt_id: GO:22
is_a: GO:1 ! root
[Term]
id: GO:3
name: part
relationship: part_of GO:2 ! child
[Term]
id: GO:4
name: regulator
relationship: regulates GO:1 ! root
[Term]
id: GO:5
name: obsolete
is_a: GO:1 ! root
is_obsolete: true
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'go.obo'
            path.write_text(obo,encoding='utf-8')
            with patch.object(biology,'PROGRAMS',{'program':['GO:1']}):
                _, groups, aliases, _ = biology.ontology(path)
        self.assertEqual(groups['program'], {'GO:1','GO:2','GO:3'})
        self.assertEqual(aliases['GO:22'], 'GO:2')

    def test_fidelity_decomposition_crosses_call_budget_boundary(self):
        # Baseline 10/20, candidate 60/80, true budget40:
        # FID .25 -> .75; symmetric precision .1875 and coverage .3125.
        result = fidelity_decomposition(10,20,60,80,40)
        self.assertAlmostEqual(float(result['fid0']),.25)
        self.assertAlmostEqual(float(result['fid1']),.75)
        self.assertAlmostEqual(float(result['precision_component']),.1875)
        self.assertAlmostEqual(float(result['coverage_component']),.3125)

    def test_annotations_reject_not_and_nonhuman_and_resolve_previous_symbol(self):
        hgnc = ('symbol\tstatus\tprev_symbol\talias_symbol\tuniprot_ids\n'
                'GENE1\tApproved\tOLD1\t\tP1\n'
                'GENE2\tApproved\t\t\tP2\n')
        def gaf(protein, symbol, qualifier, term, evidence, taxon='taxon:9606'):
            return '\t'.join(['UniProtKB',protein,symbol,qualifier,term,'PMID:1',
                evidence,'','C','name','','protein',taxon,'20260728','TEST','',''])+'\n'
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory/'hgnc_complete_set').write_text(hgnc,encoding='utf-8')
            (directory/'go_basic_obo').write_text(
                '[Term]\nid: GO:1\nname: root\n',encoding='utf-8')
            (directory/'goa_human_gaf').write_text(
                gaf('P1','obsolete_name','NOT|located_in','GO:1','IDA')+
                gaf('P1','obsolete_name','located_in','GO:1','IDA','taxon:10090')+
                gaf('P1','obsolete_name','located_in','GO:1','IEA')+
                gaf('P2','GENE2','located_in','GO:1','IDA'),encoding='utf-8')
            with patch.object(biology,'PROGRAMS',{'program':['GO:1']}):
                annotations, evidence, meta = biology.annotate(directory,{'OLD1','GENE2'})
        self.assertEqual(annotations.loc['OLD1','approved_symbol'],'GENE1')
        self.assertTrue(annotations.loc['OLD1','program'])
        self.assertFalse(annotations.loc['OLD1','program_experimental'])
        self.assertTrue(annotations.loc['GENE2','program_experimental'])
        self.assertEqual(meta['NOT_annotations_excluded'],1)
        self.assertEqual(len(evidence),2)

    def test_zero_true_budget_is_pure_precision_for_positive_predictions(self):
        result = fidelity_decomposition([10,20],[20,40],[12,12],[30,30],[0,0])
        np.testing.assert_allclose(result['coverage_component'],0)
        np.testing.assert_allclose(result['precision_component'],[-.1,-.1])
        with self.assertRaises(ValueError):
            fidelity_decomposition(0,0,10,20,40)

    def test_signed_reversal_symmetry_and_additivity(self):
        rng = np.random.default_rng(43)
        n0,n1 = rng.integers(1,1000,size=(2,100))
        k0,k1 = np.floor(rng.random(100)*n0),np.floor(rng.random(100)*n1)
        nconf = rng.integers(0,1000,size=100)
        forward = fidelity_decomposition(k0,n0,k1,n1,nconf)
        reverse = fidelity_decomposition(k1,n1,k0,n0,nconf)
        np.testing.assert_allclose(forward['fid1']-forward['fid0'],
            forward['precision_component']+forward['coverage_component'],atol=1e-14)
        for key in ('precision_component','coverage_component'):
            np.testing.assert_allclose(forward[key],-reverse[key],atol=1e-14)


if __name__ == '__main__':
    unittest.main()
