"""Create a separately registered input-axis variant from immutable pilot A."""
from pathlib import Path
import hashlib

HERE = Path(__file__).resolve().parent
ORIGINAL = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
PROTOCOL = "181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected unique replacement: {old[:80]}")
    return text.replace(old, new)


def main():
    original = HERE / "stack_pilot.py"
    if hashlib.sha256(original.read_bytes()).hexdigest() != ORIGINAL:
        raise ValueError("Frozen pilot A changed")
    if hashlib.sha256((HERE / "PROTOCOLLO_STACK_AB.md").read_bytes()).hexdigest() != PROTOCOL:
        raise ValueError("Prospective AB protocol changed")
    source = original.read_text(encoding="utf-8")
    source = replace_once(source, 'N_OUTPUT = 400', 'N_OUTPUT = 400\nPREPARATION_ADAPTER_SHA = "' + ORIGINAL + '"\nAB_PROTOCOL_SHA = "' + PROTOCOL + '"\nINPUT_AXIS_POLICY = "own_measured_support"')
    marker = '    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))'
    source = replace_once(source, marker, marker + '\n    if bundle.get("adapter_sha256") != PREPARATION_ADAPTER_SHA:\n        raise ValueError("B requires the immutable preparation from pilot A")\n    if sha(HERE / "PROTOCOLLO_STACK_AB.md") != AB_PROTOCOL_SHA:\n        raise ValueError("Prospective AB protocol changed")')
    source = replace_once(source, 'align_shared(selected.X, selected.var_names, model_genes, shared)', 'align_shared(selected.X, selected.var_names, model_genes, set(selected.var_names))')
    source = replace_once(source, '"bundle_sha256": sha(args.bundle / "bundle.json"), "adapter_sha256": sha(__file__),', '"bundle_sha256": sha(args.bundle / "bundle.json"), "adapter_sha256": sha(__file__),\n        "preparation_adapter_sha256": PREPARATION_ADAPTER_SHA,\n        "ab_protocol_sha256": AB_PROTOCOL_SHA, "input_axis_policy": INPUT_AXIS_POLICY,')
    scorer = (HERE / "score_stack_pilot.py").read_text(encoding="utf-8")
    scorer = replace_once(scorer, 'import stack_pilot as pilot', 'import stack_input_axis_pilot as pilot')
    scorer = replace_once(scorer, '"adapter_sha256": bundle["adapter_sha256"],', '"adapter_sha256": pilot.sha(pilot.__file__),\n                "preparation_adapter_sha256": pilot.PREPARATION_ADAPTER_SHA,\n                "ab_protocol_sha256": pilot.AB_PROTOCOL_SHA, "input_axis_policy": pilot.INPUT_AXIS_POLICY,')
    marker = 'def verify_inference_provenance(infer, bundle, bundle_sha):'
    scorer = replace_once(scorer, marker, marker + '\n    if bundle.get("adapter_sha256") != pilot.PREPARATION_ADAPTER_SHA:\n        raise ValueError("Bundle preparation is not frozen pilot A")')
    outputs = [("stack_input_axis_pilot.py", source), ("score_stack_input_axis.py", scorer)]
    if any((HERE / name).exists() for name, _ in outputs):
        raise FileExistsError("Variant B already created")
    for name, content in outputs:
        with (HERE / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        print(name, hashlib.sha256((HERE / name).read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
