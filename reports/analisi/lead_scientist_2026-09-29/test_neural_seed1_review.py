"""Offline review of frozen seed-1 notebook; no import or execution of its runtime."""
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent


def command_ast(path):
    return next(node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.List)
                and any(isinstance(item, ast.Constant) and item.value == '--selection-seed' for item in node.elts))


def main():
    out = HERE/'kaggle_neural_seed1_r1/review'
    review = json.loads((out/'review_manifest.json').read_text())
    payload = (out/'runtime_payload.tar.gz').read_bytes()
    assert hashlib.sha256(payload).hexdigest() == review['payload_sha256']
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
        files = {m.name:archive.extractfile(m).read() for m in archive.getmembers()}
    assert len(files) == len(review['code_allowlist']) == 14
    for item in review['code_allowlist']:
        assert len(files[item['path']]) == item['bytes']
        assert hashlib.sha256(files[item['path']]).hexdigest() == item['sha256']
        if item['path'].endswith('.py'):
            compile(files[item['path']],item['path'],'exec')
    reference = json.loads((HERE/'kaggle_neural_r1/review/review_manifest.json').read_text())
    for item in reference['code_allowlist']:
        if not item['path'].endswith('/read_neural_sources.py'):
            assert hashlib.sha256(files[item['path']]).hexdigest() == item['sha256']
    original = command_ast(HERE/'neural_kaggle_runner.py')
    replica = command_ast(HERE/'neural_seed1_runner_r1.py')
    seed_index = next(i+1 for i,n in enumerate(original.elts) if isinstance(n,ast.Constant) and n.value=='--seed')
    assert original.elts[seed_index].value=='0' and replica.elts[seed_index].value=='1'
    original.elts[seed_index].value='1'
    assert ast.dump(original,include_attributes=False)==ast.dump(replica,include_attributes=False)
    metadata = json.loads((out/'kernel-metadata.json').read_text())
    assert metadata['is_private'] is True and metadata['enable_internet'] is False
    assert metadata['dataset_sources']==[reference['dataset']] and not metadata['kernel_sources']
    notebook = json.loads((out/metadata['code_file']).read_text())
    source = ''.join(notebook['cells'][0]['source'])
    compile(source,'reviewed_notebook','exec')
    main_call = ast.parse(source).body[-1].value
    assert ast.literal_eval(main_call.args[1]) == review
    assert len(review['input_files'])==19 and sum(x['sha256'] is not None for x in review['input_files'].values())==16
    print('PASS: 14 payload hashes; four training files byte-identical; training command differs only seed0→1; 19 input sizes/16 hashes; private offline metadata; notebook syntax and embedded review identical')


if __name__=='__main__':
    main()
