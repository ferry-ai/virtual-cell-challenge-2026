"""Instrumentation must preserve return values and exceptions and hide payloads."""
import json
from pathlib import Path
import tempfile
import unittest
from ammi_timing_v1 import measured


class TimingTests(unittest.TestCase):
    def test_return_and_failure_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            value = object()
            self.assertIs(measured(folder, 'ok', lambda: value), value)
            failure = ValueError('private payload must not enter timing receipt')
            def fail():
                raise failure
            with self.assertRaises(ValueError) as caught:
                measured(folder, 'failure', fail)
            self.assertIs(caught.exception, failure)
            raw = (Path(folder)/'timing_failure.json').read_text()
            report = json.loads(raw)
            self.assertEqual(report['status'], 'ERROR')
            self.assertGreaterEqual(report['seconds'], 0)
            self.assertNotIn('private payload', raw)


if __name__ == '__main__':
    unittest.main()
