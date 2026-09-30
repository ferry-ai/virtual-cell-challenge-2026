"""Guard the mechanical085 packet: frozen inputs/code, order, environment."""
import ast
import hashlib
import json
from pathlib import Path
import re
import tarfile
import unittest

HERE = Path(__file__).resolve().parent
PACKET = HERE / 'stack_paired_scoring_setup_r1'


def read(name):
    return json.loads((PACKET / name).read_text())


class PairedRescoreTests(unittest.TestCase):
    def test_data_and_scientific_code_identical(self):
        contract, review = read('job_contract.json'), read('review.json')
        items = {i['id']: i for i in contract['inputs']}
        self.assertEqual(len(items), 15)
        for arm, folder in [('A', 'stack_a_scoring_r2'), ('B', 'stack_b_scoring_r1')]:
            old = json.loads((HERE / folder / 'evaluation_manifest.json').read_text())
            for label in ['stack', 'transfer']:
                self.assertEqual(items[f'{arm}_prediction_{label}.h5ad']['sha256'], old['prediction_hashes'][label])
        self.assertEqual(items['A_prediction_transfer.h5ad']['sha256'], items['B_prediction_transfer.h5ad']['sha256'])
        old_contract = json.loads((HERE / 'stack_b_scoring_bound_r1' / 'job_contract.json').read_text())
        for item in old_contract['inputs'][4:]:
            self.assertEqual(items[item['id']]['sha256'], item['sha256'])
        self.assertEqual(contract['target_checks'], old_contract['target_checks'])
        self.assertEqual(hashlib.sha256((PACKET/'scoring_snapshot.tar.gz').read_bytes()).hexdigest(), review['snapshot_sha256'])
        with tarfile.open(PACKET/'scoring_snapshot.tar.gz') as archive:
            for name, expected in [('score_stack_pilot.py','2d4dc6503c5ac58c6ca8ad2f3002b5d37c6293818a2179559c3fa68a0537ff37'),
                                   ('score_stack_input_axis.py','74607f249fc36642e74a374e45c32157391b875888efe715163642674045b28c')]:
                member = next(m for m in archive.getmembers() if m.name.endswith('/'+name))
                self.assertEqual(hashlib.sha256(archive.extractfile(member).read()).hexdigest(), expected)

    def test_runtime_determinism_and_preflight_before_sequential_scores(self):
        text = (PACKET/'085_lead_stack_paired_rescore_r1.sh').read_text()
        contract = read('job_contract.json')
        first_import = text.index('import importlib.metadata')
        for name, value in contract['runtime_environment_variables'].items():
            self.assertLess(text.index(name+'='+value), first_import)
        self.assertLess(text.index('--site runtime'), text.index('tar -xzf'))
        self.assertLess(text.index('--out "$OUT/A"'), text.index('--out "$OUT/B"'))
        self.assertLess(text.index('--out "$OUT/B"'), text.index("out/'complete.json'"))
        self.assertIn("metadata.version(package)==version", text)
        self.assertEqual(contract['required_runtime_versions']['polars'], '1.35.2')
        self.assertEqual({o['id'] for o in contract['outputs']}, {'A','B'})
        self.assertTrue(all(o['must_be_absent'] for o in contract['outputs']))
        self.assertNotIn('stack_confirmation', text)
        self.assertNotIn('pip install', text)
        for marker in ['PYENV', 'PYDONE']:
            code = text.split("<<'"+marker+"'\n",1)[1].split('\n'+marker,1)[0]
            ast.parse(code)

    def test_packet_hashes_and_no_publication_side_effect(self):
        plan, review = read('publish_plan.json'), read('review.json')
        self.assertEqual(review['status'], 'prepared_not_published_not_queued')
        for item in plan['transfers']:
            path = Path(item['source'])
            self.assertEqual(path.stat().st_size, item['bytes'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item['sha256'])
        self.assertEqual(hashlib.sha256(Path(plan['launcher']).read_bytes()).hexdigest(), plan['launcher_sha256'])
        publisher = (PACKET/'publish.ps1').read_text()
        self.assertLess(publisher.index('validate --manifest'), publisher.index('[IO.File]::Copy($plan.launcher'))
        self.assertIn('receipt.validator_sha256', publisher)
        self.assertIn('receipt.manifest_sha256', publisher)


if __name__ == '__main__':
    unittest.main()
