"""Fetch only the exact archived bench inputs needed for a complete local/remote preflight."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FETCH = REPO / "reports/modelli/rete_ancorata_v4_2026-10-03/fetch_outputs.py"
DIAG = REPO / "reports/modelli/diagnosi_t30_2026-10-04"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-bytes", type=int, default=1_073_741_824)
    a = p.parse_args()
    jobs = {}
    records = [json.loads(s) for s in (DIAG / "lancio_diag_r1.jsonl").read_text().splitlines()]
    for r in records:
        if not r["accepted"]:
            continue
        prior = json.loads((DIAG / f"esito/diag_{r['held'].lower()}_r1/run.json").read_text())["arguments"]
        patterns = [["train/eval_groups.json", "train/eval_observed.npz", "train/ibrido/eval_shifts.npz",
                     "train/ibrido_mean/eval_shifts.npz", "train/ancora_sola/eval_shifts.npz"],
                    ["prepass/splits.json"],
                    [Path(prior["anchors_manifest"]).parent.name + "/manifest.json"],
                    [Path(prior["real"]).name, Path(prior["targets"]).name]]
        for src, pats in zip(r["kernel_sources"], patterns):
            jobs.setdefault(src, set()).update(pats)
    def fetch(item):
        src, pats = item
        owner, slug = src.split('/')
        dest = a.out / owner / slug
        if dest.exists() and not (dest / "fetch_receipt.json").exists():
            dest = dest.with_name(dest.name + "-retry1")
        if (dest / "fetch_receipt.json").exists():
            rec = json.loads((dest / "fetch_receipt.json").read_text())
            if set(pats) <= set(rec["fetched"]):
                return src + ": already fetched"
            raise ValueError(f"incomplete cached input: {dest}")
        config = Path.home() / (".kaggle" if owner == "davidmaisterx" else ".kaggle-davideferrante11")
        args = [sys.executable, str(FETCH), "--config-dir", str(config), "--owner", owner,
                "--slug", slug, "--out", str(dest), "--max-bytes", str(a.max_bytes)]
        for pat in sorted(pats):
            args += ["--pattern", pat]
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(src + ": " + result.stderr[-600:])
        return src + ": " + result.stdout.strip()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for message in pool.map(fetch, jobs.items()):
            print(message, flush=True)


if __name__ == "__main__":
    main()
