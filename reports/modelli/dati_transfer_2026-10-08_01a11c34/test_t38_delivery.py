"""Small offline tests for rejecting unsafe delivery evidence and wrong ranges."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from collect_t38_generation import verify_receipts, EFFECT_SHA
from percorso import pin, sha
from t38_submission import download_product


class DeliveryEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.proof = {'source_job': 'owner/fit'}
        for name in ('protocol', 'prediction', 'fit_receipt'):
            path = self.root / (name + '.json')
            path.write_text('{}')
            self.proof[name] = pin(path)
        params = self.root / 'params.json'
        params.write_text(json.dumps(dict(product='prediction.vcc', embedded_sha256={'driver.py': 'test-code'})))
        self.proof['params'] = pin(params)
        self.packaging = dict(exit_code=0,
            package=dict(validation=dict(ok=True, failures=[]), n_obs=360000, n_vars=18533, archive_bytes=123),
            verification=dict(official_container_validator='passed', archive_sha256='test-product', archive_bytes=123,
                payload_vs_input=dict(matches_input=True, x_arrays_bit_identical=True)))
        self.diagnostics = dict(is_pilot=False, context_provenance_ok=True, seed=20260912,
            shape=dict(n_perturbations=300, cells_per_pert=400, n_cells=360000, contexts=['A', 'B', 'C']))
        self.manifest = dict(status='VCC_READY', candidate='T3-CRISPRi-KO', product='prediction.vcc',
            bytes=123, sha256='test-product', source_job='owner/fit', new_fit=False,
            code={'driver.py': 'test-code'},
            effects={c: dict(bytes=18846035, sha256=EFFECT_SHA) for c in ('A', 'B', 'C')},
            **{k: self.proof[k] for k in ('protocol', 'prediction', 'fit_receipt')})

    def save(self):
        for name, doc in [('packaging', self.packaging), ('compact_diagnostics', self.diagnostics)]:
            (self.root / (name + '.json')).write_text(json.dumps(doc))
        self.manifest['packaging_sha256'] = sha(self.root / 'packaging.json')
        (self.root / 'generation_manifest.json').write_text(json.dumps(self.manifest))

    def test_complete_verified_evidence_passes(self):
        self.save()
        self.assertEqual(verify_receipts(self.root, self.proof)['product'], 'prediction.vcc')

    def test_ready_flag_does_not_override_failed_independent_verification(self):
        self.packaging['verification']['payload_vs_input']['x_arrays_bit_identical'] = False
        self.save()
        with self.assertRaisesRegex(ValueError, 'independent archive'):
            verify_receipts(self.root, self.proof)

    def test_old_scientific_receipt_cannot_be_substituted(self):
        self.save()
        Path(self.proof['fit_receipt']['path']).write_text('{"different_fit":true}')
        with self.assertRaisesRegex(ValueError, 'frozen evidence'):
            verify_receipts(self.root, self.proof)

    def test_partial_contexts_are_rejected_even_if_archive_shape_claims_full(self):
        self.diagnostics['shape']['contexts'] = ['A', 'B']
        self.save()
        with self.assertRaisesRegex(ValueError, 'incomplete generation'):
            verify_receipts(self.root, self.proof)


class RangeIdentityTest(unittest.TestCase):
    def test_wrong_provider_range_never_appends_local_product(self):
        response = SimpleNamespace(files=[SimpleNamespace(file_name='prediction.vcc', url='https://example.invalid/test')], next_page_token=None)
        class Client:
            def __enter__(self):
                return SimpleNamespace(kernels=SimpleNamespace(kernels_api_client=SimpleNamespace(list_kernel_session_output=lambda _: response)))
            def __exit__(self, *args): pass
        api = SimpleNamespace(build_kaggle_client=lambda: Client())
        class HTTP:
            status_code = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with tempfile.TemporaryDirectory() as temp, patch('t38_submission.requests.get', return_value=HTTP()):
            path = Path(temp) / 'prediction.vcc'
            path.write_bytes(b'previous')
            with self.assertRaisesRegex(ValueError, 'range identity'):
                download_product(api, 'owner/job', 'prediction.vcc', path, 123, lambda *a, **k: None)
            self.assertEqual(path.read_bytes(), b'previous')


if __name__ == '__main__':
    unittest.main()
