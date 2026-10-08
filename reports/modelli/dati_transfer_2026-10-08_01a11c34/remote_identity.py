"""Read one saved kernel identity in an account-isolated process."""
import hashlib
import importlib.util
import json
import sys
from percorso import BANK

spec=importlib.util.spec_from_file_location('canonical',BANK/'percorso.py')
bank=importlib.util.module_from_spec(spec);spec.loader.exec_module(bank)
try:
    saved=bank.saved_kernel(sys.argv[1],sys.argv[2])
    print(json.dumps(dict(source_sha256=hashlib.sha256(saved.blob.source.replace('\r\n','\n').encode()).hexdigest(),
        version=saved.metadata.current_version_number,is_private=saved.metadata.is_private)))
except Exception as exc:
    response=getattr(exc,'response',None)
    print(str(exc)+((': '+response.text[:4000]) if response is not None else ''),file=sys.stderr)
    raise SystemExit(1)
