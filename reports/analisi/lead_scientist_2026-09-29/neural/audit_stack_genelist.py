"""Inspect only the 925KB pinned public gene metadata; never fetch weights."""
import argparse
import hashlib
import io
import urllib.request
from pathlib import Path

import stack_pilot as pilot


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    url = ("https://huggingface.co/arcinstitute/Stack-Large-Aligned/resolve/" + pilot.STACK_REVISION
           + "/basecount_1000per_15000max.pkl")
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(925040)
    if len(content) != 925039 or hashlib.sha256(content).hexdigest() != pilot.GENELIST_SHA:
        raise ValueError("Pinned gene metadata failed size/hash verification")
    genes = [str(g) for g in pilot.GeneListUnpickler(io.BytesIO(content)).load()]
    report = {"url": url, "bytes": len(content), "sha256": pilot.GENELIST_SHA,
              "genes": len(genes), "unique": len(set(genes)), "unique_uppercase": len(set(g.upper() for g in genes)),
              "not_uppercase": [g for g in genes if g != g.upper()], "empty": sum(not g for g in genes),
              "weight_files_downloaded": 0}
    pilot.write_json(a.out, report)
    print(report)


if __name__ == "__main__":
    main()
