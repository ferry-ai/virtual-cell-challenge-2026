"""Small fixtures for exact window retry, partial preservation and disk guards."""
import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import copy_t28_chunked as c


class Broken(io.BytesIO):
    def read(self, size=-1):
        if self.tell() >= 3:
            raise OSError(22, 'Injected Drive invalid argument')
        return super().read(min(size, 3))


class Tests(unittest.TestCase):
    def test_retry_whole_window_before_append_and_resume(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(c,'disk_guard',return_value=10**9), mock.patch.object(c.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
            root=Path(folder); source=root/'source'; partial=root/'prediction.vcc.partial'
            data=b'abcdefghijklmnopqrstuvwxyz'; source.write_bytes(data); partial.write_bytes(data[:2])
            calls=[]; handles=[]
            def opener(path):
                handle=Broken(data) if not calls else io.BytesIO(data)
                calls.append(path); handles.append(handle); return handle
            c.copy_payload(source,partial,len(data),hashlib.sha256(data).hexdigest(),c.identity(source),root,
                           reserve=1,window=8,opener=opener)
            self.assertEqual(partial.read_bytes(),data)
            self.assertEqual(len(calls),4)  # three good windows plus one retry
            self.assertTrue(all(h.closed for h in handles))

    def test_retry_is_bounded_and_partial_untouched(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(c,'disk_guard',return_value=10**9), mock.patch.object(c.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
            root=Path(folder); source=root/'source'; partial=root/'partial'
            source.write_bytes(b'abcdefgh'); partial.write_bytes(b'')
            with mock.patch.object(c,'READ',3):
                opener=mock.Mock(side_effect=lambda path:Broken(b'abcdefgh'))
                with self.assertRaises(OSError):
                    c.copy_payload(source,partial,8,'0'*64,c.identity(source),root,reserve=1,window=8,opener=opener)
            self.assertEqual(opener.call_count,4)
            self.assertEqual(partial.read_bytes(),b'')

    def test_wrong_hash_preserves_complete_partial(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(c,'disk_guard',return_value=10**9), contextlib.redirect_stdout(io.StringIO()):
            root=Path(folder); source=root/'source'; partial=root/'partial'
            source.write_bytes(b'abcdefgh'); partial.write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'SHA/size'):
                c.copy_payload(source,partial,8,'0'*64,c.identity(source),root,reserve=1,window=8)
            self.assertEqual(partial.read_bytes(),source.read_bytes())
            self.assertFalse((root/'prediction.vcc').exists())

    def test_disk_guard_before_source_read_and_source_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source'; partial=root/'partial'
            source.write_bytes(b'abc'); partial.write_bytes(b'')
            opener=mock.Mock()
            with mock.patch.object(c.shutil,'disk_usage',return_value=mock.Mock(free=8)):
                with self.assertRaises(OSError):
                    c.copy_payload(source,partial,3,'0'*64,c.identity(source),root,reserve=5,window=3,opener=opener)
            opener.assert_not_called()
            with self.assertRaisesRegex(ValueError,'identity changed'):
                c.copy_payload(source,partial,3,'0'*64,{'bytes':3,'mtime_ns':0},root)
            self.assertEqual(partial.stat().st_size,0)


if __name__=='__main__':
    unittest.main()
