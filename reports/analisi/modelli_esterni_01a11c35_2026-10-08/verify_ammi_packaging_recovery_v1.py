"""Reproduce the old packaging guard, then verify every recovered archive member."""
import ast
import base64
import hashlib
import io
import json
import lzma
from pathlib import Path
import tempfile
import zipfile
from compact_ammi_package_v1 import compact
from ammi_inputs_v3 import checked
from continue_ammi_cells_once_v1 import write_new, now
from resume_ammi_cells_dispatch_v1 import no_prior_push

HERE = Path(__file__).resolve().parent


def members(pin, compressed):
    text = checked(pin).read_text()
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(text).body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id in ('PAYLOAD', 'DIGEST')}
    raw = base64.b64decode(constants['PAYLOAD'])
    if compressed:
        raw = lzma.decompress(raw)
    assert hashlib.sha256(raw).hexdigest() == constants['DIGEST']
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def main():
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        try:
            compact(HERE/'ammi_c-ipsc_cells_prepared_r1.json', tmp/'package', tmp/'receipt.json')
        except ValueError as error:
            assert str(error) == 'source still exceeds conservative 1MB bound'
        else:
            raise AssertionError('original packaging failure did not reproduce')
        no_prior_push(tmp)
        guard_cases = 0
        for fold in ('c-k562', 'c-ipsc'):
            for suffix in ('.json', '.json.intent.json', '.json.lock'):
                case = tmp/(fold+str(guard_cases)); case.mkdir()
                (case/('ammi_'+fold+'_cells_auto_launch_r1'+suffix)).touch()
                try:
                    no_prior_push(case)
                except ValueError:
                    guard_cases += 1
                else:
                    raise AssertionError('prior push guard failed')
    verification = []
    for fold in ('c-k562', 'c-ipsc'):
        before = json.loads((HERE/('ammi_'+fold+'_cells_prepared_r1.json')).read_text())
        after = json.loads((HERE/('ammi_'+fold+'_cells_prepared_r2.json')).read_text())
        original, recovered = members(before['code'], False), members(after['code'], True)
        assert original == recovered
        assert checked(before['metadata']).read_bytes() == checked(after['metadata']).read_bytes()
        verification.append(dict(fold=fold, members=len(original),
                                 all_members_byte_identical=True, metadata_byte_identical=True,
                                 recovered_code_sha256=after['code']['sha256']))
    result = dict(utc=now(), status='PASS', original_failure_reproduced=True,
                  prior_push_guard_cases=guard_cases, folds=verification,
                  scientific_code_changed=False, cloud_jobs_launched=0)
    write_new(HERE/'ammi_packaging_recovery_verified_r1.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
