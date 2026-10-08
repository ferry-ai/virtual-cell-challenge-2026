"""Verify transport recovery, terminal errors and ownership of partial files."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from private_download_v2 import download_verified


class PrivateDownloadTests(unittest.TestCase):
    def test_transient_open_retry(self):
        data=b'small synthetic fixture'
        with tempfile.TemporaryDirectory() as tmp, patch('private_download_v2.time.sleep'), patch(
            'private_download_v2.urllib.request.urlopen', side_effect=[urllib.error.URLError(OSError(110, 'secret url')),io.BytesIO(data)]) as call:
            out=Path(tmp)/'chunk.npz'; log=io.StringIO()
            with contextlib.redirect_stdout(log):
                self.assertEqual(download_verified('private-secret',out,len(data),hashlib.sha256(data).hexdigest()),len(data))
            self.assertEqual(out.read_bytes(),data)
            self.assertEqual(call.call_count,2)
            self.assertNotIn('secret',log.getvalue())

    def test_partial_read_retry(self):
        class Broken(io.BytesIO):
            def read(self, *args):
                if self.tell():raise ConnectionResetError('private-secret')
                return super().read(2)
        data=b'fixture'
        with tempfile.TemporaryDirectory() as tmp, patch('private_download_v2.time.sleep'), patch(
            'private_download_v2.urllib.request.urlopen', side_effect=[Broken(data),io.BytesIO(data)]):
            out=Path(tmp)/'chunk.npz'
            with contextlib.redirect_stdout(io.StringIO()):
                download_verified('private-secret',out,len(data),hashlib.sha256(data).hexdigest())
            self.assertEqual(out.read_bytes(),data)
            self.assertFalse(out.with_suffix('.partial').exists())

    def test_http_auth_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp, patch('private_download_v2.urllib.request.urlopen',
            side_effect=urllib.error.HTTPError('private-secret',403,'secret',{},None)) as call:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                download_verified('private-secret',Path(tmp)/'chunk.npz',1,'unused')
            self.assertEqual(call.call_count,1)

    def test_hash_failure_no_promotion(self):
        with tempfile.TemporaryDirectory() as tmp, patch('private_download_v2.urllib.request.urlopen',return_value=io.BytesIO(b'x')) as call:
            out=Path(tmp)/'chunk.npz'
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                download_verified('private-secret',out,1,'wrong')
            self.assertFalse(out.exists());self.assertFalse(out.with_suffix('.partial').exists())
            self.assertEqual(call.call_count,1)

    def test_existing_partial_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch('private_download_v2.urllib.request.urlopen') as call:
            out=Path(tmp)/'chunk.npz'; partial=out.with_suffix('.partial');partial.write_bytes(b'prior')
            with self.assertRaises(FileExistsError):download_verified('private-secret',out,1,'unused')
            self.assertEqual(partial.read_bytes(),b'prior');call.assert_not_called()


if __name__ == '__main__':unittest.main()
