import unittest
from unittest.mock import patch
import httpx
from vcc2026.remote_ranges import HTTPRangeReader

class RangeTests(unittest.TestCase):
    def reader(self,body=b'abcdefghijklmnopqrstuvwxyz'*20,budget=1024,status=206):
        def handler(request):
            a,b=map(int,request.headers['Range'][6:].split('-'))
            b=min(b,len(body)-1)
            return httpx.Response(status,headers={'Content-Range':f'bytes {a}-{b}/{len(body)}'},content=body[a:b+1])
        client=httpx.Client(transport=httpx.MockTransport(handler))
        with patch('vcc2026.remote_ranges.httpx.Client',return_value=client):
            return HTTPRangeReader('https://example.test/data',max_bytes=budget,block_size=128)

    def test_random_access_cache_and_eof(self):
        with self.reader() as r:
            r.seek(120); self.assertEqual(len(r.read(30)),30)
            used=r.transferred
            r.seek(120); r.read(30); self.assertEqual(r.transferred,used)
            r.seek(-3,2); self.assertEqual(r.read(),b'xyz')
            self.assertEqual(r.read(),b'')

    def test_refuses_full_download(self):
        with self.assertRaisesRegex(RuntimeError,'refusing full download'): self.reader(status=200)

    def test_budget_is_cumulative(self):
        with self.reader(budget=128) as r:
            r.seek(128)
            with self.assertRaisesRegex(RuntimeError,'budget'): r.read(1)

    def test_small_file_and_invalid_seek(self):
        with self.reader(body=b'123') as r:
            self.assertEqual(r.read(),b'123')
            with self.assertRaises(ValueError): r.seek(-1)

if __name__=='__main__': unittest.main()
