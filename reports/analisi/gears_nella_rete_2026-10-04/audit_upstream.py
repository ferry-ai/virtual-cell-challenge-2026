"""Small executable checks on pinned GEARS source; never imports GEARS/PyG."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads((a.source / 'manifest.json').read_text(encoding='utf-8-sig'))
    for item in manifest['files']:
        assert hashlib.sha256(Path(item['local']).read_bytes()).hexdigest() == item['sha256']
    tree = ast.parse((a.source / 'gears__utils.py').read_text())
    loss_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'loss_fct')
    scope = {'torch': torch, 'np': np}
    exec(compile(ast.Module(body=[loss_node], type_ignores=[]), '<pinned GEARS loss_fct>', 'exec'), scope)
    y = torch.tensor([[1., -1.], [0.5, -0.5]])
    ctrl = torch.zeros(2)
    pred0 = torch.tensor([[-0.2, 0.2], [-0.3, 0.3]], requires_grad=True)
    grads, values = [], []
    for direction in (0., 10.):
        prediction = pred0.detach().clone().requires_grad_(True)
        loss = scope['loss_fct'](prediction, y, ['A', 'A'], ctrl=ctrl,
                                 direction_lambda=direction, dict_filter={'A': [0, 1]})
        values.append(float(loss.detach()))
        grads.append(torch.autograd.grad(loss, prediction)[0])
    assert values[1] > values[0]
    assert torch.equal(grads[0], grads[1])
    model_tree = ast.parse((a.source / 'gears__model.py').read_text())
    cls = next(n for n in model_tree.body if isinstance(n, ast.ClassDef) and n.name == 'GEARS_Model')
    forward = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'forward')
    x_reads = sorted(n.lineno for n in ast.walk(forward)
                     if isinstance(n, ast.Name) and n.id == 'x' and isinstance(n.ctx, ast.Load))
    lines = (a.source / 'gears__model.py').read_text().splitlines()
    result = {'commit': manifest['commit'], 'torch': torch.__version__,
              'source_hashes_verified': True, 'loss_values_lambda_0_10': values,
              'max_gradient_difference': float((grads[1] - grads[0]).abs().max()),
              'x_reads_in_forward': [{'line': n, 'code': lines[n-1].strip()} for n in x_reads],
              'scope': 'Actual upstream loss on a tiny fixture; static forward data-flow inventory. Not a GEARS training replication.'}
    with a.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
