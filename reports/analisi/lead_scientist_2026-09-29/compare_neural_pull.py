"""Compare downloaded notebook code/payload to the approved r1 without executing it."""
import argparse
import ast
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def notebook(path):
    nb = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            source = cell["source"]
            cells.append("".join(source) if isinstance(source, list) else source)
    if len(cells) != 1:
        raise ValueError("The frozen notebook has exactly one code cell")
    tree = ast.parse(cells[0])
    call = tree.body[-1]
    if not isinstance(call, ast.Expr) or not isinstance(call.value, ast.Call) or not isinstance(call.value.func, ast.Name) or call.value.func.id != "main":
        raise ValueError("The final expression is not the reviewed main invocation")
    payload64, review = [ast.literal_eval(arg) for arg in call.value.args]
    payload = base64.b64decode(payload64, validate=True)
    members = []
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                raise ValueError("Nonregular embedded member")
            content = archive.extractfile(member).read()
            members.append({"path": member.name, "bytes": len(content), "sha256": digest(content)})
    return {"file_sha256": digest(path.read_bytes()), "code_cell_sha256": digest(cells[0].encode()),
            "payload_sha256": digest(payload), "payload_bytes": len(payload), "members": members,
            "review": review}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen", type=Path, required=True)
    p.add_argument("--pulled", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    frozen, pulled = notebook(args.frozen), notebook(args.pulled)
    comparisons = {key: frozen[key] == pulled[key] for key in
                   ("code_cell_sha256", "payload_sha256", "payload_bytes", "members", "review")}
    result = {"observed_utc": datetime.now(timezone.utc).isoformat(), "comparisons": comparisons,
              "identical_code_and_payload": all(comparisons.values()), "frozen": frozen, "pulled": pulled,
              "limitation": "Verifies the code stored in remote latest, not training progress or CUDA execution."}
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: result[k] for k in ("observed_utc", "comparisons", "identical_code_and_payload", "limitation")}, indent=2))
    if not result["identical_code_and_payload"]:
        raise ValueError("Remote latest differs from frozen r1")


if __name__ == "__main__":
    main()
