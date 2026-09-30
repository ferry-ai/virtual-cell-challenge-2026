import copy
from pathlib import Path
import tempfile
import unittest
import ledger


class LedgerTest(unittest.TestCase):
    def record(self):
        return {'schema_version': 1, 'eid': 'E-20260929-001', 'revision': 1, 'previous_sha256': None,
            'recorded_utc': '2026-09-29T20:59:00+00:00', 'claim_type': 'operational_incident',
            **{key: key for key in ['title','symptom','cause','fix','regression_test','next_guard','scope']},
            'cause_verified': True, 'state': 'implemented',
            'evidence': [{'path': 'log.txt', 'sha256': 'a' * 64, 'supports': 'exception'}]}

    def test_append_revision_and_hash_chain_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            row = self.record(); first = ledger.append(temp, row)
            with self.assertRaises(ValueError):
                ledger.append(temp, row)
            update = copy.deepcopy(row); update |= {'revision': 2, 'previous_sha256': ledger.sha(first)}
            ledger.append(temp, update)
            self.assertEqual(ledger.index(temp)['incidents'][0]['revision'], 2)
            first.write_text('{}')
            with self.assertRaises(ValueError):
                ledger.index(temp)

    def test_cannot_claim_remote_success_without_hashed_evidence(self):
        row = self.record(); row['state'] = 'verified_remotely'
        with self.assertRaisesRegex(ValueError, 'Remote verification'):
            ledger.validate_record(row)
        row['remote_verification'] = {'evidence_path': 'other.txt', 'observed_utc': '2026-09-29T20:59:00Z', 'criterion': 'passed'}
        with self.assertRaisesRegex(ValueError, 'hashed evidence'):
            ledger.validate_record(row)


if __name__ == '__main__':
    unittest.main()
