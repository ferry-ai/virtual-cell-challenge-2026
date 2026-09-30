import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import tarfile
import direct_t28_submission as run


class DirectSubmissionTest(unittest.TestCase):
    def metadata(self):
        pack = json.loads((run.REPO/'reports/invii/trial_2026-09-29/t27_packaging.json').read_text())
        pack['input']['sha256'] = run.GENERATION_SHA
        v = pack['verification']
        return {'completion.json': {'status': 'complete', 'prediction_sha256': run.GENERATION_SHA,
                                   'vcc_sha256': v['archive_sha256']},
            'transfer_verification.json': {'sha256': v['archive_sha256'], 'bytes': v['archive_bytes'],
                                          'local_vs_drive_full_sha256': 'identical'},
            'stage45_checkpoint/complete.json': {'sha256': run.GENERATION_SHA,
                'bytes': pack['input']['bytes'], 'full_sha256_verified': True, 'scientific_recipe_unchanged': True},
            'pack/packaging.json': pack, 'pack/manifest_48_package_prediction.json': {},
            'gen/manifest_45_generate_prediction.json': {'config': {'trial': 'trial-ext-profile',
                'contexts': 'A,B,C', 'cells_per_pert': 400, 'seed': 20260912, 'gene_dispersion': True,
                'gene_dispersion_scale': 1., 'depth_bins': False, 'effects_scale': 1.5}},
            'gen/generation_diagnostics.json': {}, 'launch_review.json': {
                'registration_sha256': run.REGISTRATION_SHA, 'manifest_sha256': run.MANIFEST_SHA,
                'confirmation_sha256': run.CONFIRMATION_SHA, 'code_archive_sha256': run.ARCHIVE_SHA}}

    def test_complete_receipt_contract_and_false_payload_rejection(self):
        docs = self.metadata()
        self.assertEqual(run.verify_metadata(docs)[2], 2165150493)
        for key in ('matches_input', 'x_arrays_bit_identical'):
            altered = copy.deepcopy(docs)
            altered['pack/packaging.json']['verification']['payload_vs_input'][key] = False
            with self.assertRaisesRegex(ValueError, 'Payload equality'):
                run.verify_metadata(altered)
        for key, value in [('effects_scale', 1.), ('depth_bins', True), ('cells_per_pert', 399)]:
            altered = copy.deepcopy(docs)
            altered['gen/manifest_45_generate_prediction.json']['config'][key] = value
            with self.assertRaisesRegex(ValueError, 'parameters'):
                run.verify_metadata(altered)

    def test_full_hash_is_bounded_and_rejects_size_digest_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'x.vcc'; path.write_bytes(b'a'*23)
            good = run.digest(path)
            self.assertEqual(run.full_hash_checked(path, 23, good, Path(tmp), 0)['bytes'], 23)
            for size, sha in [(22, good), (23, '0'*64)]:
                with self.assertRaises(ValueError):
                    run.full_hash_checked(path, size, sha, Path(tmp), 0)
            with self.assertRaisesRegex(ValueError, 'reserve'):
                run.full_hash_checked(path, 23, good, Path(tmp), 10**30)

    def test_in_place_validation_creates_only_small_receipts_no_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'drive'; source.mkdir()
            path = source/'prediction.vcc'
            docs = self.metadata()
            # Tiny synthetic TAR tests the IO contract, not stage48 scientific validity.
            with tarfile.open(path, 'w') as archive:
                for name, value in [('meta.json', json.dumps(docs['pack/packaging.json']['verification']['meta_from_archive']).encode()),
                                    ('pred.h5ad.zst', b'fake-compressed-payload-for-contract-test')]:
                    info = tarfile.TarInfo(name); info.size = len(value)
                    archive.addfile(info, io.BytesIO(value))
            expected, size = run.digest(path), path.stat().st_size
            docs['completion.json']['vcc_sha256'] = expected
            docs['transfer_verification.json'].update(sha256=expected, bytes=size)
            docs['pack/packaging.json']['verification'].update(archive_sha256=expected, archive_bytes=size)
            for name, value in docs.items():
                dest = source/name; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(value))
            with patch.object(run.subprocess, 'run', side_effect=AssertionError('Unexpected process/upload')):
                receipt = run.validate(source, root/'receipt', root, 0)
            self.assertFalse(receipt['uploaded'])
            self.assertFalse(receipt['container_copied'])
            self.assertEqual(list(root.rglob('*.vcc')), [path])
            self.assertEqual(run.digest(path), expected)
            self.assertEqual(receipt['model_name'], 'trial-28 amplified multi-source transfer with control-fitted gene dispersion')

    def test_resume_wrong_file_stops_before_official_cli(self):
        from vcc import auth
        with patch.object(auth, 'get_pending_upload', return_value={'local_path': 'wrong.vcc'}), \
             patch.object(run.subprocess, 'run', side_effect=AssertionError('Unexpected upload')):
            with self.assertRaisesRegex(ValueError, 'different container'):
                run.submit({'source': 'right.vcc'}, Path('unused'), 'test-entry')


if __name__ == '__main__':
    unittest.main()
