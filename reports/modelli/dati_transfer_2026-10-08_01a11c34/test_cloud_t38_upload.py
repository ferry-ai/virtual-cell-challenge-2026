"""Offline checks that no wrong destination or unverified upload can pass."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent


class CloudUploadTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.work=self.root/'work';self.inputs=self.root/'input'
        self.work.mkdir();self.inputs.mkdir()
        def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
        support=SimpleNamespace(_verify_embedded=lambda _:None,_guard_resources=lambda:{},_sha256=digest,
            _write=lambda p,v:Path(p).write_text(json.dumps(v)))
        contract=SimpleNamespace(emission=lambda:{})
        with patch.dict(sys.modules,{'emission_support':support,'generate_contract':contract}):
            code=runpy.run_path(str(HERE/'package_upload_t38.py'),run_name='fixture')
        self.main=code['main'];self.main.__globals__.update(WORK=self.work,TEMP=self.root/'temp',INPUT=self.inputs)
        self.params=dict(product='test.vcc',mode='upload',source_job='owner/fit',input_generation_job='owner/gen',
            embedded_sha256={},protocol={},prediction={},fit_receipt={})
        self.cap=dict(entry_id='test-entry',upload_url='https://storage.googleapis.com/upload/storage/v1/test?upload_id=fixture')
        (self.inputs/'test.vcc').write_bytes(b'only a fixture, never uploaded')
        digest_value=digest(self.inputs/'test.vcc');size=(self.inputs/'test.vcc').stat().st_size
        self.params['input_product']=dict(bytes=size,sha256=digest_value)
        documents={
            'compact_diagnostics.json':dict(shape=dict(n_cells=360000,n_perturbations=300,cells_per_pert=400,contexts=['A','B','C']),is_pilot=False,context_provenance_ok=True,seed=20260912),
            'generation_preflight.json':dict(protocol={},prediction={},fit_receipt={},effects={c:dict(sha256='b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6') for c in 'ABC'}),
            'packaging.json':dict(exit_code=0,package=dict(n_obs=360000,n_vars=18533),verification=dict(official_container_validator='passed',payload_vs_input=dict(matches_input=True,x_arrays_bit_identical=True),archive_sha256=digest_value,archive_bytes=size,nnz_from_archive=123))}
        self.params['source_receipts']={}
        for name,doc in documents.items():
            p=self.inputs/name;p.write_text(json.dumps(doc));self.params['source_receipts'][name]=dict(bytes=p.stat().st_size,sha256=digest(p))
        (self.work/'params.json').write_text(json.dumps(self.params))

    def run_with(self,verified):
        (self.work/'delivery_capability.json').write_text(json.dumps(self.cap))
        upload=SimpleNamespace(upload_file=lambda *a,**k:SimpleNamespace(verified=verified,bytes_sent=self.params['input_product']['bytes'],md5_local='a',md5_remote='a' if verified else 'b'))
        with patch.dict(sys.modules,{'vcc.upload':upload}):self.main()

    def test_non_gcs_capability_is_rejected_before_upload(self):
        self.cap['upload_url']='https://example.invalid/untrusted'
        with self.assertRaisesRegex(ValueError,'official GCS'):self.run_with(True)
        self.assertFalse((self.work/'upload_receipt.json').exists())

    def test_missing_remote_checksum_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'MD5 verification'):self.run_with(False)
        self.assertFalse((self.work/'upload_receipt.json').exists())

    def test_matching_checksum_produces_only_scoped_entry_receipt(self):
        self.run_with(True)
        receipt=json.loads((self.work/'upload_receipt.json').read_text())
        self.assertEqual(receipt['entry_id'],'test-entry');self.assertTrue(receipt['md5_verified'])
        self.assertFalse(receipt['api_token_present']);self.assertFalse(receipt['scoring_launched'])


if __name__=='__main__':unittest.main()
