"""Exercise fail-closed readiness, without cloud or biological files."""
import unittest
from prepare_ammi_cells_v1 import gates,PRODUCER


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.contract=dict(parts={'p':{}},folds={f:dict(ntc_expected_parts={'p':'hash'})
            for f in ('C-K562','C-iPSC')})
        self.terminal=dict(status='PASS_METADATA_AND_CODE',slug=PRODUCER)
        self.ready=dict(parts={'p':{}},pending_parts=[])
        self.access=dict(status='AUTHORIZED_INPUT_LOCATORS_COMPLETE_CONSUMER_HASHES_PENDING',NTC_parts=12,NTC_files=48)

    def test_missing_manifest_never_prepares(self):
        state,missing=gates(self.contract,{},None,None,None)
        self.assertEqual(state,'WAITING_VERIFIED_NTC_MANIFESTS')
        self.assertEqual(missing['C-K562'],['p'])

    def test_completed_but_missing_part_rejected(self):
        with self.assertRaises(ValueError):gates(self.contract,{},self.terminal,self.ready,self.access)

    def test_access_is_separate_gate(self):
        state,_=gates(self.contract,{'p':{}},self.terminal,self.ready,None)
        self.assertEqual(state,'READY_FOR_AUTHORIZED_LOCATOR_EXTENSION')
        state,_=gates(self.contract,{'p':{}},self.terminal,self.ready,self.access)
        self.assertEqual(state,'READY_FOR_PACKAGE_PREPARATION')

    def test_partial_or_wrong_producer_rejected(self):
        for terminal in [dict(self.terminal,status='PASS_PARTIAL'),dict(self.terminal,slug='other/job')]:
            with self.assertRaises(ValueError):gates(self.contract,{'p':{}},terminal,self.ready,self.access)


if __name__=='__main__':unittest.main()
