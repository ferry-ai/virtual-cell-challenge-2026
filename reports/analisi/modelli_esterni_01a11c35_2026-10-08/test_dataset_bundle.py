"""Regress source-size limits and checksum-pinned private dataset packaging."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_private_package_v2 import check
from test_package_paths import PackageTests


class DatasetBundleTests(unittest.TestCase):
    def test_dataset_package_and_corrupt_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            prepared_path=PackageTests().package(root,'/kaggle/temp/bundle','/kaggle/temp/bundle/module.py')
            prepared=json.loads(prepared_path.read_text())
            assignments=ast.parse((root/'run.py').read_text()).body
            data=base64.b64decode(ast.literal_eval(assignments[1].value))
            archive=root/'bundle.bin';archive.write_bytes(data)
            digest=hashlib.sha256(data).hexdigest()
            source=('root=Path("/kaggle/temp/bundle")\nbundle_sha256='+repr(digest)+'\n').encode()
            (root/'run.py').write_bytes(source)
            prepared.update(code_sha256=hashlib.sha256(source).hexdigest(),
                            bundle_dataset=dict(path=str(archive),bytes=len(data),sha256=digest))
            prepared_path.write_text(json.dumps(prepared))
            self.assertEqual(check(prepared_path)['status'],'PASS')
            archive.write_bytes(data+b'bad')
            with self.assertRaisesRegex(ValueError,'bundle differs'):check(prepared_path)

    def test_oversized_source_is_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            prepared_path=PackageTests().package(root,'/kaggle/temp/bundle','/kaggle/temp/bundle/module.py')
            source=(root/'run.py').read_bytes()+b'#'+b'x'*1000000
            (root/'run.py').write_bytes(source)
            prepared=json.loads(prepared_path.read_text());prepared['code_sha256']=hashlib.sha256(source).hexdigest()
            prepared_path.write_text(json.dumps(prepared))
            with self.assertRaisesRegex(ValueError,'size limit'):check(prepared_path)


if __name__=='__main__':unittest.main()
