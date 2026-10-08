"""Parse the new command with the real stage-45 parser, stopping before any work."""
import argparse
import ast
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]


class Parsed(Exception):pass


class ArgumentTest(unittest.TestCase):
    def test_real_stage45_accepts_all_contexts(self):
        # Extract this pure helper without importing cloud-only runtime modules.
        tree=ast.parse((HERE/'generate_t3_existing.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='effect_arguments')
        namespace={};exec(compile(ast.Module(body=[function],type_ignores=[]),'fixture','exec'),namespace)
        effects={c:'/synthetic/effects_'+c+'.npz' for c in ('A','B','C')}
        args=['stage45','--run-id','synthetic','--trial','trial-ext-profile',
              '--effects-scale','1.5','--gene-dispersion','--cells-per-pert','400',
              *namespace['effect_arguments'](effects)]
        original=argparse.ArgumentParser.parse_args
        def capture(parser,*a,**kw):
            result=original(parser,*a,**kw)
            self.assertEqual(result.effects,[c+'='+effects[c] for c in ('A','B','C')])
            raise Parsed()
        with patch.object(sys,'argv',args),patch.object(argparse.ArgumentParser,'parse_args',capture):
            with self.assertRaises(Parsed):runpy.run_path(str(ROOT/'scripts/45_generate_prediction.py'),run_name='__main__')


if __name__=='__main__':unittest.main()
