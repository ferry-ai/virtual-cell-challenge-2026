"""Which tracked repository files name a data-root group: the code and documents that would break, or need the
Drive mirror, if that group left the laptop.

Scans every tracked text file (git ls-files) for each group path of the deletion table, as written with
forward or back slashes. Live code (scripts/, src/, configs/, tests/, notebooks/) is separated from research
records in reports/ and from documents, because only live code runs without being copied first.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIVE = ("scripts/", "src/", "configs/", "tests/", "notebooks/")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--table", required=True, type=Path, help="output of eliminabili.py")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    rows = json.loads(a.table.read_text(encoding="utf-8"))["rows"]
    groups = [r["group"] for r in rows if r["status"] in ("eliminabile col via", "in attesa della prova remota")]
    files = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    texts = {}
    for f in files:
        if not f or not f.endswith((".py", ".ps1", ".sh", ".json", ".yaml", ".yml", ".md", ".ipynb", ".toml", ".txt", ".csv")):
            continue
        try:
            t = (REPO / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if len(t) < 5_000_000:
            texts[f] = t
    hits = defaultdict(lambda: {"live": [], "reports": [], "docs": []})
    for g in groups:
        pat = re.compile(re.escape(g).replace("/", r"[/\\\\]+"))
        for f, t in texts.items():
            if pat.search(t):
                kind = "live" if f.startswith(LIVE) else "reports" if f.startswith("reports/") else "docs"
                hits[g][kind].append(f)
    a.out.write_text(json.dumps(hits, indent=1, sort_keys=True), encoding="utf-8")
    for g in groups:
        h = hits.get(g, {"live": [], "reports": [], "docs": []})
        print(f"{g:55s} live {len(h['live']):3d}  reports {len(h['reports']):3d}  docs {len(h['docs']):3d}  "
              + (" ".join(h["live"][:4]) if h["live"] else ""))


if __name__ == "__main__":
    main()
