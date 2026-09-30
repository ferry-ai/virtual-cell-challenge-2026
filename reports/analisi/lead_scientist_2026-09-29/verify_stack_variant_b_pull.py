"""Verify approved B code cells and remote metadata without executing either."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent


def main():
    local = HERE / 'neural/stack_variant_b_runtime_r1/stack_variant_b_r1.ipynb'
    remote = HERE / 'kaggle_stack_variant_b_r1/pull_after_push_r1/vcc-stack-variant-b-r1.ipynb'
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    expected = '9e5f87d176f24953cd543b492dbdc924fbe4ea630187c40c64dff7717596b579'
    assert sha(local) == expected
    codes = lambda p: [''.join(c['source']).replace('\r\n', '\n')
                       for c in json.loads(p.read_text())['cells'] if c['cell_type'] == 'code']
    assert codes(local) == codes(remote)
    for code in codes(remote):
        ast.parse(code)
    metadata = json.loads(remote.with_name('kernel-metadata.json').read_text())
    assert metadata['id'] == 'davidmaisterx/vcc-stack-variant-b-r1'
    assert metadata['is_private'] and metadata['enable_gpu'] and metadata['enable_internet']
    assert metadata['dataset_sources'] == ['davidmaisterx/vcc-stack-prompts-r1']
    assert metadata['kernel_sources'] == metadata['competition_sources'] == metadata['model_sources'] == []
    out = HERE / 'kaggle_stack_variant_b_r1/pull_verification_r1.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump({'local_notebook_sha256': expected, 'remote_notebook_sha256': sha(remote),
                   'remote_metadata_sha256': sha(remote.with_name('kernel-metadata.json')),
                   'code_cells_exact': True, 'syntax_valid': True,
                   'metadata_expected_private_sources_gpu_internet': True,
                   'whole_notebook_byte_identity_claimed': False}, stream, indent=2)
        stream.write('\n')
    print(out)


if __name__ == '__main__':
    main()
