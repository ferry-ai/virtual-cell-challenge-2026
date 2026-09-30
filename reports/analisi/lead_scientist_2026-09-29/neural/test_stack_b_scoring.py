import ast
from pathlib import Path
import subprocess
import tempfile
import unittest
import build_stack_b_scoring as build


class ScoringSnapshotTest(unittest.TestCase):
    def test_only_three_additions_preserve_every_original_byte(self):
        payload, base, files = build.make_payload()
        recovered = build.read_archive(payload)
        self.assertEqual(recovered, files)
        self.assertEqual(set(files) - set(base), {build.REL + '/' + name for name in build.ADDITIONS})
        for name, content in base.items():
            self.assertEqual(files[name], content, name)
        # Every computation other than the intended provenance verifier is identical.
        nodes = []
        for name in ['score_stack_pilot.py', 'score_stack_input_axis.py']:
            tree = ast.parse(files[build.REL + '/' + name])
            nodes.append({x.name: ast.dump(x, include_attributes=False) for x in tree.body
                          if isinstance(x, (ast.FunctionDef, ast.ClassDef)) and x.name != 'verify_inference_provenance'})
        self.assertEqual(nodes[0], nodes[1])

    def test_template_exits_before_accessing_inputs_or_creating_output(self):
        bash = Path('C:/Program Files/Git/bin/bash.exe')
        if not bash.exists():
            self.skipTest('Local Git Bash unavailable; shell syntax checked separately before run')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'unbound.sh'
            path.write_bytes(build.launcher('a' * 64).encode())
            check = subprocess.run([str(bash), '-n', str(path)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            result = subprocess.run([str(bash), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 64)
            self.assertIn('UNBOUND TEMPLATE', result.stderr)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
