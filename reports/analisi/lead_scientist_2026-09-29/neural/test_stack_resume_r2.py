"""Verify the resume preserves frozen scientific payload and the loader guard."""
import ast
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def parsed(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    call = tree.body[-1].value
    return tree, [ast.literal_eval(arg) for arg in call.args], {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}


class ResumeTest(unittest.TestCase):
    def test_frozen_scientific_inputs_and_loader_guard_are_identical(self):
        old, old_args, old_kw = parsed(HERE / "stack_remote_receipt_r2/colab_stack_infer_r1.py")
        new, new_args, new_kw = parsed(HERE / "stack_resume_r2/colab_stack_infer_r2.py")
        self.assertEqual(old_args, new_args)  # full code archive and complete scientific review
        self.assertEqual(old_kw["bundle_archive"], new_kw["bundle_archive"])
        self.assertEqual(old_kw["scratch"], new_kw["scratch"])
        self.assertNotEqual(old_kw["work"], new_kw["work"])
        def guard(tree):
            return next(ast.literal_eval(node.value) for node in ast.walk(tree) if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "guarded_entry" for t in node.targets))
        self.assertEqual(guard(old), guard(new))

    def test_main_cannot_reinstall_full_runtime(self):
        tree, _, _ = parsed(HERE / "stack_resume_r2/colab_stack_infer_r2.py")
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(n.func, ast.Name) and n.func.id == "create_managed_runtime" for n in calls))
        pip_installs = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "run" and n.args
                        and isinstance(n.args[0], ast.List)
                        and any(isinstance(a, ast.Constant) and a.value == "install" for a in n.args[0].elts)]
        self.assertEqual(len(pip_installs), 1)
        values = [n.value for n in pip_installs[0].args[0].elts if isinstance(n, ast.Constant)]
        self.assertEqual(values, ["-m", "pip", "install", "--no-cache-dir", "--no-deps", "--only-binary=:all:", "pooch==1.8.2"])


if __name__ == "__main__":
    unittest.main()
