"""Read-only byte/AST verification of prepared B notebook, never executing its code."""
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).parent
FOLDER = HERE / 'neural/stack_variant_b_runtime_r1'
EXPECTED = '9e5f87d176f24953cd543b492dbdc924fbe4ea630187c40c64dff7717596b579'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    notebook_path = FOLDER / 'stack_variant_b_r1.ipynb'
    assert sha(notebook_path.read_bytes()) == EXPECTED
    notebook = json.loads(notebook_path.read_text())
    cells = [''.join(cell['source']) for cell in notebook['cells'] if cell['cell_type'] == 'code']
    assert len(cells) == 1
    assert cells[0].replace('\r\n', '\n') == (FOLDER / 'stack_variant_b_r1.py').read_text().replace('\r\n', '\n')
    tree = ast.parse(cells[0])
    call = tree.body[-1].value
    assert isinstance(call, ast.Call) and call.func.id == 'main' and len(call.args) == 2
    payload = base64.b64decode(ast.literal_eval(call.args[0]), validate=True)
    embedded = ast.literal_eval(call.args[1])
    review = json.loads((FOLDER / 'review_manifest.json').read_text())
    assert embedded == review
    assert sha(payload) == review['code_archive_sha256']
    assert payload == (FOLDER / 'code_snapshot.tar.gz').read_bytes()
    expected = {item['path']: item for item in review['code_files']}
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(expected) == 15
        assert {item.name for item in members} == set(expected)
        for item in members:
            assert item.isfile() and not item.issym()
            content = archive.extractfile(item).read()
            assert len(content) == expected[item.name]['bytes']
            assert sha(content) == expected[item.name]['sha256']
    old = json.loads((HERE / 'neural/stack_kaggle_fresh_r2/review_manifest.json').read_text())
    old_files = {item['path']: item for item in old['code_files']}
    assert all(expected[name] == item for name, item in old_files.items())
    unchanged = ['dataset', 'bundle_manifest_sha256', 'bundle_files', 'targets', 'plan_sha256',
                 'model_files', 'model_repository', 'model_revision', 'runtime_fixes', 'resource_guards']
    assert all(review[key] == old[key] for key in unchanged)
    old_tree = ast.parse((HERE / 'neural/stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py').read_text())
    functions = lambda t: {n.name: ast.dump(n) for n in t.body if isinstance(n, ast.FunctionDef) and n.name != 'main'}
    assert functions(tree) == functions(old_tree)
    metadata = json.loads((FOLDER / 'kernel-metadata.json').read_text())
    assert metadata['id'] == 'davidmaisterx/vcc-stack-variant-b-r1'
    assert metadata['is_private'] and metadata['enable_gpu'] and metadata['enable_internet']
    assert metadata['dataset_sources'] == ['davidmaisterx/vcc-stack-prompts-r1']
    assert metadata['kernel_sources'] == metadata['competition_sources'] == metadata['model_sources'] == []
    result = {'notebook_sha256': EXPECTED, 'payload_sha256': sha(payload), 'members_verified': 15,
              'original_members_unchanged': len(old_files), 'helper_functions_ast_identical': True,
              'scientific_inputs_and_runtime_guards_unchanged': unchanged,
              'code_executed': False, 'remote_action': False}
    out = HERE / 'kaggle_stack_variant_b_review_r1.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
