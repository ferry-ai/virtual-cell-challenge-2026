"""Verify the approved Stack source and pulled source without executing either."""
import ast
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).parent
LOCAL = BASE / 'neural/stack_kaggle_fresh_r2/stack_pilot_r2.ipynb'
REMOTE = BASE / 'kaggle_stack_inputs_r1/pull_after_push_r1/vcc-stack-pilot-r1.ipynb'
EXPECTED = '742b7cee9f2a5677b154bd495d59e0e7d35e8dec7dd616b9fb8d08fadfd39d7a'


def code(path):
    notebook = json.loads(path.read_text(encoding='utf-8'))
    return [''.join(cell['source']).replace('\r\n', '\n')
            for cell in notebook['cells'] if cell['cell_type'] == 'code']


def main():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(LOCAL) == EXPECTED
    local, remote = code(LOCAL), code(REMOTE)
    assert local == remote, 'Remote code differs from approved notebook'
    for source in remote:
        ast.parse(source)
    metadata = json.loads(REMOTE.with_name('kernel-metadata.json').read_text())
    assert metadata['id'] == 'davidmaisterx/vcc-stack-pilot-r1'
    assert metadata['is_private'] is True
    assert metadata['enable_gpu'] is True
    assert metadata['enable_internet'] is True
    assert metadata['dataset_sources'] == ['davidmaisterx/vcc-stack-prompts-r1']
    assert metadata['kernel_sources'] == []
    out = BASE / 'kaggle_stack_inputs_r1/pull_verification_r1.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump({'local_notebook_sha256': sha(LOCAL), 'remote_notebook_sha256': sha(REMOTE),
                   'remote_metadata_sha256': sha(REMOTE.with_name('kernel-metadata.json')),
                   'code_cells_equal': True, 'code_cells': len(remote), 'syntax_valid': True,
                   'metadata_expected_private_sources_gpu_internet': True,
                   'whole_notebook_byte_identity_claimed': False}, stream, indent=2)
        stream.write('\n')
    print(out)


if __name__ == '__main__':
    main()
