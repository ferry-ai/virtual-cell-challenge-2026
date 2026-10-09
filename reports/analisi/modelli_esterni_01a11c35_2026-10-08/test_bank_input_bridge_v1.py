"""Tiny fixtures against the actual unchanged bank content resolver."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from bank_input_bridge_v1 import bind,stage_exports,transport_gate,digest

DRIVER=Path(__file__).resolve().parent.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco/logo_driver.py'
PIN='a11aafd8a3850f6c93f028436b6b7acef777c12d31e4444a79028e4f0eafd8d1'


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.native=self.root/'native';self.native.mkdir()
        self.staged=self.root/'staged';self.staged.mkdir()
        spec=importlib.util.spec_from_file_location('frozen_bank_fixture',DRIVER)
        self.driver=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,generate_contract=types.ModuleType('generate_contract')):
            spec.loader.exec_module(self.driver)
        self.driver.WORKING=self.root

    def test_original_resolver_unchanged_and_sees_both_roots(self):
        original=self.native/'original.npz';original.write_bytes(b'native fixture')
        pin=dict(bytes=original.stat().st_size,sha256=digest(original))
        self.driver.INPUTS=self.native
        before=self.driver._by_content(pin,'T0')
        extra=self.staged/'export.npz';extra.write_bytes(b'export fixture')
        bind(self.driver,DRIVER,PIN,self.native,self.staged)
        self.assertEqual(self.driver._by_content(pin,'T0'),before)
        self.assertEqual(self.driver._by_content(dict(bytes=extra.stat().st_size,sha256=digest(extra)),'AMMI'),extra)
        self.assertEqual(digest(DRIVER),PIN)

    def test_changed_driver_rejected(self):
        with self.assertRaises(ValueError):bind(self.driver,DRIVER,'0'*64,self.native,self.staged)

    def setup_transport(self):
        body=b'tiny prediction fixture';key=hashlib.sha256(body).hexdigest()
        files=[dict(bytes=len(body),sha256=key)]
        auth=dict(status='authorized',plan_sha256='plan',payloads=files)
        loc={key:dict(bytes=len(body),url='https://example.invalid/private-test')}
        return body,files,auth,loc

    def test_exact_transport_and_duplicate_payload_dedup(self):
        body,files,auth,loc=self.setup_transport()
        result=stage_exports('plan',files+files,auth,loc,self.root/'download',fetch=lambda url:[body[:3],body[3:]])
        self.assertEqual(len(result),1);self.assertTrue(result[0]['verified'])

    def test_missing_or_wrong_consent_fails_before_creation(self):
        body,files,auth,loc=self.setup_transport();auth['plan_sha256']='wrong'
        out=self.root/'refused'
        with self.assertRaises(ValueError):stage_exports('plan',files,auth,loc,out,fetch=lambda url:[body])
        self.assertFalse(out.exists())

    def test_corrupt_payload_and_excess_locator_rejected(self):
        body,files,auth,loc=self.setup_transport()
        with self.assertRaises(ValueError):stage_exports('plan',files,auth,loc,self.root/'corrupt',fetch=lambda url:[b'x'*len(body)])
        loc['0'*64]=dict(bytes=1,url='https://example.invalid/excess')
        with self.assertRaises(ValueError):transport_gate('plan',files,auth,loc)


if __name__=='__main__':unittest.main()
