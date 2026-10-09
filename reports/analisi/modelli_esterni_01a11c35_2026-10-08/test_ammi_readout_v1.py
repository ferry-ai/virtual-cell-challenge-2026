"""Prevent incomplete arms and mismatched anchors from reaching a readout plan."""
import json
from pathlib import Path
import tempfile
import unittest
from prepare_ammi_readout_v1 import PRIMARY, plan
from pie_adapter import sha256


class ReadoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.receipts=[]
        for fold,context in PRIMARY.items():
            for mode in ('cells','none'):
                folder=self.root/(fold+mode);folder.mkdir()
                def save(name,value):
                    path=folder/name;path.write_text(json.dumps(value),encoding='utf-8')
                    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha256(path))
                files={'complete.json':save('complete.json',dict(fold=fold,mode=mode,seed=17)),
                    'zero_residual_parity.receipt.json':save('anchor.json',dict(
                        bytes=42,anchor_sha256=fold,output_sha256=fold))}
                exports=[dict(context_id=context,intervention='native',source='mx/job',file='native.npz',bytes=123,sha256=mode+fold)]
                report=dict(status='METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING',files=files,
                    slug='mx/'+fold+mode,verification=dict(exports=exports))
                pin=save('report.json',report);self.receipts.append(pin['path'])

    def test_nested_anchor_is_distinct_and_swapped_can_be_missing(self):
        result=plan(self.receipts)
        self.assertEqual(set(result['external_arms']),{'A0','Acells','Anone'})
        self.assertIn(['AMMI_cells_minus_anchor','Acells','A0'],result['contrasts'])
        self.assertIn(['AMMI_cells_minus_original_T0','Acells','T0'],result['contrasts'])

    def test_missing_or_duplicate_fit_is_rejected(self):
        with self.assertRaises(ValueError):plan(self.receipts[:3])
        with self.assertRaises(ValueError):plan(self.receipts[:3]+self.receipts[:1])

    def test_different_anchor_is_rejected(self):
        path=Path(self.receipts[1]);report=json.loads(path.read_text())
        anchor=Path(report['files']['zero_residual_parity.receipt.json']['path'])
        anchor.write_text(json.dumps(dict(bytes=42,anchor_sha256='different',output_sha256='different')))
        report['files']['zero_residual_parity.receipt.json'].update(bytes=anchor.stat().st_size,sha256=sha256(anchor))
        path.write_text(json.dumps(report))
        with self.assertRaises(ValueError):plan(self.receipts)


if __name__=='__main__':unittest.main()
