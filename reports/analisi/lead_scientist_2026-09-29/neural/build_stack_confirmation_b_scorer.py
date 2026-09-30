"""Prepare a B confirmation scorer copy with unchanged numerical functions."""
import ast
import hashlib
from pathlib import Path
import re
from build_stack_resume_r2 import replace_once

HERE = Path(__file__).resolve().parent


def main():
    content = (HERE / "stack_confirmation_score.py").read_bytes()
    if hashlib.sha256(content).hexdigest() != "c69d41aac1aa4bc14bcb9239b39cea675430c944ea1e7c1078f659b483a6df71":
        raise ValueError("Frozen A confirmation scorer changed")
    text = content.decode()
    text = replace_once(text, 'from stack_confirmation_pack import EXPECTED',
                         'from stack_confirmation_pack import EXPECTED\nfrom stack_ab_selection_guard import validate_embedded')
    text = replace_once(text, 'PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"',
                         'ORIGINAL_PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"')
    start = text.index("def run(args):")
    text = text[:start] + re.sub(r"\bPROTOCOL_SHA\b", "protocol_sha", text[start:])
    text = replace_once(text, '    protocol = Path(__file__).with_name("PROTOCOLLO_STACK_CONFERMA.md")',
        '    protocol = Path(__file__).with_name("PROTOCOLLO_STACK_CONFERMA_B.md")\n'
        '    protocol_sha = pilot.sha(protocol)\n'
        '    if protocol_sha == ORIGINAL_PROTOCOL_SHA:\n'
        '        raise ValueError("B needs its separate final confirmation protocol")')
    text = replace_once(text, '    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))',
        '    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))\n'
        '    if bundle["ab_selector_sha256"] != pilot.sha(Path(__file__).with_name("select_stack_ab.py")):\n'
        '        raise ValueError("AB selector differs from frozen selection")\n'
        '    if validate_embedded(bundle) != "B" or bundle["adapter_sha256"] != PILOT_SHA:\n'
        '        raise ValueError("B scoring requires selected B and original preparation")')
    text = replace_once(text, '        "preparation_adapter_sha256": bundle["adapter_sha256"],',
        '        "preparation_adapter_sha256": bundle["adapter_sha256"],\n'
        '        "ab_selection_sha256": bundle["ab_selection_sha256"], "input_axis_policy": "own_measured_support",\n'
        '        "ab_protocol_sha256": bundle["ab_protocol_sha256"],')
    text = replace_once(text, '        "protocol_sha256": protocol_sha, "bootstrap_sha256": pilot.sha(args.out / "bootstrap.npz"),',
        '        "protocol_sha256": protocol_sha, "bootstrap_sha256": pilot.sha(args.out / "bootstrap.npz"),\n'
        '        "selected_variant": "B", "ab_selection_sha256": bundle["ab_selection_sha256"],')
    text = replace_once(text, 'The complete prospective protocol is PROTOCOLLO_STACK_CONFERMA.md.',
        'Prepared for selected B only. Numerical rules remain those of A.\n'
        'A separate final PROTOCOLLO_STACK_CONFERMA_B.md is required at execution.')
    ast.parse(text)
    out = HERE / "stack_confirmation_b_score.py"
    with out.open("xb") as stream:
        stream.write(text.encode())
    print(hashlib.sha256(out.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
