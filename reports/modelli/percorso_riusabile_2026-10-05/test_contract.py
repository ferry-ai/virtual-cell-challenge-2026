import copy
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from pipeline_state import catalogue_records, frozen_code, identity, sha
from training_contract import validate_manifest, validate_exposure, verify_artifacts


class ContractTests(unittest.TestCase):
    def test_frozen_code_matches_original_windows_hash_contract(self):
        payload = {'bank.py': {'sha256': 'a'*64}, 'preparation.py': {'sha256': 'b'*64},
                   'params.json': {'sha256': 'c'*64}}
        source = 'P='+repr(payload)+'\n'
        launch = {'slug': 'owner/job', 'code_sha256': hashlib.sha256(source.encode()).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'stages/job/run.py'; path.parent.mkdir(parents=True)
            path.write_bytes(source.replace('\n', '\r\n').encode())
            with patch('pipeline_state.CAMPAIGN', Path(temp)):
                self.assertEqual(frozen_code(launch), {'bank.py': 'a'*64, 'preparation.py': 'b'*64})
                path.write_text(source+'# changed\n')
                with self.assertRaisesRegex(ValueError, 'changed'):
                    frozen_code(launch)

    def test_catalogue_keeps_remote_and_ingested_evidence(self):
        records = catalogue_records({'remote': [{'id': 'a'}], 'ingested': [{'id': 'a'}],
                                     'aggregate_only': [['b', 'aggregate']]})
        self.assertEqual(len(records), 3)
        self.assertTrue(all(r['role'] == 'unresolved' for r in records))
        self.assertEqual(identity({'a': 1, 'b': 2}), identity({'b': 2, 'a': 1}))

    def test_no_silent_missing_source_or_open_adapter(self):
        manifest = {'catalogue_records': [], 'contexts': []}
        with self.assertRaisesRegex(ValueError, 'catalogue coverage'):
            validate_manifest(manifest, ['remote/a'])
        manifest['catalogue_records'] = [{'record_id': 'remote/a', 'role': 'unresolved'}]
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            validate_manifest(manifest, ['remote/a'])

    def test_changed_artifact_rejected_and_identical_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp)/'x'; f.write_bytes(b'original')
            item = {'path': 'x', 'bytes': 8, 'sha256': sha(f)}
            self.assertEqual(len(verify_artifacts([{'artifacts': [item, item]}], temp)), 1)
            f.write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'changed'):
                verify_artifacts([{'artifacts': [item]}], temp)

    def test_context_loss_and_held_targets_cannot_disappear(self):
        c = {'context_id': 'donor1', 'group': 'CD4T', 'role': 'supervision',
             'target_ids': ['G1', 'G2'], 'strata_by_target': {'G1': ['s1'], 'G2': ['s2']},
             'split_cells_sampled': 2}
        e = {'context_id': 'donor1', 'target_ids': ['G1'], 'stratum_ids': ['s1'],
             'cells_seen_unique': 2, 'control_cells_seen': 1, 'loss_weight_sum': 1}
        self.assertTrue(validate_exposure([c], [e], hidden_targets=['G2']))
        with self.assertRaisesRegex(ValueError, 'missing context'):
            validate_exposure([c], [])
        with self.assertRaisesRegex(ValueError, 'held context'):
            validate_exposure([c], [e], held_groups=['CD4T'])
        bad = copy.deepcopy(e); bad['target_ids'].append('G2')
        with self.assertRaisesRegex(ValueError, 'leakage'):
            validate_exposure([c], [bad], hidden_targets=['G2'])
        bad = copy.deepcopy(e); bad['loss_weight_sum'] = 0
        with self.assertRaisesRegex(ValueError, 'not actually consumed'):
            validate_exposure([c], [bad], hidden_targets=['G2'])


if __name__ == '__main__':
    unittest.main()
