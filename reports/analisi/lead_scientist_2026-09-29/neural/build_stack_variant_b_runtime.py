"""Prepare, never start, an independently reviewed Stack input-support variant.

The original pilot bundle, model and runtime fixes remain frozen. New adapter,
protocol, scorer and tests are accepted only with explicit reviewed byte hashes.
"""
from __future__ import annotations
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile

from build_stack_resume_r2 import replace_once
from build_stack_kaggle_fresh_r1 import save

HERE = Path(__file__).resolve().parent
REL = "reports/analisi/lead_scientist_2026-09-29/neural"
RUNTIME_SHA = "c12d18225af1d22ad44abe11c670fa64f61f8397a646b4b3cef551ce62c6441c"


def sha(content):
    return hashlib.sha256(content).hexdigest()


def read_checked(path, expected):
    if Path(path).parent.resolve() != HERE:
        raise ValueError("Variant code must be a named file in the reviewed neural folder")
    content = Path(path).read_bytes()
    if sha(content) != expected:
        raise ValueError("Reviewed variant file changed: " + Path(path).name)
    return content


def build(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    original_path = HERE / "stack_kaggle_fresh_r2/stack_kaggle_fresh_r2.py"
    source_bytes = original_path.read_bytes()
    if sha(source_bytes) != RUNTIME_SHA:
        raise ValueError("Reviewed fresh runtime changed")
    original = source_bytes.decode()
    last = ast.parse(original).body[-1]
    payload64, review = [ast.literal_eval(a) for a in last.value.args]
    old_payload = base64.b64decode(payload64, validate=True)
    if sha(old_payload) != review["code_archive_sha256"]:
        raise ValueError("Original scientific archive changed")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(old_payload), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                raise ValueError("Unexpected original archive member")
            files[m.name] = tar.extractfile(m).read()
    additions = [(args.adapter, args.adapter_sha256), (args.protocol, args.protocol_sha256),
                 (args.scorer, args.scorer_sha256), (args.test, args.test_sha256)]
    if len({Path(p).name for p, _ in additions}) != len(additions):
        raise ValueError("Variant file names must be distinct")
    for path, expected in additions:
        name = REL + "/" + Path(path).name
        if name in files:
            raise ValueError("Variant must not replace an original frozen file")
        files[name] = read_checked(path, expected)
    runtime = "\n".join(original.splitlines()[:last.lineno - 1])
    runtime = replace_once(runtime, '"/kaggle/working/lead_stack_r1"', '"/kaggle/working/lead_stack_variant_b_r1"')
    runtime = replace_once(runtime, '"/tmp/lead_stack_scratch_r1"', '"/tmp/lead_stack_variant_b_scratch_r1"')
    subcommand = ', "infer"' if args.adapter_cli == "infer-subcommand" else ""
    runtime = replace_once(runtime, 'report / "stack_pilot.py", "infer", "--bundle", bundle,',
                           'report / ' + repr(args.adapter.name) + subcommand + ', "--bundle", bundle,')
    runtime = replace_once(runtime, '        env = os.environ.copy()',
        '        for name, expected in review["variant_files"].items():\n'
        '            if sha(report / name) != expected:\n'
        '                raise ValueError("Variant code/protocol changed: " + name)\n'
        '        save(work / "variant_registration.json", {"variant": "B", "files": review["variant_files"],\n'
        '             "bundle_manifest_sha256": review["bundle_manifest_sha256"],\n'
        '             "change": "Input uses each context own measured response support; output shared support unchanged"})\n'
        '        env = os.environ.copy()')
    runtime = replace_once(runtime,
        '        run([python, "-c", "from stack.model_loading import load_model_from_checkpoint; "',
        '        run([python, report / ' + repr(args.test.name) + '], work / "variant_contract_tests.log", cwd=code, env=env)\n'
        '        run([python, "-c", "from stack.model_loading import load_model_from_checkpoint; "')
    runtime = replace_once(runtime,
        '"claim": "12 development targets, no clean pretraining holdout claim, no VCC submission"',
        '"claim": "Prospectively registered B input-support variant on same12 development targets; no clean pretraining holdout; no VCC submission"')
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as tar:
        for name, content in sorted(files.items()):
            m = tarfile.TarInfo(name)
            m.size, m.mode, m.mtime = len(content), 0o644, 0
            tar.addfile(m, io.BytesIO(content))
    payload = archive_bytes.getvalue()
    review.update(kernel=args.kernel, code_archive_sha256=sha(payload),
        code_files=[{"path": k, "bytes": len(v), "sha256": sha(v)} for k, v in sorted(files.items())],
        variant="B", variant_files={Path(p).name: digest for p, digest in additions},
        frozen_variant_a_runtime_sha256=RUNTIME_SHA,
        variant_scope="Only model input support changes; same12targets, original prompts, fixed checkpoint, output support/fallback/final RNG unchanged",
        execution_status="Prepared for concrete review only; builder does not upload or launch inference")
    cell = runtime + "\n\nmain(" + repr(base64.b64encode(payload).decode()) + ", " + repr(review) + ")\n"
    ast.parse(cell)
    args.out.mkdir(parents=True)
    (args.out / "stack_variant_b_r1.py").write_bytes(cell.encode())
    notebook = json.loads((HERE / "stack_kaggle_fresh_r2/stack_pilot_r2.ipynb").read_text())
    notebook["cells"][0]["source"] = ["# Stack B: supporto di input per contesto\n",
        "Stessi dodici target e dati pubblici del pilot A. Variante preregistrata, nessun dato A/B/C o scoring.\n"]
    notebook["cells"][1]["source"] = cell.splitlines(keepends=True)
    save(args.out / "stack_variant_b_r1.ipynb", notebook)
    metadata = json.loads((HERE / "stack_kaggle_fresh_r2/kernel-metadata.json").read_text())
    metadata.update(id=args.kernel, title="VCC Stack Variant B R1", code_file="stack_variant_b_r1.ipynb")
    save(args.out / "kernel-metadata.json", metadata)
    save(args.out / "review_manifest.json", review)
    (args.out / "code_snapshot.tar.gz").write_bytes(payload)
    save(args.out / "artifact_hashes.json", {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(args.out.iterdir())})
    return review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("adapter", "protocol", "scorer", "test", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("adapter", "protocol", "scorer", "test"):
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--kernel", default="davidmaisterx/vcc-stack-variant-b-r1")
    parser.add_argument("--adapter-cli", required=True, choices=("direct", "infer-subcommand"))
    args = parser.parse_args()
    review = build(args)
    print(json.dumps({"out": str(args.out), "variant": "B", "bundle_sha256": review["bundle_manifest_sha256"], "archive_sha256": review["code_archive_sha256"]}))


if __name__ == "__main__":
    main()
