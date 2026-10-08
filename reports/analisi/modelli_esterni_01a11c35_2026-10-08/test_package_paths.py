"""Regression for Windows-built packages targeting Kaggle Linux."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from check_private_package import check


class PackageTests(unittest.TestCase):
    def package(self, root, remote, input_path, contents=b'x=1\n'):
        data=b'x=1\n'
        contract=dict(inputs=[dict(id='module',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            paths={'runtime':input_path})],outputs=[dict(paths={'runtime':'/kaggle/working/job/fit'},must_be_absent=True)])
        zipped=io.BytesIO()
        with zipfile.ZipFile(zipped,'w',compression=zipfile.ZIP_LZMA) as z:
            z.writestr('module.py',contents)
            z.writestr('preflight.json',json.dumps(contract))
            z.writestr('job_config.json',json.dumps(dict(queries=[])))
        source=f'root=Path({remote!r})\npayload={base64.b64encode(zipped.getvalue()).decode()!r}\n'.encode()
        (root/'run.py').write_bytes(source)
        prepared=root/'prepared.json'
        prepared.write_text(json.dumps(dict(stage=str(root),code_sha256=hashlib.sha256(source).hexdigest(),queries=0,job_id='fixture')))
        return prepared

    def test_windows_serialization_is_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=self.package(root,r'\kaggle\temp\bundle',r'\kaggle\temp\bundle\module.py')
            with self.assertRaisesRegex(ValueError,'absolute POSIX'):
                check(path)

    def test_extraction_and_input_contract_must_agree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=self.package(root,'/kaggle/temp/bundle',r'\kaggle\temp\bundle\module.py')
            with self.assertRaisesRegex(ValueError,'extraction'):
                check(path)
            path=self.package(root,'/kaggle/temp/bundle','/kaggle/temp/bundle/module.py')
            self.assertEqual(check(path)['status'],'PASS')

    def test_payload_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.package(Path(tmp),'/kaggle/temp/bundle','/kaggle/temp/bundle/module.py',b'x=2\n')
            with self.assertRaisesRegex(ValueError,'hash or size'):
                check(path)


if __name__=='__main__':unittest.main()
