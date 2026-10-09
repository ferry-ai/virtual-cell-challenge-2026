"""Derive the bounded-memory runtime revision without rewriting prior evidence."""
from pathlib import Path

HERE=Path(__file__).parent


def change(text,old,new):
    if text.count(old)!=1: raise ValueError('revision source differs: '+old[:70])
    return text.replace(old,new)


def write(name,text):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)


def main():
    train=(HERE/'ammi_train_v2.py').read_text(encoding='utf-8')
    train=change(train,'from ammi_context import ContextCorrection',
        'from ammi_context import ContextCorrection\nfrom ammi_encoder_v4 import forward_grouped, control_shape, batch')
    begin=train.index('def forward_grouped(');end=train.index('def fit(',begin)
    train=train[:begin]+train[end:]
    train=change(train,'        cells, mask = controls[context]',
        '        shape = control_shape(controls[context])\n        if not shape[0]: raise ValueError("empty controls")\n        cells, mask = batch(controls[context], 0, min(shape[0], 256))')
    train=change(train,'guard, *, fixture=False):','guard, *, fixture=False, checkpoint_callback=None):')
    train=change(train,'        model.eval()\n        with torch.no_grad(): checked = guard(model,epoch+1)',
        '        model.eval()\n        if checkpoint_callback is not None:\n            checkpoint_callback(model, epoch+1, audit)\n        with torch.no_grad(): checked = guard(model,epoch+1)')
    write('ammi_train_v4.py',train)

    guard=(HERE/'ammi_guard_v3.py').read_text(encoding='utf-8')
    guard=change(guard,'from ammi_train_v2 import forward_grouped','from ammi_encoder_v4 import forward_grouped')
    guard=change(guard,"if spec.get('review_status') != 'agreed' or not spec.get('review_pin'):",
        "if spec.get('review_status') not in ('agreed', 'existing-contract-applied') or not spec.get('review_pin'):")
    guard=change(guard,"    checked(spec['review_pin'])", "    checked(spec['review_pin'])\n    if spec['review_status'] == 'existing-contract-applied':\n        checked(spec['routing_basis'])\n        if spec.get('truth_replication_policy') != 'one table is one reference; context results never pooled as independent truths':\n            raise ValueError('reused truth cannot be counted as independent replication')")
    # Failed diagnostic interventions must leave the native checkpoint intact.
    guard=change(guard,'def predict(model, features, available, context, controls, anchor, observed):',
        'def predict(model, features, available, context, controls, anchor, observed, *, diagnostic=False):')
    old="    diagnostics = final_diagnostics(torch.from_numpy(anchor.astype(np.float64)),\n        torch.from_numpy(actual), torch.from_numpy(observed), [context]*len(anchor))"
    new="    try:\n        diagnostics = final_diagnostics(torch.from_numpy(anchor.astype(np.float64)),\n            torch.from_numpy(actual), torch.from_numpy(observed), [context]*len(anchor))\n    except ValueError as error:\n        if not diagnostic: raise\n        diagnostics = [dict(context=context, pass_=False, failure=str(error))]"
    guard=change(guard,old,new)
    write('ammi_guard_v4.py',guard)

    inputs=(HERE/'ammi_inputs_v3.py').read_text(encoding='utf-8')
    start=inputs.index('def load_anchors(')
    inputs='"""Nested and production anchor contracts; shared pinned input primitives."""\nfrom collections import Counter\nimport hashlib\nimport json\nimport numpy as np\nfrom ammi_inputs_v3 import checked, read_json, module\n\n'+inputs[start:]
    inputs=change(inputs,"    needed |= {fold['inner_query_anchor'], fold['outer_query_anchor']}",
        "    held = {fold[k] for k in ('outer','inner') if fold.get(k) is not None}\n    needed |= {fold['outer_query_anchor']}\n    if fold.get('inner_query_anchor'): needed.add(fold['inner_query_anchor'])")
    inputs=change(inputs,"not {fold['outer'], fold['inner']} <= excluded", "not held <= excluded")
    inputs=change(inputs,"        expected = {fold['outer'], fold['inner']}", "        expected = set(held)")
    inputs=change(inputs,"    return result\n\n\ndef training_data", "    if fold.get('mode') == 'production':\n        if held or set(requested[fold['outer_query_anchor']]['excluded_lineages']):\n            raise ValueError('production query requires unchanged full T0')\n    return result\n\n\ndef training_data")
    old="    if (view.get('schema') != 'external-ridge-chunks/1' or view['modality'] != 'CRISPRi'\n            or view['regime'] != 'C' or fold['no_final_refit'] is not True\n            or fold['outer'] not in view['excluded_contexts']):\n        raise ValueError('frozen C response view required')"
    new="    held = {fold[k] for k in ('outer','inner') if fold.get(k) is not None}\n    production = fold.get('mode') == 'production'\n    if view.get('schema') != 'external-ridge-chunks/1' or view['modality'] != 'CRISPRi':\n        raise ValueError('frozen CRISPRi response view required')\n    if production:\n        if held or view['regime'] != 'production' or view['excluded_contexts'] or view['excluded_targets']:\n            raise ValueError('production view must declare all admitted rows and no held fold')\n    elif (view['regime'] != 'C' or fold['no_final_refit'] is not True\n          or fold['outer'] not in view['excluded_contexts']):\n        raise ValueError('frozen C response view required')"
    inputs=change(inputs,old,new)
    inputs=change(inputs,"if info['lineage'] in {fold['outer'], fold['inner']}:", "if info['lineage'] in held:")
    write('ammi_inputs_v4.py',inputs)


if __name__=='__main__':main()
