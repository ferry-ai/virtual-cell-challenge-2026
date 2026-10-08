"""Adversarial scientific invariants, not tests mirroring the implementation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
import fold_bank as F

BANK = Path(__file__).resolve().parents[1] / 'banca_canonica_2026-10-07'
spec = importlib.util.spec_from_file_location('canonical_estimator', BANK / 'consumer/estimator.py')
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)


def fixture():
    rows = []
    for context in ('train', 'held_alias'):
        for target in ('NTC', 'X', 'Y', 'Z', 'guide_unknown', 'X+Y'):
            rows.append(dict(study='s', context=context, line_group=context, donor_or_clone='d',
                condition='rest', modality='CRISPRi', chemistry='assay', target=target, n=30))
    split = dict(id='fixture-J', regime='J', held_groups=['held'], hidden_targets=['Y'],
                 protected_units=['h1_test'], group_aliases={'held_alias':'held'})
    resolutions = {t:dict(target=t, components=[t], evidence='fixture') for t in ('X','Y','Z')}
    resolutions['X+Y'] = dict(target='X+Y', components=['X','Y'], evidence='fixture')
    counts = np.random.default_rng(314).integers(50, 500, size=(len(rows), 9)).astype(float)
    return pd.DataFrame(rows), counts, np.ones_like(counts, bool), resolutions, split


def run(rows, x, m, resolutions, split, out, chunk=1):
    frame, selection = F.select_rows(rows, resolutions, split, 'unit')
    receipt = F.derive(frame, x, m, ['g'+str(i) for i in range(9)], E.effects_from_pseudobulk, E.CALL, out, chunk_targets=chunk)
    with np.load(out / 'context000_common.npz') as z:
        mean, mask = z['common'], z['mask']
    arrays = []
    for c in receipt['contexts'][0]['chunks']:
        with np.load(out / c['file']) as z:
            arrays.append(z['shrunk'])
    return mean, mask, np.concatenate(arrays), receipt, selection


class FoldBankTests(unittest.TestCase):
    def test_excluded_response_and_masks_cannot_change_training(self):
        rows,x,m,r,s = fixture()
        frame, ledger = F.select_rows(rows,r,s,'unit')
        self.assertEqual(set(frame.target), {'non-targeting','X','Z'})
        excluded = sorted(set(range(len(rows))) - set(frame.bank_row))
        with tempfile.TemporaryDirectory() as tmp:
            a=run(rows,x,m,r,s,Path(tmp)/'a')
            changed=x.copy(); changed[excluded] *= 100000
            masked=m.copy(); masked[excluded] = False
            b=run(rows,changed,masked,r,s,Path(tmp)/'b')
            np.testing.assert_array_equal(a[0], b[0])
            np.testing.assert_array_equal(a[2], b[2])
            changed=x.copy(); changed[1,0] *= 20
            c=run(rows,changed,m,r,s,Path(tmp)/'c')
            self.assertGreater(np.linalg.norm(a[0]-c[0]), 0.01)
        self.assertEqual(ledger['cells_by_role']['hidden_component'], 60)

    def test_chunking_preserves_original_estimator(self):
        rows,x,m,r,s=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            a=run(rows,x,m,r,s,Path(tmp)/'a',1)
            b=run(rows,x,m,r,s,Path(tmp)/'b',99)
            np.testing.assert_array_equal(a[2], b[2])
            np.testing.assert_array_equal(a[0], b[0])
            np.testing.assert_allclose(a[0], np.nanmean(a[2].astype(float),axis=0))
            self.assertEqual(a[3]['physical_cells_read'],0)

    def test_modality_and_donor_identity_preserved(self):
        rows,x,m,r,s=fixture()
        rows.loc[6:,'line_group']='train'
        rows.loc[6:,'modality']='KO'
        frame,_=F.select_rows(rows,r,s,'unit')
        with tempfile.TemporaryDirectory() as tmp:
            receipt=F.derive(frame,x,m,['g'+str(i) for i in range(9)],E.effects_from_pseudobulk,E.CALL,Path(tmp)/'a')
            self.assertEqual({c['identity']['modality'] for c in receipt['contexts']},{'KO','CRISPRi'})
            self.assertEqual(len(receipt['contexts']),2)

    def test_protection_unresolved_duplicates_and_missing_controls(self):
        rows,x,m,r,s=fixture()
        with self.assertRaisesRegex(ValueError,'protected'):
            F.select_rows(rows,r,s,'h1_test')
        dup=pd.concat([rows,rows.iloc[[1]]],ignore_index=True)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            F.select_rows(dup,r,s,'unit')
        rows.loc[1,'donor_or_clone']='orphan'
        frame,ledger=F.select_rows(rows,r,s,'unit')
        self.assertGreater(ledger['cells_by_role']['unresolved_target_mapping'],0)
        with tempfile.TemporaryDirectory() as tmp:
            receipt=F.derive(frame,x,m,['g'+str(i) for i in range(9)],E.effects_from_pseudobulk,E.CALL,Path(tmp)/'a')
            self.assertEqual(receipt['contexts'][0]['status'],'blocked_matched_controls')
            self.assertEqual(receipt['target_cells_contributing'],0)

    def test_unmeasured_remains_masked(self):
        rows,x,m,r,s=fixture(); m[:,8]=False; x[:,8]=0
        with tempfile.TemporaryDirectory() as tmp:
            a=run(rows,x,m,r,s,Path(tmp)/'a')
            self.assertFalse(a[1][8]); self.assertTrue(np.isnan(a[2][:,8]).all())

    def test_empty_rows_and_explicit_unit_exclusion(self):
        rows,x,m,r,s=fixture(); rows.loc[1,'n']=0
        frame,receipt=F.select_rows(rows,r,s,'unit')
        self.assertNotIn('X',set(frame.target))
        self.assertTrue(any(v['reason']=='empty_bank_row' for v in receipt['excluded_rows']))
        s['exclude_units']=['unit']
        frame,receipt=F.select_rows(rows,r,s,'unit')
        self.assertTrue(frame.empty)
        self.assertEqual(receipt['cells_by_role']['excluded_unit'],int(rows.n.sum()))

    def test_hidden_rule_covers_targets_outside_explicit_panel_list(self):
        import hashlib
        rows,x,m,r,s=fixture()
        symbol=next('OFFPANEL'+str(i) for i in range(100) if int(hashlib.sha256(('OFFPANEL'+str(i)).encode()).hexdigest(),16)%5==0)
        rows.loc[1,'target']=symbol
        r[symbol]=dict(target=symbol,components=[symbol],evidence='fixture')
        s['hidden_rule']=F.HIDDEN_RULE
        frame,receipt=F.select_rows(rows,r,s,'unit')
        self.assertNotIn(symbol,set(frame.target))
        self.assertTrue(any(v['native_target']==symbol and v['reason']=='hidden_component' for v in receipt['excluded_rows']))


if __name__ == '__main__':
    unittest.main()
