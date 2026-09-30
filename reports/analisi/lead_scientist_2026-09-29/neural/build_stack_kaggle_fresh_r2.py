"""Add verified Kaggle auto-expanded input support to the frozen fresh runtime."""
import ast
import hashlib
import json
from pathlib import Path

from build_stack_resume_r2 import replace_once
from build_stack_kaggle_fresh_r1 import save

HERE = Path(__file__).resolve().parent

INPUT_HELPERS = '''def locate_bundle(review, root=Path("/kaggle/input")):
    slug = review["dataset"].split("/")[-1]
    archives = [p for p in root.rglob("bundle.tar.gz") if slug in p.parts]
    expanded = [p.parent for p in root.rglob("bundle.json") if slug in p.parts]
    candidates = archives + expanded
    if len(candidates) != 1:
        raise ValueError("Cannot uniquely locate reviewed private prompt bundle")
    return candidates[0]


def verify_bundle_directory(bundle, review):
    bundle = Path(bundle).resolve()
    expected = set(review["bundle_files"])
    paths = list(bundle.rglob("*"))
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError("Expanded bundle contains links, directories or non-regular files")
    actual = {str(p.relative_to(bundle)).replace("\\\\", "/") for p in paths}
    if actual != expected:
        raise ValueError("Expanded bundle file list differs from frozen allowlist")
    if sha(bundle / "bundle.json") != review["bundle_manifest_sha256"]:
        raise ValueError("Prepared bundle manifest changed")
    manifest = json.loads((bundle / "bundle.json").read_text())
    if set(manifest["files"]) != expected - {"bundle.json"}:
        raise ValueError("Manifest file list differs from frozen allowlist")
    for name, digest in manifest["files"].items():
        if sha(bundle / name) != digest:
            raise ValueError(f"Input checksum failed: {name}")
    return manifest


def stage_bundle(source, destination, review):
    source, destination = Path(source), Path(destination)
    if source.is_dir():
        verify_bundle_directory(source, review)
        destination.mkdir()
        for name in review["bundle_files"]:
            shutil.copyfile(source / name, destination / name)
        verification = {"mode": "kaggle_expanded_files", "archive_sha256_verified": False,
            "identity": "Exact frozen bundle manifest and every allowlisted member SHA256 verified"}
    else:
        if sha(source) != review["bundle_archive_sha256"]:
            raise ValueError("Input bundle archive differs from reviewed preparation")
        extract_exact(source.read_bytes(), destination, {name: None for name in review["bundle_files"]})
        verification = {"mode": "original_archive", "archive_sha256_verified": True,
            "identity": "Original archive SHA256 and every allowlisted member SHA256 verified"}
    manifest = verify_bundle_directory(destination, review)
    verification.update(bundle_manifest_sha256=sha(destination / "bundle.json"),
                        member_count=len(review["bundle_files"]), source=str(source))
    return manifest, verification


'''


def main():
    old = HERE / "stack_kaggle_fresh_r1/stack_kaggle_fresh_r1.py"
    if hashlib.sha256(old.read_bytes()).hexdigest() != "e2d9e04d53825e1e5149e40c378d364aed463255909a6ea4e765c86c671d662e":
        raise ValueError("Frozen fresh runtime differs")
    original = old.read_text(encoding="utf-8")
    tree = ast.parse(original)
    last = tree.body[-1]
    payload, review = [ast.literal_eval(x) for x in last.value.args]
    runtime = "\n".join(original.splitlines()[:last.lineno - 1])
    start = runtime.index('        if bundle_archive is None:')
    stop = runtime.index('        scratch.mkdir(parents=True)', start)
    runtime = runtime[:start] + '        if bundle_archive is None:\n            bundle_archive = locate_bundle(review)\n' + runtime[stop:]
    start = runtime.index('        extract_exact(Path(bundle_archive).read_bytes(), bundle,')
    stop = runtime.index('        if manifest["plan_sha256"]', start)
    runtime = runtime[:start] + ('        manifest, input_verification = stage_bundle(bundle_archive, bundle, review)\n'
                                '        save(work / "input_verification.json", input_verification)\n') + runtime[stop:]
    runtime = replace_once(runtime, 'def main(payload64, review,', INPUT_HELPERS + 'def main(payload64, review,')
    review["input_support"] = "Original archive or Kaggle auto-expanded directory; exact 16-file manifest/hash verification before dependency installation and weights"
    review["expanded_input_archive_claim"] = "Original archive hash retained only as provenance; never claimed verified for expanded input"
    cell = runtime + "\n\nmain(" + repr(payload) + ", " + repr(review) + ")\n"
    ast.parse(cell)
    out = HERE / "stack_kaggle_fresh_r2"
    out.mkdir()
    (out / "stack_kaggle_fresh_r2.py").write_bytes(cell.encode())
    notebook = json.loads((HERE / "stack_kaggle_fresh_r1/stack_pilot_r1.ipynb").read_text())
    notebook["cells"][1]["source"] = cell.splitlines(keepends=True)
    save(out / "stack_pilot_r2.ipynb", notebook)
    metadata = json.loads((HERE / "stack_kaggle_fresh_r1/kernel-metadata.json").read_text())
    metadata["code_file"] = "stack_pilot_r2.ipynb"
    save(out / "kernel-metadata.json", metadata)
    save(out / "review_manifest.json", review)
    hashes = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())}
    save(out / "artifact_hashes.json", hashes)
    print(json.dumps(hashes, indent=2))


if __name__ == "__main__":
    main()
