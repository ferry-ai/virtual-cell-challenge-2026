"""Tiny fixture: hidden responses must not change an admitted target's anchor.

Run from the repository root with scripts/py.cmd and this file's relative path.
Uses the real bench function bodies, no corpus reads and no cloud operations.
"""
import ast
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
BENCH = ROOT / "reports/modelli/risposta_contesto_2026-10-02"
sys.path.insert(0, str(BENCH))
from splits import Split, target_fold

source = ast.parse((BENCH / "arms.py").read_text(encoding="utf-8"))
nodes = [n for n in source.body if isinstance(n, ast.FunctionDef)
         and n.name in ("table_means", "group_mean", "combine_groups")]
namespace = {"np": np, "F32": np.float32, "Cube": object, "Split": Split}
exec(compile(ast.Module(body=nodes, type_ignores=[]), "arms_fixture", "exec"), namespace)
seen = next(f"G{i}" for i in range(100) if target_fold(f"G{i}", 5) != 0)
hidden = next(f"G{i}" for i in range(100) if target_fold(f"G{i}", 5) == 0)


class CubeFixture:
    tables = ["src"]
    group = {"src": "S"}
    genes = ["a", "b"]

    def keys_of(self, table):
        return [seen, hidden]

    def tables_of(self, group):
        return ["src"]

    def get(self, table, kind, keys):
        return np.array([([1, 2] if k == seen else self.hidden) for k in keys], np.float32), np.ones(len(keys), bool)

    def cells(self, table, keys):
        return np.full(len(keys), 100.)


cube = CubeFixture()
observed = []
for response in ([3, 4], [300, 400]):
    cube.hidden = response
    current, _ = namespace["table_means"](cube, Split("C", "H", None, 5))
    filtered, _ = namespace["table_means"](cube, Split("J", "H", 0, 5))
    row = {"hidden_response": response,
           "current_C": namespace["group_mean"](cube, "S", [seen], current).tolist(),
           "filtered_J": namespace["group_mean"](cube, "S", [seen], filtered).tolist()}
    observed.append(row)
    print(json.dumps(row))
assert observed[0]["current_C"] != observed[1]["current_C"]
assert observed[0]["filtered_J"] == observed[1]["filtered_J"] == [[0.0, 0.0]]
print(json.dumps({"seen": seen, "hidden": hidden, "hidden_fold": target_fold(hidden, 5),
                  "reproduction": "PASS: only the hidden response changed; current training anchors changed"}))
