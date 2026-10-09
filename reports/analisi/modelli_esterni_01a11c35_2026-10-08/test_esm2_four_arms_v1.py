"""Compare construction with the independently frozen audit on tiny arrays."""
import ast
import importlib.util
from pathlib import Path
import unittest
import numpy as np
from esm2_four_arms_v1 import arrays

HERE=Path(__file__).resolve().parent
AUDIT=HERE.parent/'validazione_banco_eace4d03_2026-10-09/esm2/supporto_fallback.py'
METRICS=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco/metrics.py'


class FourArmTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('frozen_metrics_fixture',METRICS)
        self.M=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.M)
        rng=np.random.default_rng(17);shape=(5,7)
        def sample(mask):return dict(targets=np.array(list('ABCDE')),genes=np.array(list('abcdefg')),
            lfc=np.where(mask,rng.normal(size=shape),0).astype(np.float32),observed=mask)
        self.base=sample(rng.random(shape)>.4);self.native=sample(np.ones(shape,bool));self.generic=sample(np.ones(shape,bool))
        fill=~self.base['observed']
        self.fallback=dict(self.base,lfc=np.where(fill,np.float32(1.576)*self.native['lfc'],self.base['lfc']),observed=np.ones(shape,bool))

    def test_equal_to_original_independent_construction(self):
        values,masks,changed,donor=arrays(self.base,self.native,self.generic,self.fallback,self.M.shuffled_rows)
        function=next(n for n in ast.parse(AUDIT.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='audit')
        start=next(i for i,n in enumerate(function.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='rows_pred')
        end=next(i for i,n in enumerate(function.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='arms')
        env=dict(np=np,M=self.M,panel=self.base['targets'],obs_e2=self.native['observed'],amplitude=1.576,
            lfc_g=self.generic['lfc'],lfc_t0=self.base['lfc'],lfc_f=self.fallback['lfc'],fill_all=~self.base['observed'],
            expected=(self.native['lfc'].astype(np.float64)*1.576).astype(np.float32))
        exec(compile(ast.Module(body=function.body[start:end+1],type_ignores=[]),'frozen_audit_fragment','exec'),env)
        for name,original in [('T0','zero'),('E2f','esm2'),('Generic','generic'),('Swapped','swapped')]:
            np.testing.assert_array_equal(values[name],env['arms'][original])
            np.testing.assert_array_equal(values[name][self.base['observed']],self.base['lfc'][self.base['observed']])
        np.testing.assert_array_equal(donor,env['donor'])
        np.testing.assert_array_equal(masks['T0'],self.base['observed'])

    def test_changed_axis_or_fallback_rejected(self):
        wrong=dict(self.native,genes=self.native['genes'][::-1])
        with self.assertRaises(ValueError):arrays(self.base,wrong,self.generic,self.fallback,self.M.shuffled_rows)
        wrong=dict(self.fallback,lfc=self.fallback['lfc']+np.float32(2))
        with self.assertRaises(ValueError):arrays(self.base,self.native,self.generic,wrong,self.M.shuffled_rows)


if __name__=='__main__':unittest.main()
