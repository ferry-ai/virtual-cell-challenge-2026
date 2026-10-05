"""Exercise the generalized producer through a tiny real H5AD round trip."""
import ast
import base64
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import pandas as pd
import test_materialize as fixture


class KolfBankTest(unittest.TestCase):
    def test_group_counts_samples_and_same_size_raw_tamper(self):
        source=(Path(__file__).parent/'kolf_bank_stage_r1/run.py').read_text()
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets))
        module=types.ModuleType('kolf_fixture_bank')
        exec(base64.b64decode(ast.literal_eval(node.value)['bank.py']['data']),module.__dict__)

        def run(spec,root,out):
            spec={**spec,'line_group':'iPSC','expected_contexts':['CD4T D1 Rest']}
            module.run_unit(spec,root,out)
            self.assertEqual(set(pd.read_csv(out/'rows.csv').line_group),{'iPSC'})
            raw=root/'job/shards/cd4_D1_Rest/shard.h5ad'
            original=raw.read_bytes()
            raw.write_bytes(original[:-1]+bytes([original[-1]^1]))
            try:
                with self.assertRaisesRegex(ValueError,'changed verified raw shard'):
                    module.run_unit(spec,root,root/'tampered_bank')
            finally:
                raw.write_bytes(original)
            with self.assertRaisesRegex(ValueError,'unexpected biological context'):
                module.run_unit({**spec,'expected_contexts':['wrong']},root,root/'wrong_context')

        with patch.object(fixture,'run_unit',run):
            fixture.MaterializeTests('test_counts_identity_nested_levels_and_raw_integrity').test_counts_identity_nested_levels_and_raw_integrity()


if __name__=='__main__':
    unittest.main()
