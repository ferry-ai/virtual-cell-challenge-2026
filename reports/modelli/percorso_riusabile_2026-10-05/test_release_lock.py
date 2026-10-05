import json
from pathlib import Path
import tempfile
import unittest
from release_lock import resolve,sha


class ReleaseIdentityTest(unittest.TestCase):
    def test_rejects_same_name_old_content_and_changed_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);mount=root/'mounted';mount.mkdir()
            receipt=mount/'complete.json';receipt.write_text('current-bank')
            lock=root/'release.json'
            lock.write_text(json.dumps({'units':{'D1_Rest':{'bank':{
                'state':'remote_complete_manifest_checked','receipt_sha256':sha(receipt)}}}}))
            digest=sha(lock)
            self.assertEqual(resolve(lock,digest,'D1_Rest','bank',mount),mount)
            receipt.write_text('legacy-bank')
            with self.assertRaisesRegex(ValueError,'pinned release'):
                resolve(lock,digest,'D1_Rest','bank',mount)
            lock.write_text('{}')
            with self.assertRaisesRegex(ValueError,'lock changed'):
                resolve(lock,digest,'D1_Rest','bank',mount)

    def test_pending_never_falls_back_to_an_existing_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);lock=root/'release.json'
            lock.write_text(json.dumps({'units':{'D1_Rest':{'samples':{'state':'pending'}}}}))
            with self.assertRaisesRegex(ValueError,'no legacy fallback'):
                resolve(lock,sha(lock),'D1_Rest','samples',root)


if __name__=='__main__':
    unittest.main()
