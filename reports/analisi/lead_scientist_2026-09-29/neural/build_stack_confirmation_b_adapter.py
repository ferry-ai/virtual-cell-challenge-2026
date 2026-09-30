"""Prepare B profile exporter before outcomes; no final B protocol or data."""
from pathlib import Path
import hashlib
import ast
from build_stack_resume_r2 import replace_once

HERE = Path(__file__).resolve().parent


def main():
    source = (HERE / "stack_confirmation_infer.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != "a6147fd5dc0aea614de9101a14c13fd4c627fcecab27c93971b81e89429c6b30":
        raise ValueError("Original A confirmation exporter changed")
    text = source.decode()
    text = replace_once(text, 'from stack_confirmation_pack import EXPECTED',
                         'from stack_confirmation_pack import EXPECTED\nfrom stack_ab_selection_guard import validate_embedded')
    text = replace_once(text, 'PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"',
        'ORIGINAL_PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"\n'
        'B_PROTOCOL_PATH = Path(__file__).with_name("PROTOCOLLO_STACK_CONFERMA_B.md")\n'
        'INPUT_AXIS_POLICY = "own_measured_support"')
    text = replace_once(text,
        '    if sha(__file__) != bundle["inference_adapter_sha256"] or bundle["protocol_sha256"] != PROTOCOL_SHA:\n'
        '        raise ValueError("Confirmation inference adapter or protocol differs from plan")',
        '    if bundle["adapter_sha256"] != FROZEN_PILOT_SHA:\n'
        '        raise ValueError("B confirmation must preserve original A preparation")\n'
        '    if (sha(__file__) != bundle["inference_adapter_sha256"]\n'
        '            or bundle["protocol_sha256"] == ORIGINAL_PROTOCOL_SHA\n'
        '            or sha(B_PROTOCOL_PATH) != bundle["protocol_sha256"]):\n'
        '        raise ValueError("B confirmation adapter or separate final protocol differs")\n'
        '    if bundle["ab_selector_sha256"] != sha(Path(__file__).with_name("select_stack_ab.py")):\n'
        '        raise ValueError("AB selector differs from frozen selection")\n'
        '    if validate_embedded(bundle) != "B":\n'
        '        raise ValueError("Only prospectively selected B may run this exporter")')
    text = replace_once(text,
        'align_shared(selected.X, selected.var_names, model_genes, shared)',
        'align_shared(selected.X, selected.var_names, model_genes, set(selected.var_names))')
    text = text.replace('"protocol_sha256": PROTOCOL_SHA', '"protocol_sha256": bundle["protocol_sha256"]')
    text = replace_once(text,
        '        "preparation_adapter_sha256": bundle["adapter_sha256"], "protocol_sha256": bundle["protocol_sha256"],',
        '        "preparation_adapter_sha256": bundle["adapter_sha256"], "protocol_sha256": bundle["protocol_sha256"],\n'
        '        "ab_selection_sha256": bundle["ab_selection_sha256"], "input_axis_policy": INPUT_AXIS_POLICY,\n'
        '        "ab_protocol_sha256": bundle["ab_protocol_sha256"],')
    text = replace_once(text, 'Derived from the frozen pilot\'s infer function. Model inputs, calls, cache,',
        'Prepared for selected B only; no final B protocol exists by this build.\n'
        'Derived from frozen A confirmation. Each input retains its own measured\n'
        'model vocabulary. Output shared support, calls, cache,')
    ast.parse(text)
    out = HERE / "stack_confirmation_b_infer.py"
    with out.open("xb") as stream:
        stream.write(text.encode())
    print(hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
