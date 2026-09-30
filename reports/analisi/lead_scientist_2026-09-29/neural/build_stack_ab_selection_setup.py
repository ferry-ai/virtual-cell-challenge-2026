"""Freeze the reviewed AB selector and minimal original dependencies; no data."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REL = "reports/analisi/lead_scientist_2026-09-29/neural"


def main():
    out = HERE / "stack_ab_selection_setup_r1"
    if out.exists():
        raise FileExistsError(out)
    original = (HERE / "stack_setup_r1/code_snapshot.tar.gz").read_bytes()
    if hashlib.sha256(original).hexdigest() != "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698":
        raise ValueError("Original scientific helper archive changed")
    with tarfile.open(fileobj=io.BytesIO(original), mode="r:gz") as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    for name in ("select_stack_ab.py", "test_select_stack_ab.py", "stack_ab_selection_guard.py", "PROTOCOLLO_STACK_AB.md"):
        files[REL + "/" + name] = (HERE / name).read_bytes()
    out.mkdir()
    with tarfile.open(out / "code_snapshot.tar.gz", "w:gz") as tar:
        for name, content in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size, item.mode, item.mtime = len(content), 0o644, 0
            tar.addfile(item, io.BytesIO(content))
    manifest = {"claim": "Frozen code only; neither pilot score read; no real selection or job executed",
        "archive_sha256": hashlib.sha256((out / "code_snapshot.tar.gz").read_bytes()).hexdigest(),
        "files": {name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()} for name, content in sorted(files.items())},
        "tests": "10 tests passed: eligibility rows, exact tie, raw MSE, nullable/categories and exact baseline counts"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "archive_sha256": manifest["archive_sha256"],
                      "selector_sha256": manifest["files"][REL + "/select_stack_ab.py"]["sha256"]}))


if __name__ == "__main__":
    main()
