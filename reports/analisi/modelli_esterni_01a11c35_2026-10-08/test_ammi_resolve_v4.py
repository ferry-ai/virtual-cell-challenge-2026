"""Small tests of mounted pin integrity and disposable response downloads."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ammi_resolve_v4 import Resolver,ResponseLocations
from pie_adapter import sha256

class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.mount=self.root/'mount';self.mount.mkdir()
        self.file=self.mount/'chunk.npz';self.file.write_bytes(b'synthetic')
        self.pin=dict(path='unused',bytes=self.file.stat().st_size,sha256=sha256(self.file))
    def tearDown(self):self.temp.cleanup()

    def test_native_mount_is_verified_and_never_deleted_on_release(self):
        resolver=Resolver([self.mount],self.root/'cache')
        locations=ResponseLocations(resolver,{self.pin['sha256']:self.pin})
        self.assertEqual(Path(locations[self.pin['sha256']]),self.file)
        locations.release(self.pin['sha256']);self.assertTrue(self.file.exists())
        with self.assertRaisesRegex(ValueError,'unavailable'):
            resolver.resolve(dict(self.pin,sha256='0'*64))

    def test_download_consumes_only_one_chunk_then_releases_owned_cache(self):
        class Reply:
            status_code=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def iter_content(self,size):yield b'synthetic'
        spec=dict(self.pin,url='https://example.invalid/private')
        resolver=Resolver([],self.root/'cache',{self.pin['sha256']:spec})
        with patch('ammi_resolve_v4.requests.get',return_value=Reply()):
            path=resolver.resolve(self.pin)
        self.assertTrue(path.exists());resolver.release(self.pin['sha256'])
        self.assertFalse(path.exists());self.assertTrue(self.file.exists())

    def test_transport_failure_does_not_expose_private_locator(self):
        import requests
        spec=dict(self.pin,url='https://example.invalid/private?secret=opaque')
        resolver=Resolver([],self.root/'cache',{self.pin['sha256']:spec})
        with patch('ammi_resolve_v4.requests.get',side_effect=requests.ConnectionError(spec['url'])):
            with self.assertRaises(RuntimeError) as captured:resolver.resolve(self.pin)
        self.assertNotIn('secret',str(captured.exception));self.assertNotIn('https',str(captured.exception))

if __name__=='__main__':unittest.main()
