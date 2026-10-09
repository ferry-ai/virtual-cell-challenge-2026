"""Verify the actual frozen runner rejects the production draft before output."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ammi_inputs_v3 import checked
from run_ammi_v4 import run

HERE = Path(__file__).resolve().parent


class ProductionDraftTests(unittest.TestCase):
    def test_actual_runner_rejects_unread_pilot_gate(self):
        prepared = json.loads((HERE/'ammi_production_draft_prepared_r1.json').read_text())
        manifest = checked(prepared['runtime_template'])
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)/'production'
            # No CUDA allocation occurs before the readout gate. This allows a
            # metadata-only CPU fixture to exercise the real runner branch.
            with patch('run_ammi_v4.torch.cuda.is_available', return_value=True):
                with self.assertRaisesRegex(ValueError, 'both frozen pilot comparisons must be read'):
                    run(manifest, prepared['runtime_template']['sha256'], 'cells', 17, out)
            self.assertFalse(out.exists())

    def test_training_and_destination_parts_are_all_declared(self):
        prepared = json.loads((HERE/'ammi_production_draft_prepared_r1.json').read_text())
        spec = json.loads(checked(prepared['runtime_template']).read_text())
        contract = json.loads((HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34/ammi_ntc_runtime_contract_r3.json').read_text())
        expected = set(contract['parts']) | {'official_A','official_B','official_C'}
        self.assertEqual(set(spec['ntc_expected_parts']), expected)
        self.assertEqual(len(spec['ntc_parts']), len(expected))
        self.assertEqual(spec['destination_contexts'], ['A','B','C'])
        self.assertFalse(prepared['launchable'])
        self.assertFalse(prepared['complete_D053'])


if __name__ == '__main__':
    unittest.main()
