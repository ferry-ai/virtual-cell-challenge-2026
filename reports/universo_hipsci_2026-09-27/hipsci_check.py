"""Compare a kolf_effects universe's raw effects with authors' long-table LFCs.

    scripts/py.cmd reports/universo_hipsci_2026-09-27/hipsci_check.py \
        --universe UNIVERSE_DIR --authors GenomeWideScreen_LFC_byGene.tsv.gz --out NEW.csv

Read authors in chunks into a temporary disk index (first target/symbol pair wins),
then read one universe chunk at a time. Report finite shared genes, Pearson,
Spearman and the least-squares slope of author lfc on our raw, with an intercept.
No acceptance thresholds; constant vectors and fewer than two pairs yield NaN.
"""
from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from vcc2026.genes import official_axis  # noqa: E402


def metrics(x, y):
    """Pearson, Spearman and slope, leaving undefined statistics as NaN."""
    if len(x) < 2:
        return np.nan, np.nan, np.nan
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    dx, dy = x - x.mean(), y - y.mean()
    xx, yy = dx @ dx, dy @ dy
    slope = float(dx @ dy / xx) if xx > 0 else np.nan
    if xx == 0 or yy == 0:
        return np.nan, np.nan, slope
    return float(dx @ dy / np.sqrt(xx * yy)), float(np.corrcoef(rankdata(x), rankdata(y))[0, 1]), slope


def run(universe: Path, authors: Path, out: Path, *, chunksize: int = 100000, axis=None):
    if out.exists():
        raise FileExistsError(out)
    if chunksize < 1:
        raise ValueError("chunksize must be positive")
    manifest = json.loads((universe / "manifest.json").read_text(encoding="utf-8"))
    axis = np.asarray(official_axis().symbols if axis is None else axis, dtype=str)
    lookup = {g: i for i, g in enumerate(axis)}
    out.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix=".hipsci-check-", dir=out.parent) as tmp:
        with contextlib.closing(sqlite3.connect(str(Path(tmp) / "pairs.sqlite"))) as db:
            db.execute("PRAGMA cache_size=-16384")
            db.execute("CREATE TABLE pairs (target TEXT, gene TEXT, lfc REAL, PRIMARY KEY(target,gene)) WITHOUT ROWID")
            read, duplicate = 0, 0
            for frame in pd.read_csv(authors, sep="\t", chunksize=chunksize,
                                     usecols=["Target", "Expressed_Gene_Symbol", "lfc"],
                                     dtype={"Target": str, "Expressed_Gene_Symbol": str}):
                read += len(frame)
                frame["lfc"] = pd.to_numeric(frame.lfc, errors="raise")
                frame = frame[frame.Expressed_Gene_Symbol.isin(lookup) & np.isfinite(frame.lfc)]
                before = db.total_changes
                db.executemany("INSERT OR IGNORE INTO pairs VALUES (?,?,?)",
                               frame[["Target", "Expressed_Gene_Symbol", "lfc"]].itertuples(index=False, name=None))
                duplicate += len(frame) - (db.total_changes - before)
                db.commit()
            index = pd.read_csv(universe / "index.csv", keep_default_na=False)
            seen = set()
            for chunk in manifest["chunks"]:
                path = universe / chunk["file"]
                if path.parent.resolve() != universe.resolve():
                    raise ValueError("chunk path must be inside universe")
                with np.load(path, allow_pickle=False) as z:
                    targets, raw = z["targets"].astype(str), z["raw"]
                if raw.shape != (len(targets), len(axis)):
                    raise ValueError("effect shape differs from official axis")
                for i, target in enumerate(targets):
                    if target in seen:
                        raise ValueError(f"duplicate universe target {target}")
                    seen.add(target)
                    pairs = db.execute("SELECT gene,lfc FROM pairs WHERE target=?", (str(target),)).fetchall()
                    x = np.array([raw[i, lookup[g]] for g, _ in pairs], dtype=np.float64)
                    y = np.array([v for _, v in pairs], dtype=np.float64)
                    good = np.isfinite(x) & np.isfinite(y)
                    p, s, slope = metrics(x[good], y[good])
                    records.append((target, int(good.sum()), p, s, slope))
            for target in index.target:
                if target not in seen:
                    records.append((target, 0, np.nan, np.nan, np.nan))
    result = pd.DataFrame(records, columns=["target", "n_genes", "pearson", "spearman", "slope"]).sort_values("target")
    result.to_csv(out, index=False, mode="x")
    print(f"authors rows read {read}; duplicate finite axis pairs ignored {duplicate}; targets {len(result)}")
    print("medians: " + result[["pearson", "spearman", "slope"]].median().to_json())
    return result


def selftest():
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}")

    with tempfile.TemporaryDirectory(prefix="hipsci-check-selftest-") as tmp:
        root = Path(tmp)
        np.savez(root / "part.npz", targets=["T", "constant"], raw=[[1, 2, 3, np.nan], [4, 4, 4, 4]])
        (root / "manifest.json").write_text(json.dumps({"chunks": [{"file": "part.npz"}]}))
        pd.DataFrame({"target": ["T", "constant", "no_effect"]}).to_csv(root / "index.csv", index=False)
        pd.DataFrame({"Target": ["T"] * 5 + ["constant"] * 3,
                      "Expressed_Gene_Symbol": ["A", "B", "C", "D", "A", "A", "B", "C"],
                      "lfc": [5, 7, 9, 50, 999, 1, 2, 3]}).to_csv(root / "authors.tsv.gz", sep="\t", index=False)
        got = run(root, root / "authors.tsv.gz", root / "check.csv", chunksize=2,
                  axis=["A", "B", "C", "D"]).set_index("target")
        check("chunked join, finite overlap, duplicate first wins", got.loc["T", "n_genes"] == 3)
        check("Pearson, Spearman and lfc-on-raw slope", np.allclose(got.loc["T", ["pearson", "spearman", "slope"]], [1, 1, 2]))
        check("undefined and unavailable effects", got.loc["no_effect", "n_genes"] == 0
              and got.loc["constant", ["pearson", "spearman", "slope"]].isna().all())
        try:
            run(root, root / "authors.tsv.gz", root / "check.csv", axis=["A"])
            refused = False
        except FileExistsError:
            refused = True
        check("never overwrite", refused)
    print(f"selftest: {sum(results)} of {len(results)} checks passed")
    return int(not all(results))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", type=Path)
    ap.add_argument("--authors", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--chunksize", type=int, default=100000)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if any(v is None for v in (args.universe, args.authors, args.out)):
        ap.error("--universe, --authors and --out are required")
    run(args.universe, args.authors, args.out, chunksize=args.chunksize)


if __name__ == "__main__":
    main()
