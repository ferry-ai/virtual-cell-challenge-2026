"""Offline rejection tests; no real consent, credentials, network or locators."""
import copy
import subprocess
import sys
import unittest
from unittest.mock import patch
import issue_production_mx_private_access_r1 as emitter


class ConsentGateTests(unittest.TestCase):
    def setUp(self):
        self.job = emitter.JOB
        self.auth = dict(granted=True, original_human_response_read_directly=True,
            production_inputs_authorized=True, destination_owner=emitter.OWNER,
            destination_job=self.job, purpose=emitter.PURPOSE, private_only=True,
            plan_sha256='fixture-plan', emitter_sha256='fixture-code',
            file_count=209, total_bytes=10100920946,
            temporary_bearer_urls_explicitly_authorized=True,
            all_209_payloads_including_119_pilot_hashes_authorized=True,
            source_thread_id='fixture-not-real', source_user_message_id='fixture-not-real',
            original_answer='SYNTHETIC TEST ONLY: never saved as authorization')

    def check(self, auth):
        return emitter.validate_authorization(auth, 'fixture-plan', 'fixture-code', self.job)

    def test_exact_synthetic_scope(self):
        self.check(self.auth)

    def test_complete_offline_guard_with_actual_frozen_plan(self):
        auth = dict(self.auth, plan_sha256=emitter.PLAN_SHA,
                    emitter_sha256=emitter.sha(emitter.__file__))
        real_read = emitter.read
        def fixture_read(path):
            return auth if path == 'IN_MEMORY_TEST_ONLY' else real_read(path)
        with patch.object(emitter, 'read', side_effect=fixture_read):
            plan = emitter.guard('IN_MEMORY_TEST_ONLY', self.job)
        self.assertEqual(len(plan['files']), 209)

    def test_different_mx_job_is_rejected(self):
        with self.assertRaises(ValueError):
            emitter.validate_authorization(self.auth, 'fixture-plan', 'fixture-code',
                                           self.job + '-different')

    def test_scope_mutations_all_rejected(self):
        mutations = dict(granted=False, production_inputs_authorized=False,
            destination_owner='davideferrante11', destination_job=self.job + '-other',
            purpose='pilot', private_only=False, plan_sha256='changed',
            emitter_sha256='changed', file_count=134, total_bytes=1,
            original_human_response_read_directly=False,
            temporary_bearer_urls_explicitly_authorized=False,
            all_209_payloads_including_119_pilot_hashes_authorized=False,
            source_user_message_id='', original_answer='')
        for key, value in mutations.items():
            with self.subTest(field=key):
                auth = copy.deepcopy(self.auth); auth[key] = value
                with self.assertRaises(ValueError):
                    self.check(auth)

    def test_real_pilot_consent_is_rejected(self):
        with self.assertRaises(ValueError):
            self.check(emitter.read(emitter.HERE / 'ammi_private_access_authorization_r1.json'))

    def test_changed_plan_rejected_before_auth_read(self):
        with patch.object(emitter, 'sha', return_value='changed'), patch.object(emitter, 'read') as reader:
            with self.assertRaises(ValueError):
                emitter.guard('does-not-exist.json', self.job)
            reader.assert_not_called()

    def test_repository_cannot_hold_bearers(self):
        with self.assertRaises(ValueError):
            emitter.safe_stage(emitter.HERE / 'private-output')

    def test_actual_cli_closed_even_with_issue(self):
        result = subprocess.run([sys.executable, emitter.__file__, '--authorization',
            str(emitter.HERE / 'production_mx_private_authorization_template_r1.json'),
            '--job', self.job, '--issue'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('ValueError', result.stderr)
        self.assertNotIn('https://', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
