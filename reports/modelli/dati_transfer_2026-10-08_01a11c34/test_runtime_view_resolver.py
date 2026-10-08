"""Small resolver fixtures: frozen content, no fallback, and safe failure logs."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import io
from runtime_view_resolver import resolve, sha


class ResolverTests(unittest.TestCase):
    def fixture(self, root, payload=b'frozen chunk', regime='T'):
        view=root/'view.json';digest=hashlib.sha256(payload).hexdigest()
        spec=dict(regime=regime,expected_rows_by_context={'clone':1},
            chunks=[dict(path='UNRESOLVED_MOUNT/p/job/effects/c.npz',producer='p/job',producer_file='effects/c.npz',
                sha256=digest,bytes=len(payload),targets=['ADMITTED'],weights=[1.0],context_id='clone')])
        view.write_text(json.dumps(spec));return view,digest

    def test_same_name_and_size_wrong_content_cannot_satisfy_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);view,digest=self.fixture(root);mount=root/'mount';mount.mkdir()
            (mount/'c.npz').write_bytes(b'changed data')
            with self.assertRaisesRegex(ValueError,'required chunk unavailable'):
                resolve(view,sha(view),[mount],root/'cache',root/'resolved.json')
            self.assertFalse((root/'resolved.json').exists())

    def test_locator_download_is_hashed_and_split_weights_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);view,digest=self.fixture(root);loc=root/'private.json'
            loc.write_text(json.dumps(dict(files={'p/job/effects/c.npz':dict(url='https://private.invalid/SECRET',sha256=digest,bytes=12)})))
            with patch('runtime_view_resolver.urllib.request.urlopen',return_value=io.BytesIO(b'frozen chunk')):
                result=resolve(view,sha(view),[],root/'cache',root/'resolved.json',loc)
            self.assertEqual(result['downloaded_bytes'],12)
            resolved=json.loads((root/'resolved.json').read_text());original=json.loads(view.read_text())
            for k in ('regime','expected_rows_by_context'):self.assertEqual(resolved[k],original[k])
            for k in ('targets','weights','context_id','sha256'):self.assertEqual(resolved['chunks'][0][k],original['chunks'][0][k])
            self.assertNotIn('SECRET',(root/'resolved.receipt.json').read_text())

    def test_changed_payload_rejected_and_provider_url_not_exposed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);view,digest=self.fixture(root);loc=root/'private.json'
            loc.write_text(json.dumps(dict(files={'p/job/effects/c.npz':dict(url='https://private.invalid/SECRET',sha256=digest,bytes=12)})))
            with patch('runtime_view_resolver.urllib.request.urlopen',side_effect=OSError('https://private.invalid/SECRET')):
                with self.assertRaises(ValueError) as got:resolve(view,sha(view),[],root/'cache',root/'resolved.json',loc)
            self.assertNotIn('SECRET',str(got.exception))
            with patch('runtime_view_resolver.urllib.request.urlopen',return_value=io.BytesIO(b'changed data')):
                with self.assertRaisesRegex(ValueError,'downloaded chunk identity differs'):
                    resolve(view,sha(view),[],root/'cache',root/'resolved.json',loc)
            self.assertFalse((root/'resolved.json').exists())


if __name__=='__main__':unittest.main()
