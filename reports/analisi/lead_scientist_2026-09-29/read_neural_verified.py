"""Read downloaded fold outputs after provenance checks and the literal-null reader fix."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_neural_runs import verify
from read_neural_sources import readout

HERE = Path(__file__).resolve().parent
ORIGINAL_SHA = "95f0f37610778d26b09806cfed5614d054c8f6fa181a6844480f5277f47c8f22"
CORRECTED_SHA = "21b936b387ec734e0aaeb4b85f982f127a465a84fb3a77dc89917190881a8243"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    files = {"original_reader": HERE / "neural_reader/r1/read_neural_sources.py", "corrected_reader": HERE / "read_neural_sources.py",
             "amendment": HERE / "EMENDAMENTO_LETTORE_NEURALE_01.md", "guard": HERE / "verify_neural_runs.py"}
    hashes = {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in files.items()}
    if hashes["original_reader"] != ORIGINAL_SHA or hashes["corrected_reader"] != CORRECTED_SHA:
        raise ValueError("Reader bytes differ from the documented mechanical correction")
    checked = verify(args.runs)
    verdict, rows = readout(args.runs)
    verdict["reader_provenance"] = hashes
    args.out.mkdir(parents=True)
    (args.out / "provenance.json").write_text(json.dumps(checked, indent=2), encoding="utf-8")
    (args.out / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    rows.to_csv(args.out / "per_target.csv", index=False)
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
