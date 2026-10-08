"""Print only the public reference runtime helper code needed for recovery review."""
import ast
from percorso import ROOT
from prepare_extended_generation import unpack

members,_=unpack(ROOT/'reports/modelli/percorso_riusabile_2026-10-05/generation_successors_r1/package/run.py')
source=members['driver.py'].decode();tree=ast.parse(source)
print(members['repo/configs/config.yaml'].decode())
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('_guard_resources','_run_script','_check_axis'):
        print(ast.get_source_segment(source,node))
